@echo off
REM ========================================
REM WorklogDailyFill 计划任务创建脚本
REM ========================================
REM 用法：cmd /c scripts\create_task.bat
REM 需要输入域密码（密码不会显示）

set TASK_NAME=WorklogDailyFill
set TASK_USER=SPREADTRUM\Xianjun.Zeng
set TASK_XML=%~dp0config\daily_fill.xml

echo ========================================
echo 创建 %TASK_NAME% 计划任务
echo ========================================
echo.
echo 任务配置:
echo   - 触发时间：周二到周六 每天 8:00
echo   - 执行内容：填充前一天的工时
echo   - 运行用户: %TASK_USER%
echo   - XML 文件: %TASK_XML%
echo.

REM 检查 XML 文件是否存在
if not exist "%TASK_XML%" (
    echo [错误] XML 文件不存在：%TASK_XML%
    echo 请确保在当前工作目录下运行此脚本
    pause
    exit /b 1
)

REM 删除旧任务（如果有，忽略错误）
echo 删除旧任务（如果存在）...
schtasks /delete /tn "%TASK_NAME%" /f 2>nul

echo.
echo 请准备好你的域密码，输入后按回车继续...
pause
echo.

REM 创建新任务
echo 创建任务...
schtasks /create /tn "%TASK_NAME%" /xml "%TASK_XML%" /ru "%TASK_USER%" /rp /f

if %errorlevel% equ 0 (
    echo.
    echo [成功] 任务已创建!
    echo.
    echo 验证任务:
    schtasks /query /tn "%TASK_NAME%"
    echo.
    echo 下次运行时间将在 8:00 自动触发
    echo.
    echo 如需立即测试，运行: schtasks /run /tn "%TASK_NAME%"
) else (
    echo.
    echo [错误] 任务创建失败，错误代码: %errorlevel%
    echo 请检查:
    echo   1. 密码是否正确
    echo   2. 是否有权限创建任务（需要管理员权限）
    echo   3. XML 文件路径是否正确
    echo   4. 用户账户名称是否正确
)

echo.
echo ========================================
pause
