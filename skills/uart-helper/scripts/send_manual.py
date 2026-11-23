"""手动发送命令到 MobaXterm 串口控制台 — 交互式版本"""
import time
import ctypes
from ctypes import wintypes
import win32gui, win32con

# ============================================================
# SendInput — 模拟真人键盘打字（已验证有效）
# ============================================================
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", KEYBDINPUT),
    ]

user32 = ctypes.windll.user32

def send_text(text):
    """逐字符发送（含 Enter）"""
    inputs = []
    for ch in text:
        code = ord(ch)
        inputs.append(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE)))
        inputs.append(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)))
    if inputs:
        arr = (INPUT * len(inputs))(*inputs)
        user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

# ============================================================
# 查找并聚焦 MobaXterm
# ============================================================
def find_moba(session="COM (1)"):
    hwnd = None
    def cb(h, _):
        nonlocal hwnd
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            c = win32gui.GetClassName(h)
            if session in t and c == 'TMobaXtermForm':
                hwnd = h
    win32gui.EnumWindows(cb, None)
    return hwnd

def focus(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    user32.AllowSetForegroundWindow(-1)
    user32.keybd_event(0x12, 0, 0, 0)   # Alt down
    user32.keybd_event(0x12, 0, 2, 0)   # Alt up
    time.sleep(0.05)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.2)

# ============================================================
# 预设命令
# ============================================================
CMDS = {
    "l8":  "echo 8 8 8 8 > /proc/sys/kernel/printk",
    "l7":  "echo 7 7 7 7 > /proc/sys/kernel/printk",
    "l5":  "echo 5 5 5 5 > /proc/sys/kernel/printk",
    "l4":  "echo 4 4 4 4 > /proc/sys/kernel/printk",
    "pk":  "cat /proc/sys/kernel/printk",
    "su":  "su",
    "who": "whoami",
    "id":  "id",
    "ver": "cat /proc/version",
    "up":  "cat /proc/uptime",
    "dc":  "dmesg -c > /dev/null",
    "dt":  "dmesg | tail -50",
}

# ============================================================
# 主流程
# ============================================================
def main():
    SESSION = "COM (1)"

    hwnd = find_moba(SESSION)
    if not hwnd:
        print(f"[ERROR] 找不到 MobaXterm 窗口 '{SESSION}'")
        return
    print(f"[INFO] 找到 MobaXterm: {hwnd:#010x}")

    print(f"\n预设命令: {' | '.join(CMDS.keys())}")
    print("输入预设名或直接输入完整命令（输入 q 退出）")
    print("=" * 60)

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue
        if cmd.lower() == 'q':
            break

        # 解析命令
        text = CMDS.get(cmd, cmd)  # 预设优先，否则原样发送
        if text != cmd:
            print(f"  → {text}")

        # 加回车
        if not text.endswith('\r'):
            text += '\r'

        # 聚焦 + 发送
        focus(hwnd)
        send_text(text)

        if text.strip() == '\r':
            print("  [Enter]")
        else:
            print(f"  [SENT] {text.strip()[:60]}")

    print("Bye.")

if __name__ == "__main__":
    main()