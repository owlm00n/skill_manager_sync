#!/usr/bin/env python3
"""
Bug Workspace - 工作区创建 & 编排模块
复刻原 UI 工具 fetch_buginfo_by_API_UI.py 的核心流程：
1. 根据Bug信息生成文件夹名
2. 创建本地文件夹 + Bug Z 模板复制
3. 调用 bug-logs 下载附件（UNC / rayfile）
4. 创建 .url 快捷方式
5. 生成 bug_summary.txt + analysis_report.md
6. 路径历史管理 + 快速打开
"""

import json
import os
import re
import shutil
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


def _import_bug_logs_download():
    """三级降级加载 bug-logs 的下载函数"""
    try:
        from bug_logs import download_bug_attachments
        return download_bug_attachments
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _logs = os.path.join(_skills, "bug-logs")
        if _logs not in _sys.path:
            _sys.path.insert(0, _logs)
        from bug_logs import download_bug_attachments as _dba
        return _dba


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


def guess_workspace_path(bug: dict) -> str:
    """根据Bug上下文自动选择最佳工作区基路径。

    判断逻辑：
    - 客户Bug（SPCSS前缀）→ 优先CQ路径（历史或默认）
    - Unisoc实例Bug → 优先CQ路径
    - 其他 → 默认路径
    """
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


def generate_workspace(bug: dict, base_path: str = None, refresh: bool = False) -> dict:
    """
    创建工作区文件夹（匹配原工具 main() 流程）:
    1. 根据Bug信息生成文件夹名 (Bug + bug_title)
    2. 创建本地文件夹
    3. 创建 Attachements/ 子文件夹
    4. 创建 Bug .url 快捷方式（指向Bug页面）
    5. 创建 Attachements/{bug_id}.url 快捷方式（指向快速下载链接）
    6. 生成 rayfile 下载命令
    7. 生成 bug_summary.txt

    Args:
        refresh: True = 清空 Attachements 后重建 (匹配 REFRESH_ATTACHMENTS)

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
        base_path = guess_workspace_path(bug)

    folder_name = generate_folder_name(bug)
    folder_path = os.path.join(base_path, folder_name)

    # 创建文件夹
    os.makedirs(folder_path, exist_ok=True)
    created = os.path.isdir(folder_path)

    # 创建 Attachements 子文件夹 (匹配原工具逻辑)
    attachment_folder = os.path.join(folder_path, "Attachements")
    if refresh:
        if os.path.exists(attachment_folder):
            shutil.rmtree(attachment_folder)
    os.makedirs(attachment_folder, exist_ok=True)

    # 生成 rayfile 下载命令 (dict 格式)
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

    # 创建 Attachements/{bug_id}.url 快捷方式 (匹配原工具逻辑)
    attachment_shortcut = ""
    path_url = bug.get("path_url", "")
    bug_id = str(bug.get("bug_id", ""))
    if path_url and bug_id:
        attachment_shortcut = create_url_shortcut(
            path_url, attachment_folder, name=str(bug_id)
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
        except Exception:
            pass

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

def generate_analysis_report(bug: dict, result: dict) -> str:
    """生成完整分析报告 analysis_report.md，保存到工作区文件夹。

    报告包含：基本信息、问题描述、技术分析、AI参考、附件下载、建议处理方向。

    Returns:
        report_path: 生成的报告文件路径（失败时为空字符串）
    """
    folder_path = result.get("base_path", "")
    if not folder_path or not os.path.isdir(folder_path):
        return ""

    report_path = os.path.join(folder_path, "analysis_report.md")
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
    download: bool = True,
    refresh: bool = False,
    normalize_action: str = "copy_new",
    copy_bug_z: bool = True,
) -> dict:
    """完整工作区生成 + 附件下载（编排函数，匹配原工具 main() 流程）。

    工作流:
    1. 生成文件夹名 + 创建工作区目录
    2. 复制 Bug Z 模板（若存在）
    3. 创建 Attachements/ 子文件夹
    4. 创建 Bug .url + Attachements/{bug_id}.url 快捷方式
    5. 生成 bug_summary.txt
    6. 调用 bug-logs 下载附件 (rayfile 或 UNC)
    7. 自动解压 Attachements 下的 ZIP 附件
    8. normalize_downloaded_folder (若 normalize_action != "off")
    9. 返回完整结果 + 参数字段

    Args:
        bug: Bug 信息 dict（含 bug_id, raw_title, summary, url, ftp_urls, unc_paths）
        base_path: 工作区根目录（默认来自配置）
        download: 是否执行下载
        refresh: 清空 Attachements 后重新下载 (匹配 REFRESH_ATTACHMENTS)
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
            base_path = guess_workspace_path(bug)

        # 1. 创建工作区文件夹 (含 Attachements + 快捷方式)
        folder_info = generate_workspace(bug, base_path, refresh=refresh)
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

        # 3. 调用 bug-logs 下载附件
        if download:
            bug_id = str(bug.get("bug_id", ""))
            if bug_id:
                download_bug_attachments_fn = _import_bug_logs_download()
                dl_result = download_bug_attachments_fn(
                    bug_id=bug_id,
                    dest_dir=folder_path,
                    instance=bug.get("instance"),
                    refresh=refresh,
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

        # 5. normalize_downloaded_folder (bug-logs 内部已调用，此处为兜底)
        # bug-logs 的 download_bug_attachments 已在内部调用 normalize，
        # 但若 normalize_action != "off" 且 download 未执行，此处单独调用
        if normalize_action != "off" and not download:
            try:
                from bug_logs import normalize_downloaded_folder as _norm, copy_missing as _copy
                attachment_folder = folder_info.get("attachment_folder", "")
                if attachment_folder and os.path.isdir(attachment_folder):
                    if normalize_action == "move":
                        _norm(attachment_folder)
                    elif normalize_action == "copy_new":
                        _copy(attachment_folder)
                    result["normalized"] = {"action": normalize_action, "success": True}
            except Exception as e:
                result["normalized"] = {"action": normalize_action, "success": False, "error": str(e)}

        # 6. 生成分析报告
        result["analysis_report"] = generate_analysis_report(bug, result)

        result["success"] = len(result["errors"]) == 0

    except Exception as e:
        result["errors"].append(f"Workspace generation error: {e}")

    return result
