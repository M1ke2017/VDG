
"""VDG — niezależny walidator zestawu zdjęć (Sprint 13A).

Warunek dopuszczenia generowania:
- wszystkie zdjęcia zostały rozpoznane osobno;
- dla KAŻDEJ pary model jednoznacznie potwierdził ten sam rodzaj obiektu;
- zbiorcza ocena obrazów również jest pozytywna.

Wynik False = stwierdzona niezgodność; None = brak pewności/błąd.
Oba stany BLOKUJĄ generowanie. Brak zakodowanego słownika obiektów.
Uwaga: Qwen może się mylić; walidacja nie jest matematyczną gwarancją.
"""

import json
import logging
import re
import unicodedata
from itertools import combinations

from vision_service.vision_client import analyze_images

logger = logging.getLogger(__name__)


# ============================================================
# PROMPT ROZPOZNAWANIA
# ============================================================

# ZACHOWANY prompt skuteczny we wcześniejszych testach Vision.
RECOGNITION_PROMPT = (
    "Co znajduje się na tym zdjęciu? "
    "Nazwij główny obiekt po polsku."
)


# ============================================================
# PROMPT PORÓWNANIA DWÓCH ZDJĘĆ
# ============================================================

PAIR_PROMPT = """
Porównaj dokładnie DWA zdjęcia i niezależne rozpoznania ich głównych obiektów.
Czy oba zdjęcia przedstawiają TEN SAM RODZAJ głównego obiektu?

Różnice koloru, perspektywy i cech drugorzędnych
nie oznaczają innego rodzaju.

Jeżeli rozpoznania wskazują różne rodzaje obiektów,
odpowiedz false.

Jeśli nie możesz potwierdzić zgodności,
odpowiedz null. Nie zgaduj.

Nie korzystaj z żadnej nazwy produktu użytkownika.

Odpowiedz wyłącznie JSON z boolean true, false albo null:
{{"same_type": false, "reason": "zwięzłe uzasadnienie"}}

ROZPOZNANIE ZDJĘCIA A:
{first}

ROZPOZNANIE ZDJĘCIA B:
{second}
"""


# ============================================================
# PROMPT PORÓWNANIA CAŁEGO ZESTAWU
# ============================================================

CONSISTENCY_PROMPT = """
Oceń, czy wszystkie przesłane fotografie przedstawiają ten sam RODZAJ
GŁÓWNEGO obiektu, z uwzględnieniem każdego zdjęcia oraz jego niezależnego
rozpoznania.

Nie ignoruj żadnego zdjęcia.

Gdy widać różne rodzaje obiektów: false.
Gdy brak pewności: null.

Tylko wyraźna zgodność wszystkich zdjęć
pozwala odpowiedzieć true.

Zwróć wyłącznie JSON:
{"same_product": false, "reason": "krótkie uzasadnienie"}

ROZPOZNANIA:
"""


# ============================================================
# FUNKCJE POMOCNICZE
# ============================================================

def normalize(value: str) -> str:
    value = value.casefold().replace("ł", "l").strip()

    value = "".join(
        c
        for c in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(c)
    )

    return re.sub(r"\s+", " ", value).strip(" .,:;!?")


def read_json(response_text: str) -> dict:
    """Odczytuje pierwszy poprawny obiekt JSON, także w bloku Markdown."""

    text = response_text.strip()
    decoder = json.JSONDecoder()

    for index, char in enumerate(text):
        if char != "{":
            continue

        try:
            data, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(data, dict):
            return data

    raise ValueError(
        "Model nie zwrócił poprawnego obiektu JSON."
    )


# ============================================================
# NIEZALEŻNE ROZPOZNAWANIE OBRAZU
# ============================================================

def recognize_product(images: list[bytes]) -> str:
    """Rozpoznawanie pozostaje bez zmian.

    Przy walidacji pojedynczego zdjęcia przekazujemy
    listę zawierającą dokładnie jeden obraz.
    """

    response = analyze_images(
        images,
        RECOGNITION_PROMPT
    )

    detected = response.strip()

    if not detected or normalize(detected) in {
        "nie rozpoznano",
        "nie wiem",
        "nie mozna rozpoznac"
    }:
        return ""

    return detected


# ============================================================
# STRUKTURA WYNIKU WALIDATORA
# ============================================================

def _make_response(
    consistent: bool | None,
    recognitions: list[str],
    reason: str,
    checks: dict | None = None,
) -> dict:
    """Zachowuje API oczekiwane przez vision_generator.py."""

    return {
        "consistent": consistent,
        "detected": (
            recognitions[0]
            if recognitions
            else "Nieznany obiekt"
        ),
        "recognitions": recognitions,
        "reason": reason,
        "checks": checks if checks is not None else {},
    }


# ============================================================
# PORÓWNANIE JEDNEJ PARY
# ============================================================

def _pair_consistency(
    first_image: bytes,
    second_image: bytes,
    first_recognition: str,
    second_recognition: str,
) -> tuple[bool | None, str]:
    """Ocenia wyłącznie wskazaną parę.

    Do modelu przekazujemy:
    - dwa obrazy;
    - dwa niezależne rozpoznania;
    - brak danych użytkownika.
    """

    prompt = PAIR_PROMPT.format(
        first=first_recognition,
        second=second_recognition,
    )

    data = read_json(
        analyze_images(
            [first_image, second_image],
            prompt
        )
    )

    decision = data.get("same_type")
    reason = data.get("reason", "")

    if decision is not None and type(decision) is not bool:
        raise ValueError("Niepoprawne pole same_type.")

    if not isinstance(reason, str):
        raise ValueError("Niepoprawne uzasadnienie pary.")

    return decision, reason.strip()


