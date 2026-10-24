
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Katalog główny aplikacji.
BASE_DIR = Path(__file__).resolve().parent.parent

# Odczyt lokalnych ustawień.
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    vision_url: str = os.getenv("VISION_URL", "")
    vision_token: str = os.getenv("VISION_TOKEN", "")
    vision_model: str = os.getenv(
        "VISION_MODEL",
        "Qwen/Qwen2.5-VL-3B-Instruct"
    )
    max_image_mb: int = 8
    request_timeout: int = 120


settings = Settings()
