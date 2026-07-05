"""Standalone 42.space scraper - called as subprocess by monitor_combined.py.
Outputs JSON to stdout."""
from __future__ import annotations
import json, sys, time
from playwright.sync_api import sync_playwright

URL = "https://www.42.space/sport/fifa/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723"

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-TW",
        )
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(8)  # Wait for dynamic content to load

        result = {"url": URL, "title": page.title(), "markets": {}}

        # Try multiple selectors to find match odds
        # Approach 1: Look for tab content
        try:
            teams = page.locator("text=/Portugal.*Congo|PRT.*CDR/i").all()
            if teams:
                result["teams_found"] = [t.inner_text()[:80] for t in teams[:5]]
        except Exception:
            pass

        # Approach 2: Get all visible text in the main content area
        try:
            main = page.locator("main, [role=main], .content, #__next").first
            if main:
                text = main.inner_text()
                lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) < 200]
                result["main_text_lines"] = lines[:50]
        except Exception:
            pass

        # Approach 3: Try to find odds/prices
        try:
            prices = page.locator('[class*="price"], [class*="odd"], [class*="quote"]').all()
            result["price_elements"] = [p.inner_text()[:50] for p in prices[:20]]
        except Exception:
            pass

        # Approach 4: Try to find the match scoreline grid
        try:
            grid_cells = page.locator('[class*="cell"], [class*="grid"], [class*="score"]').all()
            if grid_cells:
                result["grid_cells"] = [c.inner_text()[:50] for c in grid_cells[:30]]
        except Exception:
            pass

        # Approach 5: Check for quick select buttons/values
        try:
            buttons = page.locator("button").all()
            button_texts = [b.inner_text().strip() for b in buttons if b.inner_text().strip()]
            result["buttons"] = button_texts[:30]
        except Exception:
            pass

        # Approach 6: Check network requests for API data
        # (Cannot easily capture this in sync API, but we can try to intercept)
        try:
            # Look for embedded JSON data in script tags
            scripts = page.locator("script").all()
            for script in scripts:
                text = script.inner_text()
                if "marketData" in text or "outcome" in text.lower() or "price" in text.lower():
                    result["script_data_found"] = True
                    snippet = text[:2000] if len(text) < 2000 else text[:2000] + "..."
                    result["script_snippet"] = snippet
                    break
        except Exception:
            pass

        browser.close()
        print(json.dumps(result, ensure_ascii=False))

except Exception as e:
    print(json.dumps({"error": str(e)}, ensure_ascii=False))
