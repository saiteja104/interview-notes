import asyncio
from playwright.async_api import async_playwright


async def check():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--display=:99",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--use-fake-ui-for-media-stream",
                "--disable-gpu"
            ]
        )
        page = await browser.new_page()

        print("Navigating...")
        await page.goto(
            "https://zoom.us/wc/join/73850955863?pwd=BZaZ6ZtrUMEVqRpubNF87tSGKIRBR2.1",
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Wait and take snapshots every 5 seconds for 40 seconds
        for i in range(8):
            await asyncio.sleep(5)
            elapsed = (i + 1) * 5

            title = await page.title()
            url   = page.url

            inputs = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input')).map(el => ({
                    id: el.id,
                    name: el.name,
                    placeholder: el.placeholder,
                    className: el.className,
                    type: el.type,
                }));
            }""")

            buttons = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button')).map(el => ({
                    text: el.innerText.trim(),
                    className: el.className,
                })).filter(b => b.text.length > 0).slice(0, 10);
            }""")

            print(f"\n--- {elapsed}s ---")
            print(f"URL:     {url}")
            print(f"Title:   {title}")
            print(f"Inputs:  {inputs}")
            print(f"Buttons: {buttons}")

            # Stop early if we find something useful
            if len(inputs) > 1:
                print(">>> Found inputs! Stopping early.")
                break

        await page.screenshot(path="/tmp/debug_final.png")
        await browser.close()


asyncio.run(check())