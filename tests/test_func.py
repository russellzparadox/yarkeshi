"""Functional checks for each tool: results are consistent with what is shown, and the draws are fair."""
import asyncio
import json
from playwright.async_api import async_playwright
from test_tools import new_page, OUT

FA = "۰۱۲۳۴۵۶۷۸۹"
fa = lambda n: "".join(FA[int(c)] if c.isdigit() else c for c in str(n))
results = []


def check(name, ok, info=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{info}]" if info else ""))


async def go(page, tool):
    tile = page.locator(f'a.tile[href="#{tool}"]')
    await tile.scroll_into_view_if_needed()
    await tile.tap()
    await page.wait_for_function(f"__yarkeshi.view === '{tool}'", timeout=4000)
    await page.wait_for_timeout(500)


async def back(page):
    view = await page.evaluate("__yarkeshi.view")
    sel = "#v-finger [data-back]" if view in ("teams", "pick", "order") else f"#v-{view} [data-back]"
    await page.tap(sel)
    await page.wait_for_timeout(500)


async def y(page, key):
    return json.loads(await page.evaluate(f"JSON.stringify(__yarkeshi.{key})"))


async def fairness(page):
    counts = await page.evaluate("""() => { const c = [0,0,0,0,0,0]; for (let i = 0; i < 60000; i++) c[__yarkeshi.sample.randInt(6)]++; return c; }""")
    chi = sum((c - 10000) ** 2 / 10000 for c in counts)
    check("dice draw is uniform (chi-square, 5 dof)", chi < 20.5, f"counts={counts} chi2={chi:.1f}")
    coin = await page.evaluate("""() => { let h = 0; for (let i = 0; i < 20000; i++) h += __yarkeshi.sample.randInt(2) === 0; return h; }""")
    check("coin draw is balanced", abs(coin - 10000) < 400, f"heads={coin}/20000")
    big = await page.evaluate("""() => { let mx = 0, mn = 1e12; for (let i = 0; i < 2000; i++) { const v = __yarkeshi.sample.randInt(1000000); mx = Math.max(mx, v); mn = Math.min(mn, v); } return [mn, mx]; }""")
    check("large ranges stay in bounds", 0 <= big[0] and big[1] < 1000000, f"min/max={big}")


async def coin(page):
    await go(page, "coin")
    for i in range(3):
        await page.tap("#coinFlip")
        await page.wait_for_timeout(1700)
    c = await y(page, "coin")
    text = await page.inner_text("#coinResult")
    check("coin: three flips counted", c["heads"] + c["tails"] == 3, json.dumps(c))
    face = "شیر!" if c["angle"] == 0 else "خط!"
    check("coin: shown face matches the result", text == face, f"text={text} angle={c['angle']}")
    await page.screenshot(path=f"{OUT}/f-coin.png")
    await back(page)


async def dice(page):
    await go(page, "dice")
    await page.tap('#diceSeg button[data-n="3"]')
    await page.wait_for_timeout(300)
    await page.tap("#diceRoll")
    await page.wait_for_timeout(2200)
    d = await y(page, "dice")
    shown = await page.inner_text("#diceSum")
    check("dice: three values", len(d["vals"]) == 3 and all(1 <= v <= 6 for v in d["vals"]), str(d["vals"]))
    check("dice: shown sum matches", shown == fa(sum(d["vals"])), f"shown={shown} vals={d['vals']}")
    await page.screenshot(path=f"{OUT}/f-dice3.png")
    await page.tap('#diceSeg button[data-n="2"]')
    await page.wait_for_timeout(300)
    await page.tap("#diceRoll")
    await page.wait_for_timeout(2200)
    d = await y(page, "dice")
    name = await page.inner_text("#diceName")
    a, b = d["vals"]
    expect = ("جفت " in name) if a == b else (name == "شش و بش!" if a + b == 11 else name == "")
    check("dice: backgammon name for two dice", expect, f"vals={d['vals']} name={name!r}")
    await page.screenshot(path=f"{OUT}/f-dice2.png")
    await back(page)


