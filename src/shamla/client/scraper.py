import zendriver as zd
import asyncio
from contextlib import asynccontextmanager
import time


class Network:
    def __init__(self, browser: zd.Browser, verbose: bool):
        self.browser = browser
        self.verbose = verbose

    @classmethod
    async def create(cls, headless, verbose: bool = True):
        config = zd.Config()
        config.headless = headless
        browser = await zd.start(config=config)
        return cls(browser, verbose)

    async def wait_for_selector(
        self, page, selector: str, timeout: float = 15, checking_interval: float = 0.2
    ):
        start = time.monotonic()

        while (time.monotonic() - start) < timeout:
            try:
                el = await page.query_selector(selector)
                if el:
                    return el
            except Exception as e:
                if self.verbose:
                    print(f"Exception {e} while waiting for selector")

            await asyncio.sleep(checking_interval)

        raise TimeoutError(f"Timeout waiting for selector: {selector}")

    async def get(self, url: str, wait_for: str | None = None, timeout=15, retries=1):
        page = await self.browser.get(url,new_tab=True)
        if wait_for:
            for attempt in range(retries):
                try:
                    await self.wait_for_selector(page, wait_for, timeout=timeout)
                    break
                except TimeoutError:
                    if self.verbose:
                        print(f"Attempt {attempt + 1}/{retries} failed for {url}")
                    await page.close()
                    if attempt < retries - 1:
                        page = await self.browser.get(url,new_tab=True)
                    else:
                        raise
        return page


class Scraper:
    def __init__(self, network: Network):
        self.network = network

    async def get_book(self, url: str) -> str:
        page = await self.network.get(url, ".text-center")

        html = await page.get_content()
        return html

    @classmethod
    @asynccontextmanager
    async def create_scraper(cls, headless=False):
        network = await Network.create(headless)
        scraper = cls(network)
        try:
            yield scraper
        finally:
            await scraper.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.network.browser.stop()