# ============================================================
# PORÓWNANIE CAŁEGO ZESTAWU
# ============================================================

def _image_consistency(
    images: list[bytes],
    recognitions: list[str]
) -> tuple[bool | None, str]:

    descriptions = "\n".join(
        f"Zdjęcie {i}: {text}"
        for i, text in enumerate(recognitions, 1)
    )

    data = read_json(
        analyze_images(
            images,
            CONSISTENCY_PROMPT + descriptions
        )
    )

    decision = data.get("same_product")
    reason = data.get("reason", "")

    if decision is not None and type(decision) is not bool:
        raise ValueError("Niepoprawne pole same_product.")

    if not isinstance(reason, str):
        raise ValueError(
            "Niepoprawne uzasadnienie zestawu."
        )

    return decision, reason.strip()


# ============================================================
# GŁÓWNA FUNKCJA WALIDATORA
# ============================================================

def validate_images(images: list[bytes]) -> dict:
    """Waliduje zestaw od jednego do trzech zdjęć.

    ZASADA FAIL-CLOSED:
    - True: zestaw zaakceptowany;
    - False: wykryta niezgodność;
    - None: brak pewności lub błąd.

    Tylko True pozwala generatorowi kontynuować.

    checks["pairs"] zachowuje oceny poszczególnych par.
    """

    if not 1 <= len(images) <= 3:
        raise ValueError(
            "Wybierz od 1 do 3 zdjęć produktu."
        )

    recognitions: list[str] = []
    checks: dict = {"pairs": []}

    # --------------------------------------------------------
    # ETAP A — NIEZALEŻNE ROZPOZNANIE KAŻDEGO ZDJĘCIA
    # --------------------------------------------------------

    for index, image in enumerate(images, 1):
        try:
            detected = recognize_product([image])

        except Exception as exc:
            logger.warning(
                "Błąd rozpoznawania zdjęcia %s: %s",
                index,
                exc
            )

            return _make_response(
                None,
                recognitions,
                f"Nie udało się przeanalizować zdjęcia {index}.",
                checks
            )

        if not detected:
            return _make_response(
                None,
                recognitions,
                f"Nie udało się rozpoznać zdjęcia {index}.",
                checks
            )

        recognitions.append(detected)

    logger.info(
        "VDG niezależne rozpoznania: %r",
        recognitions
    )

    # Dla jednego zdjęcia nie trzeba sprawdzać
    # spójności zestawu.
    if len(images) == 1:
        checks["single_image"] = True

        return _make_response(
            True,
            recognitions,
            "",
            checks
        )

    # --------------------------------------------------------
    # ETAP B — PORÓWNANIE WSZYSTKICH PAR ZDJĘĆ
    # --------------------------------------------------------

    uncertain = False

    for i, j in combinations(range(len(images)), 2):

        pair = {
            "images": [i + 1, j + 1],
            "same_type": None,
            "reason": ""
        }

        try:
            decision, reason = _pair_consistency(
                images[i],
                images[j],
                recognitions[i],
                recognitions[j]
            )

            pair["same_type"] = decision
            pair["reason"] = reason

        except Exception as exc:
            pair["reason"] = (
                "Nie udało się jednoznacznie "
                "porównać pary zdjęć."
            )

            logger.warning(
                "Błąd porównania zdjęć %s/%s: %s",
                i + 1,
                j + 1,
                exc
            )

        checks["pairs"].append(pair)

        logger.info(
            "VDG porównanie pary %s/%s: %r",
            i + 1,
            j + 1,
            pair
        )

        # Każde wykryte odrzucenie ma pierwszeństwo.
        if pair["same_type"] is False:
            return _make_response(
                False,
                recognitions,
                (
                    f"Zdjęcia {i + 1} i {j + 1} "
                    "przedstawiają różne rodzaje obiektów. "
                    + pair["reason"]
                ),
                checks
            )

        # Niepewna para nie daje zgody na generowanie.
        if pair["same_type"] is not True:
            uncertain = True

    if uncertain:
        return _make_response(
            None,
            recognitions,
            (
                "Nie udało się potwierdzić zgodności "
                "wszystkich par zdjęć."
            ),
            checks
        )

    # --------------------------------------------------------
    # ETAP C — DODATKOWA KONTROLA CAŁEGO ZESTAWU
    # --------------------------------------------------------

    try:
        decision, reason = _image_consistency(
            images,
            recognitions
        )

    except Exception as exc:
        logger.warning(
            "Błąd oceny pełnego zestawu: %s",
            exc
        )

        return _make_response(
            None,
            recognitions,
            "Nie udało się potwierdzić spójności całego zestawu.",
            checks
        )

    checks["image"] = decision
    checks["image_reason"] = reason

    if decision is False:
        return _make_response(
            False,
            recognitions,
            reason or "Zdjęcia przedstawiają różne obiekty.",
            checks
        )

    if decision is not True:
        return _make_response(
            None,
            recognitions,
            reason or "Spójność zestawu pozostaje niepewna.",
            checks
        )

    # Wszystkie warunki zostały spełnione.
    return _make_response(
        True,
        recognitions,
        reason,
        checks
    )
