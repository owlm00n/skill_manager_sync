#!/usr/bin/env python3
"""
Bug Core - Bugzilla Bug查询核心模块
支持多模式：web_fetch / REST API / 手动输入
支持多实例：kernel / mozilla / unisoc 等

部署流程：
1. pip install requests beautifulsoup4 lxml
2. 配置 config/bugzilla_instances.json
3. 通过 Claw Skill 或独立运行
"""

import json
import os
import re
import sys
from typing import Optional

# 配置路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "bugzilla_instances.json")
SAMPLE_BUGS_PATH = os.path.join(SCRIPT_DIR, "data", "sample_bugs.json")

# 非法文件名字符
INVALID_CHARS = r'[<>:"/\\|?*\n\r\t]'

# 离线模式标记：通过环境变量 OFFLINE_MODE=1 或 --offline 参数启用
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "0") == "1"


# ============================================================
# Report naming — 从 common.report_utils 导入（单一数据源）
# ============================================================
try:
    _skills_dir = os.path.dirname(SCRIPT_DIR)
    _common = os.path.join(_skills_dir, "common")
    if _common not in sys.path:
        sys.path.insert(0, _common)
    from report_utils import generate_report_filename as _gen_report
    from report_utils import generate_report_filename_from_bug as _gen_report_from_bug
except ImportError:
    # Fallback: 内联实现（当 common 模块不存在时）
    def _gen_report(topic: str, report_type: str, keyword: str, date_str: str = None) -> str:
        from datetime import datetime
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        def _clean(s): return re.sub(INVALID_CHARS, '_', str(s))
        return f"{_clean(topic)}_{_clean(report_type)}_{_clean(keyword)}__{_clean(date_str)}.md"

    def _gen_report_from_bug(bug: dict, report_type: str, keyword: str, date_str: str = None) -> str:
        alias_list = bug.get("alias", [])
        topic = alias_list[0] if alias_list else str(bug.get("bug_id", "?"))
        return _gen_report(topic, report_type, keyword, date_str)


def generate_report_filename(bug_id: str, report_type: str, keyword: str, date_str: str = None) -> str:
    """生成标准化报告文件名（Bug 场景兼容封装）。

    格式: {bug_id}_{type}_{keyword}__{YYYYMMDD}.md
    实际委托给 common.report_utils.generate_report_filename(topic=bug_id, ...)
    """
    return _gen_report(bug_id, report_type, keyword, date_str)


def generate_report_filename_from_bug(bug: dict, report_type: str, keyword: str, date_str: str = None) -> str:
    """从 Bug dict 生成标准化报告文件名（便捷封装）。

    委托给 common.report_utils.generate_report_filename_from_bug()
    """
    return _gen_report_from_bug(bug, report_type, keyword, date_str)


