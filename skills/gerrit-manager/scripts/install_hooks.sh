#!/bin/sh
#===============================================================================
# install_hooks.sh — 批量安装 commit-msg + pre-push hook 到多个仓库
#===============================================================================
# 用法：
#   sh install_hooks.sh [--dry-run] [--repo <path>] [--all]
#
# 选项：
#   --dry-run     仅检查，不实际安装
#   --repo <path> 安装到指定仓库
#   --all         安装到所有已知仓库（ENG_AI + 所有 submodule + 05_Code）
#   无参数         安装到当前目录的仓库（如果是 git 仓库）
#===============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_SRC="$SCRIPT_DIR/hooks"
COMMIT_MSG_SRC="$HOOKS_SRC/commit-msg"
PRE_PUSH_SRC="$HOOKS_SRC/pre-push"
DRY_RUN=0
TARGET=""

# ---- 参数解析 ----
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --repo) TARGET="$2"; shift 2 ;;
        --all) TARGET="ALL"; shift ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ---- 检查 hook 源文件 ----
for hook_src in "$COMMIT_MSG_SRC" "$PRE_PUSH_SRC"; do
    if [ ! -f "$hook_src" ]; then
        echo "❌ Hook 源文件不存在: $hook_src"
        exit 1
    fi
done
echo "Hook 源目录: $HOOKS_SRC"
echo ""

# ---- 安装单个 hook ----
install_hook() {
    repo="$1"
    hook_name="$2"
    hook_src="$3"

    hooks_dir="$repo/.git/hooks"
    target_file="$hooks_dir/$hook_name"

    if [ ! -f "$hook_src" ]; then
        return
    fi

    if [ -f "$target_file" ]; then
        if diff "$hook_src" "$target_file" >/dev/null 2>&1; then
            echo "    ✓  $hook_name 已是最新"
            return
        else
            echo "    📝 $hook_name 更新"
        fi
    else
        echo "    ➕ $hook_name 安装"
    fi

    if [ $DRY_RUN -eq 0 ]; then
        cp "$hook_src" "$target_file"
        chmod +x "$target_file" 2>/dev/null || true
    fi
}

# ---- 安装所有 hook 到单个仓库 ----
install_to_repo() {
    repo="$1"
    hooks_dir="$repo/.git/hooks"

    # 检查是否为 git 仓库
    if [ ! -d "$repo/.git" ]; then
        echo "  ⏭  跳过（非 git 仓库）: $repo"
        return
    fi

    mkdir -p "$hooks_dir"

    echo "  📂 $repo"
    install_hook "$repo" "commit-msg" "$COMMIT_MSG_SRC"
    install_hook "$repo" "pre-push" "$PRE_PUSH_SRC"
}

# ---- 安装到当前仓库 ----
if [ -z "$TARGET" ]; then
    if git rev-parse --git-dir >/dev/null 2>&1; then
        repo_root="$(git rev-parse --show-toplevel)"
        echo "当前仓库: $repo_root"
        echo ""
        install_to_repo "$repo_root"
        echo ""
        echo "✓ 完成"
    else
        echo "当前目录不是 git 仓库。请使用 --repo 指定路径或 --all 批量安装。"
        exit 1
    fi
    exit 0
fi

# ---- 安装到指定仓库 ----
if [ "$TARGET" != "ALL" ]; then
    echo "目标仓库: $TARGET"
    echo ""
    install_to_repo "$TARGET"
    echo ""
    echo "✓ 完成"
    exit 0
fi

# ---- 批量安装（--all）----
echo "===== 批量安装 commit-msg + pre-push hook ====="
echo ""

# 1. ENG_AI 主仓库
echo "--- ENG_AI 主仓库 ---"
install_to_repo "D:/06_Project/ENG_AI"

# 2. ENG_AI submodule 子仓库
echo ""
echo "--- ENG_AI Submodule 子仓库 ---"
for emp in cuijian heshu qihang yuncheng zhijian; do
    sub_repo="D:/06_Project/ENG_AI/EAI/employees/$emp"
    if [ -d "$sub_repo/.git" ]; then
        install_to_repo "$sub_repo"
    fi
done

# 3. F:\05_Code 下的仓库
echo ""
echo "--- F:\\05_Code 仓库 ---"
if [ -d "F:/05_Code" ]; then
    for repo_dir in "F:/05_Code"/*/; do
        repo_name=$(basename "$repo_dir")
        install_to_repo "$repo_dir"
    done
else
    echo "  ⏭  F:\\05_Code 不存在，跳过"
fi

echo ""
echo "===== 批量安装完成 ====="