from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0


class LanguageDetector:
    def detect_language(self, text: str) -> str:
        """Detect language of text. Returns ISO 639-1 code."""
        if not text or len(text.strip()) < 10:
            return "unknown"
        try:
            return detect(text)
        except Exception:
            return "unknown"
