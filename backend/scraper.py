import asyncio
import json
import logging
import time
from typing import Any, Dict, List
from urllib.parse import quote_plus

import newspaper
import requests
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode
from newspaper import Article


class WebScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.newspaper_config = newspaper.Config()
        self.newspaper_config.browser_user_agent = "Mozilla/5.0"
        self.newspaper_config.request_timeout = 10
        self.session = requests.Session()
        self.timeout = 10
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search_and_scrape(self, query: str, num_sites: int = 3) -> List[Dict[str, Any]]:
        self.logger.info(f"Starting search for: {query}")
        search_results = self._duckduckgo_search(query, num_sites)
        self.logger.info(f"Found {len(search_results)} search results")

        scraped_data = []
        for idx, url in enumerate(search_results):
            try:
                self.logger.info(f"Scraping [{idx + 1}/{len(search_results)}]: {url}")
                data = self._scrape_page(url)
                if data:
                    scraped_data.append(data)
                    self.logger.info(f"Successfully scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {str(e)}")
                continue

        self.logger.info(f"Completed scraping {len(scraped_data)} sites")
        return scraped_data

    def _duckduckgo_search(self, query: str, num_results: int) -> List[str]:
        self.logger.info("Performing DuckDuckGo search...")
        try:
            encoded_query = quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            response = self.session.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            search_results = []

            # DuckDuckGo search results are in elements with class 'result__url'
            for result in soup.select(".result__url"):
                url = result.get("href").replace(" ", "").replace("\\n", "")
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                search_results.append(url)
                if len(search_results) >= num_results:
                    break

            self.logger.info(f"Found {len(search_results)} URLs")
            return search_results

        except requests.exceptions.RequestException as e:  # Catch network errors specifically
            self.logger.error(f"DuckDuckGo search error: {str(e)}")
            return []
        except Exception as e:  # Catch any other errors
            self.logger.error(f"DuckDuckGo search error: {str(e)}")
            return []

    def _scrape_page(self, url: str) -> Dict[str, Any]:
        try:
            article = Article(url, config=self.newspaper_config)
            article.download()
            article.parse()
            article.nlp()
            soup = BeautifulSoup(article.html, "html.parser")
            links = self._extract_links(soup)

            data = {
                "url": url,
                "title": article.title,
                "text": article.text,
                "images": article.images,
                "videos": article.movies,
                "links": links,
                "authors": article.authors,
                "publish_date": article.publish_date,
                "metadata": {"language": article.meta_lang, "tags": article.tags},
            }

            if not data["text"]:
                response = self.session.get(url, timeout=self.timeout)
                soup = BeautifulSoup(response.text, "html.parser")
                selenium_data = {
                    "url": url,
                    "title": soup.title.string if soup.title else "",
                    "text": self._extract_text(soup),
                    "images": self._extract_images(soup),
                    "videos": self._extract_videos(soup),
                    "links": self._extract_links(soup),
                }
                return self._merge_extraction_results(data, selenium_data)

            return data

        except Exception as e:
            self.logger.error(f"Scraping error for {url}: {str(e)}")
            return {}

    def _extract_text(self, soup: BeautifulSoup) -> str:
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
        return " ".join(soup.stripped_strings)

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        return [img.get("src") for img in soup.find_all("img") if img.get("src")]

    def _extract_videos(self, soup: BeautifulSoup) -> List[str]:
        videos = []
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src", "")
            if "youtube.com" in src or "youtu.be" in src:
                videos.append(src)
        return videos

    def _extract_links(self, soup: BeautifulSoup) -> List[str]:
        return [a.get("href") for a in soup.find_all("a") if a.get("href")]

    def _merge_extraction_results(self, news_data: Dict, selenium_data: Dict) -> Dict[str, Any]:
        merged = selenium_data.copy()

        if news_data:
            for field in ["title", "text", "images", "links"]:
                if news_data.get(field):
                    merged[field] = news_data[field]

            merged.update(
                {
                    "summary": news_data.get("summary"),
                    "keywords": news_data.get("keywords"),
                    "authors": news_data.get("authors"),
                    "publish_date": news_data.get("publish_date"),
                    "metadata": news_data.get("metadata"),
                }
            )

        return merged


