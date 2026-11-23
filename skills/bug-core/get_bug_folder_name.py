#!/usr/bin/env python3
"""
get_bug_folder_name.py — 根据 Bugzilla Bug ID 生成规范的工作区文件夹名

严格复刻 D:\\05_Code\\python\\bugzila\\fetch_buginfo_by_API_UI.py 的命名逻辑：

  1. fetch_summary()   → "{bug_id}({alias}) - {summary}"  或  "{bug_id} - {summary}"
  2. re.sub(invalid_chars, "_", raw_title)                  → 清除非法文件名字符
  3. os.path.join(file_path, "Bug " + bug_title)            → 拼接完整路径
  4. 如果 len(bug_folder_path) > 99 → 按规则截断 title       → 路径截断
  5. "Bug " + bug_title                                     → 最终文件夹名

AI 必须运行此脚本获取规范文件夹名，禁止手动实现命名逻辑。

用法:
    python get_bug_folder_name.py <bug_id> [--base-path <path>]

    # 跳过 API 调用（已知 alias + title）
    python get_bug_folder_name.py <bug_id> --alias <alias> --title <title>

    # 从 JSON 数据解析（跳过 API 调用）
    python get_bug_folder_name.py --json '<bug_json>'

输出 (JSON):
    {
      "folder_name": "Bug 3575241(SPCSS01701938) - [UMS9370] HADCI7 voltage read 0",
      "bug_id": "3575241",
      "alias": "SPCSS01701938",
      "summary": "[UMS9370][longcheer_BU6] HADCI7 voltage read 0",
      "raw_title": "3575241(SPCSS01701938) - [UMS9370][longcheer_BU6] HADCI7 voltage read 0",
      "cleaned_title": "3575241(SPCSS01701938) - [UMS9370][longcheer_BU6] HADCI7 voltage read 0",
      "is_truncated": false
    }
"""

import sys
import os
import re
import json
import urllib.request
import urllib.error

# 技能目录（用于读取 config/bugzilla_instances.json）
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 复刻 fetch_buginfo_by_API_UI.py 第 119 行
# ============================================================
INVALID_CHARS = r'[<>:"/\\|?*\n\r\t]'


