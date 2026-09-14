#!/usr/bin/env python3
"""
Bugzilla MCP Server
基于fastmcp，兼容任意Bugzilla实例
统一入口：集中 bug-core / bug-workspace 2个Skill的功能

工具一览:
  bug_info         — 获取Bug详细信息 (bug-core)
  bug_comments     — 获取Bug评论列表 (bug-core)
  bugs_search      — 搜索Bug/quicksearch (bug-core)
  bug_comment_add  — 发布评论 (bug-core)
  bug_status_update — 更新状态 (bug-core)
  bug_workspace    — 创建工作区 + UNC优先下载附件 (bug-workspace v3.0)
  bug_logs         — ⚠️ DEPRECATED — 请使用 bug_workspace 代替
  generate_reply   — 生成客户回复预览 (bug-core)
"""

import json
import os
import re
from typing import Optional

import httpx
from fastmcp import FastMCP

# 路径常量
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_BUGS_PATH = os.path.join(SCRIPT_DIR, "..", "data", "sample_bugs.json")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "config", "bugzilla_instances.json")

mcp = FastMCP("bugzilla")

# 默认配置
DEFAULT_URL = os.environ.get("BUGZILLA_URL", "https://bugzilla.kernel.org")
API_KEY = os.environ.get("BUGZILLA_API_KEY", "")
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "0") == "1"


# ============================================================
# 跨 Skill 导入辅助
# ============================================================

def _import_from_core(names: list):
    """从 bug-core 导入指定名称"""
    try:
        import bug_core
        return [getattr(bug_core, n) for n in names]
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _core = os.path.join(_skills, "bug-core")
        if _core not in _sys.path:
            _sys.path.insert(0, _core)
        import bug_core
        return [getattr(bug_core, n) for n in names]


def _import_from_workspace(names: list):
    """从 bug-workspace 导入指定名称"""
    try:
        import bug_workspace
        return [getattr(bug_workspace, n) for n in names]
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _ws = os.path.join(_skills, "bug-workspace")
        if _ws not in _sys.path:
            _sys.path.insert(0, _ws)
        import bug_workspace
        return [getattr(bug_workspace, n) for n in names]


def _import_from_logs(names: list):
    """从 bug-logs 导入指定名称"""
    try:
        import bug_logs
        return [getattr(bug_logs, n) for n in names]
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _logs = os.path.join(_skills, "bug-logs")
        if _logs not in _sys.path:
            _sys.path.insert(0, _logs)
        import bug_logs
        return [getattr(bug_logs, n) for n in names]


# ============================================================
# 配置 & 工具
# ============================================================

def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _get_api_key_for_url(bugzilla_url: str) -> str:
    """根据URL匹配配置文件中的API key"""
    if API_KEY:
        return API_KEY
    config = _load_config()
    for inst_name, inst_cfg in config.get("instances", {}).items():
        if inst_cfg.get("base_url", "").rstrip("/") == bugzilla_url.rstrip("/"):
            return inst_cfg.get("api_key", "")
        if bugzilla_url.startswith(inst_cfg.get("base_url", "")):
            return inst_cfg.get("api_key", "")
    return ""


