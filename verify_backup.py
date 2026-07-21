"""End-to-end UI test for backup page."""
import json, urllib.request, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8771"


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(req).read())


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()

        errors = []
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.evaluate("navigate('backup')")
        page.wait_for_timeout(2000)

        # ─── Test 1: Status auto-loaded ───
        print("==> Test 1: Status auto-loaded on page entry...")
        status_text = page.evaluate("document.getElementById('backupStatus').textContent")
        print(f"  Status: {status_text[:120]}...")
        assert "Connected" in status_text, "Status not auto-loaded"
        assert "owlm00n/skill_manager_sync" in status_text, "Remote URL not shown"
        print("  [PASS] Status auto-loaded")

        # ─── Test 2: Check Status button ───
        print("\n==> Test 2: Click 'Check Status' button...")
        # It's the 2nd button in Remote Configuration section
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim() === 'Check Status') { b.click(); return; }
            }
        }""")
        page.wait_for_timeout(2000)
        status_html = page.evaluate("document.getElementById('backupStatus').innerHTML")
        print(f"  Status HTML contains last_commit: {'Last commit' in status_html}")
        print(f"  Status HTML contains clean/working: {'Uncommitted' in status_html or 'clean' in status_html.lower()}")
        assert "Last commit" in status_html, "Last commit not shown"
        print("  [PASS] Check Status shows last commit")

        # ─── Test 3: Load Git History ───
        print("\n==> Test 3: Load Git History...")
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim() === 'Load History') { b.click(); return; }
            }
        }""")
        page.wait_for_timeout(2000)
        log_text = page.evaluate("document.getElementById('gitLog').textContent")
        print(f"  Log text (first 200 chars): {log_text[:200]}")
        assert "Backup" in log_text or "commit" in log_text.lower(), "No commits shown"
        print("  [PASS] Git history loaded")

        # ─── Test 4: Back Up Now (should be no changes) ───
        print("\n==> Test 4: Click 'Back Up Now' (no changes expected)...")
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.includes('Back Up Now')) { b.click(); return; }
            }
        }""")
        page.wait_for_timeout(3000)
        # Check toast (assuming showToast creates a toast element)
        toast_text = page.evaluate("""() => {
            const t = document.querySelector('.toast, [class*="toast"], #toast');
            return t ? t.textContent : '';
        }""")
        print(f"  Toast: {toast_text}")

        # Re-check status
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim() === 'Check Status') { b.click(); return; }
            }
        }""")
        page.wait_for_timeout(2000)
        status_text2 = page.evaluate("document.getElementById('backupStatus').textContent")
        print(f"  Status after backup: {status_text2[:120]}...")
        assert "Connected" in status_text2, "Lost connection after backup"
        print("  [PASS] Back Up Now works")

        # ─── Test 5: JS errors ───
        print("\n==> Test 5: Check JS errors...")
        real_errors = [e for e in errors if "cdn.tailwindcss.com" not in e]
        print(f"  Real errors: {len(real_errors)}")
        for e in real_errors:
            print(f"    {e}")
        assert len(real_errors) == 0, f"Found JS errors: {real_errors}"
        print("  [PASS] No JS errors")

        browser.close()

    print("\n=========================================")
    print("ALL TESTS PASSED!")
    print("=========================================")


if __name__ == "__main__":
    main()