async def wheel(page):
    await go(page, "wheel")
    await page.tap("#wheelSpin")
    await page.wait_for_timeout(6200)
    w = await y(page, "wheel")
    ok = await page.evaluate("__yarkeshi.sample.sliceAt(__yarkeshi.wheel.rot, __yarkeshi.wheel.opts.length) === __yarkeshi.wheel.winner")
    text = await page.inner_text("#wheelRes")
    check("wheel: pointer slice is the winner", ok and w["winner"] >= 0, f"winner={w['winner']}")
    check("wheel: shown result is the winner", text == w["opts"][w["winner"]], f"text={text}")
    await page.screenshot(path=f"{OUT}/f-wheel.png")
    # raffle mode: winners leave the wheel
    await page.tap("#wheelRemove")
    n0 = len(w["opts"])
    await page.tap("#wheelSpin")
    await page.wait_for_timeout(6200)
    w1 = await y(page, "wheel")
    await page.tap("#wheelSpin")
    await page.wait_for_timeout(6200)
    w2 = await y(page, "wheel")
    check("wheel raffle: drawn list grows", len(w2["drawn"]) == 2, str(w2["drawn"]))
    check("wheel raffle: first winner removed", len(w2["opts"]) == n0 - 1 and w1["drawn"][0] not in w2["opts"], f"opts={w2['opts']}")
    await page.screenshot(path=f"{OUT}/f-wheel-raffle.png")
    await page.tap("#wheelRestore")
    await page.tap("#wheelRemove")
    await page.wait_for_timeout(200)
    w3 = await y(page, "wheel")
    check("wheel raffle: restore brings everyone back", len(w3["opts"]) == n0 and not w3["drawn"], str(w3["opts"]))
    # editing
    await page.fill("#wheelInput", "سوشی")
    await page.press("#wheelInput", "Enter")
    await page.wait_for_timeout(200)
    w4 = await y(page, "wheel")
    check("wheel: add an option", "سوشی" in w4["opts"] and len(w4["opts"]) == n0 + 1)
    await page.tap('#wheelList button[data-i="0"]')
    await page.wait_for_timeout(200)
    w5 = await y(page, "wheel")
    check("wheel: remove an option", len(w5["opts"]) == n0, str(w5["opts"]))
    await back(page)


async def number(page):
    await go(page, "number")
    await page.fill("#numFrom", "۱")
    await page.fill("#numTo", "5")
    await page.tap("#numNoRepeat")
    for i in range(5):
        await page.tap("#numGo")
        await page.wait_for_timeout(1150)
    n = await y(page, "number")
    check("number: five unique draws from 1-5", sorted(n["drawn"]) == [1, 2, 3, 4, 5], str(n["drawn"]))
    await page.tap("#numGo")
    await page.wait_for_timeout(300)
    err = await page.is_visible("#numErr")
    check("number: sixth draw is refused when no repeats", err, await page.inner_text("#numErr") if err else "")
    await page.screenshot(path=f"{OUT}/f-number.png")
    await page.fill("#numTo", "۱")
    await page.fill("#numFrom", "9")
    await page.tap("#numGo")
    await page.wait_for_timeout(200)
    check("number: reversed range explained", await page.is_visible("#numErr"), await page.inner_text("#numErr"))
    await page.fill("#numFrom", "1")
    await page.fill("#numTo", "100")
    await page.tap("#numClear")
    await back(page)


async def arrow(page):
    await go(page, "arrow")
    r0 = (await y(page, "arrow"))["rot"]
    await page.tap("#arrowCv", position={"x": 200, "y": 300})
    await page.wait_for_timeout(5200)
    a = await y(page, "arrow")
    check("arrow: spun and stopped", (not a["spinning"]) and abs(a["rot"] - r0) > 0.01, json.dumps(a))
    await page.screenshot(path=f"{OUT}/f-arrow.png")
    await back(page)


async def cast(page, k):
    await page.tap('[data-act="ballot"]')
    await page.tap(f'[data-act="pick"][data-k="{k}"]')
    await page.tap('[data-act="cast"]')
    await page.wait_for_timeout(1500)


