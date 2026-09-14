# ========================================
# WorklogDailyFill 计划任务创建脚本 (PowerShell)
# ========================================
# 用法：powershell -ExecutionPolicy Bypass -File scripts\create_task.ps1
# 运行后会弹出密码输入框（安全输入）

$taskName = "WorklogDailyFill"
$taskUser = "SPREADTRUM\Xianjun.Zeng"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskXmlPath = Join-Path $scriptDir "config\daily_fill.xml"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "创建 $taskName 计划任务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "任务配置:"
Write-Host "  - 触发时间：周二到周六 每天 8:00"
Write-Host "  - 执行内容：填充前一天的工时"
Write-Host "  - 运行用户: $taskUser"
Write-Host "  - XML 文件: $taskXmlPath"
Write-Host ""

# 检查 XML 文件是否存在
if (-not (Test-Path $taskXmlPath)) {
    Write-Host "[错误] XML 文件不存在：$taskXmlPath" -ForegroundColor Red
    Write-Host "请确保在当前工作目录下运行此脚本"
    exit 1
}

# 删除旧任务（如果有）
Write-Host "删除旧任务（如果存在）..." -ForegroundColor Yellow
schtasks /delete /tn "$taskName" /f 2>$null

# 获取密码（安全输入）
Write-Host "请输入域密码（输入时不会显示）..." -ForegroundColor Yellow
$securePassword = Read-Host "密码" -AsSecureString
$credential = New-Object System.Management.Automation.PSCredential($taskUser, $securePassword)

# 创建任务
Write-Host "创建任务..." -ForegroundColor Green
$result = schtasks /create /tn "$taskName" /xml "$taskXmlPath" /ru "$taskUser" /rp $credential.GetNetworkCredential().Password /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "[成功] 任务已创建!" -ForegroundColor Green
    Write-Host ""
    Write-Host "验证任务:" -ForegroundColor Cyan
    schtasks /query /tn "$taskName"
    Write-Host ""
    Write-Host "下次运行时间将在 8:00 自动触发" -ForegroundColor Green
    Write-Host "如需立即测试，运行: schtasks /run /tn '$taskName'" -ForegroundColor Yellow
} else {
    Write-Host "[错误] 任务创建失败，错误代码：$LASTEXITCODE" -ForegroundColor Red
    Write-Host "请检查:" -ForegroundColor Yellow
    Write-Host "  1. 密码是否正确"
    Write-Host "  2. 是否有权限创建任务（需要管理员权限）"
    Write-Host "  3. XML 文件路径是否正确"
    Write-Host "  4. 用户账户名称是否正确"
    exit 1
}
