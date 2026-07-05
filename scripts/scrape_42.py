"""Scrape 42.space for Portugal vs DR Congo market data using Playwright."""
from __future__ import annotations
import json, time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.42.space/sport/fifa/0xBcD1Bc19b678b3677536431c0433F18C3E4e4723"

print(f"[{datetime.now().strftime('%H:%M:%S')}] Launching browser...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"  Navigating to 42.space...")
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    
    # Save screenshot for debugging
    ss_path = Path(__file__).parent / "42_screenshot.png"
    page.screenshot(path=str(ss_path))
    print(f"  Screenshot: {ss_path}")
    
    # Get page title
    title = page.title()
    print(f"  Title: {title}")
    
    # Try to find all text containing prices or odds
    # Look for elements with specific text patterns
    text = page.locator("body").inner_text()
    
    # Save full text for analysis
    txt_path = Path(__file__).parent / "42_page_text.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Page text: {txt_path} ({len(text)} chars)")
    
    # Print first 500 chars for preview
    lines = text.split("\n")
    relevant = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            relevant.append(stripped)
    
    print(f"\n  First 30 non-empty lines:")
    for line in relevant[:30]:
        print(f"    {line[:120]}")
    
    browser.close()

print("\nDone.")
