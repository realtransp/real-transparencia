"""Verificação end-to-end do portal com Playwright.

Testa páginas, a análise auto-carregada e o fluxo "Cobrar" (captura o link do WhatsApp
com o número do gabinete). Rode com o servidor no ar:  uv run python verify_playwright.py
"""
import asyncio

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8010"


async def main():
    out = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # captura window.open (mailto/wa.me) sem abrir nada
        await page.add_init_script("window.__opened=[]; window.open=(u)=>{window.__opened.push(u); return null;}")

        async def check(name, coro):
            try:
                v = await coro
                out.append(f"✓ {name}: {v}")
            except Exception as e:  # noqa: BLE001
                out.append(f"✗ {name}: {type(e).__name__} {str(e)[:90]}")

        # 1) Landing
        await page.goto(f"{BASE}/", wait_until="load")
        out.append(f"✓ landing título: {await page.title()}")
        out.append(f"✓ hero stats: {await page.locator('.hero-stats .s').count()} blocos")

        # 2) Feed
        await page.goto(f"{BASE}/agora", wait_until="load")
        out.append(f"✓ feed: {await page.locator('.feed-item').count()} itens")

        # 3) Votação — análise auto-carregada
        href = await page.locator(".feed-item").first.get_attribute("href")
        await page.goto(f"{BASE}{href}", wait_until="load")
        await page.wait_for_timeout(3500)  # espera o hx-trigger=load
        resumo = (await page.locator("#resumo").inner_text())[:80].replace("\n", " ")
        out.append(f"✓ votação análise: \"{resumo}…\"")
        out.append(f"✓ recorte partidos: {await page.locator('.party-row').count()} partidos")

        # 4) Deputado + fluxo Cobrar (WhatsApp)
        await page.goto(f"{BASE}/deputados", wait_until="load")
        dep_href = await page.locator("a.dep-card").first.get_attribute("href")
        await page.goto(f"{BASE}{dep_href}", wait_until="load")
        await page.wait_for_timeout(3000)
        await page.locator(".js-cobrar").first.click()
        await page.wait_for_selector("#cobre-modal .modal", state="visible")
        out.append("✓ modal Cobrar abriu")
        await page.locator('.js-channel[data-channel="whatsapp"]').click()
        wa_label = await page.locator(".js-wa-label").inner_text()
        out.append(f"✓ WhatsApp do gabinete: {wa_label}")
        await page.locator(".js-send").click()
        await page.wait_for_timeout(500)
        opened = await page.evaluate("window.__opened")
        out.append(f"✓ link aberto ao enviar: {opened}")

        await browser.close()
    print("\n".join(out))


if __name__ == "__main__":
    asyncio.run(main())
