# All 7 message types in Tamil, Hindi, English
# Use render_template() to fill placeholders

TEMPLATES = {

    # ── Message Type 1 — First Introduction ─────────────────
    "INTRODUCTION": {
        "tamil": (
            "வணக்கம் {client_name},\n"
            "இது வக்கீல் {advocate_name} அவர்கள் அலுவலகத்திலிருந்து "
            "அனுப்பப்படும் தானியங்கி செய்தி.\n"
            "உங்கள் வழக்கு {case_number} பற்றிய தகவல்களை "
            "இந்த எண்ணில் அனுப்புவோம்.\n"
            "சரியான எண்ணா என்று YES என்று பதில் அனுப்புங்கள்."
        ),
        "hindi": (
            "नमस्ते {client_name},\n"
            "यह संदेश अधिवक्ता {advocate_name} के कार्यालय से भेजा जा रहा है।\n"
            "आपके मुकदमे {case_number} की जानकारी इस नंबर पर भेजी जाएगी।\n"
            "कृपया YES लिखकर जवाब दें।"
        ),
        "english": (
            "Hello {client_name},\n"
            "This is an automated assistant from Advocate {advocate_name}'s office.\n"
            "We will send updates about your case {case_number} on this number.\n"
            "Reply YES to confirm this is the right number."
        ),
    },

    # ── Message Type 2 — New Hearing Date (7+ days away) ────
    "NEW_HEARING_DATE": {
        "tamil": (
            "அன்புள்ள {client_name},\n\n"
            "உங்கள் வழக்கின் அடுத்த தேதி:\n"
            "📅 {hearing_date} | ⏰ {hearing_time}\n"
            "🏛️ {court_name}, கோர்ட் ஹால் {court_hall}\n\n"
            "கொண்டு வர வேண்டியவை:\n"
            "{documents}\n\n"
            "வக்கீல் {advocate_name} சார்பில் அனுப்பப்படுகிறது."
        ),
        "hindi": (
            "प्रिय {client_name},\n\n"
            "आपके मुकदमे की अगली तारीख:\n"
            "📅 {hearing_date} | ⏰ {hearing_time}\n"
            "🏛️ {court_name}, कोर्ट हॉल {court_hall}\n\n"
            "साथ लाने वाले दस्तावेज़:\n"
            "{documents}\n\n"
            "अधिवक्ता {advocate_name} की ओर से।"
        ),
        "english": (
            "Dear {client_name},\n\n"
            "Your next hearing date:\n"
            "📅 {hearing_date} | ⏰ {hearing_time}\n"
            "🏛️ {court_name}, Court Hall {court_hall}\n\n"
            "Documents to bring:\n"
            "{documents}\n\n"
            "Sent on behalf of Advocate {advocate_name}."
        ),
    },

    # ── Message Type 3 — Urgent Hearing Tomorrow ─────────────
    "URGENT_HEARING": {
        "tamil": (
            "அன்புள்ள {client_name},\n\n"
            "⚠️ உங்கள் வழக்கு நாளை நடைபெறும்!\n\n"
            "📅 {hearing_date} | ⏰ {hearing_time}\n"
            "🏛️ {court_name}, கோர்ட் ஹால் {court_hall}\n\n"
            "கட்டாயம் கொண்டு வர வேண்டியவை:\n"
            "{documents}\n\n"
            "⚠️ கடந்த முறை நீதிபதி இவற்றை கேட்டார். மிகவும் முக்கியம்.\n\n"
            "நீங்கள் வர முடியுமா? YES அல்லது NO என்று பதில் அனுப்புங்கள்."
        ),
        "hindi": (
            "प्रिय {client_name},\n\n"
            "⚠️ आपके मुकदमे की सुनवाई कल है!\n\n"
            "📅 {hearing_date} | ⏰ {hearing_time}\n"
            "🏛️ {court_name}, कोर्ट हॉल {court_hall}\n\n"
            "ज़रूरी दस्तावेज़:\n"
            "{documents}\n\n"
            "⚠️ पिछली बार जज ने इन्हें माँगा था। बहुत ज़रूरी है।\n\n"
            "क्या आप आ सकते हैं? YES या NO में जवाब दें।"
        ),
        "english": (
            "Dear {client_name},\n\n"
            "⚠️ Your case hearing is TOMORROW!\n\n"
            "📅 {hearing_date} | ⏰ {hearing_time}\n"
            "🏛️ {court_name}, Court Hall {court_hall}\n\n"
            "Must bring:\n"
            "{documents}\n\n"
            "⚠️ Judge specifically asked for these last time. Very important.\n\n"
            "Can you attend? Reply YES or NO."
        ),
    },

    # ── Message Type 4 — 2 Hour Reminder ────────────────────
    "TWO_HOUR_REMINDER": {
        "tamil": (
            "{client_name}, உங்கள் வழக்கு இன்று {hearing_time}க்கு நடைபெறும்.\n"
            "🏛️ {court_name}, கோர்ட் ஹால் {court_hall}\n"
            "15 நிமிடம் முன்பே வாருங்கள்.\n"
            "வக்கீல் {advocate_name} அங்கே இருப்பார்கள்."
        ),
        "hindi": (
            "{client_name}, आपके मुकदमे की सुनवाई आज {hearing_time} बजे है।\n"
            "🏛️ {court_name}, कोर्ट हॉल {court_hall}\n"
            "15 मिनट पहले पहुँचें।\n"
            "अधिवक्ता {advocate_name} वहाँ मौजूद रहेंगे।"
        ),
        "english": (
            "{client_name}, your case hearing is today at {hearing_time}.\n"
            "🏛️ {court_name}, Court Hall {court_hall}\n"
            "Please arrive 15 minutes early.\n"
            "Advocate {advocate_name} will be there."
        ),
    },

    # ── Message Type 5 — Order Summary ──────────────────────
    "ORDER_SUMMARY": {
        "tamil": (
            "அன்புள்ள {client_name},\n\n"
            "இன்று {order_date} உங்கள் வழக்கில் நீதிபதி உத்தரவிட்டுள்ளார்:\n\n"
            "📋 என்ன சொன்னார்:\n{order_summary}\n\n"
            "⏰ நீங்கள் என்ன செய்ய வேண்டும்:\n{next_action}\n\n"
            "📅 கடைசி தேதி: {deadline}\n\n"
            "மேலும் விவரங்களுக்கு வக்கீல் {advocate_name} அவர்களை தொடர்பு கொள்ளுங்கள்."
        ),
        "hindi": (
            "प्रिय {client_name},\n\n"
            "आज {order_date} को जज ने आपके मुकदमे में आदेश दिया:\n\n"
            "📋 क्या कहा:\n{order_summary}\n\n"
            "⏰ आपको क्या करना है:\n{next_action}\n\n"
            "📅 अंतिम तारीख: {deadline}\n\n"
            "अधिक जानकारी के लिए अधिवक्ता {advocate_name} से संपर्क करें।"
        ),
        "english": (
            "Dear {client_name},\n\n"
            "Today {order_date}, the judge passed an order in your case:\n\n"
            "📋 What was ordered:\n{order_summary}\n\n"
            "⏰ What you need to do:\n{next_action}\n\n"
            "📅 Deadline: {deadline}\n\n"
            "Contact Advocate {advocate_name} for more details."
        ),
    },

    # ── Message Type 6 — Urgent Alert ───────────────────────
    "URGENT_ALERT": {
        "tamil": (
            "{client_name}, மிகவும் அவசரம்!\n\n"
            "🚨 உங்கள் வழக்கில் முக்கியமான விஷயம் நடந்துள்ளது.\n\n"
            "இப்போதே வக்கீல் {advocate_name} அவர்களை அழையுங்கள்: {advocate_phone}\n\n"
            "தயவுசெய்து உடனே பதில் அனுப்புங்கள்."
        ),
        "hindi": (
            "{client_name}, बहुत ज़रूरी!\n\n"
            "🚨 आपके मुकदमे में कुछ महत्वपूर्ण हुआ है।\n\n"
            "अभी अधिवक्ता {advocate_name} को कॉल करें: {advocate_phone}\n\n"
            "कृपया तुरंत जवाब दें।"
        ),
        "english": (
            "{client_name}, URGENT!\n\n"
            "🚨 Something important has happened in your case.\n\n"
            "Call Advocate {advocate_name} immediately: {advocate_phone}\n\n"
            "Please respond right away."
        ),
    },

    # ── Message Type 7 — Case Victory ───────────────────────
    "CASE_VICTORY": {
        "tamil": (
            "அன்புள்ள {client_name},\n\n"
            "🎉 உங்கள் வழக்கில் நல்ல செய்தி!\n\n"
            "{order_date} அன்று நீதிபதி உங்களுக்கு சாதகமாக தீர்ப்பு வழங்கினார்.\n\n"
            "மேலும் விவரங்களுக்கு வக்கீல் {advocate_name} அவர்களை தொடர்பு கொள்ளுங்கள்."
        ),
        "hindi": (
            "प्रिय {client_name},\n\n"
            "🎉 आपके मुकदमे में खुशखबरी!\n\n"
            "{order_date} को जज ने आपके पक्ष में फैसला सुनाया।\n\n"
            "अधिक जानकारी के लिए अधिवक्ता {advocate_name} से संपर्क करें।"
        ),
        "english": (
            "Dear {client_name},\n\n"
            "🎉 Great news about your case!\n\n"
            "On {order_date}, the judge passed a verdict in your favour.\n\n"
            "Contact Advocate {advocate_name} for more details."
        ),
    },

    # ── Acknowledgement messages ─────────────────────────────
    "ACK_CONFIRMED": {
        "tamil":   "நன்று! நாளை காலை மீண்டும் நினைவூட்டுவோம். நீதிமன்றத்தில் சந்திக்கலாம். ✅",
        "hindi":   "बढ़िया! कल सुबह फिर याद दिलाएंगे। कोर्ट में मिलते हैं। ✅",
        "english": "Great! We will remind you again tomorrow morning. See you in court. ✅",
    },

    "ACK_CANNOT_ATTEND": {
        "tamil":   "சரி, காரணம் சொல்லுங்கள். வக்கீலிடம் உடனே தெரிவிக்கிறோம்.",
        "hindi":   "ठीक है, कारण बताएं। हम तुरंत वकील को सूचित करेंगे।",
        "english": "Understood. Can you tell us why? We will inform the advocate immediately.",
    },

    "ACK_PROBLEM": {
        "tamil":   "புரிகிறது. வக்கீல் {advocate_name} அவர்களிடம் உடனே தெரிவிக்கிறோம். சீக்கிரம் தொடர்பு கொள்வார்கள்.",
        "hindi":   "समझ गए। अधिवक्ता {advocate_name} को तुरंत सूचित कर रहे हैं। वे जल्द संपर्क करेंगे।",
        "english":  "We understand. Informing Advocate {advocate_name} immediately. They will contact you shortly.",
    },

    "ACK_UNCLEAR": {
        "tamil":   "மன்னிக்கவும், புரியவில்லை. YES அல்லது NO என்று பதில் அனுப்புங்கள்.",
        "hindi":   "माफ करें, समझ नहीं आया। कृपया YES या NO में जवाब दें।",
        "english": "Sorry, we did not understand. Can you reply with YES or NO?",
    },

    "OPT_OUT_CONFIRM": {
        "tamil":   "சரி, இனி செய்திகள் அனுப்பமாட்டோம். நேரடியாக வக்கீலை தொடர்பு கொள்ளுங்கள்.",
        "hindi":   "ठीक है, अब कोई संदेश नहीं भेजेंगे। वकील से सीधे संपर्क करें।",
        "english": "Understood. We will stop sending messages. Please contact the advocate directly.",
    },
}


def render_template(template_name: str, language: str, variables: dict) -> str:
    lang = language.lower()
    if lang == "tanglish":
        lang = "tamil"
    if lang not in ("tamil", "hindi", "english"):
        lang = "english"

    template = TEMPLATES.get(template_name, {}).get(lang, "")
    if not template:
        raise ValueError(f"Template '{template_name}' not found for language '{lang}'")

    # Format documents list if present
    if "documents" in variables and isinstance(variables["documents"], list):
        variables["documents"] = "\n".join(f"→ {d}" for d in variables["documents"])

    return template.format_map(variables)
