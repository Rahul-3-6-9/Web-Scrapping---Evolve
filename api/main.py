from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import time
import os
import requests
import json
import re
import io
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import cv2
import numpy as np

print("DEBUG — files in api/:", os.listdir("/var/task/api"))

app = FastAPI()
starttime = time.perf_counter()
class EquipmentRequest(BaseModel):
    equipmentType: str
    modelNo: str
    manufacturer: Optional[str] = ""
    voltageRating: Optional[str] = ""

@app.post("/get-front-image")
async def get_front_image(data: EquipmentRequest):
    best_url = func(data.dict())
    return {
        "equipmentType": data.equipmentType,
        "modelNo": data.modelNo,
        "frontImageUrl": best_url or "Not found",
        "time taken": time.perf_counter() - starttime,
    }


unfetchedImages = []
max_images = 3  # Number of images to analyze per query

def any_keyword_approximately_present(text, keywords):
    text = text.lower()
    text_words = set(text.split())
    matched = 0
    for kw in keywords:
        kw = kw.lower()
        if any(kw in word or word in kw for word in text_words):
            matched += 1
    return matched >= max(1, len(keywords)//2)

def compute_frontal_score(image):
    """
    Compute a score indicating how likely an image is a frontal view.
    Uses edge detection and symmetry analysis with OpenCV.
    Returns a score (higher is better).
    """
    try:
        # Convert PIL image to OpenCV format
        image_cv = np.array(image)
        if image_cv.shape[2] == 4:  # Convert RGBA to RGB if needed
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGBA2RGB)
        image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)

        # Resize for consistency
        image_cv = cv2.resize(image_cv, (300, 300))

        # Convert to grayscale
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

        # Apply edge detection
        edges = cv2.Canny(gray, 100, 200)

        # Compute symmetry by comparing left and right halves
        h, w = edges.shape
        left_half = edges[:, :w//2]
        right_half = cv2.flip(edges[:, w//2:], 1)
        symmetry_diff = np.mean(np.abs(left_half - right_half))
        symmetry_score = 1 / (1 + symmetry_diff)  # Higher score for lower difference

        # Aspect ratio check (frontal images often have balanced aspect ratios)
        aspect_ratio = image.width / image.height
        aspect_score = 1 / (1 + abs(aspect_ratio - 1))  # Prefer ratios close to 1

        # Combine scores (weights can be tuned)
        frontal_score = 0.8 * symmetry_score + 0.2 * aspect_score
        return frontal_score

    except Exception as e:
        print(f"Error computing frontal score: {e}")
        return 0

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def func(query):
    print(f"Processing query: {query}")

    search_query = " ".join([
        query["manufacturer"],
        query["modelNo"],
        query["equipmentType"],
        f"{query['voltageRating']}V"
    ])

    keywords = [
        query["manufacturer"],
        query["modelNo"],
        query["equipmentType"]
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
        unfetchedImages.append(query["id"])

    soup = BeautifulSoup(response.text, 'html.parser')
    candidate_images = []

    # Collect up to max_images candidates
    for img_tag in soup.find_all("a", class_="iusc"):
        if len(candidate_images) >= max_images:
            break
        m_attr = img_tag.get("m")
        if not m_attr:
            continue
        try:
            m_data = json.loads(m_attr)
            title = m_data.get("t", "")
            if title and any_keyword_approximately_present(title, keywords):
                image_url = m_data.get("murl")
                print(f"Found approximately matching image with title: {title}")
                print(f"Image URL: {image_url}")

                # Download image for analysis
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
        unfetchedImages.append(query["id"])

    # Analyze images for frontal view
    best_image = None
    best_score = -1
    best_url = ""
    best_img_bytes = None

    for image_url, title, img_bytes in candidate_images:
        try:
            image = Image.open(io.BytesIO(img_bytes))
            image.verify()  # Verify image integrity
            image = Image.open(io.BytesIO(img_bytes))  # Reopen for processing
            score = compute_frontal_score(image)
            print(f"Frontal score for {image_url}: {score}")
            if score > best_score:
                best_score = score
                best_image = image
                best_url = image_url
                best_img_bytes = img_bytes
        except (UnidentifiedImageError, IOError) as e:
            print(f"Failed to process image {image_url}: {e}")
            continue

    if best_image is None:
        print(f"No valid images processed for {search_query}")
        unfetchedImages.append(query["id"])

    # Save the best image
    model_folder = query["manufacturer"]
    if not os.path.exists(model_folder):
        os.makedirs(model_folder)

    try:
        endtime = time.perf_counter()
        print("Time Taken:", endtime - starttime)
        return best_url
        # safe_filename = re.sub(r'[^\w\-_\.]', '_', search_query) + ".png"
        # image_path = os.path.join(model_folder, safe_filename)
        # best_image.save(image_path)
        # print(f"Saved best frontal image to {image_path} with score {best_score}")

    except IOError as e:
        print(f"Failed to save image for {search_query}: {e}")
        unfetchedImages.append(query["id"])

print("Unfetched Images IDs:", unfetchedImages)

endtime = time.perf_counter()
print("Time Taken:", endtime - starttime)
