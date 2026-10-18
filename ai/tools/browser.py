"Local Playwright browser prototype; this module never calls an external AI inference API."

import argparse
import ipaddress
import json
import socket
import sys
import time
import urllib.parse
from pathlib import Path


MAX_TEXT = 16000
MAX_ACTIONS = 200


def validate_public_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only public HTTPS URLs are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("Credentials inside URLs are not accepted.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("Local hostnames are blocked.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except OSError as error:
        raise ValueError("The hostname could not be resolved.") from error
    if not addresses:
        raise ValueError("The hostname has no resolved addresses.")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global:
            raise ValueError("Private, loopback, link-local, and reserved IP addresses are blocked.")
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise SystemExit("Playwright is required. Install with: pip install playwright && playwright install chromium") from error
    return sync_playwright


class BrowserTool:
    def __init__(self, headless=True, timeout_ms=20000):
        self.sync_playwright = ensure_playwright()
        self.playwright_manager = self.sync_playwright()
        self.playwright = self.playwright_manager.start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            accept_downloads=False,
            service_workers="block",
        )
        self.context.set_default_timeout(timeout_ms)
        self.page = self.context.new_page()
        self.page.on("dialog", lambda dialog: dialog.dismiss())
        self.action_count = 0

        def guard(route):
            try:
                validate_public_url(route.request.url)
                route.continue_()
            except Exception:
                route.abort("blockedbyclient")

        self.context.route("**/*", guard)

    def count_action(self):
        self.action_count += 1
        if self.action_count > MAX_ACTIONS:
            raise RuntimeError("Action limit reached; start a new browser session.")

    def navigate(self, url):
        self.count_action()
        safe_url = validate_public_url(url)
        response = self.page.goto(safe_url, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(400)
        return {
            "url": self.page.url,
            "title": self.page.title(),
            "status": response.status if response else None,
            "text": self.read_text(),
        }

    def read_text(self):
        self.count_action()
        return self.page.locator("body").inner_text(timeout=8000)[:MAX_TEXT]

    def click(self, selector, confirmed=False):
        self.count_action()
        target = self.page.locator(selector).first
        details = target.evaluate("""element => ({
            tag: element.tagName.toLowerCase(),
            type: (element.getAttribute('type') || '').toLowerCase(),
            role: (element.getAttribute('role') || '').toLowerCase(),
            text: (element.innerText || element.getAttribute('aria-label') || element.getAttribute('title') || '').trim().slice(0, 300),
            href: element.getAttribute('href') || '',
            form: Boolean(element.closest('form'))
        })""")
        risky_words = ("delete", "remove", "purchase", "buy", "checkout", "pay", "publish", "post", "send", "invite", "transfer", "submit", "sign out", "log out", "cancel subscription")
        label = (details["text"] + " " + details["href"]).casefold()
        is_submit = details["type"] == "submit" or details["role"] == "submit"
        is_risky = is_submit or any(word in label for word in risky_words)
        if is_risky and not confirmed:
            raise PermissionError("This may submit a form or change external state. Ask the user for explicit confirmation, then call click(..., confirmed=True).")
        target.click()
        self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        return {"url": self.page.url, "title": self.page.title(), "text": self.read_text()}

    def fill(self, selector, value):
        self.count_action()
        if len(value) > 20000:
            raise ValueError("Input text is too long.")
        self.page.locator(selector).first.fill(value)
        return {"selector": selector, "filled": True, "value_length": len(value)}

    def screenshot(self, path):
        self.count_action()
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(target), full_page=True, animations="disabled")
        return {"screenshot": str(target), "url": self.page.url}

    def close(self):
        self.context.close()
        self.browser.close()
        self.playwright_manager.stop()


def main():
    parser = argparse.ArgumentParser(description="A user-controlled browser tool for Kowork; no external AI API.")
    parser.add_argument("--url", required=True, help="Public HTTPS URL to open.")
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=20000)
    parser.add_argument("--screenshot")
    args = parser.parse_args()
    if args.timeout_ms < 1000 or args.timeout_ms > 60000:
        parser.error("--timeout-ms must be between 1000 and 60000")
    browser = BrowserTool(headless=not args.show_browser, timeout_ms=args.timeout_ms)
    try:
        result = browser.navigate(args.url)
        if args.screenshot:
            result["screenshot_result"] = browser.screenshot(args.screenshot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        browser.close()


if __name__ == "__main__":
    main()
