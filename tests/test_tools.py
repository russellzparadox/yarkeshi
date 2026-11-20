"""Smoke-test every view of the decision kit in a phone-sized headless Chromium and save screenshots."""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

OUT = "/tmp/claude-0/-home-claude/4caeeba2-6c00-5088-8a1b-6aa49e5a72d5/scratchpad/shots"
URL = "file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "web", "index.html")) + ""
ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


async def new_page(p, w=412, h=915):
    browser = await p.chromium.launch(args=ARGS)
    ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = await ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    await page.goto(URL)
    await page.wait_for_timeout(700)
    return browser, ctx, page, logs


async def st(page, key):
    return await page.evaluate(f"JSON.stringify(__yarkeshi.{key})")


async def tour():
    async with async_playwright() as p:
        browser, ctx, page, logs = await new_page(p)
        await page.screenshot(path=f"{OUT}/t-home.png")
        await page.screenshot(path=f"{OUT}/t-home-full.png", full_page=False)
        # scroll the home view to its end for a second shot
        await page.evaluate("document.getElementById('v-home').scrollTop = 10000")
        await page.wait_for_timeout(200)
        await page.screenshot(path=f"{OUT}/t-home-end.png")
        await page.evaluate("document.getElementById('v-home').scrollTop = 0")

        for tool in ["coin", "dice", "wheel", "number", "arrow", "vote", "pick", "order", "teams"]:
            tile = page.locator(f'a.tile[href="#{tool}"]')
            await tile.scroll_into_view_if_needed()
            await tile.tap()
            await page.wait_for_function(f"__yarkeshi.view === '{tool}'", timeout=4000)
            await page.wait_for_timeout(600)
            view = await page.evaluate("__yarkeshi.view")
            await page.screenshot(path=f"{OUT}/t-{tool}-0.png")
            print(tool, "view =", view)
            await page.tap(f"#v-{'finger' if tool in ('pick','order','teams') else tool} [data-back]")
            await page.wait_for_timeout(600)
            print("  back ->", await page.evaluate("__yarkeshi.view"), "hash =", await page.evaluate("location.hash"))
        print("console:", logs or "clean")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(tour())
