import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

class SpecSheetURL:

    def __init__(self, query):
        self.query = query

    def any_keyword_approximately_present(self, text:str, keywords:list[str]) -> int:
        text = text.lower()
        text_words = set(text.split())
        matched = 0
        for kw in keywords:
            kw = kw.lower()
            if any(kw in word or word in kw for word in text_words):
                matched += 1
        return matched >= max(1, len(keywords) // 2)

    def search_engine_urls(self, max_pages=3) -> list[str]:

        search_query = " ".join([
            self.query["manufacturer"],
            self.query["modelNo"],
            self.query["equipmentType"],
            f"specifications sheet filetype:pdf"
        ])
        encoded_query = quote_plus(search_query)

        bing_urls = [
            f"https://www.bing.com/search?q={encoded_query}&form=HDRSC2&first={i * 10 + 1}"
            for i in range(max_pages)
        ]

        google_urls = [
            f"https://www.google.com/search?q={encoded_query}&start={i * 10}"
            for i in range(max_pages)
        ]

        return bing_urls + google_urls

    def specSheet(self, max_pages=3, delay=2) -> str:

        keywords = [self.query["manufacturer"]]
        search_urls = self.search_engine_urls(max_pages)

        for search_url in search_urls:
            print(f"Searching: {search_url}")
            try:
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Failed to fetch search page for {search_url}: {e}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            for h2 in soup.find_all("h2"):
                a_tag = h2.find("a")
                if not a_tag:
                    continue

                text = a_tag.text
                href = a_tag.get("href")

                if not (text and href and ".pdf" in href.lower() and self.any_keyword_approximately_present(text, keywords)):
                    continue

                try:
                    pdf_response = requests.head(href, headers=headers, timeout=5, allow_redirects=True)
                    if pdf_response.status_code == 200 and 'application/pdf' in pdf_response.headers.get('content-type',
                                                                                                         ''):
                        print(f"PDF match: {text}")
                        print(f"URL: {href}")
                        return href
                except requests.RequestException:
                    continue

            time.sleep(delay)

        print ("No valid PDF specification sheet found after searching multiple pages and engines.")
        return None
