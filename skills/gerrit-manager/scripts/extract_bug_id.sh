#!/bin/sh
#===============================================================================
# extract_bug_id.sh — 从分支名提取 Bug ID（7 位数字）
#===============================================================================
# 用法：
#   sh extract_bug_id.sh [--interactive] [--quiet]
#
# 选项：
#   --interactive   未提取到时交互式询问用户输入
#   --quiet         静默模式，只输出 Bug ID 或空
#   无参数          输出 Bug ID 或提示未找到
#
# 提取规则：
#   1. 从当前分支名提取 7 位连续数字
#   2. 支持分支名格式：bug/3502855, fix/3502855-desc, 3502855
#   3. 调试模式接受 7777777
#
# 返回值：
#   0 - 成功提取
#   1 - 未找到 Bug ID
#===============================================================================

INTERACTIVE=0
QUIET=0

# ---- 参数解析 ----
while [ $# -gt 0 ]; do
    case "$1" in
        --interactive) INTERACTIVE=1; shift ;;
        --quiet) QUIET=1; shift ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ---- 从分支名提取 Bug ID ----
extract_from_branch() {
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ -z "$branch" ]; then
        return 1
    fi

    # 提取 7 位连续数字（排除更长的数字串）
    # 先找所有数字串，过滤出恰好 7 位的
    bug_id=$(echo "$branch" | grep -oE '[0-9]+' | while IFS= read -r num; do
        if [ ${#num} -eq 7 ]; then
            echo "$num"
            break
        fi
    done)

    if [ -n "$bug_id" ]; then
        echo "$bug_id"
        return 0
    fi

    return 1
}

# ---- 交互式输入 ----
ask_bug_id() {
    printf "请输入 Bug ID（7 位数字，调试用 7777777）: "
    read -r input

    if [ -z "$input" ]; then
        return 1
    fi

    # 校验：恰好 7 位数字
    if echo "$input" | grep -qE '^[0-9]{7}$'; then
        echo "$input"
        return 0
    fi

    echo "❌ Bug ID 必须是 7 位数字，输入: '$input'"
    return 1
}

# ---- 主流程 ----
main() {
    bug_id=$(extract_from_branch)

    if [ -n "$bug_id" ]; then
        [ $QUIET -eq 0 ] && echo "✓ Bug ID: $bug_id（从分支名提取）"
        echo "$bug_id"
        return 0
    fi

    if [ $INTERACTIVE -eq 1 ]; then
        [ $QUIET -eq 0 ] && echo "⚠️  未从分支名提取到 Bug ID"
        bug_id=$(ask_bug_id)
        if [ -n "$bug_id" ]; then
            echo "$bug_id"
            return 0
        fi
        [ $QUIET -eq 0 ] && echo "❌ 未提供有效 Bug ID"
        return 1
    fi

    [ $QUIET -eq 0 ] && echo "⚠️  未找到 Bug ID（分支名: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)）"
    return 1
}

main