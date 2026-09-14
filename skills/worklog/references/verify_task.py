"""
验证并修复 Worklog 计划任务配置

检查项：
1. 任务是否存在且启用
2. 触发器是否正确（周二 - 周六 8:00）
3. 运行权限是否正确
4. 最近一次运行结果
"""

import subprocess
import json
import sys
from pathlib import Path

def run_cmd(cmd):
    """运行 cmd 命令并返回输出"""
    result = subprocess.run(
        ['cmd', '/c', cmd],
        capture_output=True,
        text=True,
        encoding='gbk',
        errors='ignore'
    )
    return result.returncode, result.stdout, result.stderr

def check_task_exists(task_name):
    """检查任务是否存在"""
    rc, out, err = run_cmd(f'schtasks /query /tn "{task_name}"')
    return rc == 0

def get_task_info(task_name):
    """获取任务详细信息"""
    rc, out, err = run_cmd(f'schtasks /query /tn "{task_name}" /v /fo LIST')
    if rc != 0:
        return None
    
    info = {}
    for line in out.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    return info

def check_last_run_result(task_name):
    """检查最近一次运行结果"""
    rc, out, err = run_cmd(f'schtasks /query /tn "{task_name}" /v /fo CSV')
    if rc != 0:
        return None
    
    # 解析 CSV 输出
    lines = out.strip().split('\n')
    if len(lines) < 2:
        return None
    
    headers = lines[0].split(',')
    values = lines[1].split(',')
    
    result = dict(zip(headers, values))
    return {
        'last_run_time': result.get('Last Run Time', 'N/A'),
        'last_result': result.get('Last Result', 'N/A'),
        'next_run_time': result.get('Next Run Time', 'N/A'),
        'status': result.get('Status', 'N/A')
    }

def enable_task_history(task_name):
    """启用任务历史记录（需要管理员权限）"""
    print(f"[信息] 任务计划程序历史记录需要手动启用:")
    print(f"  1. 打开 '任务计划程序' (taskschd.msc)")
    print(f"  2. 找到 '\\{task_name}'")
    print(f"  3. 右键 -> '属性' -> '历史记录' 选项卡")
    print(f"  4. 勾选 '启用此任务的所有历史记录'")
    print(f"  5. 点击 '确定'")
    print()

def verify_script_path():
    """验证脚本路径是否存在"""
    script_path = Path(__file__).parent.parent / 'scripts' / 'playwright' / 'scheduled_run.py'
    return script_path.exists(), str(script_path)

def main():
    task_name = 'WorklogDailyFill'
    
    print("=" * 60)
    print(f"检查计划任务：{task_name}")
    print("=" * 60)
    print()
    
    # 1. 检查任务是否存在
    if not check_task_exists(task_name):
        print(f"[错误] 任务 '{task_name}' 不存在!")
        print(f"       请使用以下命令创建:")
        print(f"       cmd /c scripts\\create_task.bat")
        print(f"       或")
        print(f"       powershell -ExecutionPolicy Bypass -File scripts\\create_task.ps1")
        print()
        print(f"       或手动在 '任务计划程序' 中创建")
        return 1
    
    print("[✓] 任务存在")
    print()
    
    # 2. 获取任务信息
    info = get_task_info(task_name)
    if info:
        print("任务配置:")
        print(f"  状态：{info.get('Status', 'N/A')}")
        print(f"  运行用户：{info.get('Run As User', 'N/A')}")
        print(f"  上次运行时间：{info.get('Last Run Time', 'N/A')}")
        print(f"  上次结果：{info.get('Last Result', 'N/A')}")
        print(f"  下次运行时间：{info.get('Next Run Time', 'N/A')}")
        print(f"  触发器：{info.get('Task To Run', 'N/A')}")
        print()
    
    # 3. 检查最近运行结果
    last_run = check_last_run_result(task_name)
    if last_run:
        print("最近运行历史:")
        print(f"  上次运行：{last_run['last_run_time']}")
        print(f"  运行结果：{last_run['last_result']}")
        print(f"  下次运行：{last_run['next_run_time']}")
        print(f"  当前状态：{last_run['status']}")
        print()
        
        # 检查上次运行结果
        last_result_hex = last_run['last_result'].strip()
        if last_result_hex != '0x0' and last_result_hex != '0':
            print(f"[警告] 上次运行失败! 结果代码: {last_result_hex}")
            print(f"       常见错误代码:")
            print(f"         0x1 - 任务执行出错")
            print(f"         0x2 - 找不到文件")
            print(f"         0x3 - 访问被拒绝")
            print(f"         0x4 - 任务已调度")
            print(f"         0x5 - 登录失败")
            print()
    
    # 4. 验证脚本路径
    script_exists, script_path = verify_script_path()
    if script_exists:
        print(f"[✓] 脚本存在：{script_path}")
    else:
        print(f"[错误] 脚本不存在：{script_path}")
        return 1
    
    # 5. 检查日志文件
    logs_dir = Path(__file__).parent.parent / 'logs'
    recent_logs = sorted(logs_dir.glob('scheduled_run_*.log'), reverse=True)[:3]
    
    print()
    print("最近运行日志:")
    if recent_logs:
        for log in recent_logs:
            print(f"  {log.name}")
    else:
        print("  无运行日志")
    print()
    
    # 6. 建议
    print("=" * 60)
    print("建议操作:")
    print("=" * 60)
    print()
    
    if last_run and last_run['last_result'].strip() not in ['0x0', '0']:
        print("1. [重要] 上次运行失败，请检查:")
        print("   - 打开 '任务计划程序' -> 找到任务 -> 查看 '历史记录'")
        print("   - 如果看不到历史记录，先启用它（见下方步骤）")
        print()
    
    print("2. 启用任务历史记录（仅一次）:")
    enable_task_history(task_name)
    
    print("3. 手动测试运行:")
    print(f"   schtasks /run /tn \"{task_name}\"")
    print(f"   # 等待 1-2 分钟后检查 logs/ 目录")
    print()
    
    print("4. 如果仍然失败，检查:")
    print("   - 8:00 时电脑是否已登录（任务需要用户会话）")
    print("   - 网络是否可用（需要访问 worklog.unisoc.com）")
    print("   - Python 环境是否可用（任务中使用的 python.exe 路径）")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
