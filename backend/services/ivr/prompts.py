"""IVR prompt texts.

Architecture: all 8 Pashu-Shield languages are first-class (selection menu, session and
survey `language` fields, dashboard labels, notification language). Prompt sets below are
fully translated for en/hi/mr; for languages without a full prompt set the engine falls
back to the English text per prompt while keeping the selected language stored everywhere
else (Twilio speech synthesis coverage varies per language — see IVR_SETUP.md).
The welcome line and the language menu are always English on first contact (spec).
"""
from __future__ import annotations

from typing import Dict, Optional

WELCOME = "Welcome to Pashu Shield livestock health helpline."

LANGUAGE_MENU = (
    "Press 1 for English. "
    "Press 2 for Hindi. "
    "Press 3 for Marathi. "
    "Press 4 for Telugu. "
    "Press 5 for Kannada. "
    "Press 6 for Tamil. "
    "Press 7 for Gujarati. "
    "Press 8 for Bengali."
)

# DTMF digit -> language code (existing Pashu-Shield language architecture)
LANGUAGE_DIGITS: Dict[str, str] = {
    "1": "en", "2": "hi", "3": "mr", "4": "te",
    "5": "kn", "6": "ta", "7": "gu", "8": "bn",
}
DIGIT_BY_LANGUAGE: Dict[str, str] = {v: k for k, v in LANGUAGE_DIGITS.items()}

SUPPORTED_LANGUAGES = tuple(DIGIT_BY_LANGUAGE.keys())

