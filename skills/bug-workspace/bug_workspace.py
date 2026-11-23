#!/usr/bin/env python3
"""
Bug Workspace — 工作区创建 & 附件下载 & 编排模块 (v3.0)
复刻原 UI 工具 fetch_buginfo_by_API_UI.py 的核心流程：
1. 根据Bug信息生成文件夹名
2. 创建本地文件夹 + Bug Z 模板复制
3. UNC 优先下载附件（rayfile FTP fallback）
4. 创建 .url 快捷方式
5. 生成 bug_summary.txt + {alias}_{concise_title}.md 分析报告
6. 路径历史管理 + 快速打开
7. 结构化评论解析 + 日志目录列表 (merged from bug-logs)

v3.0 变更:
  - 合并 bug-logs 全部功能（下载、结构化解析、日志目录列表）
  - download_mode 参数替代 download+refresh: "full" | "incremental" | "skip"
  - UNC 优先下载（Comment #0 提取 UNC 路径 → shutil.copytree/copy_missing）
  - rayfile FTP 作为 UNC 不可达时的 fallback
  - bug-logs skill 已废弃
"""

import ftplib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import zipfile
from datetime import datetime

# 配置路径 — 以 bug-core 的配置为单一数据源
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.dirname(SCRIPT_DIR)
BUG_CORE_CONFIG = os.path.join(SKILLS_DIR, "bug-core", "config", "bugzilla_instances.json")
if not os.path.exists(BUG_CORE_CONFIG):
    BUG_CORE_CONFIG = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")),
        ".claude", "skills", "bug-core", "config", "bugzilla_instances.json")
CONFIG_PATH = BUG_CORE_CONFIG
PATHS_CONFIG = os.path.join(SCRIPT_DIR, "config", "paths.json")

# 非法文件名字符
INVALID_CHARS = r'[<>:"/\\|?*\n\r\t]'

# 离线模式标记
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "0") == "1"


