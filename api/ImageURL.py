from typing import Any
import requests
import json
import re
import io
import os
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import cv2
import numpy as np
import time
from numpy import floating, complexfloating, timedelta64

starttime = time.perf_counter()
unfetchedImages = []
max_images = 3  
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
candidate_images = []
best_image = None
best_score = -1
best_url = ""

class ImageURL:

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
        return matched >= max(1, len(keywords)//2)

    def compute_frontal_score(self, image) -> float:
        try:

            image_cv = np.array(image)
            if image_cv.shape[2] == 4:
                image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGBA2RGB)
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)

            image_cv = cv2.resize(image_cv, (300, 300))

            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

            edges = cv2.Canny(gray, 100, 200)

            h, w = edges.shape
            left_half = edges[:, :w//2]
            right_half = cv2.flip(edges[:, w//2:], 1)
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
        global response, best_score
        print(f"Processing query: {self.query}")

        search_query = " ".join([
            self.query["manufacturer"],
            self.query["modelNo"],
            self.query["equipmentType"],
            f"{self.query['voltageRating']}V"
        ])

        keywords = [
            self.query["manufacturer"],
            self.query["modelNo"],
            self.query["equipmentType"]
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
            unfetchedImages.append(self.query["id"])

        soup = BeautifulSoup(response.text, 'html.parser')


        for img_tag in soup.find_all("a", class_="iusc"):
            if len(candidate_images) >= max_images:
                break
            m_attr = img_tag.get("m")
            if not m_attr:
                continue
            try:
                m_data = json.loads(m_attr)
                title = m_data.get("t", "")
                if title and self.any_keyword_approximately_present(title, keywords):
                    image_url = m_data.get("murl")
                    print(f"Found approximately matching image with title: {title}")
                    print(f"Image URL: {image_url}")


                    try:
                        img_response = requests.get(image_url, headers=headers, timeout=10)
                        img_response.raise_for_status()
                        img_bytes = img_response.content
                        candidate_images.append((image_url, title, img_bytes))
                    except requests.RequestException as e:
                        print(f"Failed to download image {image_url}: {e}")
                        continue
            except json.JSONDecodeError:
                print("Failed to parse JSON from 'm' attribute")
                continue

        if not candidate_images:
            print(f"No approximately matching images found for {search_query}")
            unfetchedImages.append(self.query["id"])


        for image_url, title, img_bytes in candidate_images:
            try:
                image = Image.open(io.BytesIO(img_bytes))
                image.verify()
                image = Image.open(io.BytesIO(img_bytes))
                score = self.compute_frontal_score(image)
                print(f"Frontal score for {image_url}: {score}")
                if score > best_score:
                    best_score = score
                    best_image = image
                    best_url = image_url
            except (UnidentifiedImageError, IOError) as e:
                print(f"Failed to process image {image_url}: {e}")
                continue

        if best_image is None:
            print(f"No valid images processed for {search_query}")
            unfetchedImages.append(self.query["id"])

        try:
            endtime = time.perf_counter()
            print("Time Taken:", endtime - starttime)
            return best_url

        except IOError as e:
            print(f"Failed to save image for {search_query}: {e}")
            unfetchedImages.append(self.query["id"])

    print("Unfetched Images IDs:", unfetchedImages)

    endtime = time.perf_counter()
    print("Time Taken:", endtime - starttime)
