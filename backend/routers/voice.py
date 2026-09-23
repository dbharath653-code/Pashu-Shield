import re
from typing import Optional
from fastapi import APIRouter, Depends
from backend.schemas import VoiceIntentRequest, VoiceIntentResponse
from backend.services.triage_service import TriageEngine
from backend.services.translation_service import translation_service
from backend.security import get_current_user_optional, get_current_user
from backend.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/voice", tags=["Voice Assistant & Natural Language Processing"])

class TranslateReq(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "mr"

@router.post("/translate")
async def translate_text_endpoint(req: TranslateReq, current_user: User = Depends(get_current_user)):
    return await translation_service.translate_text(req.text, req.source_lang, req.target_lang)

DISEASE_KEYWORDS = {
    "fmd": "Foot-and-Mouth Disease (FMD)",
    "foot and mouth": "Foot-and-Mouth Disease (FMD)",
    "laalya": "Foot-and-Mouth Disease (FMD)",
    "खुरकूत": "Foot-and-Mouth Disease (FMD)",
    "लाळ्या": "Foot-and-Mouth Disease (FMD)",
    "lsd": "Lumpy Skin Disease (LSD)",
    "lumpy": "Lumpy Skin Disease (LSD)",
    "लंपी": "Lumpy Skin Disease (LSD)",
    "ppr": "Peste des Petits Ruminants (PPR)",
    "goat plague": "Peste des Petits Ruminants (PPR)",
    "brucellosis": "Brucellosis"
}

SYMPTOM_MAP = {
    "fever": "Fever",
    "ताप": "Fever",
    "बुखार": "Fever",
    "not eating": "Loss of appetite",
    "appetite": "Loss of appetite",
    "चारा खात नाही": "Loss of appetite",
    "blister": "Blisters",
    "nodule": "Skin lesions",
    "lumps": "Skin lesions",
    "गाठी": "Skin lesions",
    "saliva": "Excessive salivation",
    "drooling": "Excessive salivation",
    "lame": "Lameness",
    "लंगडत": "Lameness",
    "cough": "Cough",
    "खोकला": "Cough",
    "discharge": "Nasal discharge",
    "swelling": "Swelling"
}

SPECIES_MAP = {
    "cow": "Cattle",
    "cattle": "Cattle",
    "bull": "Cattle",
    "गाय": "Cattle",
    "बैल": "Cattle",
    "buffalo": "Buffalo",
    "म्हैस": "Buffalo",
    "goat": "Goat",
    "शेळी": "Goat",
    "बकरी": "Goat",
    "sheep": "Sheep",
    "मेंढी": "Sheep",
    "poultry": "Poultry",
    "chicken": "Poultry",
    "कोंबडी": "Poultry"
}

@router.post("/intent", response_model=VoiceIntentResponse)
async def process_voice_intent(
    req: VoiceIntentRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    text = req.transcript.lower().strip()
    lang = req.language

    # 1. Extract Entities
    species = "Cattle"
    for k, v in SPECIES_MAP.items():
        if k in text:
            species = v
            break

    extracted_symptoms = []
    for k, v in SYMPTOM_MAP.items():
        if k in text and v not in extracted_symptoms:
            extracted_symptoms.append(v)

    # Extract affected count
    affected_match = re.search(r"(\d+)\s*(animals?|cows?|cattle|goats?|buffalos?|जनावर|गाय|शेळी)?", text)
    affected_count = int(affected_match.group(1)) if affected_match and int(affected_match.group(1)) < 500 else 1

    # Extract dead count
    dead_match = re.search(r"(\d+)\s*(dead|died|मरण|मेली)", text)
    dead_count = int(dead_match.group(1)) if dead_match else (1 if any(w in text for w in ["dead", "died", "मेली", "मरण"]) else 0)

    # 2. Determine Intent
    intent = "UNKNOWN"
    fulfillment = ""
    requires_conf = False
    action_payload = None
    next_step = None

    if any(w in text for w in ["report", "sick", "ill", "disease", "आजारी", "तक्रार", "बीमार", "fever", "blister"]):
        intent = "REPORT_DISEASE"
        requires_conf = True

        # Run triage calculation
        triage = TriageEngine.evaluate(
            species=species,
            symptoms=extracted_symptoms,
            number_affected=affected_count,
            number_dead=dead_count
        ) if extracted_symptoms else None

        action_payload = {
            "species": species,
            "number_affected": affected_count,
            "number_dead": dead_count,
            "symptoms": extracted_symptoms,
            "district": current_user.district if current_user and current_user.district else None,
            "village": current_user.village if current_user and current_user.village else None,
            "triage_risk_level": triage["risk_level"] if triage else None
        }

        if lang == "mr":
            if not extracted_symptoms:
                fulfillment = f"{affected_count} {species} साठी अहवाल सुरू केला आहे. कृपया लक्षणे सांगा (उदा. ताप, गाठी, लाळ गळणे)."
            else:
                fulfillment = f"मी {affected_count} {species} साठी अहवाल तयार केला आहे ज्यांना लक्षणे आहेत: {', '.join(extracted_symptoms)}. प्राथमिक जोखीम पातळी {triage['risk_level']} (निदान नाही). मी हा अहवाल दाखल करू का?"
        else:
            if not extracted_symptoms:
                fulfillment = f"I started a report for {affected_count} {species}. Please describe the symptoms (for example fever, skin lumps, drooling)."
            else:
                fulfillment = f"I have prepared a disease report for {affected_count} {species} with {', '.join(extracted_symptoms)}. Preliminary triage risk: {triage['risk_level']} (not a diagnosis). Shall I submit this report to the veterinary network?"

        next_step = "CONFIRM_REPORT_SUBMISSION" if extracted_symptoms else "ASK_SYMPTOMS"

    elif any(w in text for w in ["vet", "doctor", "hospital", "पशुवैद्यक", "डॉक्टर", "दवाखाना"]):
        intent = "REQUEST_VETERINARIAN"
        requires_conf = True
        action_payload = {
            "type": "EMERGENCY_DISPATCH",
            "district": current_user.district if current_user and current_user.district else None
        }
        if lang == "mr":
            fulfillment = "जवळचे शासकीय पशुवैद्यकीय अधिकारी आणि मोबाइल व्हेटर्नरी युनिट (1962) शोधत आहे. तात्काळ भेट बुक करू का?"
        else:
            fulfillment = "Connecting you with the nearest Veterinary Officer and Mobile Unit (Toll-Free 1962). Shall I request an emergency on-site visit?"
        next_step = "CONFIRM_VET_DISPATCH"

    elif any(w in text for w in ["my animal", "my cows", "show animals", "माझे प्राणी", "माझ्या गाई"]):
        intent = "VIEW_ANIMALS"
        requires_conf = False
        fulfillment = "Opening your registered livestock herd records." if lang != "mr" else "तुमच्या नोंदणीकृत जनावरांची यादी उघडत आहे."
        action_payload = {"navigate": "/animal-health"}

    elif any(w in text for w in ["vaccine", "vaccination", "लस", "लसीकरण"]):
        intent = "CHECK_VACCINATION"
        requires_conf = False
        fulfillment = "Opening your vaccination records." if lang != "mr" else "तुमच्या जनावरांच्या लसीकरण नोंदी उघडत आहे."
        action_payload = {"navigate": "/vaccination"}

    elif any(w in text for w in ["lab", "sample", "test result", "प्रयोगशाळा", "नमुना"]):
        intent = "CHECK_LAB_RESULT"
        requires_conf = False
        fulfillment = "Opening laboratory sample tracking." if lang != "mr" else "प्रयोगशाळा नमुना माहिती उघडत आहे."
        action_payload = {"navigate": "/lab"}

    elif any(w in text for w in ["sync", "offline", "समक्रमित"]):
        intent = "SYNC_DATA"
        requires_conf = False
        fulfillment = "Synchronizing local offline drafts with the central government server." if lang != "mr" else "स्थानिक ऑफलाइन डेटा मुख्य सर्व्हरसह समक्रमित केला जात आहे."
        action_payload = {"action": "TRIGGER_SYNC"}

    else:
        # Disease Q&A
        matched_disease = None
        for k, v in DISEASE_KEYWORDS.items():
            if k in text:
                matched_disease = v
                break

        if matched_disease:
            intent = "GET_DISEASE_INFORMATION"
            requires_conf = False
            if lang == "mr":
                fulfillment = f"{matched_disease} बद्दल माहिती: लक्षणे दिसताच प्राण्याला तात्काळ वेगळे करा, भरपूर स्वच्छ पाणी द्या आणि टोल-फ्री १९६२ वर संपर्क करा."
            else:
                fulfillment = f"Guidance on {matched_disease}: Isolate symptomatic cattle immediately, maintain clean ventilation and hydration, and do not self-medicate without a registered veterinary prescription."
        else:
            intent = "GENERAL_HELP"
            requires_conf = False
            if lang == "mr":
                fulfillment = "पशु-शिल्ड आवाज सहाय्यकामध्ये आपले स्वागत आहे. आपण आजारी जनावराची तक्रार करू शकता, डॉक्टर मागवू शकता किंवा लसीकरण माहिती विचारू शकता."
            else:
                fulfillment = "Welcome to Pashu-Shield Voice Assistant. You can say 'Report my sick cow', 'Request a vet', 'Check vaccinations', or ask disease questions."

    return {
        "intent": intent,
        "entities": {
            "species": species,
            "symptoms": extracted_symptoms,
            "number_affected": affected_count,
            "number_dead": dead_count
        },
        "fulfillment_text": fulfillment,
        "requires_confirmation": requires_conf,
        "action_payload": action_payload,
        "next_step": next_step
    }
