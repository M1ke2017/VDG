"""Generator opisu i SEO; kontrola obrazów jest w oddzielnym module."""
import re
import unicodedata
from vision_service.vision_client import analyze_images
from vision_service.vision_validator_image import validate_images, read_json

MIN_DESCRIPTION = 300
MAX_DESCRIPTION = 500
TARGET_KEYWORDS = 10

GENERATION_PROMPT = """
Jesteś specjalistą od analizy produktów i opisów e-commerce.

Otrzymujesz:
- zdjęcia,
- wcześniejszą odpowiedź modelu Vision,
- nazwę produktu podaną przez użytkownika,
- dodatkowe informacje użytkownika.

NAJPIERW SPRAWDŹ ZGODNOŚĆ:

Porównaj główny obiekt rozpoznany na zdjęciach
z nazwą i dodatkowymi informacjami użytkownika.

Wcześniejsze rozpoznanie jest wskazówką,
a nie nieomylnym ustaleniem.

Zasady:
- Porównuj znaczenie nazw, nie identyczność tekstu.
- Nie uznawaj różnych obiektów za ten sam produkt.
- Nie dopasowuj obrazu na siłę do nazwy użytkownika.
- Jeśli nazwa nie została podana, oceniaj sam obraz.
- Brak możliwości sprawdzenia parametru nie oznacza,
  że parametr jest nieprawdziwy.
- Jeśli nie możesz ustalić zgodności, zwróć null.

Jeśli obraz wyraźnie nie pasuje do danych:
- data_match = false,
- description = "",
- keywords = [],
- warning = krótkie wyjaśnienie sprzeczności.

Jeśli nie możesz potwierdzić rodzaju produktu:
- data_match = null,
- description = "",
- keywords = [],
- warning = przyczyna niepewności.

TYLKO PRZY ZGODNOŚCI:

Wygeneruj:
1. Naturalny opis po polsku o długości 300-500 znaków.
2. Dokładnie 10 różnych fraz SEO po 2-5 wyrazów.

Zasady opisu:
- 4-6 naturalnych zdań.
- Opisuj rzeczywiście widoczne cechy.
- Uwzględniaj informacje użytkownika,
  o ile nie przeczą obrazowi.
- Nie wymyślaj marek, norm ani certyfikatów.
- Nie zgaduj dokładnych parametrów technicznych.
- Nie wymyślaj gatunków materiałów.
- Unikaj powtórzeń i sztucznych zdań.

Zasady SEO:
- Używaj naturalnych polskich fraz.
- Zachowaj polskie znaki.
- Nie stosuj myślników zamiast spacji.
- Nie powtarzaj fraz.
- Każda fraza musi odnosić się do produktu.

Zwróć WYŁĄCZNIE poprawny JSON:

{
  "data_match": true,
  "warning": "",
  "description": "Opis produktu",
  "keywords": [
    "fraza pierwsza",
    "fraza druga"
  ]
}

data_match musi być wartością true, false albo null.
Nie dodawaj Markdown ani tekstu poza JSON.
"""

def normalize(value: str) -> str:
    value = value.casefold().replace("ł", "l").strip()

    value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )

    return re.sub(r"\s+", " ", value).strip()


def normalize_keywords(keywords: list[str]) -> list[str]:
    result = []
    seen = set()

    for keyword in keywords:
        phrase = re.sub(r"\s+", " ", keyword).strip(" ,.;")

        phrase = re.sub(
            r"(?<=\w)-(?=\w)",
            " ",
            phrase
        )

        phrase = re.sub(r"\s+", " ", phrase).strip()

        key = normalize(phrase)

        if not 2 <= len(phrase.split()) <= 5:
            continue

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(phrase)

        if len(result) == TARGET_KEYWORDS:
            break

    return result

