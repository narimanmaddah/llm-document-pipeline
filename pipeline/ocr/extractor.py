import pytesseract
from PIL import Image
import io
from typing import Tuple


class OCRExtractor:
    def extract_text(self, image_path: str) -> str:
        """Extract text from image using Tesseract OCR."""
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()

    def extract_from_bytes(self, image_bytes: bytes) -> str:
        """Extract text from image bytes."""
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
