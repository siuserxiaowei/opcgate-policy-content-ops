#!/usr/bin/env python3
"""Capture a six-frame VibeSocial submission set from the deployed app."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get(
    "VIBESOCIAL_DEMO_URL",
    "https://opc-vibesocial-trust-agent.siuserxy.workers.dev",
)
OUTPUT = Path("demo-assets/frames")
VIEWPORT = {"width": 1600, "height": 900}


def capture(page, name: str) -> None:
    page.screenshot(path=str(OUTPUT / name), full_page=False)


OUTPUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport=VIEWPORT, locale="zh-CN", device_scale_factor=1)
    page = context.new_page()
    response = page.goto(BASE_URL, wait_until="networkidle")
    assert response and response.ok, response.status if response else "no response"
    page.wait_for_function("document.querySelector('#health-badge').textContent.includes('服务正常')")

    capture(page, "01-home.png")

    page.locator("#workspace").scroll_into_view_if_needed()
    capture(page, "02-input.png")

    # Use the deterministic path so the captured evidence remains reproducible and
    # does not depend on model wording or remote inference availability.
    if page.locator("#use-ai").is_checked():
        page.locator("label[for='use-ai']").click()
    page.locator("#analyze-button").click()
    page.wait_for_function("document.querySelector('#analysis-content').hidden === false")
    assert page.locator("#copy-button").is_disabled()
    capture(page, "03-analysis.png")

    page.locator("#policy-list").scroll_into_view_if_needed()
    capture(page, "04-evidence.png")

    page.locator("#checklist").scroll_into_view_if_needed()
    assert "复制已锁定" in page.locator("#gate-status").inner_text()
    capture(page, "05-gate.png")

    page.locator(".methodology").scroll_into_view_if_needed()
    capture(page, "06-workflow.png")

    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    context.close()
    browser.close()

print(f"Captured 6 frames from {BASE_URL} into {OUTPUT}")