def load_config() -> dict:
    """加载Bugzilla实例配置"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 跨 Skill 导入：从 bug-core 获取工具函数
# ============================================================

def _import_bug_core_format():
    """三级降级加载 bug-core 的 format_bug_summary"""
    try:
        from bug_core import format_bug_summary, clean_folder_name
        return format_bug_summary, clean_folder_name
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _core = os.path.join(_skills, "bug-core")
        if _core not in _sys.path:
            _sys.path.insert(0, _core)
        from bug_core import format_bug_summary as _fmt, clean_folder_name as _cln
        return _fmt, _cln


def _import_bug_core_fetch():
    """三级降级加载 bug-core 的 fetch_bug_rest"""
    try:
        from bug_core import fetch_bug_rest
        return fetch_bug_rest
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _core = os.path.join(_skills, "bug-core")
        if _core not in _sys.path:
            _sys.path.insert(0, _core)
        from bug_core import fetch_bug_rest as _fetch
        return _fetch


def _import_get_instance_config():
    """三级降级加载 get_instance_config"""
    try:
        from bug_core import get_instance_config as gic
        return gic
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _core = os.path.join(_skills, "bug-core")
        if _core not in _sys.path:
            _sys.path.insert(0, _core)
        from bug_core import get_instance_config as _gic
        return _gic


def _import_bug_core_report():
    """三级降级加载 generate_report_filename_from_bug。
    优先 common.report_utils → bug_core → fallback
    """
    import sys as _sys
    _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Level 1: common.report_utils（单一数据源）
    try:
        from common.report_utils import generate_report_filename_from_bug
        return generate_report_filename_from_bug
    except ImportError:
        pass

    # Level 2: bug_core（向后兼容）
    try:
        from bug_core import generate_report_filename_from_bug
        return generate_report_filename_from_bug
    except ImportError:
        pass

    # Level 3: sys.path 注入后从 bug-core 加载
    _core = os.path.join(_skills, "bug-core")
    if _core not in _sys.path:
        _sys.path.insert(0, _core)
    from bug_core import generate_report_filename_from_bug as _gen
    return _gen


def get_instance_config(instance_name: str = None) -> tuple:
    """获取指定实例配置 (name, config_dict)，优先委托给 bug-core"""
    try:
        gic = _import_get_instance_config()
        return gic(instance_name)
    except Exception:
        config = load_config()
        if instance_name is None:
            instance_name = config.get("default_instance", "kernel")
        instances = config.get("instances", {})
        if instance_name not in instances:
            raise ValueError(f"未知实例: {instance_name}, 可用: {list(instances.keys())}")
        return instance_name, instances[instance_name]


# ============================================================
# 结构化评论解析 (merged from bug-logs)
# ============================================================

def parse_unisoc_structured_fields(text: str) -> dict:
    """解析unisoc Bugzilla结构化Bug报告格式（Comment #0的19字段模板）。

    返回dict包含:
        - header: {severity_desc, external_conditions, probability, ...}
        - fields: {N: {name, value}} 编号字段
        - log_name: str, log_path: str, log_servers: dict
        - log_type: str, occur_time: str, version_path: str
        - has_structured_format: bool
    """
    result = {
        "has_structured_format": False,
        "header": {},
        "fields": {},
        "log_name": "",
        "log_path": "",
        "log_servers": {},
        "log_type": "",
        "occur_time": "",
        "version_path": "",
    }

    # Header field patterns (Chinese labels with colons, before first [N.])
    HEADER_FIELDS = {
        "严重级别": "severity_desc",
        "外部条件": "external_conditions",
        "出现概率": "probability",
        "用户操作类型": "user_operation_type",
        "业务功能类型": "business_function_type",
        "故障影响": "fault_impact",
        "恢复性": "recoverability",
    }

    # Parse header fields
    for cn_label, key in HEADER_FIELDS.items():
        m = re.search(rf'{cn_label}[：:]\s*(.*?)(?:\n|$)', text)
        if m:
            result["header"][key] = m.group(1).strip()

    # Parse numbered fields: [N.Field Name]: value
    field_pattern = re.compile(r'\[(\d+)\.([^\]]+)\]\s*:?\s*([\s\S]*?)(?=\[\d+\.|\Z)')
    for m in field_pattern.finditer(text):
        field_num = m.group(1)
        field_name = m.group(2).strip()
        field_value = m.group(3).strip()
        result["fields"][field_num] = {"name": field_name, "value": field_value}

    if not result["fields"]:
        return result

    result["has_structured_format"] = True

    # Extract [14.Logpath] sub-fields
    logpath = result["fields"].get("14", {}).get("value", "")
    if logpath:
        # LogName (may be empty — no value after colon)
        m = re.search(r'LogName[^\S\n]*:[^\S\n]*(.*?)(?:\n|$)', logpath)
        if m and m.group(1).strip():
            result["log_name"] = m.group(1).strip()

        # LogPath (UNC path on line(s) until next section key)
        m = re.search(r'LogPath[^\S\n]*:[^\S\n]*((?:[^\n]+(?:\n(?!(?:The Path|LogName|External|Internal|UNISOC|DES|\[\d+\.))[^\n]*)*))', logpath)
        if m:
            result["log_path"] = m.group(1).strip().replace('\n', '').replace('\r', '')

        # Log Servers
        servers = {}
        ext_m = re.search(r'External[^\S\n]*:[^\S\n]*([^\n]+)', logpath)
        if ext_m:
            servers["external"] = ext_m.group(1).strip()
        int_m = re.search(r'Internal[^\S\n]*:[^\S\n]*([^\n]+)', logpath)
        if int_m:
            servers["internal"] = int_m.group(1).strip()
        ftp_m = re.search(r'(?:UNISOC\s*)?FTP[^\S\n]*:[^\S\n]*([^\n]+)', logpath)
        if ftp_m:
            servers["ftp"] = ftp_m.group(1).strip()
        des_m = re.search(r'DES[^\S\n]*:[^\S\n]*([^\n]+)', logpath)
        if des_m:
            servers["des"] = des_m.group(1).strip()
        result["log_servers"] = servers

    # Extract [15.Logtype]
    logtype_field = result["fields"].get("15", {}).get("value", "")
    if logtype_field:
        result["log_type"] = logtype_field.strip()

    # Extract [16.Occur Time]
    occur_field = result["fields"].get("16", {}).get("value", "")
    if occur_field:
        result["occur_time"] = occur_field.strip()

    # Extract [19.Version Path]
    ver_field = result["fields"].get("19", {}).get("value", "")
    if ver_field:
        result["version_path"] = ver_field.strip()

    return result


# ============================================================
# 日志目录列表 — 双通道 (UNC + FTP) (merged from bug-logs)
# ============================================================

def _try_unc_listdir(unc_path: str) -> dict:
    """尝试通过Windows UNC路径列出目录内容。"""
    if platform.system() != "Windows":
        return {"accessible": False, "error": "UNC listing only supported on Windows"}

    try:
        items = []
        with os.scandir(unc_path) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                except OSError:
                    stat = None
                items.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": stat.st_size if stat and entry.is_file() else 0,
                    "modified": "",
                })
        return {
            "accessible": True,
            "method": "unc",
            "entries": sorted(items, key=lambda x: (x["type"], x["name"])),
        }
    except OSError as e:
        return {"accessible": False, "method": "unc", "error": str(e)}


def _try_ftp_listdir(ftp_url_or_path: str, config: dict) -> dict:
    """尝试通过FTP列出目录内容。"""
    host = config.get("ftp_host", "")
    port = int(config.get("ftp_port", 21))
    user = config.get("ftp_user", "anonymous")
    password = config.get("ftp_password", "")
    use_ssl = config.get("ftp_use_ssl", False)

    if not host:
        return {"accessible": False, "method": "ftp", "error": "No FTP host configured"}

    # Convert UNC path to FTP path
    ftp_path = ftp_url_or_path
    if ftp_path.startswith("ftp://"):
        parsed = ftp_path.replace("ftp://", "")
        if "/" in parsed:
            ftp_path = "/" + parsed.split("/", 1)[1]
        else:
            ftp_path = "/"
    elif ftp_path.startswith("\\\\"):
        parts = ftp_path.replace("\\\\", "").split("\\", 1)
        if len(parts) > 1:
            ftp_path = "/" + parts[1].replace("\\", "/")
        else:
            ftp_path = "/"

    ftp_path = ftp_path.rstrip("/")
    if not ftp_path:
        ftp_path = "/"

    try:
        if use_ssl:
            ctx = ssl.create_default_context()
            ftp = ftplib.FTP_TLS(context=ctx, timeout=15)
        else:
            ftp = ftplib.FTP(timeout=15)

        ftp.connect(host, port)
        ftp.login(user, password)
        if use_ssl:
            ftp.prot_p()

        items = []
        ftp.cwd(ftp_path)

        def _parse_line(line):
            """Parse FTP LIST line into name/type/size."""
            parts = line.split()
            if len(parts) < 4:
                return None
            perms = parts[0]
            name = parts[-1]
            if name in (".", ".."):
                return None
            is_dir = perms.startswith("d") or "<DIR>" in line
            try:
                size = int(parts[4]) if not is_dir and len(parts) > 4 and perms[0] != "d" else 0
            except (ValueError, IndexError):
                size = 0
            return {"name": name, "type": "dir" if is_dir else "file", "size": size, "modified": ""}

        for line in ftp.dir():
            parsed = _parse_line(line)
            if parsed:
                items.append(parsed)

        ftp.quit()
        return {
            "accessible": True,
            "method": "ftp",
            "entries": sorted(items, key=lambda x: (x["type"], x["name"])),
        }
    except Exception as e:
        return {"accessible": False, "method": "ftp", "error": str(e)}


def list_log_directory(path: str, config: dict = None) -> dict:
    """列出日志目录内容，依次尝试UNC和FTP方式。

    Args:
        path: UNC路径 (\\\\server\\share\\...) 或 ftp:// URL
        config: 实例配置dict（含FTP凭证），可选

    Returns:
        {
            "path": str,
            "method": "unc" | "ftp" | "none",
            "accessible": bool,
            "entries": [...],
            "files": [str, ...],
            "subdirs": [str, ...],
            "error": str or None,
        }
    """
    result = {
        "path": path,
        "method": "none",
        "accessible": False,
        "entries": [],
        "files": [],
        "subdirs": [],
        "error": None,
    }

    if not path:
        result["error"] = "No path provided"
        return result

    # Method 1: Try UNC (Windows direct access)
    if path.startswith("\\\\"):
        unc_result = _try_unc_listdir(path)
        if unc_result["accessible"]:
            result.update(unc_result)
            result["files"] = [e["name"] for e in unc_result["entries"] if e["type"] == "file"]
            result["subdirs"] = [e["name"] for e in unc_result["entries"] if e["type"] == "dir"]
            return result

    # Method 2: Try FTP
    if config and config.get("ftp_host"):
        ftp_result = _try_ftp_listdir(path, config)
        if ftp_result["accessible"]:
            result.update(ftp_result)
            result["files"] = [e["name"] for e in ftp_result["entries"] if e["type"] == "file"]
            result["subdirs"] = [e["name"] for e in ftp_result["entries"] if e["type"] == "dir"]
            return result
        # If both failed, return the errors
        if isinstance(path, str) and path.startswith("\\\\"):
            result["error"] = f"UNC: {unc_result.get('error', 'N/A')}; FTP: {ftp_result.get('error', 'N/A')}"
        else:
            result["error"] = ftp_result.get("error", "FTP listing failed")
        return result

    # No config, UNC-only path
    if path.startswith("\\\\"):
        unc_result = _try_unc_listdir(path)
        if unc_result["accessible"]:
            result.update(unc_result)
            result["files"] = [e["name"] for e in unc_result["entries"] if e["type"] == "file"]
            result["subdirs"] = [e["name"] for e in unc_result["entries"] if e["type"] == "dir"]
        else:
            result["error"] = f"UNC: {unc_result.get('error', 'N/A')}"
    else:
        result["error"] = "Unsupported path scheme (not UNC or FTP)"

    return result


# ============================================================
# 组合查询：Bug信息 + 结构化解析 + 日志目录 (merged from bug-logs)
# ============================================================

def fetch_bug_with_logs(bug_id: str, instance: str = None) -> dict:
    """获取Bug完整信息（含结构化评论解析和日志目录列表）。

    对unisoc类型的Bug，解析Comment #0中的结构化Bug报告字段，
    列出LogPath目录下的日志文件，帮助AI根据文件名/修改时间识别相关日志。

    Returns:
        标准的fetch_bug_rest()结果，另增加:
            - "structured_fields": parse_unisoc_structured_fields()结果 或 {}
            - "log_directory": list_log_directory()结果 或 None
    """
    fetch_bug_rest = _import_bug_core_fetch()

    result = fetch_bug_rest(bug_id, instance=instance)

    if "error" in result:
        return result

    result["structured_fields"] = {}
    result["log_directory"] = None

    # Get instance config for FTP credentials
    try:
        inst_name, inst_config = get_instance_config(instance)
    except (ValueError, KeyError):
        inst_config = {}

    # Fetch comments to find structured bug report
    import requests
    rest_url = inst_config.get("rest_url", "")
    api_key = inst_config.get("api_key", "")

    if rest_url:
        try:
            params = {"include_fields": "_all"} if not api_key else {"api_key": api_key}
            comment_resp = requests.get(
                f"{rest_url}/bug/{bug_id}/comment",
                params=params,
                headers={"Accept": "application/json"},
                timeout=15
            )
            comment_resp.raise_for_status()
            comment_data = comment_resp.json()
            comments = []
            for bc in comment_data.get("bugs", {}).values():
                comments = bc.get("comments", [])
                break
        except Exception:
            comments = []
    else:
        comments = []

    # Parse structured fields from first comment
    if comments:
        first_text = comments[0].get("text", "")
        structured = parse_unisoc_structured_fields(first_text)
        result["structured_fields"] = structured

        # If LogPath found, try to list it
        log_path = structured.get("log_path", "")
        if log_path and structured.get("has_structured_format"):
            dir_result = list_log_directory(log_path, config=inst_config)
            result["log_directory"] = dir_result

    return result


# ============================================================
# UNC 路径提取 — 从 Comment #0 提取系统生成的 UNC 路径
# ============================================================

# 通用 UNC 路径正则：\\server\share\path...（不硬编码 IP/服务器名）
UNC_PATH_RE = re.compile(r'\\\\[\w.-]+(?:\\[^\s\[\]()]+)+')

# unisupport 关键词（辅助确认 Comment #0 是系统生成的）
UNISUPPORT_KEYWORDS = ['unisupport', 'uni support', 'UniSupport']


def _extract_unc_from_comment0(bug_id: str, instance_config: dict) -> str:
    """从 Comment #0 提取 UNC 路径（系统生成的 unisupport 评论）。

    仅提取 Comment #0 中的 UNC 路径，以 'unisupport' 关键词作为辅助信号。
    通用 UNC 正则: \\\\[\\w.-]+(?:\\\\[^\\s\\[\\]()]+)+

    Returns:
        UNC 路径字符串，未找到返回空字符串。
    """
    rest_url = instance_config.get("rest_url", "")
    api_key = instance_config.get("api_key", "")

    if not rest_url:
        return ""

    try:
        import requests
        params = {"include_fields": "_all"} if not api_key else {"api_key": api_key}
        resp = requests.get(
            f"{rest_url}/bug/{bug_id}/comment",
            params=params,
            headers={"Accept": "application/json"},
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        comments = []
        for bc in data.get("bugs", {}).values():
            comments = bc.get("comments", [])
            break

        if not comments:
            return ""

        # 仅检查 Comment #0
        comment0_text = comments[0].get("text", "")

        # 辅助信号：unisupport 关键词
        has_unisupport = any(kw.lower() in comment0_text.lower() for kw in UNISUPPORT_KEYWORDS)

        # 提取 UNC 路径
        matches = UNC_PATH_RE.findall(comment0_text)
        for m in matches:
            # 清理尾部标点
            m = m.rstrip('.,;:!?）)')
            # 排除明显不是文件路径的模式（如 registry 路径）
            if any(x in m.lower() for x in ['hkey_', 'registry', '\\\\warehouse']):
                continue
            # 如果有 unisupport 关键词，直接返回第一个匹配
            if has_unisupport:
                return m
            # 否则返回第一个看起来像文件共享的路径
            if '\\' in m.replace('\\\\', '', 1):
                return m

        return ""

    except Exception:
        return ""


# ============================================================
# Bug 附件下载 — 智能识别 + UNC 优先 + rayfile fallback
# ============================================================

def detect_attachment_type(bug_id: str, instance: str = None) -> dict:
    """智能检测 Bug 的附件类型。

    检测逻辑（按优先级）：
    1. Type "unc": Comment #0 含 unisupport UNC 路径（系统生成）
    2. Type "unc": Comment #0 含 [14.Logpath] 结构化字段 + 有效 UNC 路径
    3. Type "rayfile": Comment #0 含 "下载附件:" 开头的 FTP/rayfile 路径
    4. Type "none": 无法识别任何附件类型

    Returns:
        {
            "type": "unc" | "rayfile" | "none",
            "source_path": str,       # UNC 路径 或 FTP 路径
            "bug_info": dict,         # Bug 基本信息
            "instance_config": dict,  # 实例配置（含 FTP 凭证）
            "error": str or None,
        }
    """
    result = {
        "type": "none",
        "source_path": "",
        "bug_info": {},
        "instance_config": {},
        "error": None,
    }

    try:
        # 获取 Bug 完整信息（含结构化解析和评论）
        bug_data = fetch_bug_with_logs(bug_id, instance=instance)
        if "error" in bug_data:
            result["error"] = f"Failed to fetch bug: {bug_data['error']}"
            return result

        # 获取实例配置
        try:
            inst_name, inst_config = get_instance_config(instance)
            result["instance_config"] = inst_config
        except (ValueError, KeyError):
            inst_config = {}

        # 提取 Bug 基本信息
        result["bug_info"] = {
            "bug_id": bug_data.get("bug_id", bug_id),
            "summary": bug_data.get("summary", ""),
            "status": bug_data.get("status", ""),
            "product": bug_data.get("product", ""),
            "component": bug_data.get("component", ""),
            "url": bug_data.get("url", ""),
        }

        # 检测优先级 1: Comment #0 unisupport UNC 路径（系统生成）
        unc_from_comment0 = _extract_unc_from_comment0(bug_id, inst_config)
        if unc_from_comment0:
            result["type"] = "unc"
            result["source_path"] = unc_from_comment0
            return result

        # 检测优先级 2: UNC 路径（结构化评论 [14.Logpath]）
        structured = bug_data.get("structured_fields", {})
        if structured.get("has_structured_format"):
            log_path = structured.get("log_path", "")
            if log_path and log_path.startswith("\\\\"):
                result["type"] = "unc"
                result["source_path"] = log_path
                return result

        # 检测优先级 3: FTP/rayfile（Comment #0 中 "下载附件:" 模式）
        import requests
        rest_url = inst_config.get("rest_url", "")
        api_key = inst_config.get("api_key", "")

        if rest_url:
            try:
                params = {"include_fields": "_all"} if not api_key else {"api_key": api_key}
                comment_resp = requests.get(
                    f"{rest_url}/bug/{bug_id}/comment",
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=15
                )
                comment_resp.raise_for_status()
                comment_data = comment_resp.json()
                comments = []
                for bc in comment_data.get("bugs", {}).values():
                    comments = bc.get("comments", [])
                    break

                # 搜索 "下载附件:" 模式
                for c in comments:
                    text = c.get("text", "")
                    m = re.search(r'下载附件\s*[：:]\s*(\S+)', text)
                    if m:
                        result["type"] = "rayfile"
                        result["source_path"] = m.group(1).strip()
                        return result

                # Fallback: 搜索 ftp:// 链接
                for c in comments:
                    text = c.get("text", "")
                    m = re.search(r'(ftp://[^\s)\]]+)', text)
                    if m:
                        result["type"] = "rayfile"
                        result["source_path"] = m.group(1).strip()
                        return result

            except Exception as e:
                result["error"] = f"Failed to detect attachment type: {e}"
                return result

        result["error"] = "No attachment source found (neither UNC path nor FTP/rayfile link)"
        return result

    except Exception as e:
        result["error"] = f"Detection error: {e}"
        return result


def copy_missing(src: str, dst: str) -> dict:
    """递归复制 src 到 dst，仅复制目标不存在的文件/目录（不覆盖已有）。
    移植自原 UI 工具 fetch_buginfo_by_API_UI.py line 152-174。

    Returns:
        {"copied": [str, ...], "skipped": [str, ...], "failed": [str, ...]}
        每个元素是目标路径字符串，failed 元素包含异常信息。
    """
    result = {"copied": [], "skipped": [], "failed": []}

    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s):
                sub = copy_missing(s, d)
                for k in ("copied", "skipped", "failed"):
                    result[k].extend(sub[k])
            else:
                if os.path.exists(d):
                    result["skipped"].append(d)
                else:
                    try:
                        shutil.copy2(s, d)
                        result["copied"].append(d)
                    except Exception as e:
                        result["failed"].append(f"{d} ({e})")
    else:
        # 单文件情况
        if os.path.exists(dst):
            result["skipped"].append(dst)
        else:
            try:
                shutil.copy2(src, dst)
                result["copied"].append(dst)
            except Exception as e:
                result["failed"].append(f"{dst} ({e})")

    return result


def download_from_unc_path(unc_path: str, dest_dir: str, mode: str = "incremental") -> dict:
    """通过 UNC 路径直接复制文件到本地（v3.1 — 增强错误报告）。

    Args:
        unc_path: UNC 源路径 (\\\\server\\share\\path)
        dest_dir: 本地目标目录
        mode: "full" = 完整覆盖 (shutil.copytree dirs_exist_ok=True)
              "incremental" = 增量复制 (copy_missing, 跳过已存在文件)

    Returns:
        {"success": bool, "copied": int, "skipped": int, "errors": [str, ...],
         "missing_files": [str, ...], "dest_dir": str}
    """
    result = {
        "success": False,
        "copied": 0,
        "skipped": 0,
        "errors": [],
        "missing_files": [],
        "dest_dir": dest_dir,
    }

    try:
        os.makedirs(dest_dir, exist_ok=True)

        if not os.path.exists(unc_path):
            result["errors"].append(f"UNC path not accessible: {unc_path}")
            return result

        if mode == "full":
            # 完整覆盖：shutil.copytree with dirs_exist_ok
            try:
                shutil.copytree(unc_path, dest_dir, dirs_exist_ok=True)
                file_count = 0
                for _, _, files in os.walk(dest_dir):
                    file_count += len(files)
                result["copied"] = file_count
            except Exception as e:
                result["errors"].append(f"Full copy failed: {e}")
                # Fallback to incremental
                cp_result = copy_missing(unc_path, dest_dir)
                result["errors"].append("Fell back to incremental copy")
                result["copied"] = len(cp_result["copied"])
                result["skipped"] = len(cp_result["skipped"])
                if cp_result["failed"]:
                    result["errors"].extend(
                        [f"Copy failed: {f}" for f in cp_result["failed"]]
                    )
        else:
            # 增量复制：仅复制不存在的文件
            cp_result = copy_missing(unc_path, dest_dir)
            result["copied"] = len(cp_result["copied"])
            result["skipped"] = len(cp_result["skipped"])
            if cp_result["failed"]:
                result["errors"].extend(
                    [f"Copy failed: {f}" for f in cp_result["failed"]]
                )

        # --- 下载后源/目标文件清单对比（v3.1 新增）---
        try:
            src_files = set()
            for root, dirs, files in os.walk(unc_path):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), unc_path)
                    src_files.add(rel)

            dst_files = set()
            for root, dirs, files in os.walk(dest_dir):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), dest_dir)
                    dst_files.add(rel)

            missing = sorted(src_files - dst_files)
            if missing:
                result["missing_files"] = missing
                result["errors"].append(
                    f"Source has {len(missing)} file(s) not in destination: "
                    + ", ".join(missing[:5])
                    + (f" ... and {len(missing) - 5} more" if len(missing) > 5 else "")
                )
        except Exception as e:
            # diff 失败不影响主流程
            result["errors"].append(f"Post-download diff failed: {e}")

        result["success"] = (len(result["errors"]) == 0
                             or (result["copied"] > 0 and not result["missing_files"]))

    except Exception as e:
        result["errors"].append(f"UNC download error: {e}")

    return result


# 已知的 rayfile exe 错误模式（exe 返回 exit code 0 但实际失败）
RAYFILE_ERROR_PATTERNS = [
    "The remote path is invalid",
    "Invalid args",
    "Share link is invalid",
]


def download_from_rayfile(ftp_path: str, dest_dir: str, instance_config: dict = None) -> dict:
    """通过 rayfile-c_cmd.exe 从 FTP 下载附件（SPCSS 客户附件）。

    使用与原工具完全一致的命令行参数执行 rayfile 子进程。

    Returns:
        {"success": bool, "command": str, "stdout": str, "stderr": str, "error": str or None}
    """
    result = {
        "success": False,
        "command": "",
        "stdout": "",
        "stderr": "",
        "error": None,
    }

    if instance_config is None:
        instance_config = {}

    # 从实例配置读取 FTP 凭证（与原工具一致）
    host = instance_config.get("ftp_host", "unitrans.unisoc.com")
    port = str(instance_config.get("ftp_port", "2443"))
    user = instance_config.get("ftp_user", "ctd01")
    password = instance_config.get("ftp_password", "ctd01@abAB")
    exe_path = instance_config.get("rayfile_exe", r"E:\08_Bug\sync-cmd-windows\rayfile-c_cmd.exe")

    # Normalize ftp_path: strip ftp:// prefix, ensure leading /
    if "://" in ftp_path:
        ftp_path = ftp_path.split("://", 1)[1]
        ftp_path = ftp_path.split("/", 1)[1] if "/" in ftp_path else ""
    ftp_path = ftp_path.replace("\\", "/")
    if not ftp_path.startswith("/"):
        ftp_path = "/" + ftp_path

    # 确保目标目录存在
    os.makedirs(dest_dir, exist_ok=True)

    # 构造 rayfile 命令（完全匹配原工具参数）
    args = [
        exe_path,
        "-a", host,
        "-p", port,
        "-ssl",
        "-u", user,
        "-w", password,
        "-o", "download",
        "-d", dest_dir,
        "-s", ftp_path,
        "-space_id", "2",
        "-gr", "31240",
        "-file-update", "append",
    ]

    result["command"] = " ".join(args)

    try:
        # MSYS2_ARG_CONV_EXCL prevents bash/MSYS2 from mangling Unix-style paths
        env = os.environ.copy()
        env["MSYS2_ARG_CONV_EXCL"] = "*"
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["success"] = proc.returncode == 0
        if result["success"] and proc.stdout:
            # rayfile exe 即使报错也返回 0，需检查 stdout 中的错误模式
            for pattern in RAYFILE_ERROR_PATTERNS:
                if pattern in proc.stdout:
                    result["success"] = False
                    result["error"] = f"rayfile: {pattern}"
                    break
        if not result["success"] and not result.get("error"):
            result["error"] = f"rayfile exited with code {proc.returncode}: {proc.stderr.strip()}"
    except FileNotFoundError:
        result["error"] = f"rayfile executable not found: {exe_path}"
    except subprocess.TimeoutExpired:
        result["error"] = "rayfile download timed out (600s)"
    except Exception as e:
        result["error"] = f"rayfile execution error: {e}"

    return result


def normalize_downloaded_folder(attachment_folder: str, bug_id: str, action: str = "copy_new") -> dict:
    """规范化下载后的附件文件夹。
    移植自原 UI 工具 fetch_buginfo_by_API_UI.py line 122-235。

    如果 attachment_folder 下恰好一个有效子目录（不以 '.' 开头、
    名称等于 bug_id 或以 "SPCSS" 开头），则：
    - "off": 不做任何处理
    - "move": 移动子目录所有内容到根层级，删除子目录
    - "copy_new": 仅复制不存在的文件到根层级（不覆盖已有）

    Returns:
        {"action": str, "processed": bool, "child_name": str or None, "error": str or None}
    """
    result = {
        "action": action,
        "processed": False,
        "child_name": None,
        "error": None,
    }

    try:
        if action == "off":
            return result

        if not os.path.isdir(attachment_folder):
            result["error"] = f"Attachment folder does not exist: {attachment_folder}"
            return result

        # 查找第一个有效子目录
        entries = [e for e in os.listdir(attachment_folder)
                   if not e.startswith('.') and os.path.isdir(os.path.join(attachment_folder, e))]

        if len(entries) != 1:
            return result

        child_name = entries[0]
        child_path = os.path.join(attachment_folder, child_name)

        if not os.path.isdir(child_path):
            return result

        # 子目录名必须匹配条件
        bug_id_str = str(bug_id)
        if not (child_name == bug_id_str
                or child_name.upper().startswith("SPCSS")
                or child_name.startswith(bug_id_str)):
            return result

        result["child_name"] = child_name

        if action == "move":
            # 移动子目录所有内容到上层，冲突时重命名
            for name in os.listdir(child_path):
                src = os.path.join(child_path, name)
                dst = os.path.join(attachment_folder, name)
                if os.path.exists(dst):
                    base, ext = os.path.splitext(name)
                    i = 1
                    newname = f"{base}_{i}{ext}"
                    while os.path.exists(os.path.join(attachment_folder, newname)):
                        i += 1
                        newname = f"{base}_{i}{ext}"
                    dst = os.path.join(attachment_folder, newname)
                shutil.move(src, dst)
            try:
                os.rmdir(child_path)
            except OSError:
                shutil.rmtree(child_path, ignore_errors=True)
            result["processed"] = True

        else:
            # "copy_new" — 仅复制新增内容，不覆盖
            copy_errors = []
            for name in os.listdir(child_path):
                src = os.path.join(child_path, name)
                dst = os.path.join(attachment_folder, name)
                if os.path.isdir(src):
                    if os.path.exists(dst) and os.path.isdir(dst):
                        cp = copy_missing(src, dst)
                        if cp["failed"]:
                            copy_errors.extend(cp["failed"])
                    elif not os.path.exists(dst):
                        try:
                            shutil.copytree(src, dst)
                        except Exception as e:
                            copy_errors.append(f"{dst} ({e})")
                else:
                    if not os.path.exists(dst):
                        try:
                            shutil.copy2(src, dst)
                        except Exception as e:
                            copy_errors.append(f"{dst} ({e})")

            if copy_errors:
                result["error"] = f"Copy errors during normalize: {'; '.join(copy_errors[:5])}"

            # 如果子目录已空则删除
            try:
                if not any(os.scandir(child_path)):
                    os.rmdir(child_path)
            except (OSError, IOError):
                pass  # rmdir 失败不影响主流程（目录可能非空或被占用）
            result["processed"] = True

    except Exception as e:
        result["error"] = f"Normalize error: {e}"

    return result


def download_bug_attachments(
    bug_id: str,
    dest_dir: str,
    instance: str = None,
    download_mode: str = "incremental",
    normalize_action: str = "copy_new",
) -> dict:
    """下载 Bug 附件的统一入口（v3.0: UNC 优先 + rayfile fallback）。

    智能检测附件类型，UNC 优先直接复制，rayfile FTP 作为 fallback。

    Args:
        bug_id: Bug ID
        dest_dir: 下载目标根目录（附件的实际路径为 {dest_dir}/Attachements/）
        instance: Bugzilla 实例名（可选）
        download_mode: "full" = 完整覆盖下载
                       "incremental" = 仅下载新增文件（默认）
                       "skip" = 跳过下载
        normalize_action: "off" | "move" | "copy_new"（默认 "copy_new"）

    Returns:
        {
            "success": bool,
            "bug_id": str,
            "attachment_type": "unc" | "rayfile" | "none",
            "dest_dir": str,
            "attachment_folder": str,
            "files_copied": int,
            "errors": [str, ...],
            "normalize_result": dict or None,
        }
    """
    result = {
        "success": False,
        "bug_id": str(bug_id),
        "attachment_type": "none",
        "dest_dir": dest_dir,
        "attachment_folder": os.path.join(dest_dir, "Attachements"),
        "files_copied": 0,
        "errors": [],
        "normalize_result": None,
    }

    if download_mode == "skip":
        result["success"] = True
        return result

    try:
        # 1. 检测附件类型
        detection = detect_attachment_type(bug_id, instance=instance)
        result["attachment_type"] = detection["type"]

        if detection.get("error") and detection["type"] == "none":
            result["errors"].append(detection["error"])
            return result

        # 2. 创建附件目录
        attachment_folder = result["attachment_folder"]
        if download_mode == "full" and os.path.exists(attachment_folder):
            shutil.rmtree(attachment_folder)
        os.makedirs(attachment_folder, exist_ok=True)

        # 3. 按类型执行下载（UNC 优先）
        source_path = detection.get("source_path", "")

        if detection["type"] == "unc":
            dl_result = download_from_unc_path(source_path, attachment_folder, mode=download_mode)
            result["files_copied"] = dl_result.get("copied", 0)
            result["errors"].extend(dl_result.get("errors", []))

            # UNC 失败时尝试 rayfile fallback
            if not dl_result.get("success") and result["files_copied"] == 0:
                # 尝试从 Comment #0 提取 FTP 路径作为 fallback
                inst_config = detection.get("instance_config", {})
                ftp_fallback = _extract_ftp_from_comment0(bug_id, inst_config)
                if ftp_fallback:
                    ftp_result = download_from_rayfile(ftp_fallback, attachment_folder, inst_config)
                    if ftp_result.get("success"):
                        result["attachment_type"] = "rayfile"
                        result["files_copied"] = -1
                        result["errors"] = []  # fallback 成功，清除 UNC 错误
                    else:
                        result["errors"].append(
                            f"UNC failed, rayfile fallback also failed: {ftp_result.get('error', 'unknown')}")
                else:
                    result["errors"].append("UNC download failed, no rayfile fallback available")

        elif detection["type"] == "rayfile":
            inst_config = detection.get("instance_config", {})
            dl_result = download_from_rayfile(source_path, attachment_folder, inst_config)
            if not dl_result.get("success"):
                result["errors"].append(
                    dl_result.get("error", "rayfile download failed"))
            result["files_copied"] = -1

        # 4. 规范化文件夹
        if normalize_action != "off":
            norm_result = normalize_downloaded_folder(
                attachment_folder, bug_id, action=normalize_action)
            result["normalize_result"] = norm_result

        result["success"] = len(result["errors"]) == 0

    except Exception as e:
        result["errors"].append(f"Download error: {e}")

    return result


def _extract_ftp_from_comment0(bug_id: str, instance_config: dict) -> str:
    """从 Comment #0 提取 FTP/rayfile 路径（UNC fallback 用）。

    Returns:
        FTP 路径字符串，未找到返回空字符串。
    """
    rest_url = instance_config.get("rest_url", "")
    api_key = instance_config.get("api_key", "")

    if not rest_url:
        return ""

    try:
        import requests
        params = {"include_fields": "_all"} if not api_key else {"api_key": api_key}
        resp = requests.get(
            f"{rest_url}/bug/{bug_id}/comment",
            params=params,
            headers={"Accept": "application/json"},
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        comments = []
        for bc in data.get("bugs", {}).values():
            comments = bc.get("comments", [])
            break

        if not comments:
            return ""

        text = comments[0].get("text", "")

        # 搜索 "下载附件:" 模式
        m = re.search(r'下载附件\s*[：:]\s*(\S+)', text)
        if m:
            return m.group(1).strip()

        # Fallback: 搜索 ftp:// 链接
        m = re.search(r'(ftp://[^\s)\]]+)', text)
        if m:
            return m.group(1).strip()

        return ""
    except Exception:
        return ""


# ============================================================
# 工作区创建 & 附件下载
# ============================================================

def generate_folder_name(bug: dict) -> str:
    """
    根据Bug信息生成文件夹名。
    格式: "Bug " + bug_title (匹配原工具逻辑)
    其中 bug_title = clean_folder_name(raw_title)
    raw_title 格式: "{bug_id}({alias}) - {summary}"
    """
    _, clean_folder_name = _import_bug_core_format()

    raw_title = bug.get("raw_title", "")
    if not raw_title:
        bug_id = str(bug.get("bug_id", "unknown"))
        summary = bug.get("summary", "")
        alias = bug.get("alias", [])
        if alias:
            alias_str = alias[0] if isinstance(alias, list) else str(alias)
            raw_title = f"{bug_id}({alias_str}) - {summary}"
        else:
            raw_title = f"{bug_id} - {summary}"

    folder_name = "Bug " + clean_folder_name(raw_title)
    return folder_name


def get_default_workspace_path() -> str:
    """获取默认工作区路径（与reference中paths配置一致）"""
    config = load_config()
    unisoc_cfg = config.get("instances", {}).get("unisoc", {})
    default_path = unisoc_cfg.get("default_workspace", r"E:\08_Bug")
    return os.path.expandvars(default_path)


def guess_workspace_path(bug: dict, routing_key: str = None) -> str:
    """根据Bug上下文自动选择最佳工作区基路径。

    判断逻辑：
    - routing_key 显式指定 → 从 workspace_routing 读取 base_path（最高优先级）
    - 客户Bug（SPCSS前缀）→ 优先CQ路径（历史或默认）
    - Unisoc实例Bug → 优先CQ路径
    - 其他 → 默认路径
    """
    # 显式 routing_key 优先（manual_only routing entries）
    if routing_key:
        config = load_config()
        routing = config.get("instances", {}).get("unisoc", {}).get("workspace_routing", {})
        if routing_key in routing:
            return os.path.normpath(routing[routing_key]["base_path"])

    paths = load_workspace_paths()
    default = get_default_workspace_path()

    alias = bug.get("alias", [])
    if isinstance(alias, list) and alias:
        alias_str = str(alias[0]) if alias[0] else ""
    elif isinstance(alias, str):
        alias_str = alias
    else:
        alias_str = ""
    instance = bug.get("instance", "")

    # 客户Bug（SPCSS前缀）或 unisoc 实例 → 优先CQ目录
    if alias_str.startswith("SPCSS") or instance == "unisoc":
        # 在历史路径中找第一个包含CQ的路径
        for p in paths:
            norm = os.path.normpath(p)
            if norm.endswith("CQ") or norm.endswith("cq"):
                return os.path.normpath(p)
        # 无CQ历史，使用默认CQ路径
        cq_path = os.path.join(default, "CQ")
        return os.path.normpath(cq_path)

    return default


def get_rayfile_command(ftp_path: str, local_dir: str) -> dict:
    """
    生成 rayfile-c_cmd.exe 下载命令（匹配原工具精确参数）。

    原工具命令:
      rayfile-c_cmd.exe -a unitrans.unisoc.com -p 2443 -ssl
        -u ctd01 -w ctd01@abAB -o download
        -d {local_dir} -s {ftp_path}
        -space_id 2 -gr 31240 -file-update append

    Returns:
        {"command": str, "args": [str, ...]}
    """
    config = load_config()
    unisoc_cfg = config.get("instances", {}).get("unisoc", {})

    host = unisoc_cfg.get("ftp_host", "unitrans.unisoc.com")
    port = str(unisoc_cfg.get("ftp_port", "2443"))
    user = unisoc_cfg.get("ftp_user", "ctd01")
    password = unisoc_cfg.get("ftp_password", "ctd01@abAB")
    use_ssl = unisoc_cfg.get("ftp_use_ssl", True)
    exe_path = unisoc_cfg.get("rayfile_exe", r"E:\08_Bug\sync-cmd-windows\rayfile-c_cmd.exe")

    args = [exe_path, "-a", host, "-p", port]
    if use_ssl:
        args.append("-ssl")
    args.extend(["-u", user, "-w", password,
                 "-o", "download",
                 "-d", local_dir,
                 "-s", ftp_path,
                 "-space_id", "2",
                 "-gr", "31240",
                 "-file-update", "append"])

    return {
        "command": " ".join(args),
        "args": args,
    }


def create_bug_shortcut(bug: dict, folder_path: str) -> str:
    """创建 Bug 页面 .url 快捷方式（匹配原工具格式）。

    使用 [InternetShortcut] 格式，包含 URL/IconFile/IconIndex。
    路径 >200 字符时自动简化为 "Bug.url"。
    """
    url = bug.get("url", "")
    bug_id = str(bug.get("bug_id", "unknown"))

    if not url:
        return ""

    shortcut_name = f"Bug_{bug_id}.url"
    shortcut_path = os.path.join(folder_path, shortcut_name)

    # 路径过长时简化（原工具 >200 字符阈值）
    if len(shortcut_path) > 200:
        shortcut_path = os.path.join(folder_path, "Bug.url")

    os.makedirs(folder_path, exist_ok=True)

    content = f"""[InternetShortcut]