async def vote(page):
    await go(page, "vote")
    await page.fill("#voteQ", "امشب کجا برویم؟")
    await page.tap("#vMinus")          # 4 -> 3 voters
    await page.tap("#voteStart")
    await page.wait_for_timeout(400)
    await page.screenshot(path=f"{OUT}/f-vote-cover.png")
    await page.tap('[data-act="ballot"]')
    await page.wait_for_timeout(300)
    await page.screenshot(path=f"{OUT}/f-vote-ballot.png")
    await page.tap('[data-act="pick"][data-k="0"]')
    await page.tap('[data-act="cast"]')
    await page.wait_for_timeout(1500)
    # leaving mid-vote asks first
    await back(page)
    check("vote: leaving mid-vote asks first", await page.is_visible("#modal") and (await y(page, "view")) == "vote")
    await page.screenshot(path=f"{OUT}/f-vote-guard.png")
    await page.tap("#modalCancel")
    await page.wait_for_timeout(300)
    check("vote: staying keeps the votes", (await y(page, "vote"))["i"] == 1 and (await y(page, "view")) == "vote")
    await cast(page, 1)
    await cast(page, 1)
    v = await y(page, "vote")
    check("vote: everyone voted", v["step"] == "done" and v["counts"][:3] == [1, 2, 0], json.dumps(v))
    await page.tap('[data-act="results"]')
    await page.wait_for_timeout(1200)
    verdict = await page.inner_text(".verdict")
    check("vote: winner announced", "کافه" in verdict, verdict)
    await page.screenshot(path=f"{OUT}/f-vote-results.png")
    # a tie, then a draw between the tied options
    await page.tap('[data-act="edit"]')
    await page.tap("#vMinus")          # 3 -> 2 voters
    await page.tap("#voteStart")
    await page.wait_for_timeout(300)
    await cast(page, 0)
    await cast(page, 2)
    await page.tap('[data-act="results"]')
    await page.wait_for_timeout(600)
    await page.tap('[data-act="tiebreak"]')
    await page.wait_for_timeout(2500)
    v = await y(page, "vote")
    check("vote: tie broken by draw", v["tiePick"] in (0, 2), json.dumps(v))
    await page.screenshot(path=f"{OUT}/f-vote-tie.png")
    await back(page)
    check("vote: results screen leaves freely", (await y(page, "view")) == "home")


async def fingers(page, ctx, tool, n_points, setting=None):
    await go(page, tool)
    if setting:
        await page.tap(f'#fseg button[data-n="{setting}"]')
        await page.wait_for_timeout(300)
    cdp = await ctx.new_cdp_session(page)
    pts = [(90, 760), (310, 720), (70, 470), (330, 450), (140, 220), (290, 200)][:n_points]
    tp = [{"x": x, "y": yy, "id": i} for i, (x, yy) in enumerate(pts)]
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": tp})
    await page.wait_for_timeout(4200)
    res = await y(page, "result")
    labels = await y(page, "labels")
    await page.screenshot(path=f"{OUT}/f-{tool}.png")
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await page.wait_for_timeout(900)
    await page.screenshot(path=f"{OUT}/f-{tool}-held.png")
    mode = await y(page, "mode")
    await page.tap("#again")
    await page.wait_for_timeout(500)
    await back(page)
    return res, labels, mode


async def main():
    async with async_playwright() as p:
        browser, ctx, page, logs = await new_page(p)
        await fairness(page)
        await coin(page)
        await dice(page)
        await wheel(page)
        await number(page)
        await arrow(page)
        await vote(page)
        res, labels, mode = await fingers(page, ctx, "pick", 5, setting=2)
        check("pick: two people chosen", res and res["kind"] == "pick" and res["k"] == 2 and labels.count("تو!") == 2, f"{res} {labels}")
        check("pick: result stays after hands lift", mode == "held", mode)
        res, labels, mode = await fingers(page, ctx, "order", 6)
        check("order: every finger numbered once", sorted(labels) == sorted(fa(i) for i in range(1, 7)), str(labels))
        res, labels, mode = await fingers(page, ctx, "teams", 6, setting=3)
        check("teams: three teams of two", res and res["kind"] == "teams" and res["counts"] == [2, 2, 2], str(res))
        print("console:", logs or "clean")
        await browser.close()
    print(f"\n{sum(ok for _, ok in results)}/{len(results)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
