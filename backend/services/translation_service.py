import httpx
from typing import Dict, Any
from backend.config import settings

class TranslationUnavailable(Exception):
    pass


class TranslationProvider:
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        raise NotImplementedError

class GoogleTranslationProvider(TranslationProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            url = f"https://translation.googleapis.com/language/translate/v2?key={self.api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json={"q": text, "source": source_lang, "target": target_lang, "format": "text"})
                if res.status_code == 200:
                    data = res.json()
                    return data["data"]["translations"][0]["translatedText"]
        except Exception:
            pass
        raise TranslationUnavailable("Google translation request failed")

class LocalGlossaryFallbackProvider(TranslationProvider):
    """Accurate linguistic fallback for veterinary, animal husbandry, and UI terms."""

    GLOSSARY: Dict[str, Dict[str, str]] = {
        "mr": {
            "cow": "गाय",
            "cattle": "जनावरे",
            "buffalo": "म्हैस",
            "goat": "शेळी",
            "sheep": "मेंढी",
            "fever": "ताप",
            "sick": "आजारी",
            "not eating": "चारा खात नाही",
            "blisters": "फोड",
            "skin lesions": "त्वचेवर गाठी",
            "mouth ulcers": "तोंडात व्रण",
            "lameness": "लंगडेपणा",
            "veterinarian": "पशुवैद्यक",
            "vaccination": "लसीकरण",
            "healthy": "निरोगी"
        },
        "hi": {
            "cow": "गाय",
            "cattle": "पशु",
            "buffalo": "भैंस",
            "goat": "बकरी",
            "sheep": "भेड़",
            "fever": "बुखार",
            "sick": "बीमार",
            "not eating": "खाना नहीं खा रहा",
            "blisters": "छाले",
            "skin lesions": "त्वचा पर गांठें",
            "mouth ulcers": "मुंह में छाले",
            "lameness": "लंगड़ापन",
            "veterinarian": "पशु चिकित्सक",
            "vaccination": "टीकाकरण",
            "healthy": "स्वस्थ"
        },
        "te": {
            "cow": "ఆవు",
            "cattle": "పశువులు",
            "buffalo": "గేదె",
            "goat": "మేక",
            "fever": "జ్వరం",
            "sick": "అనారోగ్యం",
            "veterinarian": "పశువైద్యుడు",
            "vaccination": "టీకా"
        },
        "kn": {
            "cow": "ಹಸು",
            "cattle": "ಜಾನುವಾರು",
            "buffalo": "ಎಮ್ಮೆ",
            "goat": "ಆಡು",
            "fever": "ಜ್ವರ",
            "sick": "ಅನಾರೋಗ್ಯ",
            "veterinarian": "ಪಶುವೈದ್ಯ",
            "vaccination": "ಲಸಿಕೆ"
        },
        "gu": {
            "cow": "ગાય",
            "cattle": "પશુધન",
            "buffalo": "ભેંસ",
            "goat": "બકરી",
            "fever": "તાવ",
            "sick": "બીમાર",
            "veterinarian": "પશુચિકિત્સક",
            "vaccination": "રસીકરણ"
        },
        "ta": {
            "cow": "பசு",
            "cattle": "கால்நடைகள்",
            "buffalo": "எருமை",
            "goat": "ஆடு",
            "fever": "காய்ச்சல்",
            "sick": "நோய்வாய்ப்பட்டது",
            "veterinarian": "கால்நடை மருத்துவர்",
            "vaccination": "தடுப்பூசி"
        },
        "bn": {
            "cow": "গরু",
            "cattle": "গবাদি পশু",
            "buffalo": "মহিষ",
            "goat": "ছাগল",
            "fever": "জ্বর",
            "sick": "অসুস্থ",
            "veterinarian": "পশু চিকিৎসক",
            "vaccination": "টিকা"
        }
    }

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang:
            return text

        target_dict = self.GLOSSARY.get(target_lang, {})
        translated = text
        for en_term, target_term in target_dict.items():
            translated = translated.replace(en_term, target_term)
            translated = translated.replace(en_term.capitalize(), target_term)

        return translated

class TranslationService:
    def __init__(self):
        if settings.TRANSLATION_PROVIDER == "google" and settings.TRANSLATION_API_KEY:
            self.provider = GoogleTranslationProvider(settings.TRANSLATION_API_KEY)
        else:
            self.provider = LocalGlossaryFallbackProvider()

    async def translate_text(self, text: str, source_lang: str = "en", target_lang: str = "mr") -> Dict[str, Any]:
        """Returns translation with explicit provenance. Glossary substitution is a partial
        term-level fallback, NOT a full translation, and is labelled as such."""
        status, provider = "TRANSLATED", "Google Cloud Translation API"
        if isinstance(self.provider, GoogleTranslationProvider):
            try:
                result = await self.provider.translate(text, source_lang, target_lang)
            except TranslationUnavailable:
                result = await LocalGlossaryFallbackProvider().translate(text, source_lang, target_lang)
                status, provider = "FALLBACK_GLOSSARY_PARTIAL", "Local veterinary glossary (provider unavailable)"
        else:
            result = await LocalGlossaryFallbackProvider().translate(text, source_lang, target_lang)
            status, provider = "FALLBACK_GLOSSARY_PARTIAL", "Local veterinary glossary (no translation provider configured)"
        return {
            "original_text": text,
            "translated_text": result,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "provider": provider,
            "status": status,
        }

translation_service = TranslationService()