URL={url}
IconFile={url}
IconIndex=0
"""
    with open(shortcut_path, "w", encoding="ascii") as f:
        f.write(content)

    return shortcut_path


def create_url_shortcut(url: str, folder_path: str, name: str = None) -> str:
    """创建任意 URL 的 .url 快捷方式。

    与 create_bug_shortcut 不同，此函数允许自定义名称。
    """
    if name is None:
        name = "Shortcut.url"
    elif not name.endswith(".url"):
        name = f"{name}.url"

    shortcut_path = os.path.join(folder_path, name)

    if len(shortcut_path) > 200:
        shortcut_path = os.path.join(folder_path, "Bug.url")

    os.makedirs(folder_path, exist_ok=True)

    content = f"""[InternetShortcut]
URL={url}
IconFile={url}
IconIndex=0
"""
    with open(shortcut_path, "w", encoding="ascii") as f:
        f.write(content)

    return shortcut_path


def generate_workspace(bug: dict, base_path: str = None, routing_key: str = None) -> dict:
    """
    创建工作区文件夹（匹配原工具 main() 流程）:
    1. 根据Bug信息生成文件夹名 (Bug + bug_title)
    2. 创建本地文件夹
    3. 创建 Attachements/ 子文件夹
    4. 创建 Bug .url 快捷方式（指向Bug页面）
    5. 创建 Attachements/UNC_{bug_id}.url 快捷方式（指向快速下载链接）
    6. 生成 bug_summary.txt
    7. 生成 rayfile 下载命令（供手动执行）

    返回值:
        {
            "folder_name": str,
            "folder_path": str,
            "attachment_folder": str,
            "created": bool,
            "rayfile_commands": [dict, ...],
            "shortcut_file": str,
            "attachment_shortcut": str,
            "summary_file": str,
        }
    """
    format_bug_summary, _ = _import_bug_core_format()

    if base_path is None:
        base_path = guess_workspace_path(bug, routing_key=routing_key)
    elif routing_key:
        # routing_key 显式指定时，使用 routing 配置的 base_path，跳过自动修正
        base_path = guess_workspace_path(bug, routing_key=routing_key)
    else:
        # SPCSS Bug 即使显式传了 base_path，也自动修正到 CQ 子目录
        # 防止调用方硬编码 E:\08_Bug 绕过 guess_workspace_path 的自动路由
        inferred = guess_workspace_path(bug)
        if os.path.normpath(inferred) != os.path.normpath(base_path):
            base_path = inferred

    folder_name = generate_folder_name(bug)
    folder_path = os.path.join(base_path, folder_name)

    # 创建文件夹
    os.makedirs(folder_path, exist_ok=True)
    created = os.path.isdir(folder_path)

    # 创建 Attachements 子文件夹 (匹配原工具逻辑)
    attachment_folder = os.path.join(folder_path, "Attachements")
    os.makedirs(attachment_folder, exist_ok=True)

    # 生成 rayfile 下载命令 (dict 格式，供手动执行)
    ftp_urls = bug.get("ftp_urls", [])
    rayfile_cmds = []
    for ftp_url in ftp_urls:
        cmd = get_rayfile_command(ftp_url, attachment_folder)
        rayfile_cmds.append(cmd)

    # 如果没有FTP URL但有UNC路径，生成替代命令
    unc_paths = bug.get("unc_paths", [])
    for unc in unc_paths:
        ftp_equiv = unc.replace("\\\\", "ftp://").replace("\\", "/")
        cmd = get_rayfile_command(ftp_equiv, attachment_folder)
        rayfile_cmds.append(cmd)

    # 如果以上都没有，使用 ftp_path（从评论中提取的"下载附件:"路径）
    ftp_path = bug.get("ftp_path", "")
    if not rayfile_cmds and ftp_path:
        cmd = get_rayfile_command(ftp_path, attachment_folder)
        rayfile_cmds.append(cmd)

    # 创建 Bug 页面 .url 快捷方式
    shortcut = create_bug_shortcut(bug, folder_path)

    # 创建 Attachements/UNC_{bug_id}.url 快捷方式 (匹配原工具逻辑)
    attachment_shortcut = ""
    path_url = bug.get("path_url", "")
    bug_id = str(bug.get("bug_id", ""))
    if path_url and bug_id:
        attachment_shortcut = create_url_shortcut(
            path_url, attachment_folder, name=f"UNC_{bug_id}"
        )

    # 生成 Bug 摘要文件
    summary_file = os.path.join(folder_path, "bug_summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(format_bug_summary(bug))
        # 末尾附加完整的第一条评论（包含下载链接）
        first_comment = bug.get("first_comment", "")
        if first_comment:
            f.write("\n\n[First Comment]\n")
            f.write("=" * 40 + "\n")
            f.write(first_comment)
            f.write("\n")

    return {
        "folder_name": folder_name,
        "folder_path": folder_path,
        "attachment_folder": attachment_folder,
        "created": created,
        "rayfile_commands": rayfile_cmds,
        "shortcut_file": shortcut,
        "attachment_shortcut": attachment_shortcut,
        "summary_file": summary_file,
    }


# ============================================================
# Bug Z 模板 + 路径历史 + 快速打开
# ============================================================

def copy_bug_z_template(base_path: str, dest_folder: str) -> bool:
    """复制 Bug Z 模板文件夹到目标工作区。

    若 {base_path}/Bug Z 存在，使用 shutil.copytree 复制到 dest_folder，
    冲突时合并（dirs_exist_ok=True）。
    移植自原 UI 工具 line 421-432。

    Returns:
        True = 已复制, False = 模板不存在或 dest_folder 本身就是 Bug Z
    """
    bug_z = os.path.join(base_path, "Bug Z")

    if not os.path.exists(bug_z):
        return False

    # 防止自复制（目标路径就是 Bug Z 本身）
    if os.path.normpath(dest_folder) == os.path.normpath(bug_z):
        return False

    try:
        shutil.copytree(bug_z, dest_folder, dirs_exist_ok=True)
        return True
    except Exception:
        return False


def load_workspace_paths(config_dir: str = None) -> list:
    """从 config/paths.json 加载工作区路径历史。

    若文件不存在则返回预设的 14 个默认路径（移植自原工具 paths.json）。
    """
    if config_dir is None:
        config_dir = SCRIPT_DIR

    paths_file = PATHS_CONFIG if config_dir == SCRIPT_DIR else os.path.join(config_dir, "paths.json")

    if os.path.exists(paths_file):
        try:
            with open(paths_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # 配置文件损坏或不可读，使用默认路径

    # 默认路径（移植自原工具 paths 列表）
    return [
        r"E:\08_Bug",
        r"E:\08_Bug\CQ",
        r"E:\08_Bug\Task",
        r"E:\08_Bug\Test",
        r"F:\PD认证",
        r"F:\PD认证\XIAOMI",
        r"F:\PD认证\vivo_T612",
        r"F:\PD认证\VIVO",
        r"F:\PD认证\REALME",
        r"F:\PD认证\transsion",
        r"F:\PD认证\SAGEREAL",
        r"F:\PD认证\ZTE\UMS9620S]P820F03",
        r"F:\PD认证\ZTE\UMS9620][P720F12]",
        r"F:\PD认证\YINGKA",
        r"F:\PD认证\SPROCOMM",
        r"F:\PD认证\S51CUBE",
        r"F:\PD认证\ZTE",
    ]


def save_workspace_paths(paths: list, config_dir: str = None) -> bool:
    """保存工作区路径历史到 config/paths.json。
    去重并保持顺序。
    """
    if config_dir is None:
        config_dir = SCRIPT_DIR

    paths_file = PATHS_CONFIG if config_dir == SCRIPT_DIR else os.path.join(config_dir, "paths.json")
    os.makedirs(os.path.dirname(paths_file), exist_ok=True)

    # 去重保持顺序
    seen = set()
    unique = []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            unique.append(p)

    try:
        with open(paths_file, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def open_workspace_path(path: str) -> bool:
    """在文件资源管理器中打开工作区路径（os.startfile）。

    移植自原 UI 工具 open_base_path() line 511-520。
    """
    if not path or not os.path.exists(path):
        return False
    try:
        os.startfile(path)
        return True
    except Exception:
        return False


# ============================================================
# ZIP 自动解压
# ============================================================

def extract_zip_attachments(attachment_folder: str, remove_zip: bool = False) -> dict:
    """扫描 Attachements 目录下所有 .zip 文件，就地解压。

    Args:
        attachment_folder: Attachements 目录路径
        remove_zip: 解压后是否删除原 ZIP（默认 False，保留原文件）

    Returns:
        {"extracted": [...], "skipped": [...], "errors": [...]}
    """
    result = {"extracted": [], "skipped": [], "errors": []}
    if not attachment_folder or not os.path.isdir(attachment_folder):
        return result

    for entry in os.listdir(attachment_folder):
        if not entry.lower().endswith(".zip"):
            continue
        zip_path = os.path.join(attachment_folder, entry)
        if not os.path.isfile(zip_path):
            continue
        target_dir = os.path.join(attachment_folder, os.path.splitext(entry)[0])
        if os.path.isdir(target_dir):
            result["skipped"].append(entry)
            continue
        try:
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
            result["extracted"].append({"zip": entry, "target": target_dir})
            if remove_zip:
                os.remove(zip_path)
        except Exception as e:
            result["errors"].append({"zip": entry, "error": str(e)})

    return result


# ============================================================
# 编排函数 — 完整工作区生成（含下载）
# ============================================================

def generate_concise_report_title(bug: dict, max_len: int = 60) -> str:
    """从 Bug 摘要中提取简洁标题，用于报告文件名。

    输入格式: "[UMS312][INNOVATECH][VTH_NM006][17319][无线座机/固话]怎么设置外置DCDC的电压为0.8V"
    输出格式: "UMS312_外置DCDC电压配置"

    Args:
        bug: Bug 字典，需包含 summary, alias 等字段
        max_len: 简洁标题最大长度（不含 alias 前缀）

    Returns:
        filename-safe 的简洁标题，不含非法字符
    """
    _, clean_folder_name = _import_bug_core_format()

    summary = bug.get("summary", bug.get("raw_title", ""))
    if not summary:
        return "bug_report"

    # 提取平台名（第一个 [...] 标签内容）
    platform = ""
    platform_match = re.match(r'^\[([^\]]+)\]', summary)
    if platform_match:
        platform = platform_match.group(1)

    # 去除所有开头的 [...] 标签，得到核心描述
    core = re.sub(r'^(?:\[[^\]]*\])+\s*', '', summary).strip()

    # 如果去除标签后为空，使用原始 summary
    if not core:
        core = summary

    # 截断过长标题
    if len(core) > max_len:
        core = core[:max_len]

    # 组合：平台_核心描述
    if platform and platform not in core:
        title = f"{platform}_{core}"
    else:
        title = core

    # 清理文件名非法字符
    title = clean_folder_name(title, max_len=80)
    return title


def generate_analysis_report(bug: dict, result: dict,
                            report_type: str = "analysis",
                            keyword: str = None) -> str:
    """生成完整分析报告，保存到工作区文件夹。

    报告文件名使用标准化格式: {bug_id}_{type}_{keyword}__{YYYYMMDD}.md
    通过 bug-core.generate_report_filename_from_bug() 生成。

    向后兼容：不传 report_type/keyword 时，会自动生成默认 keyword。

    Args:
        bug: Bug 字典
        result: generate_workspace_with_download 的返回结果
        report_type: 报告类型，默认 "analysis"（如 "analysis", "harness", "patch_eval"）
        keyword: 会话相关关键词，必填。未传时自动使用 Bug 平台名

    Returns:
        report_path: 生成的报告文件路径（失败时为空字符串）
    """
    folder_path = result.get("base_path", "")
    if not folder_path or not os.path.isdir(folder_path):
        return ""

    # ---- 生成标准化文件名 ----
    if keyword is None:
        # 自动生成 keyword：使用 Bug 的平台名
        summary = bug.get("summary", bug.get("raw_title", ""))
        platform_match = re.match(r'^\[([^\]]+)\]', summary)
        keyword = platform_match.group(1) if platform_match else "report"

    try:
        gen_fn = _import_bug_core_report()
        report_name = gen_fn(bug, report_type, keyword)
    except Exception:
        # fallback: 使用旧命名方式作为最后手段
        concise_title = generate_concise_report_title(bug)
        if alias:
            report_name = f"{alias}_{concise_title}.md"
        else:
            report_name = f"{bug_id}_{concise_title}.md"

    report_path = os.path.join(folder_path, report_name)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---- 提取 Bug 字段 ----
    bug_id = str(bug.get("bug_id", "?"))
    alias_list = bug.get("alias", [])
    alias = alias_list[0] if alias_list else ""
    summary = bug.get("summary", bug.get("raw_title", "?"))
    raw_title = bug.get("raw_title", summary)
    status = bug.get("status", "?")
    priority = bug.get("priority", "?")
    severity = bug.get("severity", "?")
    product = bug.get("product", "?")
    component = bug.get("component", "?")
    assignee = bug.get("assignee", "?")
    url = bug.get("url", "")
    created = bug.get("creation_time", bug.get("created", "?"))
    changed = bug.get("last_change_time", bug.get("last_changed", "?"))
    ftp_path = bug.get("ftp_path", "")
    path_url = bug.get("path_url", "")
    first_comment = bug.get("first_comment", "")
    comments_count = bug.get("comments_count", 0)

    # ---- 下载结果 ----
    dl = result.get("download", {})
    dl_success = dl.get("success", False)
    dl_type = dl.get("attachment_type", "none")
    dl_files = dl.get("files_copied", 0)
    dl_errors = dl.get("errors", [])

    # ---- 撰写报告 ----
    lines = []
    lines.append(f"# {alias or bug_id} — Bug Hub 完整流程分析报告")
    lines.append("")
    lines.append(f"**分析时间**: {now}")
    lines.append(f"**Bug 页面**: {url}" if url else f"**Bug ID**: {bug_id}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、Bug 基本信息")
    lines.append("")
    lines.append("| 字段 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| **Bug ID** | {bug_id}{' (' + alias + ')' if alias else ''} |")
    lines.append(f"| **标题** | {summary} |")
    lines.append(f"| **状态** | {status} |")
    lines.append(f"| **优先级/严重度** | {priority} / {severity} |")
    lines.append(f"| **产品/组件** | {product} / {component} |")
    lines.append(f"| **指派人** | {assignee} |")
    if created:
        lines.append(f"| **创建时间** | {created} |")
    if changed:
        lines.append(f"| **最后更新** | {changed} |")
    if comments_count:
        lines.append(f"| **评论数** | {comments_count} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- 问题描述 ----
    lines.append("## 二、问题描述")
    lines.append("")
    if first_comment:
        lines.append("### 客户原始描述")
        lines.append("")
        lines.append("```")
        # 截取前 2000 字符
        lines.append(first_comment[:2000])
        if len(first_comment) > 2000:
            lines.append("... (内容过长，已截断)")
        lines.append("```")
    else:
        lines.append("_（未获取到客户原始描述）_")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- 技术分析 ----
    lines.append("## 三、技术分析")
    lines.append("")
    lines.append("_（待补充：请根据 Bug 内容进行技术分析）_")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- 附件下载 ----
    lines.append("## 四、附件下载")
    lines.append("")
    lines.append("| 项目 | 结果 |")
    lines.append("|------|------|")
    lines.append(f"| **下载方式** | {dl_type} |")
    if dl_type == "rayfile" and ftp_path:
        lines.append(f"| **FTP 路径** | `{ftp_path}` |")
    if path_url:
        lines.append(f"| **快捷链接** | {path_url} |")
    lines.append(f"| **下载成功** | {'✅ 是' if dl_success else '❌ 否'} |")
    lines.append(f"| **文件数量** | {dl_files if dl_files >= 0 else '未知'} |")
    if dl_errors:
        lines.append(f"| **错误** | {', '.join(dl_errors[:3])} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- Workspace ----
    lines.append("## 五、Workspace")
    lines.append("")
    lines.append("| 项目 | 路径 |")
    lines.append("|------|------|")
    lines.append(f"| **工作区** | `{folder_path}` |")
    lines.append(f"| **快捷方式** | `Bug_{bug_id}.url` |")
    lines.append(f"| **摘要文件** | `bug_summary.txt` |")
    lines.append(f"| **附件目录** | `Attachements/` |")
    if result.get("bug_z_copied"):
        lines.append(f"| **Bug Z 模板** | `Bug Z/` |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- 建议处理方向 ----
    lines.append("## 六、建议处理方向")
    lines.append("")
    lines.append("_（待补充：请根据 Bug 分析结果填写处理建议）_")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*报告由 Bug Hub 自动生成 | {now}*")

    # ---- 写入文件 ----
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return report_path
    except Exception:
        return ""


def generate_workspace_with_download(
    bug: dict,
    base_path: str = None,
    download_mode: str = "incremental",
    normalize_action: str = "copy_new",
    copy_bug_z: bool = True,
    routing_key: str = None,
) -> dict:
    """完整工作区生成 + 附件下载（编排函数，v3.0 重写）。

    工作流:
    1. 生成文件夹名 + 创建工作区目录
    2. 复制 Bug Z 模板（若存在）
    3. 创建 Attachements/ 子文件夹
    4. 创建 Bug .url + Attachements/UNC_{bug_id}.url 快捷方式
    5. 生成 bug_summary.txt
    6. UNC 优先下载附件（rayfile FTP fallback）
    7. 自动解压 Attachements 下的 ZIP 附件
    8. normalize_downloaded_folder (若 normalize_action != "off")
    9. 返回完整结果

    Args:
        bug: Bug 信息 dict（含 bug_id, raw_title, summary, url, ftp_urls, unc_paths）
        base_path: 工作区根目录（默认来自配置）
        download_mode: "full" = 完整覆盖下载（清空后重下）
                       "incremental" = 仅下载新增文件（默认，跳过已有）
                       "skip" = 跳过下载（仅创建文件夹结构）
        normalize_action: "off" | "move" | "copy_new" (匹配 NORMALIZE_ACTION)
        copy_bug_z: 是否复制 Bug Z 模板

    Returns:
        {
            "success": bool,
            "bug_id": str,
            "bug_title": str,       # raw_title (匹配原工具 param_bug_title)
            "base_path": str,       # 工作区路径 (匹配原工具 param_base_path)
            "ftp_path": str,        # FTP/UNC 路径 (匹配原工具 param_ftp_path)
            "path_url": str,        # 快捷下载链接 (匹配原工具 param_path_url)
            "folder": dict,         # generate_workspace 返回
            "download": dict,       # download_bug_attachments 返回
            "normalized": dict,     # normalize 返回
            "analysis_report": str, # 分析报告路径
            "bug_z_copied": bool,
            "errors": [str, ...],
        }
    """
    result = {
        "success": False,
        "bug_id": str(bug.get("bug_id", "")),
        "bug_title": bug.get("raw_title", bug.get("summary", "")),
        "base_path": "",
        "ftp_path": bug.get("ftp_path", ""),
        "path_url": bug.get("path_url", ""),
        "folder": {},
        "download": {},
        "extracted": {},
        "normalized": {},
        "analysis_report": "",
        "bug_z_copied": False,
        "errors": [],
    }

    try:
        if base_path is None:
            base_path = guess_workspace_path(bug, routing_key=routing_key)
        elif routing_key:
            # routing_key 显式指定时，使用 routing 配置的 base_path
            base_path = guess_workspace_path(bug, routing_key=routing_key)
        else:
            # SPCSS Bug 即使显式传了 base_path，也自动修正到 CQ 子目录
            inferred = guess_workspace_path(bug)
            if os.path.normpath(inferred) != os.path.normpath(base_path):
                base_path = inferred

        # 1. 创建工作区文件夹 (含 Attachements + 快捷方式)
        folder_info = generate_workspace(bug, base_path, routing_key=routing_key)
        result["folder"] = folder_info
        result["base_path"] = folder_info.get("folder_path", "")

        if not folder_info.get("created"):
            result["errors"].append("Failed to create workspace folder")
            return result

        folder_path = folder_info["folder_path"]
        attachment_folder = folder_info.get("attachment_folder", "")

        # 2. Bug Z 模板复制
        if copy_bug_z:
            result["bug_z_copied"] = copy_bug_z_template(base_path, folder_path)

        # 3. 下载附件（UNC 优先 + rayfile fallback）
        if download_mode != "skip":
            bug_id = str(bug.get("bug_id", ""))
            if bug_id:
                dl_result = download_bug_attachments(
                    bug_id=bug_id,
                    dest_dir=folder_path,
                    instance=bug.get("instance"),
                    download_mode=download_mode,
                    normalize_action=normalize_action,
                )
                result["download"] = dl_result
                if not dl_result.get("success"):
                    result["errors"].extend(dl_result.get("errors", []))
            else:
                result["errors"].append("No bug_id for download")

        # 4. 自动解压 Attachements 下的 ZIP 附件
        if attachment_folder and os.path.isdir(attachment_folder):
            result["extracted"] = extract_zip_attachments(attachment_folder)

        # 5. normalize_downloaded_folder 兜底
        # download_bug_attachments 已在内部调用 normalize，
        # 但若 normalize_action != "off" 且 download_mode == "skip"，此处单独调用
        if normalize_action != "off" and download_mode == "skip":
            try:
                if attachment_folder and os.path.isdir(attachment_folder):
                    if normalize_action == "move":
                        normalize_downloaded_folder(attachment_folder, bug_id, action="move")
                    elif normalize_action == "copy_new":
                        copy_missing(attachment_folder, attachment_folder)
                    result["normalized"] = {"action": normalize_action, "success": True}
            except Exception as e:
                result["normalized"] = {"action": normalize_action, "success": False, "error": str(e)}

        # 6. 生成分析报告
        result["analysis_report"] = generate_analysis_report(bug, result)

        result["success"] = len(result["errors"]) == 0

    except Exception as e:
        result["errors"].append(f"Workspace generation error: {e}")

    return result