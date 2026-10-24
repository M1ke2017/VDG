import streamlit as st
from tabs.image_tab import render_image_tab

st.set_page_config(
    page_title="VDG | Vision Description Generator",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# STYL APLIKACJI
# ============================================================

st.markdown("""
<style>
    :root {
        --bg-main: #EEF0EC;
        --bg-soft: #F7F8F5;
        --panel: #FFFFFF;
        --panel-2: #F5F6F3;
        --text-main: #171A18;
        --text-soft: #5B635E;
        --border: #D9DED8;
        --primary: #7E9F83;
        --primary-dark: #69866D;
        --secondary: #AEBCC5;
        --accent: #1C1E1C;
        --shadow: 0 8px 24px rgba(25, 30, 25, 0.06);
        --radius-xl: 18px;
        --radius-lg: 14px;
        --radius-md: 12px;
        --radius-sm: 10px;
    }

    html, body, [class*="css"] {
        font-family: "Inter", "Segoe UI", sans-serif;
    }

    .stButton > button[kind="primary"] {
    background: #70977D !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    }

    .stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #5D826A !important;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    .block-container {
        max-width: 1280px;
        padding-top: 1.1rem;
        padding-bottom: 1.5rem;
    }

    h1, h2, h3, h4 {
        color: var(--text-main) !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-size: 1.9rem !important;
        margin-bottom: 0.15rem !important;
    }

    h2 {
        font-size: 1.35rem !important;
    }

    h3 {
        font-size: 1.08rem !important;
    }

    p, label, span, div {
        color: var(--text-main);
    }

    .vdg-subtitle {
        color: var(--text-soft);
        font-size: 0.96rem;
        margin-top: -0.25rem;
        margin-bottom: 0.75rem;
    }

    .vdg-top-card {
        background: rgba(255,255,255,0.55);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 1rem 1.1rem 0.6rem 1.1rem;
        box-shadow: var(--shadow);
        margin-bottom: 0.8rem;
        backdrop-filter: blur(6px);
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        color: var(--text-soft) !important;
        padding-top: 0.45rem !important;
        padding-bottom: 0.55rem !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--text-main) !important;
    }

    /* Główne sekcje w kartach */
    .vdg-section-card {
        background: rgba(255,255,255,0.76);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 0.95rem 1rem 1rem 1rem;
        box-shadow: var(--shadow);
        margin-bottom: 0.8rem;
    }

    .vdg-mini-card {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 0.85rem 0.95rem;
        box-shadow: var(--shadow);
    }

    /* Inputs */
    .stTextInput input,
    .stTextArea textarea {
        background: var(--panel) !important;
        border: 1px solid #D1D7D0 !important;
        border-radius: 12px !important;
        color: var(--text-main) !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border: 1px solid var(--primary) !important;
        box-shadow: 0 0 0 1px var(--primary) !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.75);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 0.3rem;
    }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: var(--primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        min-height: 44px !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--primary-dark) !important;
    }

    .stButton > button {
        border-radius: 12px !important;
    }

    /* Segmented control / pills */
    [data-testid="stSegmentedControl"] {
        margin-bottom: 0.35rem !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.82);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 0.8rem 0.95rem;
        box-shadow: var(--shadow);
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-soft) !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--text-main) !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }

    /* Alerts */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    /* Expander */
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--border);
        border-radius: 14px;
        overflow: hidden;
    }

    /* Code blocks */
    pre, code {
        border-radius: 12px !important;
    }

    /* Divider */
    hr {
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }

    /* Reduce spacing globally קצת */
    [data-testid="stVerticalBlock"] {
        gap: 0.55rem;
    }

    /* Preview image cards so they do not overlap */
    .vdg-preview-frame {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 0.45rem;
        box-shadow: var(--shadow);
        height: 100%;
    }

    .vdg-preview-title {
        font-size: 0.82rem;
        color: var(--text-soft);
        margin-top: 0.35rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# NAGŁÓWEK
# ============================================================


st.markdown("#### VDG · Vision Description Generator")

st.caption(
    "Analiza produktów z wykorzystaniem Qwen2.5-VL "
    "· Autorzy: Natalia Oleska (113850), "
    "Michał Łuczak (113801)"
)


analysis_tab, architecture_tab = st.tabs([
    "Analiza produktu",
    "Architektura i kod modelu"
])

with analysis_tab:
    render_image_tab()

with architecture_tab:
    st.markdown('<div class="vdg-section-card">', unsafe_allow_html=True)
    st.markdown("### Opis dla prowadzącego")

    st.write(
        "Aplikacja VDG została podzielona na dwie warstwy. "
        "Lokalny interfejs użytkownika został przygotowany w Streamlit, "
        "natomiast właściwy model Vision działa w Google Colab, gdzie ma dostęp do GPU."
    )

    st.write(
        "Dzięki takiemu podejściu aplikacja na komputerze użytkownika pozostaje lekka, "
        "a cięższe obliczenia są wykonywane zdalnie."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("1. Ogólna architektura rozwiązania", expanded=True):
        st.code("""Użytkownik -> Streamlit (lokalna aplikacja)
            -> vision_generator.py
            -> vision_client.py
            -> HTTPS / Cloudflare Tunnel
            -> FastAPI w Google Colab
            -> Model Qwen2.5-VL-3B-Instruct
            -> odpowiedź JSON
            -> opis produktu + słowa kluczowe SEO
""", language="text")

        st.write(
            "Interfejs użytkownika zbiera zdjęcia i dane wejściowe, "
            "następnie wysyła je do warstwy komunikacyjnej. "
            "Ta komunikuje się z API uruchomionym w Colab."
        )

    with st.expander("2. Ładowanie modelu w Colab"):
        st.code("""from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
import torch

MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"

model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto"
)

processor = AutoProcessor.from_pretrained(MODEL_NAME)
model.eval()
""", language="python")

        st.write(
            "Model ładowany jest po stronie Colab tylko raz, "
            "a następnie używany do kolejnych żądań analizy."
        )

    with st.expander("3. Uruchomienie API FastAPI w Colab"):
        st.code("""from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {
        "model_ready": True,
        "model": "Qwen/Qwen2.5-VL-3B-Instruct"
    }
""", language="python")

        st.write(
            "Endpoint /health pozwala sprawdzić, czy model został poprawnie załadowany. "
            "Główny endpoint /analyze przyjmuje dane obrazu i zwraca wynik w formacie JSON."
        )

    with st.expander("4. Tunelowanie połączenia z Colab"):
        st.code("""# przykładowa idea
tunnel_url = "https://twoj-adres.trycloudflare.com"
VISION_URL = tunnel_url
VISION_TOKEN = "token_z_colab"
""", language="python")

        st.write(
            "Aby lokalna aplikacja mogła połączyć się z Colab, "
            "wykorzystywany jest publiczny adres tunelu. "
            "Dostęp zabezpieczany jest tokenem."
        )

    with st.expander("5. Komunikacja aplikacji z API"):
        st.code("""response = requests.post(
    f"{VISION_URL}/analyze",
    json=payload,
    headers={"Authorization": f"Bearer {VISION_TOKEN}"},
    timeout=60
)
result = response.json()
""", language="python")

        st.write(
            "Lokalna aplikacja wysyła do API zdjęcia produktu, nazwę oraz parametry, "
            "a następnie odbiera gotowy opis i słowa kluczowe."
        )

    with st.expander("6. Rola plików w projekcie"):
        st.code("""app.py
- uruchamia aplikację Streamlit
- ustawia wygląd i zakładki

tabs/image_tab.py
- renderuje główny panel analizy produktu

vision_service/vision_client.py
- odpowiada za komunikację HTTP z API modelu

vision_service/vision_generator.py
- składa prompt, odbiera odpowiedź i pilnuje poprawnego JSON

core/config.py
- przechowuje konfigurację, np. adres modelu i token
""", language="text")

        st.write(
            "Podział na pliki pozwala lepiej rozdzielić odpowiedzialności "
            "i uprościć rozwój aplikacji."
        )

    st.markdown('<div class="vdg-section-card">', unsafe_allow_html=True)
    st.markdown("### Wniosek")

    st.write(
        "Projekt VDG łączy lokalną aplikację użytkową ze zdalnym modelem Vision. "
        "Pozwala generować opisy produktów i frazy SEO na podstawie jednego lub kilku zdjęć produktu. "
        "Największą zaletą rozwiązania jest lekki frontend oraz wykorzystanie GPU w Colab bez obciążania komputera użytkownika."
    )
    st.markdown('</div>', unsafe_allow_html=True)