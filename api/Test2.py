import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import time


def any_keyword_approximately_present(text, keywords):
    text = text.lower()
    text_words = set(text.split())
    matched = 0
    for kw in keywords:
        kw = kw.lower()
        if any(kw in word or word in kw for word in text_words):
            matched += 1
    return matched >= max(1, len(keywords) // 2)


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def search_engine_urls(query, max_pages=3):
    """Generate search URLs for Bing and Google."""
    search_query = " ".join([
        query["manufacturer"],
        query["modelNo"],
        query["equipmentType"],
        f"{query['voltageRating']}V",
        f"specifications sheet filetype:pdf"
    ])
    encoded_query = quote_plus(search_query)

    # Bing search URLs
    bing_urls = [
        f"https://www.bing.com/search?q={encoded_query}&form=HDRSC2&first={i * 10 + 1}"
        for i in range(max_pages)
    ]

    # Google search URLs
    google_urls = [
        f"https://www.google.com/search?q={encoded_query}&start={i * 10}"
        for i in range(max_pages)
    ]

    return bing_urls + google_urls


def specSheet(query, max_pages=3, delay=2):
    """Search for a PDF specification sheet within <a> tags inside <h2> tags across multiple pages and search engines."""
    keywords = [query["manufacturer"], query["modelNo"]]

    # Get search URLs for Bing and Google
    search_urls = search_engine_urls(query, max_pages)

    for search_url in search_urls:
        print(f"Searching: {search_url}")
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch search page for {search_url}: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all <h2> tags and check their <a> tags
        for h2 in soup.find_all("h2"):
            a_tag = h2.find("a")
            if not a_tag:
                continue

            text = a_tag.text
            href = a_tag.get("href")

            # Skip if no text or href, or if not a PDF link
            if not (text and href and ".pdf" in href.lower() and any_keyword_approximately_present(text, keywords)):
                continue

            # Verify the link points to a valid PDF
            try:
                pdf_response = requests.head(href, headers=headers, timeout=5, allow_redirects=True)
                if pdf_response.status_code == 200 and 'application/pdf' in pdf_response.headers.get('content-type',
                                                                                                     ''):
                    print(f"PDF match: {text}")
                    print(f"URL: {href}")
                    return href  # Return the first valid PDF URL
            except requests.RequestException:
                continue

        # Add delay to avoid rate-limiting
        time.sleep(delay)

    print ("No valid PDF specification sheet found after searching multiple pages and engines.")
    return None

# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import quote_plus
#
# def specSheet(query, max_pages=3, delay=2):
#     searchQuery = " ".join([
#         query["manufacturer"],
#         query["modelNo"],
#         query["equipmentType"],
#         f"{query['voltageRating']}V",
#         f"specifications sheet filetype:pdf"
#     ])
#     search_url = "https://www.google.com/search?q=" + quote_plus(searchQuery)
#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
#         )
#     }
#
#     response = requests.get(search_url, headers=headers)
#     response.raise_for_status()
#
#     soup = BeautifulSoup(response.text, "html.parser")
#
#     # Find all result blocks
#     for h2 in soup.find_all("h2"):
#         print(h2)
#         a = h2.find("a")
#         href = a.get("href")
#         return href
#
#     return "No valid result found."
#
# print(specSheet({
#   "equipmentType": "EV Charger",
#   "modelNo": "Terra 54 HV",
#   "manufacturer": "ABB",
#   "voltageRating": ""
# })
# )

