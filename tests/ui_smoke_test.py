"""One-off manual smoke test driven via Playwright — not part of the pytest
suite (backend tests use FastAPI's TestClient instead). Run with the
frontend dev server on :5173 and backend on :8000."""
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        page.goto(f"{BASE}/login")
        page.wait_for_selector("form input", timeout=5000)
        page.locator("form input").first.fill("admin")
        page.fill("input[type=password]", "ChangeMe123!")
        page.click("button[type=submit]")
        page.wait_for_url(f"{BASE}/", timeout=5000)
        page.wait_for_selector("text=Total Cases", timeout=5000)
        print("LOGIN + DASHBOARD OK, title:", page.title())
        page.screenshot(path="/tmp/dashboard.png", full_page=True)

        page.click("text=Cases")
        page.wait_for_selector("text=CASE-2026", timeout=5000)
        print("CASES LIST OK")
        page.screenshot(path="/tmp/cases.png", full_page=True)

        page.click("text=CASE-2026-000010")
        page.wait_for_selector("text=Evidence", timeout=5000)
        print("CASE DETAIL OK")
        page.screenshot(path="/tmp/case_detail.png", full_page=True)

        page.goto(f"{BASE}/account-finder")
        page.wait_for_selector("text=Account Violation Finder", timeout=5000)
        print("ACCOUNT FINDER PAGE OK")
        page.screenshot(path="/tmp/account_finder.png", full_page=True)

        page.goto(f"{BASE}/reviews")
        page.wait_for_selector("text=Review Queue", timeout=5000)
        print("REVIEW QUEUE PAGE OK")

        browser.close()

        if errors:
            print("CONSOLE/PAGE ERRORS:", errors)
            sys.exit(1)
        print("NO CONSOLE ERRORS")


if __name__ == "__main__":
    main()