class CrawlForAIScraper:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.base_browser = BrowserConfig(
            browser_type="chromium",
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            accept_downloads=True,
        )
        self.crawler = AsyncWebCrawler(config=self.base_browser)
        self._is_started = False

    async def start(self):
        if not self._is_started:
            await self.crawler.start()
            time.sleep(1)
            self._is_started = True

    async def close(self):
        if self._is_started:
            await self.crawler.close()
            self._is_started = False

    async def search_and_scrape(self, query: str, num_sites: int = 10) -> List[Dict[str, Any]]:
        await self.start()
        self.logger.info(f"Starting search for: {query}")

        # Perform a search to get a list of webpages
        search_results = await self._search(query, num_sites)
        self.logger.info(f"Found {len(search_results)} search results")

        # Scrape each webpage
        scraped_data = []
        self.logger.info(f"Scraping {len(search_results)} sites...")
        data = await self._scrape_pages(search_results)
        if data:
            scraped_data.extend(data)

        self.logger.info(f"Completed scraping {len(scraped_data)} sites")
        return scraped_data

    async def _search(self, query: str, num_results: int) -> List[str]:
        self.logger.info("Performing Google search...")
        try:
            encoded_query = quote_plus(query)
            search_uri = f"https://www.google.com/search?q={encoded_query}"

            result = await self.crawler.arun(
                url=search_uri,
                screenshot=False,
                cache_mode=CacheMode.BYPASS,
                delay_before_return_html=2,
                scan_full_page=True,
            )

            soup = BeautifulSoup(result.html, "html.parser")
            search_results = []

            for link in list(soup.select("div > span > a"))[2:]:
                url = link.get("href").replace(" ", "").replace("\n", "").strip()
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                search_results.append(url)
                if len(search_results) >= num_results:
                    break

            self.logger.info(f"Found {len(search_results)} URLs")
            return search_results

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Google search error: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Google search error: {str(e)}")
            return []

    async def _scrape_pages(self, urls: str) -> Dict[str, Any]:
        await self.start()

        try:
            # Run the crawler on a URL
            results = await self.crawler.arun_many(
                urls=urls,
                screenshot=False,
                cache_mode=CacheMode.BYPASS,
                scan_full_page=True,
                semaphore_count=4,
                wait_for_images=True,
                page_timeout=25000,
            )
            scraped_sites = []
            for result in results:
                if result.success:
                    soup = BeautifulSoup(result.html, "html.parser")
                    data = {
                        "url": result.url,
                        "text": result.markdown,
                        "images": self._extract_images(soup, result.url),
                        "videos": self._extract_videos(soup),
                        "links": result.links["external"],
                    }
                    scraped_sites.append(data)
            return scraped_sites

        except Exception as e:
            self.logger.error(f"Scraping error while {urls}: {str(e)}")
            return {}

    def _extract_images(self, soup: BeautifulSoup, url: str) -> List[str]:
        # Extract images with width and height greater than 300 pixels
        images = []
        for img in soup.find_all("img"):
            if "src" in img.attrs:
                src = img["src"]
                if not "width" or not "height" in img.attrs:
                    continue
                if "width" in img.attrs and img.get("width").lower() == "auto":
                    images.append((src, 999, 0))
                # Remove units from width and height: get start of the entity till the first non-digit character
                width = "".join([i for i in img.get("width", "0") if i.isdigit() or i == "."])
                height = "".join([i for i in img.get("height", "0") if i.isdigit() or i == "."])
                width, height = float(width), float(height)
                if width > 300 and height > 300 and "pixel" not in src and "icon" not in src:
                    images.append((src, width, height))
        images = sorted(images, key=lambda img: -1 * (img[1] * img[2]))
        images = [img[0] for img in images]

        # Add base URL to relative URLs
        base_url = "/".join(url.split("/")[:3])
        images = [img if img.startswith("http") else base_url + img for img in images]
        return images

    def _extract_videos(self, soup: BeautifulSoup) -> List[str]:
        # Extract videos from iframes and video tags
        videos = []
        nodes = list(soup.find_all("iframe")) + list(soup.find_all("video")) + list(soup.find_all("a"))
        for node in nodes:
            if node.name == "iframe":
                src = node.get("src", "")
                if "youtube.com" in src or "youtu.be" in src:
                    videos.append(src)
            elif node.name == "video":
                src = node.get("src", "")
                if "youtube.com" in src or "youtu.be" in src:
                    videos.append(src)
            elif node.name == "a":
                href = node.get("href", "")
                if "youtube.com" in href or "youtu.be" in href:
                    videos.append(href)
        return videos


if __name__ == "__main__":
    import sys

    urls = [
        "https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview",
        "https://docs.crawl4ai.com/advanced/multi-url-crawling/",
        "https://github.com/SesameAILabs/csm",
        "https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview",
        "https://docs.crawl4ai.com/advanced/multi-url-crawling/",
        "https://github.com/SesameAILabs/csm",
    ]
    if len(sys.argv) > 1:
        urls = sys.argv[1:]

    async def main():
        scraper = CrawlForAIScraper()
        await scraper.start()
        data = await scraper.search_and_scrape("quantum computing")
        await scraper.close()
        with open("output.json", "w") as f:
            f.write(json.dumps(data, indent=2))
        print(json.dumps(data, indent=2))

    asyncio.run(main())
