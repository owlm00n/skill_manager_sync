"""
Send keystrokes to MobaXterm serial console via Windows SendInput API.

Simulates real keyboard typing — works with any terminal, regardless of
keyboard layout (uses KEYEVENTF_UNICODE). Requires briefly focusing the
MobaXterm window.

Usage:
  python send_to_moba.py "cat /proc/sys/kernel/printk"
  python send_to_moba.py printk               # shortcut
  python send_to_moba.py --list               # list shortcuts
  python send_to_moba.py                      # just send Enter
"""

import sys
import time
import ctypes
import ctypes.wintypes
import argparse
import win32gui
import win32con

user32 = ctypes.windll.user32

# ============================================================
# SendInput constants & structures
# ============================================================
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("ki", KEYBDINPUT),
    ]


def _send_unicode(text):
    """Send Unicode text via SendInput (KEYEVENTF_UNICODE).
    This works regardless of keyboard layout — sends character codes directly."""
    inputs = []
    for ch in text:
        code = ord(ch)
        # Key down
        inp = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE))
        inputs.append(inp)
        # Key up
        inp2 = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        inputs.append(inp2)

    if inputs:
        n = len(inputs)
        INPUT_ARRAY = INPUT * n
        user32.SendInput(n, INPUT_ARRAY(*inputs), ctypes.sizeof(INPUT))


def _send_enter():
    """Send Enter via keybd_event (VK_RETURN)"""
    user32.keybd_event(0x0D, 0, 0, 0)
    user32.keybd_event(0x0D, 0, KEYEVENTF_KEYUP, 0)


def _focus_window(hwnd):
    """Focus a window, bypassing Windows foreground lock with Alt trick"""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    user32.AllowSetForegroundWindow(-1)          # ASFW_ANY
    user32.keybd_event(0x12, 0, 0, 0)            # VK_MENU down
    user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP) # VK_MENU up
    time.sleep(0.03)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.1)


# ============================================================
# Main send function
# ============================================================

def send_to_moba(text, session_title="COM (1)", restore_focus=True):
    """
    Send text to a MobaXterm serial console session.

    Finds the MobaXterm window, focuses it, types the text using
    SendInput (KEYEVENTF_UNICODE), and sends Enter. Optionally
    restores the previously focused window.
    """
    # Find MobaXterm window
    main_hwnd = None
    def enum_cb(hwnd, _):
        nonlocal main_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            if session_title in title and cls == 'TMobaXtermForm':
                main_hwnd = hwnd
    win32gui.EnumWindows(enum_cb, None)

    if not main_hwnd:
        return False, f"MobaXterm session '{session_title}' not found", None

    prev_fg = win32gui.GetForegroundWindow()

    _focus_window(main_hwnd)

    # Type the command (Enter already included as \r in text)
    if text.strip():
        _send_unicode(text)
        time.sleep(0.05)

    # Fallback: if no Enter in text, send one
    if not text.endswith('\r'):
        _send_enter()
        time.sleep(0.05)

    # Restore previous focus
    if restore_focus and prev_fg and prev_fg != main_hwnd:
        try:
            win32gui.SetForegroundWindow(prev_fg)
        except:
            pass

    preview = text.strip() if text.strip() else "<Enter>"
    return True, f"Sent: {preview[:60]}", main_hwnd


# ============================================================
# CLI
# ============================================================

COMMANDS = {
    "loglevel-8": "echo 8 8 8 8 > /proc/sys/kernel/printk",
    "loglevel-7": "echo 7 7 7 7 > /proc/sys/kernel/printk",
    "loglevel-4": "echo 4 4 4 4 > /proc/sys/kernel/printk",
    "dmesg-clear": "dmesg -c > /dev/null",
    "dmesg-tail": "dmesg | tail -50",
    "printk": "cat /proc/sys/kernel/printk",
    "sysrq": "cat /proc/sys/kernel/sysrq",
    "version": "cat /proc/version",
    "uptime": "cat /proc/uptime",
    "interrupts": "cat /proc/interrupts | head -20",
    "mount": "mount",
    "df": "df -h",
    "ps": "ps -A | head -30",
    "logcat-clear": "logcat -c",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send keystrokes to MobaXterm serial console")
    parser.add_argument("command", nargs="?", help="Command or shortcut name (see --list)")
    parser.add_argument("--list", action="store_true", help="List predefined shortcuts")
    parser.add_argument("--session", type=str, default="COM (1)", help="MobaXterm session title")
    parser.add_argument("--no-enter", action="store_true", help="Don't append Enter after command")
    parser.add_argument("--no-restore", action="store_true", help="Don't restore previous focus")
    args = parser.parse_args()

    if args.list:
        print("Predefined shortcuts:")
        for name, cmd in sorted(COMMANDS.items()):
            print(f"  {name:18s}  {cmd}")
        sys.exit(0)

    if not args.command:
        text = "\r"
    else:
        text = COMMANDS.get(args.command, args.command)
        if not args.no_enter and not text.endswith("\r"):
            text += "\r"

    success, msg, _ = send_to_moba(text, args.session, restore_focus=not args.no_restore)
    print(f"[{'OK' if success else 'FAIL'}] {msg}")
    sys.exit(0 if success else 1)