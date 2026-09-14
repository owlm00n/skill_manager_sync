#!/bin/sh
#===============================================================================
# ssh_setup.sh — SSH 双域配置脚本（gerrit.unisoc.com + exgerrit.unisoc.com）
#===============================================================================
# 用法：
#   sh ssh_setup.sh [--dry-run] [--user <username>]
#
# 功能：
#   1. 检查 ~/.ssh 目录和密钥对
#   2. 生成 SSH 密钥（如不存在）
#   3. 配置 ~/.ssh/config 双域
#   4. 验证两个 Gerrit 的 SSH 连接
#===============================================================================

set -e

DRY_RUN=0
SSH_USER="xianjun.zeng"
SSH_DIR="$HOME/.ssh"
SSH_CONFIG="$SSH_DIR/config"
SSH_KEY="$SSH_DIR/id_rsa"

# ---- 参数解析 ----
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --user) SSH_USER="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

echo "========================================="
echo " Gerrit SSH 双域配置向导"
echo "========================================="
echo "用户: $SSH_USER"
echo "SSH 目录: $SSH_DIR"
[ $DRY_RUN -eq 1 ] && echo "模式: DRY RUN（仅检查）"
echo ""

# ---- 步骤 1: 检查 SSH 目录和密钥 ----
echo "--- 步骤 1: 检查 SSH 密钥 ---"

if [ ! -d "$SSH_DIR" ]; then
    echo "  SSH 目录不存在"
    if [ $DRY_RUN -eq 0 ]; then
        mkdir -p "$SSH_DIR"
        chmod 700 "$SSH_DIR"
        echo "  ✓ 已创建 $SSH_DIR"
    fi
else
    echo "  ✓ SSH 目录存在"
fi

if [ ! -f "$SSH_KEY" ]; then
    echo "  SSH 密钥不存在"
    if [ $DRY_RUN -eq 0 ]; then
        echo "  正在生成 RSA 密钥对..."
        ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N "" -C "$SSH_USER@unisoc.com"
        echo "  ✓ 密钥已生成"
    fi
else
    echo "  ✓ SSH 密钥存在: $SSH_KEY"
    echo "  指纹: $(ssh-keygen -lf "$SSH_KEY" 2>/dev/null | cut -d' ' -f2)"
fi

echo ""

# ---- 步骤 2: 配置 SSH config ----
echo "--- 步骤 2: 配置 SSH config ---"

# 检查是否已配置
HAS_INTERNAL=$(grep -c "Host gerrit.unisoc.com" "$SSH_CONFIG" 2>/dev/null || true)
HAS_EXTERNAL=$(grep -c "Host exgerrit.unisoc.com" "$SSH_CONFIG" 2>/dev/null || true)

if [ "$HAS_INTERNAL" -gt 0 ] && [ "$HAS_EXTERNAL" -gt 0 ]; then
    echo "  ✓ 双域 SSH 配置已存在"
else
    echo "  需要添加配置"
    if [ $DRY_RUN -eq 0 ]; then
        # 备份现有配置
        if [ -f "$SSH_CONFIG" ]; then
            cp "$SSH_CONFIG" "$SSH_CONFIG.bak-$(date +%Y%m%d-%H%M%S)"
            echo "  ✓ 已备份现有配置"
        fi

        cat >> "$SSH_CONFIG" << SSH_CONFIG_EOF

# ===== Gerrit 双域配置（由 gerrit-manager 管理）=====
# 内网 Gerrit
Host gerrit.unisoc.com
    HostName gerrit.unisoc.com
    Port 29418
    User $SSH_USER
    IdentityFile $SSH_KEY
    PreferredAuthentications publickey

# 外网 Gerrit（低密级代码外网操作）
Host exgerrit.unisoc.com
    HostName exgerrit.unisoc.com
    Port 29418
    User $SSH_USER
    IdentityFile $SSH_KEY
    PreferredAuthentications publickey
SSH_CONFIG_EOF
        echo "  ✓ SSH 双域配置已添加"
    fi
fi

echo ""

# ---- 步骤 3: 显示公钥 ----
echo "--- 步骤 3: 公钥信息 ---"
echo "  请确保以下公钥已在两个 Gerrit 注册："
echo ""
echo "  内网: https://gerrit.unisoc.com/gerrit/settings/#SSHKeys"
echo "  外网: https://exgerrit.unisoc.com/gerrit/settings/#SSHKeys"
echo ""
echo "  公钥内容:"
echo "  ─────────────────────────────────────"
cat "$SSH_KEY.pub" 2>/dev/null || echo "  (密钥文件不存在)"
echo "  ─────────────────────────────────────"
echo ""

# ---- 步骤 4: 验证连接 ----
echo "--- 步骤 4: 验证 SSH 连接 ---"

if [ $DRY_RUN -eq 1 ]; then
    echo "  DRY RUN 模式，跳过连接验证"
    exit 0
fi

echo ""
echo "  测试内网 Gerrit..."
INTERNAL_RESULT=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    -p 29418 "$SSH_USER@gerrit.unisoc.com" 2>&1 || true)
if echo "$INTERNAL_RESULT" | grep -q "gerrit"; then
    echo "  ✓ 内网 Gerrit 连接成功"
else
    echo "  ❌ 内网 Gerrit 连接失败"
    echo "     $INTERNAL_RESULT"
fi

echo ""
echo "  测试外网 Gerrit..."
EXTERNAL_RESULT=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    -p 29418 "$SSH_USER@exgerrit.unisoc.com" 2>&1 || true)
if echo "$EXTERNAL_RESULT" | grep -q "gerrit"; then
    echo "  ✓ 外网 Gerrit 连接成功"
else
    echo "  ❌ 外网 Gerrit 连接失败"
    echo "     $EXTERNAL_RESULT"
fi

echo ""
echo "========================================="
echo " SSH 双域配置完成"
echo "========================================="
echo ""
echo "下一步："
echo "  1. 如果连接失败，检查公钥是否已在 Gerrit 注册"
echo "  2. 如果使用 MobaXterm，检查路径冲突问题"
echo "  3. 参考: code-puller/references/known_issues.md"