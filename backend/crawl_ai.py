import asyncio
import json

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode


async def main(urls):
    base_browser = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        accept_downloads=True,
    )

    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler(config=base_browser) as crawler:
        # Run the crawler on a URL
        results = await crawler.arun_many(
            urls=urls,
            screenshot=False,
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            semaphore_count=3,
            wait_for_images=True,
        )
        with open("output.json", "w") as f:
            f.write("")
        for result in results:
            if result.success:
                dump_result = {
                    "url": result.url,
                    "markdown": result.markdown,
                }
                with open("output.json", "a") as f:
                    json.dump(dump_result, f)
                # Print the extracted content
                hr = lambda n=1: print(("-" * 80) * 2 * n)
                print("[OK] URL:", result.url)
                hr()

        # if result.success:
        #     # Save screenshot
        #     if result.screenshot:
        #         with open("screenshot.png", "wb") as f:
        #             f.write(b64decode(result.screenshot))
        #
        #     # Save PDF
        #     if result.pdf:
        #         with open("download.pdf", "wb") as f:
        #             f.write(result.pdf)
        #
        #     print("[OK] PDF & screenshot captured.")
        # else:
        #     print("[ERROR]", result.error_message)


if __name__ == "__main__":
    urls = [
        "https://www.google.com",
        "https://www.amazon.com",
        "https://www.facebook.com",
        "https://www.twitter.com",
        "https://www.instagram.com",
    ]
    asyncio.run(main(urls))
