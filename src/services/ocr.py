import pytesseract
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_bytes
import os

pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", "tesseract"
)

def preprocess_image(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def extract_text_from_image(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        pages = convert_from_bytes(file_bytes)
        texts = [pytesseract.image_to_string(page) for page in pages]
        return "\n".join(texts).strip()

    img_array = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    processed = preprocess_image(img)
    return pytesseract.image_to_string(Image.fromarray(processed)).strip()