# ------------------------------------------------------------------------------------------
# Per-language survey prompts. Missing languages fall back to EN per prompt.
# ------------------------------------------------------------------------------------------
_PROMPTS: Dict[str, Dict[str, str]] = {
    "en": {
        "greeting": "Thank you. A short health survey for your animals will follow. Press 0 at any time to repeat a question.",
        "vet_search": "Searching for an available veterinarian. Please hold.",
        "vet_unavailable": "No veterinarian is available to take your call right now. We will take your answers in a short survey instead.",
        "species": "What animal is affected? Press 1 for Cattle, 2 for Buffalo, 3 for Goat, 4 for Sheep, 5 for Poultry, 6 for Other.",
        "affected_count": "How many animals are affected? Enter the number using the keypad, then press hash.",
        "symptoms": "What symptoms are being observed? Press 1 Fever, 2 Loss of appetite, 3 Skin lesions, 4 Blisters, 5 Lameness, 6 Excessive salivation, 7 Cough, 8 Nasal discharge. Combine keys like 1 and 3, then press hash. Press 9 if you cannot say.",
        "duration": "How long have symptoms been present? Press 1 for less than a day, 2 for 1 to 2 days, 3 for 3 to 7 days, 4 for more than a week, 5 if you are not sure.",
        "deaths": "Have any animals died? Enter the number of deaths using the keypad, then press hash. Enter 0 if none.",
        "vaccination": "Are the animals vaccinated? Press 1 for Yes, 2 for No, 3 if you do not know.",
        "location": "What is your village or location? Say your village name after the tone, or press 1 to use your registered village.",
        "confirm": "Please confirm. Press 1 to submit this report, 2 to start the survey again, or 9 to cancel.",
        "invalid": "Sorry, that is not a valid option. ",
        "too_many_attempts": "We still did not understand the answer, so we will leave that answer unknown. ",
        "survey_aborted": "We could not complete the survey. Your request has been added to the callback queue and a veterinarian will call you back.",
        "report_created": "Thank you. Your report number is {report_number}. Preliminary triage level is {risk}. A veterinarian will follow up. Goodbye.",
        "report_created_callback": "Thank you. Your report number is {report_number} has been recorded and a veterinarian will call you back. Goodbye.",
        "cancelled": "The survey was cancelled. Your request has been added to the callback queue. Goodbye.",
        "ivr_disabled": "Pashu Shield livestock health helpline. The interactive survey is currently unavailable. Please try again later or call helpline 1962. Goodbye.",
        "call_bye": "Thank you for calling Pashu Shield. Goodbye.",
    },
    "hi": {
        "greeting": "धन्यवाद। अब आपके पशुओं के बारे में छोटा स्वास्थ्य सर्वेक्षण होगा। किसी भी प्रश्न को दोहराने के लिए 0 दबाएँ।",
        "vet_search": "उपलब्ध पशु चिकित्सक खोजा जा रहा है। कृपया प्रतीक्षा करें।",
        "vet_unavailable": "अभी कोई पशु चिकित्सक उपलब्ध नहीं है। हम छोटे सर्वेक्षण से आपके उत्तर लेंगे।",
        "species": "कौन सा पशु प्रभावित है? गाय के लिए 1, भैंस के लिए 2, बकरी के लिए 3, भेड़ के लिए 4, मुर्गी पालन के लिए 5, अन्य के लिए 6 दबाएँ।",
        "affected_count": "कितने पशु प्रभावित हैं? कीपैड पर संख्या दर्ज करें, फिर हैश दबाएँ।",
        "symptoms": "कौन से लक्षण दिख रहे हैं? बुखार हेतु 1, भूख न लगना हेतु 2, त्वचा के घाव हेतु 3, छाले हेतु 4, लंगड़ापन हेतु 5, अधिक लार हेतु 6, खाँसी हेतु 7, नाक का स्राव हेतु 8 दबाएँ। संयुक्त रूप से दबाकर हैश दबाएँ। न बता पाने पर 9 दबाएँ।",
        "duration": "लक्षण कितने समय से हैं? एक दिन से कम हेतु 1, 1 से 2 दिन हेतु 2, 3 से 7 दिन हेतु 3, एक सप्ताह से अधिक हेतु 4, अनिश्चित हो तो 5 दबाएँ।",
        "deaths": "क्या कोई पशु मरा है? मृत्यु की संख्या कीपैड पर दर्ज करें, फिर हैश दबाएँ। कोई नहीं तो 0 दबाएँ।",
        "vaccination": "क्या पशुओं का टीकाकरण हुआ है? हाँ हेतु 1, नहीं हेतु 2, नहीं पता हेतु 3 दबाएँ।",
        "location": "आपका गाँव या स्थान क्या है? टोन के बाद अपना गाँव बोलें, या पंजीकृत गाँव के लिए 1 दबाएँ।",
        "confirm": "कृपया पुष्टि करें। रिपोर्ट भेजने के लिए 1, सर्वेक्षण फिर से शुरू करने के लिए 2, रद्द करने के लिए 9 दबाएँ।",
        "invalid": "क्षमा करें, यह वैकल्पिक विकल्प नहीं है। ",
        "too_many_attempts": "उत्तर समझ नहीं आया, इसलिए वह उत्तर अज्ञात रहेगा। ",
        "survey_aborted": "सर्वेक्षण पूरा नहीं हो सका। आपका अनुरोध कॉलबैक सूची में जोड़ दिया गया है और पशु चिकित्सक आपको कॉल करेंगे।",
        "report_created": "धन्यवाद। आपकी रिपोर्ट संख्या {report_number} है। प्रारंभिक ट्रायेज स्तर {risk} है। पशु चिकित्सक संपर्क करेंगे। नमस्ते।",
        "report_created_callback": "धन्यवाद। रिपोर्ट संख्या {report_number} दर्ज हो गई है और पशु चिकित्सक आपको कॉल करेंगे। नमस्ते।",
        "cancelled": "सर्वेक्षण रद्द किया गया। आपका अनुरोध कॉलबैक सूची में जोड़ दिया गया है। नमस्ते।",
        "ivr_disabled": "पशु शील्ड पशु स्वास्थ्य हेल्पलाइन। इंटरैक्टिव सर्वेक्षण अभी उपलब्ध नहीं है। बाद में पुनः प्रयास करें या 1962 पर कॉल करें। नमस्ते।",
        "call_bye": "पशु शील्ड को कॉल करने के लिए धन्यवाद। नमस्ते।",
    },
    "mr": {
        "greeting": "धन्यवाद. आत तुमच्या जनावरांबद्दल छोटा आरोग्य सर्वेक्षण होईल. प्रत्येक प्रश्न पुन्हा विचारण्यासाठी 0 दाबा.",
        "vet_search": "उपलब्ध पशुवैद्य शोधत आहे. कृपया प्रतीक्षा करा.",
        "vet_unavailable": "सध्या कोणताही पशुवैद्य उपलब्ध नाही. आम्ही छोट्या सर्वेक्षणातून तुमची उत्तरे घेऊ.",
        "species": "कोणते जनावर प्रभावित आहे? गाय: 1, म्हैस: 2, शेळी: 3, मेंढी: 4, कोंबडी: 5, इतर: 6 दाबा.",
        "affected_count": "किती जनावरे प्रभावित आहेत? कीपॅडवर संख्या टाइप करा आणि हॅश दाबा.",
        "symptoms": "कोणती लक्षणे दिसत आहेत? ताप: 1, चारा खात नाही: 2, त्वचेवर गाठी: 3, फोड: 4, लंगडेपणा: 5, अति लाळ: 6, खोकला: 7, नाकात स्राव: 8 दाबा. एकापेक्षा जास्त दाबून नंतर हॅश दाबा. सांगता येत नसेल तर 9 दाबा.",
        "duration": "लक्षणे किती वेळापासून आहेत? एका दिवसापेक्षा कमी: 1, 1 ते 2 दिवस: 2, 3 ते 7 दिवस: 3, एका आठवड्यापेक्षा जास्त: 4, खात्री नसेल तर 5 दाबा.",
        "deaths": "कोणतेही जनावर मेले आहे का? मृत्यू संख्या कीपॅडवर टाइप करा आणि हॅश दाबा. कोणी नसेल तर 0 दाबा.",
        "vaccination": "जनावरांना लसीकरण झाले आहे का? होय: 1, नाही: 2, माहीत नाही: 3 दाबा.",
        "location": "तुमचे गाव किंवा ठिकाण कोणते? टोननंतर तुमचे गाव सांगा, किंवा नोंदणीकृत गावासाठी 1 दाबा.",
        "confirm": "कृपया खात्री करा. अहवाल पाठवण्यासाठी 1, सर्वेक्षण पुन्हा सुरू करण्यासाठी 2, रद्द करण्यासाठी 9 दाबा.",
        "invalid": "माफ करा, हा पर्याय वैध नाही. ",
        "too_many_attempts": "उत्तर समजले नाही, त्यामुळे ते अज्ञात राहील. ",
        "survey_aborted": "सर्वेक्षण पूर्ण होऊ शकले नाही. तुमची विनंती कॉलबॅक यादीत जोडली आहे आणि पशुवैद्य तुम्हाला कॉल करतील.",
        "report_created": "धन्यवाद. तुमचा अहवाल क्रमांक {report_number} आहे. प्राथमिक ट्रायेज पातळी {risk} आहे. पशुवैद्य पुढील पावले घेतील. निरोग.",
        "report_created_callback": "धन्यवाद. अहवाल क्रमांक {report_number] नोंदवला आहे आणि पशुवैद्य तुम्हाला कॉल करतील. निरोग.",
        "cancelled": "सर्वेक्षण रद्द केले. तुमची विनंती कॉलबॅक यादीत जोडली आहे. निरोग.",
        "ivr_disabled": "पशु शील्ड पशु आरोग्य हेल्पलाइन. इंटरॅक्टिव्ह सर्वेक्षण सध्या उपलब्ध नाही. नंतर पुन्हा प्रयत्न करा किंवा 1962 वर कॉल करा. निरोग.",
        "call_bye": "पशु शील्डला कॉल केल्याबद्दल धन्यवाद. निरोग.",
    },
}

# Fix typo in mr report_created_callback placeholder
_PROMPTS["mr"]["report_created_callback"] = (
    "धन्यवाद. अहवाल क्रमांक {report_number} नोंदवला आहे आणि पशुवैद्य तुम्हाला कॉल करतील. निरोग."
)


def prompt(language: Optional[str], key: str) -> str:
    """Return the prompt for `key` in `language`, falling back to English per prompt."""
    lang = (language or "en").lower()
    table = _PROMPTS.get(lang) or _PROMPTS["en"]
    return table.get(key) or _PROMPTS["en"][key]


def format_prompt(language: Optional[str], key: str, **kwargs) -> str:
    try:
        return prompt(language, key).format(**kwargs)
    except (KeyError, IndexError):
        return _PROMPTS["en"][key].format(**{k: v for k, v in kwargs.items() if "{" + k + "}" in _PROMPTS["en"][key]})
