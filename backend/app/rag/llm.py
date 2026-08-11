from groq import Groq

from ..config import settings

LANG_NAMES = {
    "az": "Azərbaycan dili",
    "ru": "rus dili (русский язык)",
    "en": "English",
}

SYSTEM_PROMPT = """Sən elmi məqalələr üzrə axtarış köməkçisisən. Yalnız aşağıdakı KONTEKST-də
verilmiş abstraktlara əsaslanaraq cavab ver.

Qaydalar:
1. CAVABIN DİLİ MÜTLƏQ BUDUR: {answer_lang}. Bütün cavabı yalnız bu dildə yaz —
   sualın dili fərqli görünsə belə.
2. Hər əsas iddiadan sonra mənbəni [arxiv_id] formatında göstər.
3. KONTEKST-də cavab yoxdursa, bunu həmin dildə açıq bildir (cavab tapılmadı). Heç nə uydurma.
4. Texniki terminləri ingiliscə saxla (məs. retrieval, fine-tuning).

KONTEKST:
{context}"""


def translate_to_english(text: str) -> str:
    """Axtarış sorğusunu ingiliscəyə çevirir (çoxdilli axtarış yönləndirməsi)."""
    client = Groq(api_key=settings.groq_api_key)
    resp = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": "Translate the user's text to English for a scientific search engine. Return ONLY the English translation, nothing else.",
            },
            {"role": "user", "content": text},
        ],
        temperature=0.0,
        max_tokens=300,
    )
    return (resp.choices[0].message.content or text).strip()


def ask_llm(question: str, blocks: list[dict], lang: str = "az") -> str:
    """Retrieval nəticələrini kontekst kimi verib Groq-dan cavab alır.

    lang — translator.detect_lang-ın nəticəsi; cavab dili LLM-in təxmininə
    buraxılmır, prompt-a məcburi direktiv kimi yazılır.
    """
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY təyin olunmayıb")

    context = "\n\n".join(
        f"[{b['paper'].arxiv_id}] {b['paper'].title}\n{b['chunk'].content}" for b in blocks
    )
    client = Groq(api_key=settings.groq_api_key)
    resp = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    context=context,
                    answer_lang=LANG_NAMES.get(lang, "English"),
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0.3,
        max_tokens=800,
    )
    return resp.choices[0].message.content or ""
