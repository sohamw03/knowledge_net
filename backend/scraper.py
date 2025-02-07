from bs4 import BeautifulSoup
from selenium import webdriver
import logging
from typing import List, Dict, Any
import newspaper
from newspaper import Article
import re
import requests


class WebScraper:
    def __init__(self):
        self.chrome_options = webdriver.ChromeOptions()
        # self.chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.logger = logging.getLogger(__name__)
        self.newspaper_config = newspaper.Config()
        self.newspaper_config.browser_user_agent = "Mozilla/5.0"
        self.newspaper_config.request_timeout = 10
        self.session = requests.Session()
        self.timeout = 30

    def setup(self):
        pass  # No setup needed for synchronous operation

    def cleanup(self):
        if self.driver:
            self.driver.quit()

    def search_and_scrape(
        self, query: str, num_sites: int = 10
    ) -> List[Dict[str, Any]]:
        self.logger.info(f"Starting search for: {query}")
        search_results = self._google_search(query, num_sites)
        self.logger.info(f"Found {len(search_results)} search results")

        scraped_data = []
        for idx, url in enumerate(search_results):
            try:
                self.logger.info(f"Scraping [{idx + 1}/{len(search_results)}]: {url}")
                data = self._scrape_url(url)
                if data:
                    scraped_data.append(data)
                    self.logger.info(f"Successfully scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {str(e)}")
                continue

        self.logger.info(f"Completed scraping {len(scraped_data)} sites")
        return scraped_data

    def _google_search(self, query: str, num_results: int) -> List[str]:
        self.logger.info("Performing Google search...")
        try:
            self.driver.get(
                f"https://www.google.com/search?q={query.replace(' ', '+')}&num={num_results}"
            )
            self.driver.implicitly_wait(5)

            elements = self.driver.find_elements("css selector", "div.g div.yuRUbf > a")
            search_results = []
            for element in elements:
                url = element.get_attribute("href")
                if url and url.startswith("http"):
                    search_results.append(url)
                    if len(search_results) >= num_results:
                        break

            self.logger.info(f"Found {len(search_results)} URLs")
            return search_results

        except Exception as e:
            self.logger.error(f"Google search error: {str(e)}")
            return []

    def _scrape_url(self, url: str) -> Dict[str, Any]:
        try:
            article = Article(url, config=self.newspaper_config)
            article.download()
            article.parse()
            article.nlp()

            data = {
                "url": url,
                "title": article.title,
                "text": article.text,
                "summary": article.summary,
                "keywords": article.keywords,
                "images": article.images,
                "videos": [],
                "links": article.links,
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
            return None

    def _merge_extraction_results(
        self, news_data: Dict, selenium_data: Dict
    ) -> Dict[str, Any]:
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
