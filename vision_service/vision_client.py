
import base64
from io import BytesIO

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

from core.config import settings


# Sesja HTTP umożliwia ponowne wykorzystywanie połączeń.
session = requests.Session()

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 8 * 1024 * 1024


# _headers — przygotowuje nagłówki autoryzacji.
def _headers():
    return {
        "Authorization": f"Bearer {settings.vision_token}"
    }


# check_health — sprawdza gotowość modelu w Colab.
def check_health():
    if not settings.vision_url or not settings.vision_token:
        return False

    try:
        response = session.get(
            f"{settings.vision_url.rstrip('/')}/health",
            headers=_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("model_ready") is True

    except (requests.RequestException, ValueError):
        return False


# prepare_image — zmniejsza i kompresuje zdjęcie.
def prepare_image(image_bytes: bytes) -> bytes:
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Zdjęcie jest puste lub przekracza 8 MB.")

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format not in ("JPEG", "PNG"):
                raise ValueError("Obsługiwane są tylko JPG i PNG.")

            if source.width * source.height > 20_000_000:
                raise ValueError("Zdjęcie ma zbyt dużą rozdzielczość.")

            image = ImageOps.exif_transpose(source)
            image.thumbnail((1024, 1024))

            if image.mode != "RGB":
                image = image.convert("RGB")

            buffer = BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=82,
                optimize=True
            )
            return buffer.getvalue()

    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Nie można odczytać obrazu.") from error


# analyze_images — wykonuje jedno żądanie do Colab
# dla maksymalnie trzech zdjęć tego samego produktu.
def analyze_images(images: list[bytes], prompt: str) -> str:
    if not settings.vision_url:
        raise RuntimeError("Brak VISION_URL w pliku .env.")

    if not settings.vision_token:
        raise RuntimeError("Brak VISION_TOKEN w pliku .env.")

    if not 1 <= len(images) <= MAX_IMAGES:
        raise ValueError("Wybierz od 1 do 3 zdjęć.")

    if not prompt.strip():
        raise ValueError("Polecenie dla modelu jest puste.")

    encoded_images = []

    for image_bytes in images:
        prepared = prepare_image(image_bytes)
        encoded_images.append(
            base64.b64encode(prepared).decode("ascii")
        )

    payload = {
        "images_base64": encoded_images,
        "mime_type": "image/jpeg",
        "prompt": prompt
    }

    try:
        response = session.post(
            f"{settings.vision_url.rstrip('/')}/analyze",
            json=payload,
            headers=_headers(),
            timeout=settings.request_timeout
        )
        response.raise_for_status()

    except requests.Timeout as error:
        raise RuntimeError(
            "Przekroczono czas oczekiwania na model."
        ) from error

    except requests.HTTPError as error:
        status = error.response.status_code

        if status == 401:
            message = "Nieprawidłowy token modelu."
        elif status == 413:
            message = "Obrazy przekraczają dozwolony limit."
        elif status == 429:
            message = "Model jest zajęty. Spróbuj ponownie."
        else:
            message = f"Colab zwrócił HTTP {status}."

        raise RuntimeError(message) from error

    except requests.RequestException as error:
        raise RuntimeError(
            "Nie udało się połączyć z modelem Vision."
        ) from error

    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError(
            "Serwer nie zwrócił poprawnej odpowiedzi JSON."
        ) from error

    text = result.get("text") if isinstance(result, dict) else None

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Model zwrócił pustą odpowiedź.")

    return text.strip()
