import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8787"
ARTIFACTS = Path("test-results/ui-qa")
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def element_state(page, selector):
    return page.locator(selector).evaluate(
        "el => ({hidden: el.hidden, display: getComputedStyle(el).display, visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)})"
    )


def attach_diagnostics(page, diagnostics):
    page.on("console", lambda message: diagnostics["console"].append({"type": message.type, "text": message.text}))
    page.on("pageerror", lambda error: diagnostics["pageErrors"].append(str(error)))
    page.on(
        "requestfailed",
        lambda request: diagnostics["requestFailures"].append(
            {"url": request.url, "method": request.method, "failure": request.failure}
        ),
    )


def assert_no_horizontal_overflow(page):
    dimensions = page.evaluate(
        "() => ({innerWidth, bodyScrollWidth: document.body.scrollWidth, documentScrollWidth: document.documentElement.scrollWidth})"
    )
    assert dimensions["bodyScrollWidth"] <= dimensions["innerWidth"] + 1, dimensions
    assert dimensions["documentScrollWidth"] <= dimensions["innerWidth"] + 1, dimensions
    return dimensions


def run_viewport(browser, name, viewport):
    context = browser.new_context(viewport=viewport, locale="zh-CN")
    page = context.new_page()
    diagnostics = {"console": [], "pageErrors": [], "requestFailures": []}
    attach_diagnostics(page, diagnostics)

    response = page.goto(BASE_URL, wait_until="networkidle")
    assert response and response.ok, response.status if response else "no response"
    page.wait_for_function("document.querySelector('#health-badge').textContent.includes('服务正常')")

    initial = {
        "sampleFields": element_state(page, "#sample-fields"),
        "manualFields": element_state(page, "#manual-fields"),
        "analysisEmpty": element_state(page, "#analysis-empty"),
        "analysisContent": element_state(page, "#analysis-content"),
        "draftEmpty": element_state(page, "#draft-empty"),
        "draftContent": element_state(page, "#draft-content"),
        "toast": element_state(page, "#toast"),
    }
    assert initial["sampleFields"]["visible"] is True, initial
    for key in ("manualFields", "analysisContent", "draftContent", "toast"):
        assert initial[key]["hidden"] is True and initial[key]["display"] == "none" and initial[key]["visible"] is False, initial

    page.screenshot(path=str(ARTIFACTS / f"{name}-initial.png"), full_page=True)
    initial_dimensions = assert_no_horizontal_overflow(page)

    page.get_by_role("tab", name="手动粘贴公开文本").click()
    assert element_state(page, "#sample-fields")["display"] == "none"
    assert element_state(page, "#manual-fields")["visible"] is True
    page.locator("#analyze-button").click()
    assert page.locator("#form-error").is_visible()
    assert "请填写话题标题和公开文本" in page.locator("#form-error").inner_text()

    page.locator("#topic-title").fill("AI 智能体创业讨论")
    page.locator("#topic-summary").fill("用户手动输入公开文本，讨论 OPC 创业政策与核验工作流。")
    page.locator("#topic-tags").fill("AI智能体, OPC, 创业政策")
    page.locator("label[for='use-ai']").click()
    assert page.locator("#use-ai").is_checked() is False
    page.locator("#analyze-button").click()
    page.wait_for_function("document.querySelector('#analysis-content').hidden === false")
    assert element_state(page, "#analysis-empty")["display"] == "none"
    assert element_state(page, "#draft-empty")["display"] == "none"
    assert page.locator("#analysis-content").is_visible()
    assert page.locator("#draft-content").is_visible()
    assert "手动输入待核验" in page.locator("#draft-text").input_value()
    assert page.locator("#draft-mode").inner_text() == "确定性降级草稿"
    assert page.locator("#source-score").inner_text() == "0"
    assert page.locator("#risk-score").inner_text() == "48"
    assert page.locator("#policy-list .policy-card").count() >= 1
    assert page.locator("#checklist .check-item").count() >= 1

    review_boxes = page.locator("#checklist input[type='checkbox']")
    total_boxes = review_boxes.count()
    assert page.locator("#gate-count").inner_text() == f"0 / {total_boxes}"
    assert page.locator("#copy-button").is_disabled()
    assert "复制已锁定" in page.locator("#gate-status").inner_text()
    locked_copy_prevented = page.locator("#draft-text").evaluate(
        "el => { const event = new ClipboardEvent('copy', {cancelable: true}); return !el.dispatchEvent(event); }"
    )
    assert locked_copy_prevented is True
    review_boxes.first.check()
    assert page.locator("#gate-count").inner_text() == f"1 / {total_boxes}"

    for index in range(1, total_boxes):
        review_boxes.nth(index).check()
    assert page.locator("#gate-count").inner_text() == f"{total_boxes} / {total_boxes}"
    assert page.locator("#copy-button").is_enabled()
    assert "可以复制" in page.locator("#gate-status").inner_text()
    unlocked_copy_prevented = page.locator("#draft-text").evaluate(
        "el => { const event = new ClipboardEvent('copy', {cancelable: true}); return !el.dispatchEvent(event); }"
    )
    assert unlocked_copy_prevented is False

    page.locator("#draft-text").fill("人工修改后的草稿")
    assert page.locator("#draft-count").inner_text() == "8 字"
    assert page.locator("#gate-count").inner_text() == f"0 / {total_boxes}"
    assert page.locator("#copy-button").is_disabled()
    for index in range(total_boxes):
        review_boxes.nth(index).check()
    assert page.locator("#copy-button").is_enabled()
    page.evaluate("navigator.clipboard.writeText = async () => undefined")
    page.locator("#copy-button").click()
    page.locator("#toast").wait_for(state="visible")
    assert page.locator("#toast").is_visible()
    assert "草稿已复制" in page.locator("#toast").inner_text() or "已选中草稿" in page.locator("#toast").inner_text()

    page.screenshot(path=str(ARTIFACTS / f"{name}-manual-result.png"), full_page=True)
    result_dimensions = assert_no_horizontal_overflow(page)

    page.get_by_role("tab", name="用内置样例").click()
    page.locator("#sample-select").select_option("sample-ai-agent-opc-001")
    page.locator("#analyze-button").click()
    page.wait_for_function("document.querySelector('#draft-text').value.includes('非实时样例解读')")
    assert page.locator("#risk-score").inner_text() == "48"
    assert page.locator("#checklist .blocked input").count() >= 1
    assert page.locator("#copy-button").is_disabled()
    page.screenshot(path=str(ARTIFACTS / f"{name}-sample-result.png"), full_page=True)
    sample_dimensions = assert_no_horizontal_overflow(page)

    problematic_console = [item for item in diagnostics["console"] if item["type"] in ("error", "warning")]
    assert not problematic_console, problematic_console
    assert not diagnostics["pageErrors"], diagnostics["pageErrors"]
    assert not diagnostics["requestFailures"], diagnostics["requestFailures"]

    result = {
        "viewport": viewport,
        "initialHiddenState": initial,
        "initialDimensions": initial_dimensions,
        "resultDimensions": result_dimensions,
        "sampleDimensions": sample_dimensions,
        "manualPolicyCards": page.locator("#policy-list .policy-card").count(),
        "console": diagnostics["console"],
        "pageErrors": diagnostics["pageErrors"],
        "requestFailures": diagnostics["requestFailures"],
        "screenshots": [
            str(ARTIFACTS / f"{name}-initial.png"),
            str(ARTIFACTS / f"{name}-manual-result.png"),
            str(ARTIFACTS / f"{name}-sample-result.png"),
        ],
    }
    context.close()
    return result


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    report = {
        "baseUrl": BASE_URL,
        "desktop": run_viewport(browser, "desktop-1440x1000", {"width": 1440, "height": 1000}),
        "mobile": run_viewport(browser, "mobile-390x844", {"width": 390, "height": 844}),
    }
    browser.close()

(ARTIFACTS / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