def make_result(
    detected: str,
    match: bool | None,
    warning: str = ""
) -> dict:

    return {
        "detected_product": detected,
        "product_match": match,
        "description": "",
        "keywords": [],
        "warning": warning,
        "quality_ok": False,
        "quality_message": "",
        "description_length": 0,
        "keyword_count": 0,
        "image_recognitions": [],
        "image_consistent": None
    }

def validate_content(
    data: dict,
    detected: str
) -> dict:

    match = data.get("data_match")
    warning = data.get("warning", "")

    if "data_match" not in data:
        raise ValueError("Brak pola data_match w odpowiedzi modelu.")

    if match is not None and type(match) is not bool:
        raise ValueError(
            "Model zwrócił niepoprawne pole data_match."
        )

    if not isinstance(warning, str):
        raise ValueError(
            "Model zwrócił niepoprawne pole warning."
        )

    # Wyraźna niezgodność obrazu i danych.
    if match is False:
        return make_result(
            detected,
            False,
            warning.strip() or (
                "Zdjęcie nie pasuje do danych użytkownika."
            )
        )

    # Niepewna identyfikacja.
    if match is None:
        return make_result(
            detected,
            None,
            warning.strip()
        )

    description = data.get("description")
    keywords = data.get("keywords")

    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "Model nie wygenerował poprawnego opisu."
        )

    if not isinstance(keywords, list) or not all(
        isinstance(word, str) for word in keywords
    ):
        raise ValueError(
            "Model nie zwrócił poprawnej listy SEO."
        )

    description = description.strip()
    keywords = normalize_keywords(keywords)

    result = make_result(detected, True)

    result["description"] = description
    result["keywords"] = keywords
    result["description_length"] = len(description)
    result["keyword_count"] = len(keywords)

    description_ok = (
        MIN_DESCRIPTION <= len(description) <= MAX_DESCRIPTION
    )

    seo_ok = len(keywords) == TARGET_KEYWORDS

    result["quality_ok"] = description_ok and seo_ok

    if not result["quality_ok"]:
        problems = []

        if not description_ok:
            problems.append(
                f"Opis: {len(description)} znaków "
                f"(cel: {MIN_DESCRIPTION}-{MAX_DESCRIPTION})"
            )

        if not seo_ok:
            problems.append(
                f"Frazy SEO: {len(keywords)} "
                f"(cel: {TARGET_KEYWORDS})"
            )

        result["quality_message"] = ". ".join(problems) + "."

    return result


def generate(images: list[bytes], product_name: str, technical_data: str) -> dict:
    # Walidator jest jedynym miejscem odpowiedzialnym za obrazy.
    verification = validate_images(images)
    detected = verification["detected"]
    consistent = verification["consistent"]

    if consistent is not True:
        recognitions = verification["recognitions"]
        details = "\n".join(
            f"Zdjęcie {i}: {name}" for i, name in enumerate(recognitions, 1)
        )
        warning = (
            "Zdjęcia nie przedstawiają tego samego rodzaju produktu."
            if consistent is False else
            "Nie udało się potwierdzić spójności wszystkich zdjęć."
        )
        if verification.get("reason"):
            warning += " " + verification["reason"]
        if details:
            warning += "\n" + details
        result = make_result(detected, consistent, warning)
        result["image_recognitions"] = recognitions
        result["image_consistent"] = consistent
        return result

    # Zachowujemy istniejący prompt generowania bez zmian.
    prompt = (
        GENERATION_PROMPT
        + "\nWCZEŚNIEJSZE ROZPOZNANIE VISION:\n" + detected
        + "\n\nNAZWA PODANA PRZEZ UŻYTKOWNIKA:\n"
        + (product_name.strip() or "Nie podano")
        + "\n\nDODATKOWE INFORMACJE UŻYTKOWNIKA:\n"
        + (technical_data.strip() or "Nie podano")
    )
    response_text = analyze_images(images, prompt)
    data = read_json(response_text)
    result = validate_content(data, detected)
    result["image_recognitions"] = verification["recognitions"]
    result["image_consistent"] = True
    return result
