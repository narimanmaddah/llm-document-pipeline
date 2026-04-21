import json
import os
from typing import Dict, Any
import openai


class LLMExtractor:
    """Extract structured fields from text using LLM."""

    PROMPT_TEMPLATES = {
        "v1_invoice": """Extract the following fields from the invoice text. Return valid JSON only.

Invoice text:
{text}

Return JSON with these fields:
- invoice_number (string)
- vendor_name (string)
- total_amount (string, keep currency/formatting)
- issue_date (string, ISO format YYYY-MM-DD if possible)
- due_date (string, ISO format YYYY-MM-DD if possible)

For any field you cannot confidently extract, use null.
Return ONLY valid JSON, no additional text.""",
    }

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    def extract(self, text: str, prompt_version: str = "v1_invoice") -> Dict[str, Any]:
        """Extract fields from text using LLM."""
        if prompt_version not in self.PROMPT_TEMPLATES:
            raise ValueError(f"Unknown prompt version: {prompt_version}")

        prompt = self.PROMPT_TEMPLATES[prompt_version].format(text=text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=500,
            )

            response_text = response.choices[0].message.content
            extracted = json.loads(response_text)

            return extracted
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            raise RuntimeError(f"LLM extraction failed: {e}")
