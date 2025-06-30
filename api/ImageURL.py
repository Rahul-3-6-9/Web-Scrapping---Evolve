from typing import Any
import requests
import json
import re
import io
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import cv2
import numpy as np
import time

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

class ImageURL:
    def __init__(self, query):
        self.query = query
        self.max_images = 3
        self.candidate_images = []
        self.best_image = None
        self.best_score = -1
        self.best_url = None
        self.unfetched_ids = []

    def any_keyword_approximately_present(self, text: str, keywords: list[str]) -> bool:
        text = text.lower()
        text_words = set(text.split())
        matched = 0
        for kw in keywords:
            kw = kw.lower()
            if any(kw in word or word in kw for word in text_words):
                matched += 1
        return matched >= max(1, len(keywords) // 2)

    def compute_frontal_score(self, image) -> float:
        try:
            image_cv = np.array(image)
            if len(image_cv.shape) == 3 and image_cv.shape[2] == 4:
                image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGBA2RGB)
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)
            image_cv = cv2.resize(image_cv, (300, 300))

            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)

            h, w = edges.shape
            left_half = edges[:, :w // 2]
            right_half = cv2.flip(edges[:, w // 2:], 1)
            symmetry_diff = np.mean(np.abs(left_half - right_half))
            symmetry_score = 1 / (1 + symmetry_diff)

            aspect_ratio = image.width / image.height
            aspect_score = 1 / (1 + abs(aspect_ratio - 1))

            frontal_score = 0.8 * symmetry_score + 0.2 * aspect_score
            return frontal_score

        except Exception as e:
            print(f"Error computing frontal score: {e}")
            return 0

    def imageURLFinder(self) -> str | None:
        starttime = time.perf_counter()
        print(f"Processing query: {self.query}")

        search_query = " ".join([
            self.query.get("manufacturer", ""),
            self.query.get("modelNo", ""),
            self.query.get("equipmentType", ""),
            f'{self.query.get("voltageRating", "")}V'
        ])
        keywords = [
            self.query.get("manufacturer", ""),
            self.query.get("modelNo", ""),
            self.query.get("equipmentType", "")
        ]
        print(f"Keywords for approximate filtering: {keywords}")

        encoded_query = quote_plus(search_query)
        search_url = f"https://www.bing.com/images/search?q={encoded_query}&form=HDRSC2"
        print(f"Search URL: {search_url}")

        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch search page for {search_query}: {e}")
            self.unfetched_ids.append(self.query.get("id", "unknown"))
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        for img_tag in soup.find_all("a", class_="iusc"):
            if len(self.candidate_images) >= self.max_images:
                break
            m_attr = img_tag.get("m")
            if not m_attr:
                continue
            try:
                m_data = json.loads(m_attr)
                title = m_data.get("t", "")
                image_url = m_data.get("murl")
                if title and image_url and self.any_keyword_approximately_present(title, keywords):
                    print(f"Found matching image with title: {title}")
                    print(f"Image URL: {image_url}")
                    try:
                        img_response = requests.get(image_url, headers=headers, timeout=10)
                        img_response.raise_for_status()
                        self.candidate_images.append((image_url, title, img_response.content))
                    except requests.RequestException as e:
                        print(f"Failed to download image {image_url}: {e}")
            except json.JSONDecodeError:
                print("Failed to parse JSON from 'm' attribute")

        if not self.candidate_images:
            print(f"No matching images found for {search_query}")
            self.unfetched_ids.append(self.query.get("id", "unknown"))
            return None

        for image_url, title, img_bytes in self.candidate_images:
            try:
                image = Image.open(io.BytesIO(img_bytes))
                image.verify()
                image = Image.open(io.BytesIO(img_bytes))
                score = self.compute_frontal_score(image)
                print(f"Frontal score for {image_url}: {score}")
                if score > self.best_score:
                    self.best_score = score
                    self.best_image = image
                    self.best_url = image_url
            except (UnidentifiedImageError, IOError) as e:
                print(f"Failed to process image {image_url}: {e}")

        endtime = time.perf_counter()
        print("Time Taken:", endtime - starttime)

        if not self.best_image:
            print(f"No valid images processed for {search_query}")
            self.unfetched_ids.append(self.query.get("id", "unknown"))
            return None

        return self.best_url
