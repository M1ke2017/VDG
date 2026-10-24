
import hashlib
import time
from io import BytesIO
import re

import streamlit as st
from PIL import Image, UnidentifiedImageError

from core.examples import EXAMPLES
from vision_service.vision_generator import generate


def input_key(images, name, details):
    return (
        tuple(hashlib.sha256(img).hexdigest() for img in images),
        name.strip(),
        details.strip()
    )

def short_object_name(text: str) -> str:
    text = text.strip()

    match = re.search(
        r"(?:znajduje się|widać|przedstawia)\s+(.+?)(?:,|\.|$)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        text = match.group(1).strip()

    text = re.sub(
        r"^(?:jeden|jedna|jedno|pojedyncza|pojedynczy)\s+",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text[:1].upper() + text[1:] if text else "Nieznany obiekt"


def show_result(result, elapsed, count, product_name):
    st.markdown("#### Wynik analizy")

    col1, col2, col3 = st.columns(3)
    col1.metric("Zdjęcia", count)
    col2.metric("Czas analizy", f"{elapsed:.2f} s")
    col3.metric("Rozpoznano", short_object_name(result["detected_product"])
    )

    match = result["product_match"]

    
    if match is False:
        st.error(
            "Zdjęcie nie pasuje do danych "
            "podanych przez użytkownika."
        )

        st.write(
            f"**Nazwa użytkownika:** "
            f"{product_name or 'Nie podano'}"
        )

        st.write(
            f"**Model rozpoznał:** "
            f"{result['detected_product']}"
        )

        if result["warning"]:
            st.caption(result["warning"])

        st.caption(
            "Opis produktu i frazy SEO nie zostały "
            "wygenerowane."
        )
        return


    if match is None:
        st.warning(
            "Nie potwierdzono rodzaju produktu. "
            + result["warning"]
        )
        return

    description = result["description"]
    keywords = result["keywords"]

    if result["quality_ok"]:
        st.success("Wynik spełnia wymagania ilościowe.")
    else:
        st.warning(
            "Wynik częściowy — " + result["quality_message"]
        )

    m1, m2 = st.columns(2)
    m1.metric("Długość opisu", f"{len(description)} znaków")
    m2.metric("Frazy SEO", len(keywords))

    left, right = st.columns([1.15, 1], gap="medium")

    with left:
        st.text_area(
            "Opis produktu",
            value=description,
            height=140
        )

    with right:
        st.text_area(
            "Frazy SEO",
            value=", ".join(keywords),
            height=140
        )

    st.caption(
        "Wynik modelu AI wymaga weryfikacji merytorycznej."
    )


def render_image_tab():
    # Rezerwujemy miejsce na wynik na górze strony.
    result_placeholder = st.empty()

    has_result = "vdg_result" in st.session_state

    # Formularz jest otwarty przed analizą,
    # a po analizie można go rozwinąć do edycji.
    with st.expander(
        "Dane produktu i zdjęcia",
        expanded=not has_result
    ):
        example = st.segmented_control(
            "Przykładowe dane",
            list(EXAMPLES.keys()),
            default="Własny produkt",
            key="vdg_example_selector"
        )

        if st.session_state.get("vdg_last_example") != example:
            selected = EXAMPLES[example]
            st.session_state["vdg_name"] = selected["name"]
            st.session_state["vdg_details"] = selected["details"]
            st.session_state["vdg_last_example"] = example
            st.session_state.pop("vdg_result", None)

        left, right = st.columns([1.3, 1], gap="medium")

        with left:
            name = st.text_input(
                "Nazwa produktu",
                key="vdg_name"
            )

            details = st.text_area(
                "Informacje użytkownika",
                height=76,
                key="vdg_details"
            )

            files = st.file_uploader(
                "Zdjęcia produktu",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="vdg_files"
            )

            too_many = len(files) > 3

            if too_many:
                st.warning("Maksymalnie 3 zdjęcia.")

            analyze = st.button(
                "Analizuj produkt",
                type="primary",
                width="stretch",
                disabled=not files or too_many
            )

        with right:
            st.markdown("**Podgląd zdjęć**")

            if files:
                cols = st.columns(min(len(files), 3))

                for index, file in enumerate(files[:3]):
                    with cols[index]:
                        try:
                            with Image.open(
                                BytesIO(file.getvalue())
                            ) as image:
                                image.load()
                                st.image(image, width=140)
                        except (UnidentifiedImageError, OSError):
                            st.error("Błędne zdjęcie")

                        st.caption(f"Zdjęcie {index + 1}")

    images = [file.getvalue() for file in files]
    current_key = input_key(images, name, details)

    if analyze:
        try:
            started = time.perf_counter()

            with st.spinner("Analiza obrazu i produktu..."):
                result = generate(images, name, details)

            elapsed = time.perf_counter() - started

            st.session_state["vdg_result"] = result
            st.session_state["vdg_elapsed"] = elapsed
            st.session_state["vdg_result_key"] = current_key
            st.session_state["vdg_result_name"] = name
            st.session_state["vdg_image_count"] = len(images)

            st.rerun()

        except Exception as error:
            st.session_state.pop("vdg_result", None)
            st.error(f"Analiza nie powiodła się: {error}")
            return

    result = st.session_state.get("vdg_result")

    if (
        result is not None
        and st.session_state.get("vdg_result_key") == current_key
    ):
        with result_placeholder.container():
            show_result(
                result,
                st.session_state["vdg_elapsed"],
                st.session_state["vdg_image_count"],
                st.session_state["vdg_result_name"]
            )
