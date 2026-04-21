import cv2
import numpy as np
from PIL import Image


class QualityClassifier:
    """Lightweight CNN-inspired quality scorer without requiring pretrained weights."""

    def score(self, image_path: str) -> float:
        """Score document quality 0-1 based on image properties."""
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return 0.0

            # Brightness check: docs typically 80-200 average intensity
            brightness = np.mean(img)
            brightness_score = 1.0 - abs(brightness - 140) / 255.0
            brightness_score = max(0, min(1, brightness_score))

            # Contrast check: sufficient variance indicates readable text
            contrast = np.std(img)
            contrast_score = min(1.0, contrast / 60.0)

            # Sharpness check via Laplacian variance
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            sharpness = laplacian.var()
            sharpness_score = min(1.0, sharpness / 500.0)

            # Skew detection: check if document is rotated
            edges = cv2.Canny(img, 50, 150)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)
            skew_score = 0.9 if lines is None or len(lines) > 3 else 1.0

            # Weighted combination
            score = (
                brightness_score * 0.2
                + contrast_score * 0.3
                + sharpness_score * 0.3
                + skew_score * 0.2
            )

            return float(score)
        except Exception:
            return 0.0