def _load_sample_bugs() -> list:
    try:
        with open(SAMPLE_BUGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _offline_bug_info(bug_id: int) -> str:
    """离线模式下查询Bug"""
    bugs = _load_sample_bugs()
    match = None
    for b in bugs:
        bid = b.get("bug_id", "")
        if bid.upper() == f"BUG-{bug_id}".upper() or str(b.get("bug_id", "")) == str(bug_id):
            match = b
            break
    if not match:
        return json.dumps({"error": f"Bug {bug_id} not found in offline data"}, ensure_ascii=False)
    result = {
        "id": match["bug_id"],
        "alias": [],
        "summary": match.get("title", ""),
        "status": match.get("status", ""),
        "resolution": "",
        "priority": match.get("priority", ""),
        "severity": match.get("severity", ""),
        "product": match.get("product", ""),
        "component": match.get("component", ""),
        "assignee": match.get("assignee", ""),
        "description": match.get("description", ""),
        "url": f"# (offline)",
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_headers(base_url: str = "") -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    key = _get_api_key_for_url(base_url) if base_url else API_KEY
    if key:
        headers["api_key"] = key
    return headers


# ============================================================
# MCP 工具: bug_info (bug-core)
# ============================================================

@mcp.tool()
def bug_info(bug_id: int, bugzilla_url: str = "") -> str:
    """获取Bug详细信息。bug_id为Bug编号，bugzilla_url为Bugzilla地址（可选，默认kernel）"""
    if OFFLINE_MODE:
        return _offline_bug_info(bug_id)

    base = bugzilla_url or DEFAULT_URL
    params = {"include_fields": "_all"}
    key = _get_api_key_for_url(base)
    if key:
        params["api_key"] = key

    try:
        resp = httpx.get(f"{base}/rest/bug/{bug_id}", params=params, headers=get_headers(base), timeout=15)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return json.dumps({"error": f"需要API Key才能访问 {base}，请设置 BUGZILLA_API_KEY 环境变量"}, ensure_ascii=False)
        elif e.response.status_code == 403:
            return json.dumps({"error": f"禁止访问 {base} (403 Forbidden)，该实例可能不对外开放"}, ensure_ascii=False)
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}"}, ensure_ascii=False)

    data = resp.json()

    bugs = data.get("bugs", [])
    if not bugs:
        return json.dumps({"error": f"Bug {bug_id} not found"}, ensure_ascii=False)

    bug = bugs[0]
    result = {
        "id": bug.get("id"),
        "alias": bug.get("alias", []),
        "summary": bug.get("summary", ""),
        "status": bug.get("status", ""),
        "resolution": bug.get("resolution", ""),
        "priority": bug.get("priority", ""),
        "severity": bug.get("severity", ""),
        "product": bug.get("product", ""),
        "component": bug.get("component", ""),
        "url": f"{base}/show_bug.cgi?id={bug_id}",
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================
# MCP 工具: bug_comments (bug-core)
# ============================================================

@mcp.tool()
def bug_comments(bug_id: int, bugzilla_url: str = "") -> str:
    """获取Bug评论。bug_id为Bug编号"""
    if OFFLINE_MODE:
        return json.dumps({"note": "离线模式下无评论数据"}, ensure_ascii=False, indent=2)

    base = bugzilla_url or DEFAULT_URL
    params = {}
    key = _get_api_key_for_url(base)
    if key:
        params["api_key"] = key

    try:
        resp = httpx.get(f"{base}/rest/bug/{bug_id}/comment", params=params, headers=get_headers(base), timeout=15)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return json.dumps({"error": f"需要API Key才能访问 {base}"}, ensure_ascii=False)
        return json.dumps({"error": f"HTTP {e.response.status_code}"}, ensure_ascii=False)
    data = resp.json()

    comments = []
    for bug_comments in data.get("bugs", {}).values():
        for c in bug_comments.get("comments", []):
            comments.append({
                "id": c.get("id"),
                "author": c.get("creator", ""),
                "time": c.get("time", ""),
                "text": c.get("text", "")[:500],
            })
        break

    return json.dumps(comments, ensure_ascii=False, indent=2)


# ============================================================
# MCP 工具: bugs_search (bug-core)
# ============================================================

@mcp.tool()
def bugs_search(query: str, bugzilla_url: str = "", limit: int = 10) -> str:
    """搜索Bug。query为搜索关键词，支持Bugzilla quicksearch语法"""
    if OFFLINE_MODE:
        search_bugs = _import_from_core(["search_bugs"])[0]
        results = search_bugs(keyword=query, limit=limit)
        out = []
        for b in results:
            out.append({
                "bug_id": b.get("bug_id"),
                "title": b.get("title"),
                "status": b.get("status"),
                "priority": b.get("priority"),
                "severity": b.get("severity"),
                "product": b.get("product"),
                "component": b.get("component"),
            })
        return json.dumps(out, ensure_ascii=False, indent=2)

    base = bugzilla_url or DEFAULT_URL
    params = {
        "quicksearch": query,
        "limit": limit,
        "include_fields": "id,summary,status,priority,product,component",
    }
    key = _get_api_key_for_url(base)
    if key:
        params["api_key"] = key

    try:
        resp = httpx.get(f"{base}/rest/bug", params=params, headers=get_headers(base), timeout=15)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return json.dumps({"error": f"需要API Key才能搜索 {base}"}, ensure_ascii=False)
        return json.dumps({"error": f"HTTP {e.response.status_code}"}, ensure_ascii=False)
    data = resp.json()

    bugs = data.get("bugs", [])
    results = []
    for b in bugs:
        results.append({
            "id": b.get("id"),
            "summary": b.get("summary", ""),
            "status": b.get("status", ""),
            "priority": b.get("priority", ""),
            "product": b.get("product", ""),
            "component": b.get("component", ""),
        })
    return json.dumps(results, ensure_ascii=False, indent=2)


# ============================================================
# MCP 工具: bug_comment_add (bug-core write)
# ============================================================

@mcp.tool()
def bug_comment_add(bug_id: int, comment_text: str, bugzilla_url: str = "",
                    new_status: str = "") -> str:
    """向Bug添加评论。comment_text为评论内容。

    Args:
        bug_id: Bug编号
        comment_text: 评论内容
        bugzilla_url: Bugzilla实例地址（可选）
        new_status: 如果提供，会同时更新状态并将评论合并进去（只产生一条comment）
    """
    if OFFLINE_MODE:
        return json.dumps({"error": "离线模式下不支持写操作"}, ensure_ascii=False)

    base = bugzilla_url or DEFAULT_URL
    params = {}
    key = _get_api_key_for_url(base)
    if key:
        params["api_key"] = key

    # 如果同时提供 new_status，使用组合模式
    if new_status:
        from bug_core import bug_commit
        result = bug_commit(str(bug_id), comment_text, new_status, instance=None)
        return json.dumps(result, ensure_ascii=False, indent=2)

    try:
        resp = httpx.post(
            f"{base}/rest/bug/{bug_id}/comment",
            params=params,
            json={"comment": comment_text},
            headers=get_headers(base),
            timeout=30
        )
        if resp.status_code in [200, 201]:
            data = resp.json()
            return json.dumps({
                "success": True,
                "comment_id": data.get("id"),
                "bug_id": bug_id,
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# MCP 工具: bug_status_update (bug-core write)
# ============================================================

@mcp.tool()
def bug_status_update(bug_id: int, new_status: str, comment_text: str = "",
                      bugzilla_url: str = "") -> str:
    """更新Bug状态。bug_id为Bug编号，new_status为简短状态名（如needinfo/resolved），
    comment_text为可选的状态变更说明"""
    if OFFLINE_MODE:
        return json.dumps({"error": "离线模式下不支持写操作"}, ensure_ascii=False)

    base = bugzilla_url or DEFAULT_URL
    params = {}
    key = _get_api_key_for_url(base)
    if key:
        params["api_key"] = key

    # 解析 instance 以获取 status_map
    config = _load_config()
    inst_config = {}
    for k, v in config.get("instances", {}).items():
        if v.get("base_url", "").rstrip("/") == base.rstrip("/"):
            inst_config = v
            break

    # 使用 status_map 解析状态名
    status_map = inst_config.get("status_map", {})
    resolved = new_status
    if new_status not in status_map.values():
        key_lower = new_status.lower().replace(" ", "_").replace("-", "_")
        if key_lower in status_map:
            resolved = status_map[key_lower]
        else:
            for k, v in status_map.items():
                if k.replace("_", "").lower() == new_status.replace("_", "").replace(" ", "").lower():
                    resolved = v
                    break

    body = {"status": resolved}
    if comment_text:
        body["comment"] = {"body": comment_text}
    else:
        body["comment"] = {"body": f"Status changed to {resolved}."}

    try:
        resp = httpx.put(
            f"{base}/rest/bug/{bug_id}",
            params=params,
            json=body,
            headers=get_headers(base),
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            bugs = data.get("bugs", [])
            actual_status = bugs[0].get("status", resolved) if bugs else resolved
            return json.dumps({
                "success": True,
                "bug_id": bug_id,
                "new_status": actual_status,
                "url": f"{base}/show_bug.cgi?id={bug_id}",
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# MCP 工具: bug_workspace (bug-workspace)
# ============================================================

@mcp.tool()
def bug_workspace(bug_id: int, bugzilla_url: str = "", base_path: str = "",
                  download_mode: str = "incremental",
                  normalize: str = "copy_new", copy_bug_z: bool = True) -> str:
    """创建Bug工作区 + UNC优先下载附件（v3.0）。

    获取Bug信息后，生成文件夹、.url快捷方式、UNC优先下载附件（rayfile FTP fallback）。

    Args:
        bug_id: Bug编号
        bugzilla_url: Bugzilla实例地址（可选，默认kernel）
        base_path: 工作区根目录（可选）
        download_mode: 下载模式 — "incremental"仅下载新增文件（默认）,
                       "full"完整覆盖下载, "skip"跳过下载仅创建文件夹
        normalize: 下载后规范化模式 "off"|"move"|"copy_new"（默认copy_new）
        copy_bug_z: 是否复制Bug Z模板（默认True）
    """
    if OFFLINE_MODE:
        bug_json = _offline_bug_info(bug_id)
        bug = json.loads(bug_json)
        if "error" in bug:
            return json.dumps({"error": f"Bug {bug_id} not found in offline data"}, ensure_ascii=False)
        bug["instance"] = None
    else:
        base = bugzilla_url or DEFAULT_URL
        params = {"include_fields": "_all"}
        key = _get_api_key_for_url(base)
        if key:
            params["api_key"] = key

        try:
            resp = httpx.get(f"{base}/rest/bug/{bug_id}", params=params, headers=get_headers(base), timeout=15)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return json.dumps({"error": f"API Key required for {base}"}, ensure_ascii=False)
            return json.dumps({"error": f"HTTP {e.response.status_code}"}, ensure_ascii=False)

        bug_data = resp.json()
        bugs = bug_data.get("bugs", [])
        if not bugs:
            return json.dumps({"error": f"Bug {bug_id} not found"}, ensure_ascii=False)

        bug = bugs[0]

        # 获取评论以提取FTP路径
        try:
            comment_resp = httpx.get(f"{base}/rest/bug/{bug_id}/comment", params=params, headers=get_headers(base), timeout=15)
            comment_resp.raise_for_status()
            comment_data = comment_resp.json()
            comments = []
            for bc in comment_data.get("bugs", {}).values():
                comments = bc.get("comments", [])
                break
        except Exception:
            comments = []

        # 提取FTP路径
        all_text = " ".join(c.get("text", "") for c in comments)
        ftp_urls = list(set(re.findall(r'ftp://[^\s)\]]+', all_text)))
        unc_paths = list(set(re.findall(r'\\\\[a-zA-Z0-9_.-]+\\(?:[^\s)\]]+\\)*[^\s)\]]+', all_text)))

        # 解析 instance name（从 base URL 匹配配置）
        inst_name = None
        config = _load_config()
        for k, v in config.get("instances", {}).items():
            if v.get("base_url", "").rstrip("/") == base.rstrip("/"):
                inst_name = k
                break

        constructed = {
            "bug_id": str(bug.get("id", bug_id)),
            "summary": bug.get("summary", ""),
            "status": bug.get("status", ""),
            "product": bug.get("product", ""),
            "component": bug.get("component", ""),
            "assignee": str(bug.get("assigned_to", "")),
            "url": f"{base}/show_bug.cgi?id={bug_id}",
            "ftp_urls": ftp_urls,
            "unc_paths": unc_paths,
            "instance": inst_name,
        }
        bug = constructed

    ws_base = base_path or get_default_workspace_path()

    if download_mode != "skip":
        # 使用编排函数：创建文件夹 + Bug Z 模板 + 下载附件（v3.0: UNC优先 + rayfile fallback）
        gwwd, get_default = _import_from_workspace(
            ["generate_workspace_with_download", "get_default_workspace_path"])
        ws_base = base_path or get_default()
        workspace = gwwd(
            bug=bug,
            base_path=ws_base,
            download_mode=download_mode,
            normalize_action=normalize,
            copy_bug_z=copy_bug_z,
        )
    else:
        # 仅创建文件夹（不下载）
        generate_workspace, get_default = _import_from_workspace(
            ["generate_workspace", "get_default_workspace_path"])
        ws_base = base_path or get_default()
        workspace = generate_workspace(bug, base_path=ws_base)

    return json.dumps(workspace, ensure_ascii=False, indent=2)


# ============================================================
# MCP 工具: generate_reply (customer reply template)
# ============================================================

@mcp.tool()
def generate_reply(bug_id: int = 0, platform: str = "UMS512",
                   bug_summary: str = "", content: str = "", extra: str = "") -> str:
    """生成客户回复预览。SPCSS bug 自动匹配 Dear CUS 格式，写入本地文件供用户 review。
    用户修改确认后再调用 send_reply 提交。

    Args:
        bug_id: Bug编号
        platform: 平台名称（如 UMS512）
        bug_summary: Bug摘要
        content: 用户要回复的实际内容
        extra: 额外字段，JSON字符串格式
    """
    if OFFLINE_MODE:
        return json.dumps({"error": "离线模式下不支持回复生成"}, ensure_ascii=False)

    try:
        from bug_core import prepare_customer_reply
    except ImportError:
        import sys as _sys
        _skills = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _core = os.path.join(_skills, "bug-core")
        if _core not in _sys.path:
            _sys.path.insert(0, _core)
        from bug_core import prepare_customer_reply

    result = prepare_customer_reply(
        bug_id=str(bug_id),
        content=content or bug_summary,
        platform=platform,
    )

    if result.get("success"):
        lines = [
            f"Bug {result['bug_id']} -> 回复预览已写入文件",
            "=" * 60,
            f"文件: {result['filepath']}",
            "-" * 60,
            result["reply"],
            "-" * 60,
        ]
        return json.dumps({
            "formatted": "\n".join(lines),
            "filepath": result["filepath"],
            "reply": result["reply"],
        }, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"error": result.get("error", "Unknown error")}, ensure_ascii=False)


# ============================================================
# MCP 工具: bug_logs (⚠️ DEPRECATED — 请使用 bug_workspace)
# ============================================================

@mcp.tool()
def bug_logs(bug_id: int, bugzilla_url: str = "",
             download: bool = False, dest_dir: str = "",
             refresh: bool = False, normalize: str = "copy_new") -> str:
    """⚠️ DEPRECATED — 请使用 bug_workspace 工具代替（支持 download_mode 参数）。

    获取Bug的日志目录列表或下载附件。
    所有功能已合并到 bug_workspace v3.0，此工具保留仅为向后兼容。

    无 download 时（默认）:
      1. 解析bug报告中的结构化字段（LogPath、LogType、VersionPath、OccurTime等）
      2. 列出LogPath目录下的日志文件（文件名、大小、类型）
      3. 返回AI可调用的结构化信息，帮助根据文件名/修改时间等手段识别相关日志

    有 download=True 时:
      智能检测附件类型（UNC路径或FTP/rayfile），自动下载到指定目录。

    Args:
        bug_id: Bug编号
        bugzilla_url: Bugzilla实例地址（可选，默认kernel）
        download: 是否执行下载附件（默认False）
        dest_dir: 下载目标目录（download=True时必填）
        refresh: 下载时是否清空已有附件（默认False）
        normalize: 下载后规范化模式 "off"|"move"|"copy_new"（默认copy_new）
    """
    if OFFLINE_MODE:
        if download:
            return json.dumps({"error": "bug_logs下载模式不支持离线"}, ensure_ascii=False)
        return json.dumps({"error": "bug_logs不支持离线模式，请使用真实Bugzilla实例"}, ensure_ascii=False)

    base = bugzilla_url or DEFAULT_URL

    # 下载模式（v3.0: 从 bug_workspace 导入，所有下载功能已迁移）
    if download:
        if not dest_dir:
            return json.dumps({"error": "download=True时必填dest_dir参数"}, ensure_ascii=False)

        download_bug_attachments = _import_from_workspace(["download_bug_attachments"])[0]
        # Resolve instance name from base URL
        config = _load_config()
        inst_name = None
        for k, v in config.get("instances", {}).items():
            if v.get("base_url", "").rstrip("/") == base.rstrip("/"):
                inst_name = k
                break

        # Map old refresh param to download_mode
        mode = "full" if refresh else "incremental"
        result = download_bug_attachments(
            bug_id=str(bug_id),
            dest_dir=dest_dir,
            instance=inst_name,
            download_mode=mode,
            normalize_action=normalize,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    # List mode（v3.0: 从 bug_workspace 导入，所有结构化解析功能已迁移）
    parse_unisoc_structured_fields, list_log_directory = _import_from_workspace(
        ["parse_unisoc_structured_fields", "list_log_directory"])
    get_instance_config, load_config = _import_from_core(["get_instance_config", "load_config"])

    # Get instance config
    try:
        inst_name, inst_config = get_instance_config(
            next((k for k, v in load_config().get("instances", {}).items()
                  if v.get("base_url", "").rstrip("/") == base.rstrip("/")), None)
        )
    except (ValueError, StopIteration):
        inst_config = {}

    # Fetch bug info
    params = {"include_fields": "_all"}
    key = _get_api_key_for_url(base)
    if key:
        params["api_key"] = key

    try:
        resp = httpx.get(f"{base}/rest/bug/{bug_id}", params=params, headers=get_headers(base), timeout=15)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}"}, ensure_ascii=False)

    bug_data = resp.json()
    bugs = bug_data.get("bugs", [])
    if not bugs:
        return json.dumps({"error": f"Bug {bug_id} not found"}, ensure_ascii=False)

    bug = bugs[0]

    # Fetch comments
    try:
        comment_resp = httpx.get(f"{base}/rest/bug/{bug_id}/comment", params=params, headers=get_headers(base), timeout=15)
        comment_resp.raise_for_status()
        comment_data = comment_resp.json()
        comments = []
        for bc in comment_data.get("bugs", {}).values():
            comments = bc.get("comments", [])
            break
    except Exception:
        comments = []

    # Parse structured fields from first comment
    structured = {}
    log_directory = None
    if comments:
        first_text = comments[0].get("text", "")
        structured = parse_unisoc_structured_fields(first_text)
        log_path = structured.get("log_path", "")
        if log_path and structured.get("has_structured_format"):
            log_directory = list_log_directory(log_path, config=inst_config)

    # Build response
    result = {
        "bug_info": {
            "id": bug.get("id"),
            "summary": bug.get("summary", ""),
            "status": bug.get("status", ""),
            "product": bug.get("product", ""),
            "component": bug.get("component", ""),
            "url": f"{base}/show_bug.cgi?id={bug_id}",
        },
        "structured_fields": {
            "has_structured_format": structured.get("has_structured_format", False),
            "log_name": structured.get("log_name", ""),
            "log_path": structured.get("log_path", ""),
            "log_servers": structured.get("log_servers", {}),
            "log_type": structured.get("log_type", ""),
            "occur_time": structured.get("occur_time", ""),
            "version_path": structured.get("version_path", ""),
            "header": structured.get("header", {}),
        },
        "log_directory": log_directory,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