def load_config():
    """从 bugzilla_instances.json 读取配置"""
    config_path = os.path.join(SKILL_DIR, "config", "bugzilla_instances.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 复刻 fetch_buginfo_by_API_UI.py:fetch_bug()  (第 273-291 行)
# ============================================================
def fetch_bug(bugid_url, api_key):
    """调用 Bugzilla REST API 获取 Bug JSON 数据"""
    url = f"{bugid_url}?api_key={api_key}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ============================================================
# 复刻 fetch_buginfo_by_API_UI.py:fetch_summary()  (第 293-320 行)
# ============================================================
def fetch_summary(data):
    """
    从 Bugzilla REST API 返回的 JSON 中提取格式化标题。
    精确复刻原工具逻辑：
      summary = f"{bug_id}" + (f"({alias})" if alias else "") + " - " + summary
    """
    bugs = data.get("bugs", [])

    bug_id = ""
    alias = ""
    summary = ""

    if bugs and "id" in bugs[0]:
        bug_id = bugs[0]["id"]

    if bugs and "alias" in bugs[0]:
        alias_list = bugs[0]["alias"]
        alias = alias_list[0] if alias_list else ""

    if bugs and "summary" in bugs[0]:
        summary = bugs[0]["summary"]
    else:
        summary = "No summary found"

    raw_title = f"{bug_id}" + (f"({alias})" if alias else "") + " - " + summary

    return str(bug_id), alias, summary, raw_title


# ============================================================
# 复刻 fetch_buginfo_by_API_UI.py:main() 中的截断逻辑  (第 399-414 行)
# ============================================================
def clean_and_truncate(raw_title, base_path):
    """
    清除非法字符 + 按完整路径长度截断。
    精确复刻原工具 main() 中第 399-414 行的逻辑。
    """
    # Step 1: 清除非法字符（第 399 行）
    bug_title = re.sub(INVALID_CHARS, "_", raw_title)

    # Step 2: 拼接完整路径（第 402 行）
    bug_folder_path = os.path.join(base_path, "Bug " + bug_title)

    # Step 3: 截断（第 404-414 行）
    max_folder_name_len = 99
    is_truncated = False

    if len(bug_folder_path) > max_folder_name_len:
        is_truncated = True
        remain_len = max_folder_name_len - len(base_path) - 5  # 5 for 'Bug '
        if remain_len > 50:
            bug_title = bug_title[:50] + bug_title[-(remain_len - 50):]
        else:
            bug_title = bug_title[:remain_len]

    return bug_title, is_truncated


def resolve_by_quicksearch(alias_str, instance_config):
    """
    通过 quicksearch 解析 SPCSS/Unicase alias → Bugzilla Bug ID。
    复刻 bug-workspace skill.md 规则 5 的 alias 解析逻辑。
    """
    rest_url = instance_config["rest_url"]
    api_key = instance_config.get("api_key", "")
    url = f"{rest_url}/bug?quicksearch={alias_str}&api_key={api_key}"

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    bugs = data.get("bugs", [])
    if not bugs:
        raise ValueError(f"Cannot resolve alias: {alias_str}")

    bug = bugs[0]
    bug_id = str(bug.get("id", ""))
    summary = bug.get("summary", "")
    alias_list = bug.get("alias", [])
    alias = alias_list[0] if alias_list else alias_str

    return bug_id, alias, summary


def get_folder_name(bug_id, alias="", summary="", base_path=None, instance="unisoc"):
    """
    生成规范的 Bug 工作区文件夹名。

    严格复刻 D:\\05_Code\\python\\bugzila\\fetch_buginfo_by_API_UI.py
    的完整命名逻辑（第 293-420 行）。

    参数:
        bug_id:   Bugzilla Bug ID 或 SPCSS/Unicase alias
        alias:    已知 alias（跳过 API 调用时使用）
        summary:  已知 title（跳过 API 调用时使用）
        base_path: 工作区基础路径（用于截断计算，可选）
        instance: Bugzilla 实例名（默认 unisoc）

    返回 dict: {folder_name, bug_id, alias, summary, raw_title, cleaned_title, is_truncated}
    """
    config = load_config()
    instance_config = config["instances"].get(instance)
    if not instance_config:
        raise ValueError(f"Unknown instance: {instance}")

    rest_url = instance_config["rest_url"]
    api_key = instance_config.get("api_key", "")

    # Step 1: 获取 Bug 信息
    if summary:
        # 跳过 API 调用 — 已有 title/alias
        pass
    else:
        # 判断是否需要 quicksearch 解析
        bug_id_str = str(bug_id)
        needs_resolve = (
            bug_id_str.upper().startswith("SPCSS")
            or bug_id_str.lower().startswith("unicase")
        )

        if needs_resolve:
            bug_id, alias, summary = resolve_by_quicksearch(bug_id_str, instance_config)
        else:
            # 直接 GET /rest/bug/{id}
            bugid_url = f"{rest_url}/bug/{bug_id}"
            try:
                data = fetch_bug(bugid_url, api_key)
                bug_id, alias, summary, _ = fetch_summary(data)
            except urllib.error.HTTPError as e:
                # 数字 ID 也可能需要 quicksearch（有些 Bug 编号不是 Bugzilla 原生 ID）
                if e.code == 404:
                    bug_id, alias, summary = resolve_by_quicksearch(bug_id_str, instance_config)
                else:
                    raise

    # Step 2: 构建 raw_title — 复刻 fetch_summary() 第 316 行
    raw_title = f"{bug_id}" + (f"({alias})" if alias else "") + " - " + summary

    # Step 3: 清除非法字符 + 截断 — 复刻 main() 第 399-414 行
    if base_path:
        cleaned_title, is_truncated = clean_and_truncate(raw_title, base_path)
    else:
        # 无 base_path 时仅清除非法字符，不截断
        cleaned_title = re.sub(INVALID_CHARS, "_", raw_title)
        is_truncated = False

    # Step 4: 最终文件夹名 = "Bug " + cleaned_title
    folder_name = "Bug " + cleaned_title

    return {
        "folder_name": folder_name,
        "bug_id": str(bug_id),
        "alias": alias,
        "summary": summary,
        "raw_title": raw_title,
        "cleaned_title": cleaned_title,
        "is_truncated": is_truncated,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="生成规范的 Bug 工作区文件夹名（精确复刻 fetch_buginfo_by_API_UI.py 逻辑）"
    )
    parser.add_argument(
        "bug_id", nargs="?",
        help="Bugzilla Bug ID（纯数字、SPCSS 前缀、或 unicase 前缀）"
    )
    parser.add_argument(
        "--base-path", "-p", default=None,
        help="工作区基础路径（用于截断计算，如 E:\\08_Bug\\CQ）"
    )
    parser.add_argument(
        "--alias", "-a", default=None,
        help="Bug alias（已知时跳过 API 调用）"
    )
    parser.add_argument(
        "--title", "-t", default=None,
        help="Bug title/summary（已知时跳过 API 调用）"
    )
    parser.add_argument(
        "--json", "-j", default=None,
        help="Bug JSON 数据字符串（跳过 API 调用，直接解析）"
    )
    parser.add_argument(
        "--instance", "-i", default="unisoc",
        help="Bugzilla 实例名（默认 unisoc）"
    )

    args = parser.parse_args()

    if args.json:
        # 从 JSON 字符串解析
        data = json.loads(args.json)
        bug_id, alias, summary, _ = fetch_summary(data)
    elif args.title:
        # 跳过 API 调用
        bug_id = args.bug_id or ""
        alias = args.alias or ""
        summary = args.title
    elif args.bug_id:
        bug_id = args.bug_id
        alias = ""
        summary = ""
    else:
        parser.print_help()
        sys.exit(1)

    result = get_folder_name(
        bug_id=bug_id,
        alias=alias,
        summary=summary,
        base_path=args.base_path,
        instance=args.instance,
    )

    # 输出 JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()