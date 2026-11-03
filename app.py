import os
from pathlib import Path

import openai
import streamlit as st
from dotenv import dotenv_values

# Read .env fresh on every rerun (instead of load_dotenv) so that removing a key
# or the whole file takes effect on reload, not only after a server restart.
_ENV = {**os.environ, **dotenv_values(Path(__file__).with_name(".env"))}

LANGUAGES = {"영어": "English", "일본어": "Japanese", "베트남어": "Vietnamese"}
MAX_CHARS = 5000
SYSTEM_PROMPT = (
    "You are a professional translator.\n"
    "Translate the user's text into {target_language}.\n"
    "Preserve the original meaning, tone, line breaks, and formatting.\n"
    "Output only the translated text without any explanations."
)

API_KEY = (_ENV.get("OPENAI_API_KEY") or "").strip()
MODEL = (_ENV.get("OPENAI_MODEL") or "").strip() or "gpt-6-astra"


def translate(text: str, target_language: str) -> str:
    client = openai.OpenAI(api_key=API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(target_language=target_language)},
            {"role": "user", "content": text},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def error_message(exc: Exception) -> str:
    if isinstance(exc, openai.AuthenticationError):
        return "API 키가 올바르지 않습니다."
    if isinstance(exc, openai.NotFoundError):
        return "모델을 찾을 수 없습니다. .env의 OPENAI_MODEL 값을 확인하세요."
    if isinstance(exc, openai.RateLimitError):
        return "요청이 너무 많습니다. 잠시 후 다시 시도하세요."
    if isinstance(exc, openai.APIConnectionError):
        return "번역 중 오류가 발생했습니다: 네트워크에 연결할 수 없습니다."
    if isinstance(exc, openai.APIStatusError):
        return f"번역 중 오류가 발생했습니다: API 오류 (HTTP {exc.status_code})"
    return f"번역 중 오류가 발생했습니다: {type(exc).__name__}"


FLAGS = {"영어": "🇺🇸", "일본어": "🇯🇵", "베트남어": "🇻🇳"}

st.set_page_config(page_title="다국어 번역기", page_icon="🌐", layout="centered")
st.markdown(
    """
    <style>
    /* Windows has no flag emoji glyphs (shows "US"/"JP"); this font covers flags only. */
    @font-face {
        font-family: "Twemoji Country Flags";
        unicode-range: U+1F1E6-1F1FF, U+1F3F4, U+E0062-E0063, U+E0065, U+E0067,
            U+E006C, U+E006E, U+E0073-E0074, U+E0077, U+E007F;
        src: url("https://cdn.jsdelivr.net/npm/country-flag-emoji-polyfill@0.1.8/dist/TwemojiCountryFlags.woff2") format("woff2");
        font-display: swap;
    }
    div[data-testid="stButton"] button p, .result-label {
        font-family: "Twemoji Country Flags", "Source Sans", "Source Sans Pro", sans-serif;
    }
    /* Result is natural-language text: use the body font, not monospace. */
    div[data-testid="stCode"] code, div[data-testid="stCode"] pre {
        font-family: "Source Sans", "Source Sans Pro", sans-serif !important;
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
    }
    .block-container { padding-top: 2.5rem; max-width: 760px; }
    h1 { font-size: 2.1rem !important; margin-bottom: 0 !important; }
    .app-subtitle { opacity: 0.7; margin: 0.25rem 0 1.5rem; }
    div[data-testid="stButton"] button { font-size: 1.05rem; padding: 0.6rem 0; border-radius: 10px; }
    .result-label { font-size: 1.15rem; font-weight: 600; margin: 0 0 0.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.session_state.setdefault("result", None)
st.session_state.setdefault("result_lang", None)

st.title("🌐 다국어 번역기")
st.markdown(
    '<p class="app-subtitle">텍스트를 입력하고 원하는 언어 버튼을 누르세요</p>',
    unsafe_allow_html=True,
)

if not API_KEY:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

text = st.text_area(
    "번역할 내용을 입력하세요",
    height=200,
    placeholder="예: 안녕하세요. 오늘 회의는 오후 3시에 시작합니다.",
    # Built-in counter updates live in the browser while typing (a server-side
    # counter only refreshes after the field loses focus).
    max_chars=MAX_CHARS,
    help=f"최대 {MAX_CHARS:,}자까지 입력할 수 있습니다.",
)
over = len(text) > MAX_CHARS  # safety net; max_chars already blocks this in the UI

clicked = None
for col, label in zip(st.columns(len(LANGUAGES)), LANGUAGES):
    if col.button(f"{FLAGS[label]} {label}", disabled=not API_KEY, width="stretch"):
        clicked = label

if clicked:
    rejected = True
    if not text.strip():
        st.warning("번역할 내용을 입력해 주세요.")
    elif over:
        st.warning(f"입력은 최대 {MAX_CHARS:,}자까지 가능합니다. (현재 {len(text):,}자)")
    else:
        try:
            with st.spinner(f"{clicked}로 번역하는 중..."):
                result = translate(text, LANGUAGES[clicked])
            st.session_state.result = result
            st.session_state.result_lang = clicked
            rejected = False
        except Exception as exc:
            st.error(error_message(exc))
    if rejected:
        # Don't leave an older translation under a warning/error for different input.
        st.session_state.result = None
        st.session_state.result_lang = None

if st.session_state.result is not None:
    lang = st.session_state.result_lang
    with st.container(border=True):
        st.markdown(
            f'<p class="result-label">{FLAGS[lang]} {lang} 번역 결과</p>',
            unsafe_allow_html=True,
        )
        st.code(st.session_state.result, language=None, wrap_lines=True)