def load_config() -> dict:
    """加载Bugzilla实例配置"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_instance_config(instance_name: str = None) -> dict:
    """获取指定实例配置"""
    config = load_config()
    if instance_name is None:
        instance_name = config.get("default_instance", "kernel")
    instances = config.get("instances", {})
    if instance_name not in instances:
        raise ValueError(f"未知实例: {instance_name}, 可用: {list(instances.keys())}")
    return instance_name, instances[instance_name]


# ============================================================
# 模式D：离线模拟数据查询（无需联网）
# ============================================================

def _load_sample_bugs() -> list:
    """加载离线模拟Bug数据"""
    try:
        with open(SAMPLE_BUGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def fetch_bug_offline(bug_id: str) -> dict:
    """通过离线模拟数据查询Bug（无需网络）"""
    bugs = _load_sample_bugs()
    match = None
    for b in bugs:
        if b.get("bug_id", "").upper() == bug_id.upper():
            match = b
            break
    if not match:
        return {"error": f"离线模式下未找到 Bug {bug_id}"}

    return {
        "source": "offline:sample",
        "instance": "local",
        "bug_id": match["bug_id"],
        "alias": [],
        "summary": match.get("title", ""),
        "raw_title": f"{match['bug_id']} - {match.get('title', '')}",
        "status": match.get("status", ""),
        "resolution": "",
        "priority": match.get("priority", ""),
        "severity": match.get("severity", ""),
        "product": match.get("product", ""),
        "component": match.get("component", ""),
        "assignee": match.get("assignee", ""),
        "reporter": match.get("reporter", ""),
        "module": match.get("module", ""),
        "description": match.get("description", ""),
        "attachment_hint": match.get("attachment_hint", ""),
        "tags": match.get("tags", []),
        "update_time": match.get("update_time", ""),
        "url": f"# (离线模式)",
    }


# ============================================================
# 模式A：REST API 查询（直接HTTP请求）
# ============================================================

# Unicase 工单号正则：unicase + 数字（如 unicase015809）
UNICASE_ID_PATTERN = re.compile(r'^unicase(\d+)$', re.IGNORECASE)


def _is_unicase_id(bug_id: str) -> bool:
    """判断是否为 Unicase 工单号格式（unicase\d+）"""
    return bool(UNICASE_ID_PATTERN.match(str(bug_id)))


def _resolve_unicase_id(rest_url: str, api_key: str, unicase_id: str) -> Optional[str]:
    """通过 REST API quicksearch/alias 将 Unicase 工单号解析为 Bugzilla Bug ID。

    Unicase 工单通过 Bugzilla 的 alias 字段与 SPCSS Bug 关联。
    搜索策略：
    1. quicksearch=unicaseXXXXXX（Bugzilla 全文搜索）
    2. alias=unicaseXXXXXX（Bugzilla alias 精确匹配）

    Returns:
        解析到的 Bugzilla Bug ID 字符串，未找到返回 None
    """
    import requests as _requests

    params = {}
    if api_key:
        params["api_key"] = api_key

    for method, param_key in [("quicksearch", "quicksearch"), ("alias", "alias")]:
        try:
            search_params = {**params, param_key: unicase_id}
            resp = _requests.get(
                f"{rest_url}/bug",
                params=search_params,
                headers={"Accept": "application/json"},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            bugs = data.get("bugs", [])
            if bugs:
                resolved_id = str(bugs[0].get("id", ""))
                if resolved_id:
                    return resolved_id
        except Exception:
            continue

    return None


def fetch_bug_rest(bug_id: str, instance: str = None) -> dict:
    """通过REST API获取Bug信息。

    自动识别 Unicase 工单号（unicase\d+ 格式），通过 quicksearch/alias 解析为 Bugzilla Bug ID。
    """
    if OFFLINE_MODE:
        return fetch_bug_offline(bug_id)

    # Handle "local" instance (alias for offline)
    if instance == "local":
        return fetch_bug_offline(bug_id)

    import requests

    inst_name, inst_config = get_instance_config(instance)
    rest_url = inst_config["rest_url"]
    api_key = inst_config.get("api_key", "")

    params = {"include_fields": "_all"}
    if api_key:
        params["api_key"] = api_key

    # === Unicase 工单号自动解析 ===
    original_bug_id = bug_id
    if _is_unicase_id(bug_id):
        resolved = _resolve_unicase_id(rest_url, api_key, bug_id)
        if resolved:
            bug_id = resolved
        else:
            return {"error": f"Unicase 工单号 {original_bug_id} 未找到关联的 Bugzilla Bug，请确认工单号是否正确"}

    # 获取Bug信息
    bug_resp = requests.get(
        f"{rest_url}/bug/{bug_id}",
        params=params,
        headers={"Accept": "application/json"},
        timeout=15
    )
    bug_resp.raise_for_status()
    bug_data = bug_resp.json()

    bugs = bug_data.get("bugs", [])
    if not bugs:
        return {"error": f"Bug {bug_id} 不存在或无权限访问"}

    bug = bugs[0]

    # 获取评论
    try:
        # 评论端点不支持 include_fields=_all，只用 api_key
        comment_params = {}
        if api_key:
            comment_params["api_key"] = api_key
        comment_resp = requests.get(
            f"{rest_url}/bug/{bug_id}/comment",
            params=comment_params,
            headers={"Accept": "application/json"},
            timeout=15
        )
        comment_resp.raise_for_status()
        comment_data = comment_resp.json()
        comments = []
        for bug_comments in comment_data.get("bugs", {}).values():
            comments = bug_comments.get("comments", [])
            break
    except Exception:
        comments = []

    # 提取附件路径（unisoc Bugzilla特有）
    ftp_paths = []
    ftp_urls = []
    unc_paths = []
    if comments:
        # 扫描所有评论（通常第一条评论包含FTP/UNC路径）
        all_text = " ".join(c.get("text", "") for c in comments)
        # 提取 ftp:// URL
        ftp_urls = list(set(re.findall(r'ftp://[^\s)\]]+', all_text)))
        # 提取 UNC 路径 (\\server\share\...)
        unc_paths = list(set(re.findall(r'\\\\[a-zA-Z0-9_.-]+\\(?:[^\s)\]]+\\)*[^\s)\]]+', all_text)))
        # 提取 下载附件 路径
        attachment_match = re.search(r'下载附件:\s*([^\n]+)', all_text)
        if attachment_match:
            ftp_paths.append(attachment_match.group(1).strip())
        # 合并所有FTP路径
        ftp_path = ftp_paths[0] if ftp_paths else (ftp_urls[0] if ftp_urls else (unc_paths[0] if unc_paths else ""))

    path_url = ""
    if comments:
        all_text = " ".join(c.get("text", "") for c in comments)
        url_match = re.search(r'或使用快捷链接下载.*?:\s*(https?://[^\s]+)', all_text)
        if not url_match:
            url_match = re.search(r'(https?://unitrans\.unisoc\.com/share/[^\s)\]]+)', all_text)
        if url_match:
            path_url = url_match.group(1).strip()

    # 构建 raw_title (匹配原工具 fetch_summary 格式)
    bug_id_str = str(bug.get("id", bug_id))
    alias_list = bug.get("alias", [])
    summary = bug.get("summary", "")
    if alias_list:
        raw_title = f"{bug_id_str}({alias_list[0]}) - {summary}"
    else:
        raw_title = f"{bug_id_str} - {summary}"

    # 构建结果
    result = {
        "source": f"rest_api:{inst_name}",
        "instance": inst_name,
        "bug_id": bug_id_str,
        "alias": alias_list,
        "original_unicase_id": original_bug_id if original_bug_id != bug_id_str else None,
        "summary": summary,
        "raw_title": raw_title,
        "status": bug.get("status", ""),
        "resolution": bug.get("resolution", ""),
        "priority": bug.get("priority", ""),
        "severity": bug.get("severity", ""),
        "product": bug.get("product", ""),
        "component": bug.get("component", ""),
        "assignee": "",
        "reporter": "",
        "creation_time": bug.get("creation_time", ""),
        "last_change_time": bug.get("last_change_time", ""),
        "url": f"{inst_config['base_url']}/show_bug.cgi?id={bug_id}",
        "comments": comments,
        "comments_count": len(comments),
        "first_comment": comments[0].get("text", "") if comments else "",
        "last_comment": comments[-1].get("text", "") if comments else "",
        "ftp_path": ftp_path,
        "ftp_urls": ftp_urls,
        "unc_paths": unc_paths,
        "path_url": path_url,
        # 分支/版本信息（SPCSS Bugzilla自定义字段）
        "base_on_ver": bug.get("cf_base_on_ver", ""),
        "fix_on_ver": bug.get("cf_fix_on_ver", ""),
        "branch_to_merge": bug.get("cf_branchtobemerged", ""),
    }

    # 提取 assignee / reporter
    assigned = bug.get("assigned_to", "")
    if isinstance(assigned, dict):
        assigned = assigned.get("name", str(assigned))
    result["assignee"] = str(assigned)

    reported = bug.get("reporter", "")
    if isinstance(reported, dict):
        reported = reported.get("name", str(reported))
    result["reporter"] = str(reported)

    return result


def fetch_bugs_batch(
    query_params: dict,
    instance: str = None,
    include_comments: bool = True,
    include_history: bool = True,
    page_size: int = 500,
    max_results: int = None,
    progress_callback: callable = None,
) -> dict:
    """批量查询 Bugzilla Bug（搜索+过滤），返回完整 Bug 数据。

    通过 Bugzilla REST API 的搜索端点批量查询 Bug，
    支持分页、逐 Bug 获取评论和历史记录。

    Args:
        query_params: Bugzilla 搜索参数 dict，支持:
            - product, component, status, priority, severity
            - assigned_to, creator, qa_contact
            - creation_time, last_change_time (ISO 8601 或相对时间)
            - limit, offset (由本函数管理分页，外部传入的 limit/offset 会被忽略)
            - 其他 Bugzilla REST API 支持的搜索参数
        instance: Bugzilla 实例名（默认使用配置中的 default_instance）
        include_comments: 是否拉取每个 Bug 的评论
        include_history: 是否拉取每个 Bug 的变更历史
        page_size: 每页 Bug 数量（Bugzilla 默认上限 1000）
        max_results: 最大返回 Bug 数，None=全部
        progress_callback: 进度回调 fn(phase, current, total)
            phase: "search" | "comments" | "history"

    Returns:
        {
            "bugs": [
                {
                    "id": 123456,
                    "fields": {...},       # 所有 Bug 字段
                    "comments": [...],     # 评论列表（include_comments=False 时为空列表）
                    "history": [...]       # 历史记录列表（include_history=False 时为空列表）
                },
                ...
            ],
            "query_info": {
                "total_matches": 1234,    # 服务端返回的总匹配数（可能为 None）
                "returned": 500,          # 实际返回数
                "has_more": True,         # 是否还有更多结果（被 max_results 截断）
                "params": {...},          # 使用的查询参数（回显）
                "instance": "unisoc",
                "fetched_at": "2025-11-02T10:00:00"
            },
            "errors": []                  # 非致命错误列表
        }
    """
    if OFFLINE_MODE:
        return {
            "bugs": [],
            "query_info": {
                "total_matches": 0, "returned": 0, "has_more": False,
                "params": query_params, "instance": instance or "local",
                "fetched_at": _now_iso(),
            },
            "errors": [{"error": "OFFLINE_MODE is enabled, batch query not available"}]
        }

    if instance == "local":
        return {
            "bugs": [],
            "query_info": {
                "total_matches": 0, "returned": 0, "has_more": False,
                "params": query_params, "instance": "local",
                "fetched_at": _now_iso(),
            },
            "errors": [{"error": "local instance does not support batch query"}]
        }

    import requests

    inst_name, inst_config = get_instance_config(instance)
    rest_url = inst_config["rest_url"]
    api_key = inst_config.get("api_key", "")
    base_url = inst_config.get("base_url", "")
    status_map = inst_config.get("status_map", {})

    # 构建 API 请求参数（排除 limit/offset，由分页逻辑管理）
    params = {"include_fields": "_all"}
    if api_key:
        params["api_key"] = api_key
    for key, value in query_params.items():
        if key in ("limit", "offset"):
            continue
        params[key] = value

    # ============================================================
    # Phase 1: 分页搜索
    # ============================================================
    all_bugs_raw = []
    total_matches = None
    errors = []
    offset = 0

    while True:
        if max_results is not None and len(all_bugs_raw) >= max_results:
            break

        page_params = dict(params)
        page_params["limit"] = page_size
        page_params["offset"] = offset

        try:
            resp = requests.get(
                f"{rest_url}/bug",
                params=page_params,
                headers={"Accept": "application/json"},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            errors.append({
                "phase": "search",
                "offset": offset,
                "error": str(e)
            })
            break

        bugs_page = data.get("bugs", [])
        if not bugs_page:
            break

        all_bugs_raw.extend(bugs_page)

        # 尝试获取 total_matches（Bugzilla 可能在首个响应中返回）
        if total_matches is None:
            # Bugzilla REST API 不直接返回 total，从响应推断
            pass

        if progress_callback:
            progress_callback("search", len(all_bugs_raw), max_results or 0)

        # 如果返回数少于 page_size，说明已是最后一页
        if len(bugs_page) < page_size:
            break

        offset += page_size

    total_found = len(all_bugs_raw)
    if progress_callback:
        progress_callback("search", total_found, max_results or total_found)

    # ============================================================
    # Phase 2: 逐 Bug 获取 comments
    # ============================================================
    bugs_with_comments = {}
    if include_comments and all_bugs_raw:
        for i, bug in enumerate(all_bugs_raw):
            bug_id = bug.get("id")
            if not bug_id:
                continue

            if progress_callback and i % 10 == 0:
                progress_callback("comments", i + 1, total_found)

            try:
                comment_resp = requests.get(
                    f"{rest_url}/bug/{bug_id}/comment",
                    params={"api_key": api_key} if api_key else {},
                    headers={"Accept": "application/json"},
                    timeout=15
                )
                comment_resp.raise_for_status()
                comment_data = comment_resp.json()
                comments = []
                for bug_comments in comment_data.get("bugs", {}).values():
                    comments = bug_comments.get("comments", [])
                    break
                bugs_with_comments[str(bug_id)] = comments
            except Exception as e:
                bugs_with_comments[str(bug_id)] = []
                errors.append({
                    "phase": "comments",
                    "bug_id": bug_id,
                    "error": str(e)
                })

        if progress_callback:
            progress_callback("comments", total_found, total_found)

    # ============================================================
    # Phase 3: 逐 Bug 获取 history
    # ============================================================
    bugs_with_history = {}
    if include_history and all_bugs_raw:
        for i, bug in enumerate(all_bugs_raw):
            bug_id = bug.get("id")
            if not bug_id:
                continue

            if progress_callback and i % 10 == 0:
                progress_callback("history", i + 1, total_found)

            try:
                history_resp = requests.get(
                    f"{rest_url}/bug/{bug_id}/history",
                    params={"api_key": api_key} if api_key else {},
                    headers={"Accept": "application/json"},
                    timeout=15
                )
                history_resp.raise_for_status()
                history_data = history_resp.json()
                # history 返回格式: {"bugs": [{"id": ..., "history": [...]}]}
                history_entries = []
                for h_bug in history_data.get("bugs", []):
                    if str(h_bug.get("id")) == str(bug_id):
                        history_entries = h_bug.get("history", [])
                        break
                bugs_with_history[str(bug_id)] = history_entries
            except Exception as e:
                bugs_with_history[str(bug_id)] = []
                errors.append({
                    "phase": "history",
                    "bug_id": bug_id,
                    "error": str(e)
                })

        if progress_callback:
            progress_callback("history", total_found, total_found)

    # ============================================================
    # Phase 4: 组装结果
    # ============================================================
    bugs_result = []
    for bug in all_bugs_raw:
        bug_id = bug.get("id")
        bug_id_str = str(bug_id)

        # 提取 assignee / reporter（可能是字符串或 dict）
        assigned = bug.get("assigned_to", "")
        if isinstance(assigned, dict):
            assigned = assigned.get("name", str(assigned))

        reported = bug.get("reporter", "")
        if isinstance(reported, dict):
            reported = reported.get("name", str(reported))

        # 状态标准化
        raw_status = bug.get("status", "")
        normalized_status = status_map.get(raw_status.lower().replace(" ", "_"), raw_status)

        # 构建 fields dict（保留所有原始字段 + 标准化后的字段）
        fields = {
            "id": bug_id,
            "alias": bug.get("alias", []),
            "summary": bug.get("summary", ""),
            "status": normalized_status,
            "status_raw": raw_status,
            "resolution": bug.get("resolution", ""),
            "product": bug.get("product", ""),
            "component": bug.get("component", ""),
            "version": bug.get("version", ""),
            "platform": bug.get("platform", ""),
            "op_sys": bug.get("op_sys", ""),
            "priority": bug.get("priority", ""),
            "severity": bug.get("severity", ""),
            "assigned_to": str(assigned),
            "reporter": str(reported),
            "qa_contact": bug.get("qa_contact", ""),
            "target_milestone": bug.get("target_milestone", ""),
            "creation_time": bug.get("creation_time", ""),
            "last_change_time": bug.get("last_change_time", ""),
            "is_open": bug.get("is_open", True),
            "url": f"{base_url}/show_bug.cgi?id={bug_id}" if base_url else "",
            # 自定义字段
            "cf_come_from": bug.get("cf_come_from", ""),
            "cf_root_cause": bug.get("cf_root_cause", ""),
            "cf_solution": bug.get("cf_solution", ""),
            "cf_base_on_ver": bug.get("cf_base_on_ver", ""),
            "cf_fix_on_ver": bug.get("cf_fix_on_ver", ""),
            "cf_branchtobemerged": bug.get("cf_branchtobemerged", ""),
        }

        bugs_result.append({
            "id": bug_id,
            "fields": fields,
            "comments": bugs_with_comments.get(bug_id_str, []),
            "history": bugs_with_history.get(bug_id_str, []),
        })

    # 按 max_results 截断
    has_more = False
    if max_results is not None and len(bugs_result) > max_results:
        bugs_result = bugs_result[:max_results]
        has_more = True

    return {
        "bugs": bugs_result,
        "query_info": {
            "total_matches": total_found,  # 实际获取到的总数
            "returned": len(bugs_result),
            "has_more": has_more,
            "params": {k: v for k, v in query_params.items() if k not in ("limit", "offset")},
            "instance": inst_name,
            "fetched_at": _now_iso(),
        },
        "errors": errors,
    }


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================
# 写操作：Post Comment / Update Status / Commit
# ============================================================

def _resolve_status(instance_name: str, inst_config: dict, new_status: str) -> str:
    """将简短状态名（如 needinfo）解析为实例实际状态名（如 Need_Info）"""
    status_map = inst_config.get("status_map", {})
    # 先尝试直接匹配
    if new_status in status_map.values():
        return new_status
    # 再尝试 key 映射
    key = new_status.lower().replace(" ", "_").replace("-", "_")
    if key in status_map:
        return status_map[key]
    # 最后做模糊匹配
    for k, v in status_map.items():
        if k.replace("_", "").lower() == new_status.replace("_", "").replace(" ", "").lower():
            return v
    # 无匹配则返回原值，由 API 自行报错
    return new_status


def _check_recent_comments(bug_id: str, comment_text: str, instance: str = None,
                           lookback_minutes: int = 10) -> dict:
    """检查最近评论中是否已有相同内容（幂等性检查）。

    在 POST/PUT 超时后调用，判断操作是否已在服务端生效，
    避免因超时重试导致重复评论。

    Args:
        bug_id: Bug ID
        comment_text: 待检查的评论内容
        instance: Bugzilla 实例名
        lookback_minutes: 回溯时间窗口（分钟），默认10分钟

    Returns:
        {"found": False} 或 {"found": True, "comment_id": ..., "duplicate_info": ...}
    """
    import requests as _requests
    from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone

    try:
        inst_name, inst_config = get_instance_config(instance)
        rest_url = inst_config["rest_url"]
        api_key = inst_config.get("api_key", "")
    except Exception:
        return {"found": False, "error": "Failed to get instance config"}

    params = {}
    if api_key:
        params["api_key"] = api_key

    try:
        resp = _requests.get(
            f"{rest_url}/bug/{bug_id}/comment",
            params=params,
            headers={"Accept": "application/json"},
            timeout=30
        )
        if resp.status_code != 200:
            return {"found": False, "error": f"HTTP {resp.status_code} when checking comments"}

        data = resp.json()
        comments = data.get("bugs", {}).get(str(bug_id), {}).get("comments", [])
    except Exception as e:
        return {"found": False, "error": f"Failed to fetch comments: {e}"}

    # Normalize the candidate text for comparison
    def _normalize(text: str) -> str:
        if not text:
            return ""
        return text.strip().replace("\r\n", "\n").replace("\r", "\n")

    normalized_candidate = _normalize(comment_text)
    if not normalized_candidate:
        return {"found": False}

    # Calculate time window
    now = _datetime.now(_timezone.utc)
    cutoff_time = now - _timedelta(minutes=lookback_minutes)

    for c in reversed(comments):  # Check most recent first
        creation_time_str = c.get("creation_time", "")
        try:
            creation_time = _datetime.fromisoformat(creation_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        # Skip comments outside the lookback window
        if creation_time < cutoff_time:
            continue

        comment_text_existing = c.get("text", "")
        normalized_existing = _normalize(comment_text_existing)

        # Exact match on normalized text
        if normalized_existing == normalized_candidate:
            return {
                "found": True,
                "comment_id": c.get("id"),
                "comment_count": c.get("count"),
                "creation_time": creation_time_str,
                "creator": c.get("creator"),
                "message": (
                    f"Duplicate comment detected: already posted as "
                    f"comment #{c.get('count')} (id={c.get('id')}) "
                    f"at {creation_time_str}"
                ),
            }

    return {"found": False}


def post_comment(bug_id: str, comment_text: str, instance: str = None,
                 send_mode: str = None) -> dict:
    """向 Bug 添加评论（REST API POST）。

    Args:
        bug_id: Bug ID
        comment_text: 评论内容
        instance: Bugzilla 实例名
        send_mode: 发送模式。
            - 'preview' (默认): 只写本地预览文件，不发送。需用户确认后手动设置 send_mode='live'
            - 'live': 实际发送到 Bugzilla
    """
    # 默认 send_mode 从环境变量读取，环境变量未设置则默认 'preview'
    if send_mode is None:
        send_mode = os.environ.get("BUGZILLA_SEND_MODE", "preview")

    if send_mode == "preview":
        # 写入本地预览文件，不发送
        safe_id = bug_id.replace("/", "_").replace("\\", "_") if bug_id else "preview"
        filename = f"reply_{safe_id}_preview.txt"
        filepath = _resolve_reply_filepath(bug_id, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Reply Preview (NOT SENT)\n")
            f.write(f"Bug: {bug_id}\n")
            f.write(f"Mode: preview (send_mode='live' to actually send)\n")
            f.write(f"---\n\n")
            f.write(comment_text + "\n")
        try:
            os.startfile(filepath)
        except Exception:
            pass
        return {
            "success": True,
            "mode": "preview",
            "bug_id": bug_id,
            "filepath": filepath,
            "message": "预览已生成，请审核。确认后设置 send_mode='live' 或设置环境变量 BUGZILLA_SEND_MODE=live 发送。",
        }

    if OFFLINE_MODE or instance == "local":
        return {"error": "离线模式下不支持写操作"}

    import requests
    inst_name, inst_config = get_instance_config(instance)
    rest_url = inst_config["rest_url"]
    api_key = inst_config.get("api_key", "")

    params = {}
    if api_key:
        params["api_key"] = api_key

    try:
        resp = requests.post(
            f"{rest_url}/bug/{bug_id}/comment",
            params=params,
            json={"comment": comment_text},
            headers={"Accept": "application/json"},
            timeout=120
        )
        if resp.status_code in [200, 201]:
            data = resp.json()
            return {
                "success": True,
                "mode": "live",
                "comment_id": data.get("id"),
                "bug_id": bug_id,
                "instance": inst_name,
            }
        else:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    except Exception as e:
        # Idempotency check: a timeout/client error does NOT mean the
        # server didn't process the request. Verify whether the comment
        # was actually posted before reporting failure.
        dedup = _check_recent_comments(bug_id, comment_text, instance)
        if dedup.get("found"):
            return {
                "success": True,
                "mode": "live",
                "comment_id": dedup.get("comment_id"),
                "bug_id": bug_id,
                "instance": inst_name,
                "dedup_detected": True,
                "original_error": str(e),
                "note": (
                    f"Request failed with '{str(e)[:100]}' but comment was "
                    f"already posted (id={dedup.get('comment_id')}). "
                    f"No duplicate was created."
                ),
            }
        return {"error": str(e)}


def update_bug_status(bug_id: str, new_status: str, comment_text: str = None,
                      instance: str = None, custom_fields: dict = None) -> dict:
    """更新 Bug 状态（REST API PUT）。

    Args:
        bug_id: Bug ID
        new_status: 目标状态（简短名，如 rootcaused/fixed/needinfo）
        comment_text: 评论内容
        instance: Bugzilla 实例名
        custom_fields: 自定义字段 dict，如 {"cf_root_cause": "...", "cf_resolution": "..."}
    """
    if OFFLINE_MODE or instance == "local":
        return {"error": "离线模式下不支持写操作"}

    import requests
    inst_name, inst_config = get_instance_config(instance)
    rest_url = inst_config["rest_url"]
    api_key = inst_config.get("api_key", "")

    # 解析状态名
    resolved_status = _resolve_status(inst_name, inst_config, new_status)

    # === custom_fields 必填校验 ===
    required_fields_config = inst_config.get("status_required_fields", {})
    required_fields = required_fields_config.get(resolved_status, {})
    if required_fields:
        if not custom_fields:
            missing = [required_fields[k] for k in required_fields]
            return {
                "error": f"Status '{resolved_status}' requires custom_fields: {missing}. "
                         f"Pass custom_fields={{'cf_root_cause': '...', 'cf_resolution': '...', ...}}"
            }
        for cf_key, cf_label in required_fields.items():
            if cf_key not in custom_fields or not custom_fields[cf_key]:
                return {
                    "error": f"Status '{resolved_status}' requires '{cf_label}' ({cf_key}) but it is missing or empty."
                }

    params = {}
    if api_key:
        params["api_key"] = api_key

    body = {"status": resolved_status}
    if comment_text:
        body["comment"] = {"body": comment_text}
    else:
        body["comment"] = {"body": f"Status changed to {resolved_status}."}

    # 合并自定义字段到 PUT body
    if custom_fields:
        body.update(custom_fields)

    try:
        resp = requests.put(
            f"{rest_url}/bug/{bug_id}",
            params=params,
            json=body,
            headers={"Accept": "application/json"},
            timeout=120
        )
        if resp.status_code == 200:
            data = resp.json()
            bugs = data.get("bugs", [])
            actual_status = bugs[0].get("status", resolved_status) if bugs else resolved_status
            return {
                "success": True,
                "bug_id": bug_id,
                "new_status": actual_status,
                "instance": inst_name,
                "url": f"{inst_config['base_url']}/show_bug.cgi?id={bug_id}",
            }
        else:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return {
                "error": (
                    f"{error_msg}. ⚠️ WARNING: Timeout does NOT mean the operation failed! "
                    f"The server may have already processed the request. "
                    f"Check Bugzilla before retrying: "
                    f"{inst_config['base_url']}/show_bug.cgi?id={bug_id}"
                )
            }
        return {"error": error_msg}


def bug_commit(bug_id: str, comment_text: str, new_status: str = "needinfo",
               instance: str = None, use_combined: bool = True,
               send_mode: str = None, custom_fields: dict = None) -> dict:
    """一键组合：发评论并改状态。

    Args:
        bug_id: Bug ID
        comment_text: 评论内容
        new_status: 目标状态（默认 needinfo）
        instance: Bugzilla 实例名
        use_combined: 是否使用组合模式（默认 True）。
            - True: 将评论合并到状态变更的 comment 中，只产生一条评论（推荐）
            - False: 先发评论，再改状态（产生两条评论，兼容旧行为）
        send_mode: 发送模式。
            - 'preview' (默认): 只写本地预览文件，不发送。需用户确认后手动设置 send_mode='live'
            - 'live': 实际发送到 Bugzilla
        custom_fields: 自定义字段 dict，如 {"cf_root_cause": "xxx", "cf_resolution": "..."}
            - 写入 preview 文件 header，send 阶段解析后传给 Bugzilla API
    """
    # 默认 send_mode 从环境变量读取，环境变量未设置则默认 'preview'
    if send_mode is None:
        send_mode = os.environ.get("BUGZILLA_SEND_MODE", "preview")

    if send_mode == "preview":
        # 写入本地预览文件，不发送
        safe_id = bug_id.replace("/", "_").replace("\\", "_") if bug_id else "preview"
        filename = f"reply_{safe_id}_preview.txt"
        filepath = _resolve_reply_filepath(bug_id, filename)
        status_line = f"New Status: {new_status}"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Reply Preview (NOT SENT)\n")
            f.write(f"Bug: {bug_id}\n")
            f.write(f"{status_line}\n")
            f.write(f"Mode: preview (send_mode='live' to actually send)\n")
            f.write(f"Combined: {use_combined}\n")
            if custom_fields:
                for cf_key, cf_val in custom_fields.items():
                    f.write(f"{cf_key}: {cf_val}\n")
            f.write(f"---\n\n")
            f.write(comment_text + "\n")
        try:
            os.startfile(filepath)
        except Exception:
            pass
        return {
            "success": True,
            "mode": "preview",
            "bug_id": bug_id,
            "new_status": new_status,
            "filepath": filepath,
            "message": "预览已生成，请审核。确认后设置 send_mode='live' 或设置环境变量 BUGZILLA_SEND_MODE=live 发送。",
        }

    if use_combined:
        # 组合模式：一条 PUT 请求同时改状态 + 附带评论
        status_result = update_bug_status(bug_id, new_status, comment_text=comment_text,
                                          instance=instance, custom_fields=custom_fields)
        if "error" in status_result:
            # Idempotency check: timeout does not mean failure.
            # The server may have already committed the combined update.
            dedup = _check_recent_comments(bug_id, comment_text, instance)
            if dedup.get("found"):
                return {
                    "success": True,
                    "bug_id": bug_id,
                    "new_status": new_status,
                    "combined": True,
                    "dedup_detected": True,
                    "original_error": status_result.get("error"),
                    "note": (
                        f"Request failed with '{status_result.get('error', '')[:100]}' "
                        f"but comment was already posted (id={dedup.get('comment_id')}). "
                        f"Status may have been updated. Verify on Bugzilla."
                    ),
                }
            return {"error": f"Combined update failed: {status_result['error']}", "step": "combined"}

        # 获取评论 ID：从 bug_info 获取最新评论
        try:
            from bug_core import fetch_bug_rest
            bug_info = fetch_bug_rest(bug_id, instance=instance)
            latest_comment_id = None
            # 从所有 comments 中提取最新 comment id
            # REST API 评论在 bug_data["bugs"][0]["comments"]
        except Exception:
            latest_comment_id = None

        return {
            "success": True,
            "bug_id": bug_id,
            "new_status": status_result.get("new_status"),
            "url": status_result.get("url"),
            "instance": status_result.get("instance"),
            "combined": True,
            "note": "评论已合并到状态变更中，仅产生一条评论",
        }
    else:
        # 旧行为：先 post comment，再 update status
        comment_result = post_comment(bug_id, comment_text, instance)
        if "error" in comment_result:
            return {"error": f"Comment failed: {comment_result['error']}", "step": "comment"}

        status_result = update_bug_status(bug_id, new_status, instance=instance,
                                          custom_fields=custom_fields)
        if "error" in status_result:
            return {
                "error": f"Status update failed: {status_result['error']}",
                "step": "status",
                "comment_id": comment_result.get("comment_id"),
            }

        return {
            "success": True,
            "bug_id": bug_id,
            "comment_id": comment_result.get("comment_id"),
            "new_status": status_result.get("new_status"),
            "url": status_result.get("url"),
            "instance": status_result.get("instance"),
            "combined": False,
        }


# ============================================================
# 模式B：web_fetch 查询（通过Claw内置web_fetch工具）
# ============================================================

def fetch_bug_webfetch(bug_id: str, instance: str = None) -> dict:
    """
    生成web_fetch URL，供Claw agent调用web_fetch工具获取页面内容
    返回URL字典，agent按顺序调用
    """
    if OFFLINE_MODE:
        return fetch_bug_offline(bug_id)
    if instance == "local":
        return fetch_bug_offline(bug_id)

    inst_name, inst_config = get_instance_config(instance)
    base_url = inst_config["base_url"]

    urls = {
        "bug_page": f"{base_url}/show_bug.cgi?id={bug_id}",
        "bug_xml": f"{base_url}/show_bug.cgi?id={bug_id}&ctype=xml",
        "bug_rest": f"{inst_config['rest_url']}/bug/{bug_id}",
        "comment_rest": f"{inst_config['rest_url']}/bug/{bug_id}/comment",
    }
    return urls


# ============================================================
# 模式C：手动输入解析（用户粘贴内容）
# ============================================================

def parse_bug_from_text(text: str) -> dict:
    """从用户粘贴的Bug页面内容中提取结构化信息"""
    result = {
        "source": "manual_input",
        "bug_id": None,
        "summary": "",
        "status": "",
        "priority": "",
        "severity": "",
        "product": "",
        "component": "",
        "ftp_path": "",
        "path_url": "",
    }

    # 提取Bug ID（SPCSS开头或纯数字或 BUG-xxxx 或 unicase\d+）
    m = re.search(r'(SPCSS\d+)', text)
    if m:
        result["bug_id"] = m.group(1)
    else:
        m = re.search(r'(BUG-\d+)', text)
        if m:
            result["bug_id"] = m.group(1)
        else:
            m = re.search(r'[Bb]ug[\s#:]+(\d{4,})', text)
            if m:
                result["bug_id"] = m.group(1)
            else:
                # Unicase 工单号（unicase\d+）
                m = re.search(r'(unicase\d+)', text, re.IGNORECASE)
                if m:
                    result["bug_id"] = m.group(1)

    # 提取标题
    m = re.search(r'[Ss]ummary[\s:]+(.+?)(?:\n|$)', text)
    if m:
        result["summary"] = m.group(1).strip()

    # 提取状态
    m = re.search(r'[Ss]tatus[\s:]+(\w+)', text)
    if m:
        result["status"] = m.group(1)

    # 提取优先级
    m = re.search(r'[Pp]riority[\s:]+(\S+)', text)
    if m:
        result["priority"] = m.group(1)

    # 提取FTP路径（unisoc特有格式）
    m = re.search(r'下载附件:\s*([^\n]+)', text)
    if m:
        result["ftp_path"] = "/" + m.group(1).strip()

    # 提取快捷下载链接
    m = re.search(r'或使用快捷链接下载.*?:\s*(https?://[^\s]+)', text)
    if m:
        result["path_url"] = m.group(1).strip()

    # 提取Product/Component
    m = re.search(r'[Pp]roduct[\s:]+(.+?)(?:\n|$)', text)
    if m:
        result["product"] = m.group(1).strip()
    m = re.search(r'[Cc]omponent[\s:]+(.+?)(?:\n|$)', text)
    if m:
        result["component"] = m.group(1).strip()

    return result


def search_bugs(keyword: str = "", severity: str = "", limit: int = 20) -> list:
    """离线搜索Bug（支持关键词和严重度过滤）"""
    bugs = _load_sample_bugs()
    results = []
    for b in bugs:
        if severity and b.get("severity", "").upper() != severity.upper():
            continue
        if keyword:
            search_text = f"{b.get('title', '')} {b.get('description', '')} {b.get('tags', [])} {b.get('bug_id', '')}"
            if keyword.lower() not in search_text.lower():
                continue
        results.append(b)
    return results[:limit]


# ============================================================
# 客户回复系统 (v2.0)
# SPCSS 场景：Dear CUS + 用户内容 + Thanks
# 流程：生成预览文件 → 用户 review/修改 → 用户确认发送 → 提交
# ============================================================

_REPLY_PREVIEW_DIR = os.path.join(SCRIPT_DIR, "config")

# 当前回复上下文（bug_id 等，用于匹配模板）
_reply_context = {}


def _find_bug_workspace(bug_id: str) -> Optional[str]:
    """查找 Bug 工作区目录。

    递归搜索 default_workspace 下匹配 bug_id 的目录，
    返回最近修改的匹配项，无匹配返回 None。

    三态 ID 兼容：纯数字 Bug ID / SPCSS ID / Unisoc case ID 均可匹配。
    """
    try:
        import glob as _glob
        ws_base = _get_default_workspace()
        ws_dirs = sorted(
            [d for d in _glob.glob(os.path.join(ws_base, "**", f"*{bug_id}*"), recursive=True)
             if os.path.isdir(d)],
            key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
            reverse=True
        )
        return ws_dirs[0] if ws_dirs else None
    except Exception:
        return None


def _resolve_reply_filepath(bug_id: str, filename: str) -> str:
    """解析预览文件的写入/读取路径。

    Bug 工作区优先，不存在时 fallback 到 skill config 目录。

    Returns:
        文件完整路径（不检查文件是否存在）
    """
    ws_path = _find_bug_workspace(bug_id)
    if ws_path:
        return os.path.join(ws_path, filename)
    else:
        return os.path.join(_REPLY_PREVIEW_DIR, filename)


def _get_reply_context() -> dict:
    return _reply_context


def _get_default_workspace() -> str:
    """从 config 读取 default_workspace，失败时返回 E:\\08_Bug"""
    try:
        config_path = os.path.join(SCRIPT_DIR, "config", "bugzilla_instances.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("instances", {}).get("unisoc", {}).get("default_workspace", r"E:\08_Bug")
    except Exception:
        return r"E:\08_Bug"


def _load_reply_templates() -> list:
    """加载客户回复模板配置"""
    templates_path = os.path.join(SCRIPT_DIR, "config", "customer_reply_templates.json")
    try:
        with open(templates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("templates", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def match_spccs_template(bug_id: str = None) -> Optional[dict]:
    """检查 SPCSS bug，匹配模板"""
    bid = bug_id or _reply_context.get("bug_id", "")
    if not bid:
        return None
    for tpl in _load_reply_templates():
        trigger = tpl.get("product_trigger", "")
        if trigger and trigger.lower() in bid.lower():
            return tpl
    return None


def prepare_customer_reply(bug_id: str, content: str, platform: str = "",
                             new_status: str = "needinfo",
                             custom_fields: dict = None,
                             style_violations: list = None) -> dict:
    """
    准备客户回复预览。

    流程：组装 Dear CUS + 用户内容 + Thanks → 写入本地文件 → 返回预览。
    用户 review/修改文件后，再调用 send_customer_reply() 提交。

    文件优先写入 Bug 工作区（ws 下），ws 不存在时 fallback 到 config 目录。

    Args:
        bug_id: Bug ID
        content: 用户要回复的实际内容
        platform: 平台名称（可选）
        new_status: 目标状态（默认 needinfo），写入 header 供 send 阶段使用
        custom_fields: 自定义字段 dict，如 {"cf_root_cause": "...", "cf_resolution": "..."}
            - 写入 header 供 send_customer_reply() 解析发送
        style_violations: LLM 自检风格违规列表（可选），每项为 {"rule": "R1", "severity": "error", "desc": "..."}
            - 由 AI 读取 reply_style_rules.md 后自检生成，传入本函数写入预览 header
            - None 表示跳过风格检测

    Returns:
        {
            "success": True/False,
            "filepath": "/path/to/reply_SPCSS01690575_preview.txt",
            "workspace": "E:\\08_Bug\\Bug ...\\" or None,
            "reply": "Dear CUS\\n\\n...\\n\\nThanks",
        }
    """
    if not bug_id:
        return {"success": False, "error": "Missing bug_id"}
    if not content:
        return {"success": False, "error": "Missing content"}

    # 保存上下文（用于模板匹配）
    _reply_context["bug_id"] = bug_id

    # 组装格式
    reply = f"Dear CUS\n\n{content.strip()}\n\nThanks"

    # === 风格检测（由 LLM 自检结果传入） ===
    violations = style_violations or []
    errors = sum(1 for v in violations if v.get("severity") == "error")
    warns = sum(1 for v in violations if v.get("severity") == "warn")
    score = max(0, 100 - errors * 25 - warns * 10)
    passed = errors == 0
    style_result = {
        "passed": passed,
        "score": score,
        "violations": violations,
    }

    safe_id = bug_id.replace("/", "_").replace("\\", "_") if bug_id else "preview"
    filename = f"reply_{safe_id}_preview.txt"

    # === 查找 Bug 工作区 ===
    ws_path = _find_bug_workspace(bug_id)

    # === 确定写入路径：ws 优先，不存在则 fallback ===
    if ws_path:
        filepath = os.path.join(ws_path, filename)
    else:
        print(f"[prepare_customer_reply] ⚠️  Bug 工作区不存在，fallback 到 config 目录")
        print(f"  建议先运行 bug-workspace 创建工作区")
        filepath = os.path.join(_REPLY_PREVIEW_DIR, filename)

    # === 生成一次性 Token（防 AI 跳过预览直接发送） ===
    import uuid
    token = uuid.uuid4().hex[:12]

    tpl = match_spccs_template(bug_id)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Reply Preview\n")
        f.write(f"Bug: {bug_id}\n")
        f.write(f"Workspace: {ws_path or 'N/A'}\n")
        f.write(f"Status: {new_status}\n")
        if tpl:
            f.write(f"Template: {tpl.get('name', '')}\n")
        f.write(f"Token: {token}\n")

        # === 风格检测结果写入 header ===
        f.write(f"StyleCheck: {'PASS' if style_result['passed'] else 'FAIL'} "
                f"(score={style_result['score']})\n")
        if style_result["violations"]:
            f.write(f"StyleViolations: {len(style_result['violations'])}\n")
            for v in style_result["violations"]:
                f.write(f"  [{v['rule']}] {v['desc']}\n")

        if custom_fields:
            for cf_key, cf_val in custom_fields.items():
                f.write(f"{cf_key}: {cf_val}\n")
        f.write(f"---\n\n")
        f.write(reply + "\n")

    try:
        os.startfile(filepath)
    except Exception:
        pass

    return {
        "success": True,
        "bug_id": bug_id,
        "reply": reply,
        "filepath": filepath,
        "preview_file": filepath,  # alias for LLM consumers that look for this key
        "workspace": ws_path,
        "token": token,
        "style_check": style_result,
    }


def send_customer_reply(bug_id: str, filepath: str = None,
                        new_status: str = "needinfo",
                        instance: str = "unisoc",
                        use_combined: bool = True) -> dict:
    """
    发送已确认的客户回复。

    从预览文件读取已 review 过的内容，调用 bug_commit 提交。

    Args:
        bug_id: Bug ID
        filepath: 预览文件路径
        new_status: 目标状态
        instance: Bugzilla 实例
        use_combined: 是否组合模式

    Returns:
        bug_commit 的返回结果
    """
    # bug_commit is defined in this same module — call directly, no import needed

    # 读取已确认的内容
    safe_id = bug_id.replace("/", "_").replace("\\", "_")
    target_filename = f"reply_{safe_id}_preview.txt"

    if filepath is None:
        # Bug 工作区优先（通过 _find_bug_workspace 统一查找，避免重复实现）
        ws_path = _find_bug_workspace(bug_id)
        if ws_path:
            candidate = os.path.join(ws_path, target_filename)
            if os.path.exists(candidate):
                filepath = candidate

        # Fallback — skill config 目录精确匹配
        if filepath is None:
            candidate = os.path.join(_REPLY_PREVIEW_DIR, target_filename)
            if os.path.exists(candidate):
                filepath = candidate

        if filepath is None:
            return {"success": False,
                    "error": f"No preview file found for {bug_id}. "
                             f"Call prepare_customer_reply first, or pass filepath explicitly."}

    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse header (Bug/Workspace/Status/Template/Token/cf_* lines before ---)
    # and extract body (content between --- delimiters).
    header_ws = None
    header_status = None
    header_token = None
    header_custom_fields = {}
    if "\n---\n" in content or content.startswith("---\n"):
        lines = content.splitlines(keepends=True)
        body_lines = []
        in_header = True
        in_body = False
        for line in lines:
            stripped = line.strip()
            if stripped == "---":
                if in_header:
                    in_header = False
                    in_body = True
                    continue
                elif in_body:
                    break
            if in_header:
                # Parse header fields: "Key: value"
                if ": " in stripped:
                    key, val = stripped.split(": ", 1)
                    if key == "Workspace":
                        header_ws = val if val != "N/A" else None
                    elif key == "Status":
                        header_status = val
                    elif key == "Token":
                        header_token = val
                    elif key.startswith("cf_"):
                        header_custom_fields[key] = val
            elif in_body:
                body_lines.append(line)
        comment_text = "".join(body_lines).strip()
    else:
        comment_text = content.strip()

    # === Token 校验（软检查—警告但不阻止发送） ===
    if not header_token:
        print("[send_customer_reply] ⚠️ 预览文件中没有 Token，可能是旧格式预览文件。")

    # Use header status as fallback if new_status not explicitly overridden
    if header_status and new_status == "needinfo":
        pass  # Keep new_status as-is; header_status is for record-keeping

    # send_mode='live' is CRITICAL here — this function is called AFTER
    # user confirmation, so it MUST actually post to Bugzilla.
    # Without send_mode='live', bug_commit() defaults to 'preview' mode
    # and silently writes a local file instead of sending.

    # === Pre-send dedup verification ===
    # Check if an identical reply was already posted within the last 10 minutes.
    # This prevents double-sending when send_customer_reply() is called again
    # after a timeout (the first call may have succeeded on the server).
    pre_check = _check_recent_comments(bug_id, comment_text, instance, lookback_minutes=10)
    if pre_check.get("found"):
        _print(f"[send_customer_reply] ⚠️ DUPLICATE DETECTED: {pre_check.get('message')}")
        _print(f"[send_customer_reply]    This exact reply already exists on Bugzilla. Skipping send.")
        return {
            "success": True,
            "skip_send": True,
            "dedup_detected": True,
            "bug_id": bug_id,
            "existing_comment_id": pre_check.get("comment_id"),
            "new_status": new_status,
            "message": (
                f"Reply already posted as comment #{pre_check.get('comment_count')} "
                f"(id={pre_check.get('comment_id')}) at {pre_check.get('creation_time')}. "
                f"Send was skipped to avoid duplicate."
            ),
        }

    result = bug_commit(bug_id, comment_text, new_status, instance, use_combined,
                        send_mode='live', custom_fields=header_custom_fields or None)

    # Save a copy of the sent reply to the Bug workspace folder for record-keeping
    if result.get("success") and result.get("mode") != "preview":
        try:
            from datetime import datetime as _datetime

            # Use workspace from header (written by prepare_customer_reply), fallback to search
            ws_dir = header_ws
            if not ws_dir:
                import glob as _glob2
                ws_base = _get_default_workspace()
                ws_dirs = sorted(
                    _glob2.glob(os.path.join(ws_base, f"*{bug_id}*")),
                    key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
                    reverse=True
                )
                if ws_dirs:
                    ws_dir = ws_dirs[0]

            if ws_dir:
                date_str = _datetime.now().strftime("%Y%m%d")
                sent_filename = f"reply_{bug_id}_sent_{date_str}.txt"
                sent_filepath = os.path.join(ws_dir, sent_filename)
                with open(sent_filepath, "w", encoding="utf-8") as f:
                    f.write(f"# Reply Sent Record\n")
                    f.write(f"Bug: {bug_id}\n")
                    f.write(f"Status: {new_status}\n")
                    f.write(f"Date: {_datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"---\n\n")
                    f.write(comment_text + "\n")
            else:
                # Workspace not found — save to _REPLY_PREVIEW_DIR as fallback
                date_str = _datetime.now().strftime("%Y%m%d")
                sent_filename = f"reply_{bug_id}_sent_{date_str}.txt"
                sent_filepath = os.path.join(_REPLY_PREVIEW_DIR, sent_filename)
                with open(sent_filepath, "w", encoding="utf-8") as f:
                    f.write(f"# Reply Sent Record (workspace not found)\n")
                    f.write(f"Bug: {bug_id}\n")
                    f.write(f"Status: {new_status}\n")
                    f.write(f"Date: {_datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"---\n\n")
                    f.write(comment_text + "\n")
        except Exception:
            pass  # Record-keeping failure should not block the send result

    # ================================================================
    # Fix 4b: Post-send verification — confirm the comment actually
    # appeared on Bugzilla. This closes the verification gap where
    # bug_commit() returns success but the comment never actually lands.
    # ================================================================
    if result.get("success") and result.get("mode") != "preview":
        try:
            verify = _check_recent_comments(bug_id, comment_text, instance, lookback_minutes=5)
            if verify.get("found"):
                print(f"✅ 已确认发送：Comment #{verify.get('comment_count')} (ID={verify.get('comment_id')})")
            else:
                print(f"⚠️ 发送API返回成功，但未在Bugzilla上找到确认评论，请手动检查 {bug_id}")
        except Exception:
            pass  # Verification failure should not block the result

    return result


# ============================================================
# 工具函数
# ============================================================

def clean_folder_name(name: str, max_len: int = 99) -> str:
    """清除文件夹名中的非法字符，复刻原工具逻辑"""
    cleaned = re.sub(INVALID_CHARS, "_", name)
    # Windows: strip trailing spaces, dots, and hyphens from each path segment
    cleaned = cleaned.strip()
    cleaned = re.sub(r'[\s.\-]+$', '', cleaned)
    if len(cleaned) > max_len:
        if max_len > 50:
            cleaned = cleaned[:50] + cleaned[-(max_len - 50):]
        else:
            cleaned = cleaned[:max_len]
    return cleaned


def format_bug_summary(bug: dict) -> str:
    """格式化Bug摘要输出"""
    lines = []
    lines.append(f"[Bug Summary]")
    lines.append("=" * 40)
    lines.append(f"ID: {bug.get('bug_id', 'N/A')}")

    alias = bug.get("alias", [])
    if isinstance(alias, list) and alias:
        lines.append(f"Alias: {alias[0]}")
    elif alias:
        lines.append(f"Alias: {alias}")

    lines.append(f"Title: {bug.get('summary', 'N/A')}")
    lines.append(f"Status: {bug.get('status', 'N/A')}")
    if bug.get("resolution"):
        lines.append(f"  Resolution: {bug['resolution']}")

    priority = bug.get("priority", "")
    severity = bug.get("severity", "")
    if priority or severity:
        lines.append(f"Priority: {priority} | Severity: {severity}")

    lines.append(f"Product: {bug.get('product', 'N/A')} / {bug.get('component', 'N/A')}")

    # 分支/版本信息（SPCSS Bugzilla自定义字段）
    base_on_ver = bug.get("base_on_ver", "")
    if base_on_ver:
        lines.append(f"Base On Version: {base_on_ver}")
    fix_on_ver = bug.get("fix_on_ver", "")
    if fix_on_ver:
        lines.append(f"Fix On Version: {fix_on_ver}")
    branch_to_merge = bug.get("branch_to_merge", "")
    if branch_to_merge:
        lines.append(f"Branch To Merge: {branch_to_merge}")

    assignee = bug.get("assignee", "")
    if assignee:
        lines.append(f"Assignee: {assignee}")

    reporter = bug.get("reporter", "")
    if reporter:
        lines.append(f"Reporter: {reporter}")

    lines.append(f"URL: {bug.get('url', 'N/A')}")
    lines.append(f"Source: {bug.get('source', 'N/A')}")

    # FTP/附件路径 (unisoc特有)
    if bug.get("ftp_path"):
        lines.append(f"\n[FTP Path]: {bug['ftp_path']}")
    ftp_urls = bug.get("ftp_urls", [])
    if ftp_urls:
        lines.append("[FTP URLs]:")
        for u in ftp_urls:
            lines.append(f"  {u}")
    unc_paths = bug.get("unc_paths", [])
    if unc_paths:
        lines.append("[UNC Paths]:")
        for u in unc_paths:
            lines.append(f"  {u}")
    if bug.get("path_url"):
        lines.append(f"[Quick Link]: {bug['path_url']}")

    # 离线模式附加信息
    module = bug.get("module", "")
    if module:
        lines.append(f"[Module]: {module}")
    desc = bug.get("description", "")
    if desc:
        lines.append(f"[Description]: {desc}")
    tags = bug.get("tags", [])
    if tags:
        lines.append(f"[Tags]: {', '.join(tags)}")
    hint = bug.get("attachment_hint", "")
    if hint:
        lines.append(f"[Attachment Hint]: {hint}")
    update = bug.get("update_time", "")
    if update:
        lines.append(f"[Update Time]: {update}")

    creation = bug.get("creation_time", "")
    if creation:
        lines.append(f"[Created]: {creation}")
    last_change = bug.get("last_change_time", "")
    if last_change:
        lines.append(f"[Last Changed]: {last_change}")

    comments_count = bug.get("comments_count", 0)
    if comments_count:
        lines.append(f"\n[Comments]: {comments_count}")
        first = bug.get("first_comment", "")
        if first:
            preview = first[:200] + "..." if len(first) > 200 else first
            lines.append(f"  First: {preview}")

    return "\n".join(lines)


# ============================================================
# 主入口（独立脚本运行）
# ============================================================

if __name__ == "__main__":
    import argparse
    import io

    # Fix Windows console UTF-8 output
    if sys.stdout.encoding is None or "936" in sys.stdout.encoding or "ascii" in sys.stdout.encoding.lower():
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(description="Bug Core - Bug查询工具")
    parser.add_argument("bug_id", nargs="?", help="Bug ID (数字或 BUG-xxxx)")
    parser.add_argument("instance", nargs="?", default="kernel",
                        help="Bugzilla实例: kernel(默认) / mozilla / unisoc / local")
    parser.add_argument("--offline", action="store_true", help="离线模式（使用模拟数据）")
    parser.add_argument("--list", action="store_true", help="列出所有本地模拟Bug")
    parser.add_argument("--webfetch", action="store_true", help="仅输出web_fetch URL（JSON格式）")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出Bug信息")
    parser.add_argument("--commit", action="store_true", help="一键提交：发评论 + 改状态")
    parser.add_argument("--status", default="needinfo", help="目标状态（默认: needinfo）")
    parser.add_argument("--comment", default="", help="评论内容")
    parser.add_argument("--patch", default="", help="附加的patch文件路径")
    parser.add_argument("--custom-fields", default="", metavar="JSON",
                        help='自定义字段 JSON，如 \'{"cf_root_cause":"xxx","cf_resolution":"yyy"}\'')
    parser.add_argument("--comment-only", action="store_true",
                        help="仅发评论，不改状态（避免 --commit 默认改 needinfo）")
    parser.add_argument("--reply", action="store_true",
                        help="从 reply_{bug_id}_preview.txt 文件读取回复内容并提交（组合模式）")
    args = parser.parse_args()

    # === 解析 --custom-fields JSON ===
    cli_custom_fields = None
    if args.custom_fields:
        try:
            cli_custom_fields = json.loads(args.custom_fields)
            if not isinstance(cli_custom_fields, dict):
                print(f"[ERROR] --custom-fields must be a JSON object, got {type(cli_custom_fields).__name__}")
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[ERROR] --custom-fields JSON parse error: {e}")
            sys.exit(1)

    if args.list:
        bugs = _load_sample_bugs()
        print(f"[Local Bug List] ({len(bugs)} entries):")
        print("=" * 50)
        for b in bugs:
            print(f"  {b['bug_id']}  [{b['severity']}] {b['title']}")
            print(f"    Assignee: {b['assignee']} | Status: {b['status']} | Update: {b['update_time']}")
        sys.exit(0)

    if args.offline:
        os.environ["OFFLINE_MODE"] = "1"

    if not args.bug_id:
        parser.print_help()
        sys.exit(1)

    bug_id = args.bug_id

    # --comment-only 模式：仅发评论，不改状态
    if args.comment_only:
        comment_text = args.comment
        if args.patch:
            try:
                with open(args.patch, "r", encoding="utf-8", errors="replace") as f:
                    patch_content = f.read()
                comment_text = comment_text + "\n\n" + patch_content if comment_text else patch_content
            except FileNotFoundError:
                print(f"[ERROR] Patch file not found: {args.patch}")
                sys.exit(1)
        if not comment_text:
            print("[ERROR] --comment-only requires --comment or --patch")
            sys.exit(1)

        print(f"[Comment-Only] Bug {bug_id} (instance: {args.instance or 'default'})...\n")
        result = post_comment(bug_id, comment_text, instance=args.instance)
        inst_config = get_instance_config(args.instance)[1]
        if result.get("success"):
            result["url"] = f"{inst_config['base_url']}/show_bug.cgi?id={bug_id}"
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("success"):
            if result.get('comment_id'):
                print(f"  ✅ Comment posted (ID: {result['comment_id']})")
            else:
                print(f"  ✅ Comment posted (combined mode)")
            print(f"  🔗 {result['url']}")
        else:
            print(f"  ❌ {result.get('error', 'Unknown error')}")
        sys.exit(0 if result.get("success") else 1)

    # --reply 模式：从 reply_{bug_id}_preview.txt 文件读取回复内容并提交
    # 解决 bash 命令行中无法正确传递中文文本的问题
    if args.reply:
        safe_id = bug_id.replace("/", "_").replace("\\", "_")
        reply_filename = f"reply_{safe_id}_preview.txt"
        reply_filepath = None

        # 1) Bug 工作区优先 — 通过 _find_bug_workspace 统一查找
        ws_path = _find_bug_workspace(bug_id)
        if ws_path:
            candidate = os.path.join(ws_path, reply_filename)
            if os.path.exists(candidate):
                reply_filepath = candidate

        # 2) Fallback — skill config 目录精确匹配
        if reply_filepath is None:
            candidate = os.path.join(_REPLY_PREVIEW_DIR, reply_filename)
            if os.path.exists(candidate):
                reply_filepath = candidate

        if reply_filepath is None:
            print(f"[ERROR] 未找到回复文件: {reply_filename}")
            print(f"  请先调用 prepare_customer_reply() 或手动创建文件")
            sys.exit(1)

        # 读取文件内容，提取 body（跳过 frontmatter）
        with open(reply_filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            body_lines = []
            in_body = False
            for line in lines:
                stripped = line.strip()
                if stripped == "---":
                    if in_body:
                        break
                    in_body = True
                    continue
                if in_body:
                    body_lines.append(line)
            comment_text = "".join(body_lines).strip()

        if not comment_text:
            print(f"[ERROR] 回复文件为空: {reply_filepath}")
            sys.exit(1)

        print(f"[Reply] Bug {bug_id} -> status={args.status} (instance: {args.instance or 'unisoc'})...")
        print(f"  读取文件: {reply_filepath}")
        print(f"  内容预览: {comment_text[:80]}...")
        result = bug_commit(bug_id, comment_text, args.status, instance=args.instance,
                              custom_fields=cli_custom_fields)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("success"):
            if result.get('comment_id'):
                print(f"  ✅ Comment posted (ID: {result['comment_id']})")
            else:
                print(f"  ✅ Comment posted (combined mode)")
            print(f"  ✅ Status changed -> {result['new_status']}")
            print(f"  🔗 {result['url']}")
        else:
            print(f"  ❌ {result.get('error', 'Unknown error')}")
        sys.exit(0 if result.get("success") else 1)

    # --commit 模式：发评论 + 改状态
    if args.commit:
        comment_text = args.comment
        if args.patch:
            try:
                with open(args.patch, "r", encoding="utf-8", errors="replace") as f:
                    patch_content = f.read()
                comment_text = comment_text + "\n\n" + patch_content if comment_text else patch_content
            except FileNotFoundError:
                print(f"[ERROR] Patch file not found: {args.patch}")
                sys.exit(1)
        if not comment_text:
            print("[ERROR] --commit requires --comment or --patch")
            sys.exit(1)

        print(f"[Commit] Bug {bug_id} -> status={args.status} (instance: {args.instance or 'default'})...\n")
        result = bug_commit(bug_id, comment_text, args.status, instance=args.instance,
                              custom_fields=cli_custom_fields)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("success"):
            if result.get('comment_id'):
                print(f"  ✅ Comment posted (ID: {result['comment_id']})")
            else:
                print(f"  ✅ Comment posted (combined mode)")
            print(f"  ✅ Status changed -> {result['new_status']}")
            print(f"  🔗 {result['url']}")
        else:
            print(f"  ❌ {result.get('error', 'Unknown error')}")
        sys.exit(0 if result.get("success") else 1)

    if args.webfetch:
        urls = fetch_bug_webfetch(bug_id, args.instance)
        print(json.dumps(urls, indent=2))
        sys.exit(0)

    print(f"[Query] Bug {bug_id} (instance: {args.instance or 'default'})...\n")

    try:
        result = fetch_bug_rest(bug_id, args.instance)
        if "error" in result:
            print(f"[ERROR] {result['error']}")
        else:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(format_bug_summary(result))
    except Exception as e:
        msg = str(e)
        if "401" in msg:
            print(f"[ERROR] API Key required for instance ({args.instance})")
            print(f"   Configure api_key in config/bugzilla_instances.json")
        elif "403" in msg:
            print(f"[ERROR] Access denied to instance ({args.instance})")
        else:
            print(f"[ERROR] Query failed: {e}")
