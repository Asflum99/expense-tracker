import logging
import os

import requests
from groq import APIError, AuthenticationError, Groq, RateLimitError

from config import Settings

logger = logging.getLogger(__name__)

GROQ_API_KEY = Settings.groq_api_key
PROMPT_TEMPLATE = "categorization_prompt.md"
AI_MODEL = "openai/gpt-oss-20b"


def _load_prompt_template(file_path: str):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, file_path)
    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()


def assign_category(movement: dict[str, float | str]) -> str:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt_template = _load_prompt_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(
            amount=movement["amount"], beneficiary=movement["beneficiary"]
        )

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=AI_MODEL
        )

        if content := chat_completion.choices[0].message.content:
            return content.strip()
        else:
            logger.warning("Empty response from Groq API")
            return "Desconocido"

    except (RateLimitError, AuthenticationError) as e:
        logger.error(f"Groq API error: {e}")
        return "Desconocido"
    except (requests.exceptions.RequestException, APIError) as e:
        logger.warning(f"Network/API error assigning category: {e}")
        return "Desconocido"
    except (KeyError, FileNotFoundError) as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error assigning category: {e}")
        return "Desconocido"
