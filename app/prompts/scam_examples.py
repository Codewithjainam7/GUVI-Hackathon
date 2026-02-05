"""
Real-world Indian Scam Examples for Few-Shot Prompting
These examples help the LLM understand the nuance of local scams.
"""

SCAM_EXAMPLES = """
EXAMPLE 1 (UPI Scam):
Message: "Sir 2000 rupees sent by mistake to your PhonePe. Please return to 98XXX."
Analysis:
- is_scam: True
- risk_level: High
- scam_type: "Refund Scam"
- reasoning: Classic social engineering to trigger guilt and urgency.

EXAMPLE 2 (Lottery Scam):
Message: "KBC Lucky Draw Winner! You won 25 Lakhs. Contact Rana Pratap Singh at Whatsapp."
Analysis:
- is_scam: True
- risk_level: Critical
- scam_type: "Lottery Scam"
- reasoning: Unsolicited prize claim from TV show, requesting contact on WhatsApp.

EXAMPLE 3 (Sextortion):
Message: "I have recorded your video calling. Pay 10k or I upload on YouTube."
Analysis:
- is_scam: True
- risk_level: Critical
- scam_type: "Sextortion"
- reasoning: Threatening blackmail with video evidence (common pattern).

EXAMPLE 4 (Safe Message):
Message: "Your OTP for login is 123456. Do not share this with anyone."
Analysis:
- is_scam: False
- risk_level: Low
- scam_type: None
- reasoning: Standard transactional message, warns NOT to share.

EXAMPLE 5 (Job Scam):
Message: "Work from home part time job. Daily 5000-8000. Just like YouTube videos."
Analysis:
- is_scam: True
- risk_level: High
- scam_type: "Job Scam"
- reasoning: Unrealistic income promises for simple tasks ("like videos").
"""

def get_few_shot_prompt() -> str:
    return f"""
Refer to these examples when analyzing:
{SCAM_EXAMPLES}
"""
