"""Drive the app in a phone-sized headless Chromium with real multi-touch events and save screenshots."""
import asyncio
import sys
from playwright.async_api import async_playwright

OUT = "/tmp/claude-0/-home-claude/4caeeba2-6c00-5088-8a1b-6aa49e5a72d5/scratchpad/shots"
URL = "file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "web", "index.html")) + ""


async def state(page):
    return await page.evaluate("({mode: __yarkeshi.mode, renderer: __yarkeshi.renderer, scale: __yarkeshi.glScale, fingers: __yarkeshi.fingers})")


async def run(w, h, tag, points, teams_button=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        logs = []
        page.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        await page.goto(URL)
        await page.wait_for_timeout(1200)
        print(tag, "start", await state(page))
        await page.screenshot(path=f"{OUT}/{tag}-1-idle.png")
        if teams_button:
            await page.tap(teams_button)
            await page.wait_for_timeout(300)
            pressed = await page.evaluate(f"document.querySelector('{teams_button}').getAttribute('aria-pressed')")
            print(tag, "tapped", teams_button, "pressed =", pressed, await state(page))
        cdp = await ctx.new_cdp_session(page)
        pts = [{"x": x, "y": y, "id": i, "radiusX": 8, "radiusY": 8, "force": 1} for i, (x, y) in enumerate(points)]
        # one finger first, to see the "need more players" state
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": pts[:1]})
        await page.wait_for_timeout(500)
        print(tag, "one finger", await state(page))
        await page.screenshot(path=f"{OUT}/{tag}-2-one.png")
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": pts})
        await page.wait_for_timeout(600)
        print(tag, "all fingers", await state(page))
        await page.screenshot(path=f"{OUT}/{tag}-3-touch.png")
        await page.wait_for_timeout(1100)
        await page.screenshot(path=f"{OUT}/{tag}-4-countdown.png")
        await page.wait_for_timeout(2000)
        print(tag, "after hold", await state(page))
        await page.screenshot(path=f"{OUT}/{tag}-5-reveal.png")
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        await page.wait_for_timeout(1000)
        print(tag, "lifted", await state(page))
        await page.screenshot(path=f"{OUT}/{tag}-6-held.png")
        await page.tap("#again")
        await page.wait_for_timeout(900)
        print(tag, "after again", await state(page))
        await page.screenshot(path=f"{OUT}/{tag}-7-back.png")
        print(tag, "console:", logs or "clean")
        await browser.close()


SIX = [(96, 750), (305, 705), (74, 488), (134, 224), (336, 470), (296, 198)]
SEVEN = [(70, 560), (200, 520), (300, 470), (90, 300), (260, 250), (180, 120), (300, 590)]

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "main"
    if which == "main":
        asyncio.run(run(412, 915, "p412", SIX))
    else:
        asyncio.run(run(360, 640, "p360", SEVEN, teams_button="#t3"))
