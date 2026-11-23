#!/usr/bin/env python3
"""
Report Naming Utilities — 通用报告文件名生成模块

为所有 Claude Code 会话提供标准化的报告命名，不限于 Bug 技能。
格式: {topic}_{type}_{keyword}__{YYYYMMDD}.md

## 使用方式

### 1. Python API（Skill 内部使用）
```python
from common.report_utils import generate_report_filename

# 通用场景
name = generate_report_filename("my_topic", "analysis", "performance")
# → 'my_topic_analysis_performance__20260916.md'

# Bug 场景（从 dict 自动提取 bug_id）
from common.report_utils import generate_report_filename_from_bug
name = generate_report_filename_from_bug(bug, "analysis", "efuse")
```

### 2. CLI（非 Skill 的 CC 会话使用）
```bash
python report_utils.py <topic> <type> <keyword> [date]
python report_utils.py my_project analysis perf 20260916
# 输出: my_project_analysis_perf__20260916.md
```

## 参数说明
- **topic**: 主题标识（如 Bug ID、项目名、会话主题），必填
- **type**: 报告类型（analysis | harness | patch_eval | summary | ...），必填
- **keyword**: 会话相关关键词，必填
- **date**: 日期 YYYYMMDD，可选，默认今天
"""

import re
import os
import sys

# 非法文件名字符（Windows + 通用）
INVALID_CHARS = r'[<>:"/\\|?*\n\r\t]'


def generate_report_filename(topic: str, report_type: str, keyword: str, date_str: str = None) -> str:
    """生成标准化报告文件名（通用版）。

    格式: {topic}_{type}_{keyword}__{YYYYMMDD}.md

    Args:
        topic: 主题标识（如 "3556390", "SPCSS01696773", "my_project"）
        report_type: 报告类型（如 "analysis", "harness", "patch_eval", "summary"）
        keyword: 会话相关关键词，必填（如 "efuse", "dcdc", "vddsim"）
        date_str: 日期字符串 YYYYMMDD，默认今天

    Returns:
        filename-safe 的报告文件名

    Examples:
        >>> generate_report_filename("3556390", "analysis", "efuse")
        '3556390_analysis_efuse__20260916.md'
        >>> generate_report_filename("my_project", "summary", "weekly", "20260901")
        'my_project_summary_weekly__20260901.md'
    """
    from datetime import datetime

    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")

    def _clean(s: str) -> str:
        return re.sub(INVALID_CHARS, '_', str(s))

    topic_clean = _clean(topic)
    type_clean = _clean(report_type)
    keyword_clean = _clean(keyword)
    date_clean = _clean(date_str)

    return f"{topic_clean}_{type_clean}_{keyword_clean}__{date_clean}.md"


def generate_report_filename_from_bug(bug: dict, report_type: str, keyword: str, date_str: str = None) -> str:
    """从 Bug dict 生成标准化报告文件名（Bug 场景便捷封装）。

    自动从 bug dict 提取 bug_id，优先使用 alias。

    Args:
        bug: Bug 字典，需包含 bug_id 或 alias 字段
        report_type: 报告类型
        keyword: 会话相关关键词，必填
        date_str: 日期字符串 YYYYMMDD，默认今天

    Returns:
        filename-safe 的报告文件名
    """
    alias_list = bug.get("alias", [])
    if alias_list:
        topic = alias_list[0]
    else:
        topic = str(bug.get("bug_id", "?"))

    return generate_report_filename(topic, report_type, keyword, date_str)


# ============================================================
# CLI 入口 — 供非 Skill 的 CC 会话直接调用
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: python {os.path.basename(__file__)} <topic> <type> <keyword> [date]")
        print(f"Example: python {os.path.basename(__file__)} my_project analysis perf 20260916")
        print(f"Output: my_project_analysis_perf__20260916.md")
        sys.exit(1)

    topic = sys.argv[1]
    report_type = sys.argv[2]
    keyword = sys.argv[3]
    date_str = sys.argv[4] if len(sys.argv) > 4 else None

    filename = generate_report_filename(topic, report_type, keyword, date_str)
    print(filename)