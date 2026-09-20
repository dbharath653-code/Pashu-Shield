from typing import List, Dict, Any, Optional

class TriageEngine:
    """
    Safe rule-based clinical triage engine for livestock early-warning.
    Evaluates symptoms, mortality, temperature, and epidemiological risks
    WITHOUT claiming certainty of medical diagnosis.
    """
    
    # Critical warning sign keywords
    CRITICAL_SIGNS = [
        "sudden death", "bleeding from orifices", "high fever", "paralysis", 
        "severe blisters", "respiratory distress", "rapid death", "severe lameness"
    ]
    
    HIGH_CONCERN_SYMPTOMS = [
        "skin lesions", "nodules", "mouth ulcers", "blisters on gums", 
        "abortion", "swollen lymph nodes", "salivation", "fever"
    ]

    @classmethod
    def evaluate(
        cls,
        species: str,
        symptoms: List[str],
        number_affected: int = 1,
        number_dead: int = 0,
        temperature: Optional[float] = None,
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        normalized_symptoms = [s.lower().strip() for s in symptoms]
        
        # 1. Mortality or severe systemic distress = CRITICAL
        if number_dead > 0 or any(cs in normalized_symptoms for cs in cls.CRITICAL_SIGNS):
            risk_level = "CRITICAL"
            urgency = "EMERGENCY"
            requires_vet = True
            requires_lab = True
            diagnostic_note = "Potential high-consequence disease alert. Immediate containment and investigation warranted."
            recommendations = [
                "Immediately isolate affected and in-contact animals in a separate shed.",
                "Prevent movement of animals, vehicles, and personnel off premises.",
                "Do NOT dispose of carcasses without veterinary supervision.",
                "Emergency Veterinary Mobile Unit has been alerted."
            ]
            biosecurity = [
                "Disinfect footware with 4% sodium carbonate or bleach solution before entering/exiting.",
                "Wear protective boots and gloves when handling suspected livestock.",
                "Quarantine water troughs and fodder supplies."
            ]
            
        # 2. Multiple affected animals or high fever (> 104 F / 40 C)
        elif (
            number_affected >= 3 or 
            (temperature is not None and (temperature >= 104.0 or temperature >= 40.0)) or
            any(hc in normalized_symptoms for hc in cls.HIGH_CONCERN_SYMPTOMS)
        ):
            risk_level = "HIGH"
            urgency = "URGENT"
            requires_vet = True
            requires_lab = any("blister" in s or "lesion" in s or "ulcer" in s for s in normalized_symptoms)
            diagnostic_note = "Clinical presentation indicates significant infectious risk. Requires timely veterinary assessment."
            recommendations = [
                "Separate symptomatic animals from healthy herd members.",
                "Provide clean shade, fresh water, and soft palatable feed.",
                "Record daily morning and evening temperatures of the herd.",
                "Avoid administering unprescribed antibiotics; await qualified veterinary diagnosis."
            ]
            biosecurity = [
                "Limit farm visitors and restrict livestock contact with neighboring herds.",
                "Clean equipment with disinfectant after contact with sick livestock."
            ]
            
        # 3. Mild symptoms (reduced appetite, mild cough, diarrhea)
        elif len(normalized_symptoms) > 0:
            risk_level = "MODERATE"
            urgency = "ROUTINE"
            requires_vet = True
            requires_lab = False
            diagnostic_note = "Mild to moderate systemic signs observed. Monitor closely for symptom progression."
            recommendations = [
                "Maintain clean bedding and ensure good shed ventilation.",
                "Ensure clean drinking water with electrolyte supplementation if needed.",
                "Schedule a checkup with the nearest block veterinary officer if signs persist > 24 hours."
            ]
            biosecurity = [
                "Maintain standard biosecurity and check vaccination records."
            ]
            
        # 4. Healthy / Routine
        else:
            risk_level = "LOW"
            urgency = "ROUTINE"
            requires_vet = False
            requires_lab = False
            diagnostic_note = "No acute disease signs reported. Continue regular herd health maintenance."
            recommendations = [
                "Continue standard feeding, biosecurity, and deworming schedule.",
                "Ensure regular booster vaccinations against FMD, HS, BQ, and LSD."
            ]
            biosecurity = [
                "Keep shed dry and vector-free."
            ]

        # Clinical disclaimer
        disclaimer = (
            "IMPORTANT NOTICE: Pashu-Shield automated triage is an early-warning decision support tool, "
            "not a definitive veterinary medical diagnosis. Final diagnosis and pharmaceutical therapy "
            "must be prescribed exclusively by a registered veterinary practitioner."
        )

        return {
            "risk_level": risk_level,
            "urgency": urgency,
            "requires_veterinary_dispatch": requires_vet,
            "requires_lab_sampling": requires_lab,
            "diagnostic_note": diagnostic_note,
            "recommendations": recommendations,
            "biosecurity_instructions": biosecurity,
            "disclaimer": disclaimer,
            "evaluated_symptoms": symptoms
        }
