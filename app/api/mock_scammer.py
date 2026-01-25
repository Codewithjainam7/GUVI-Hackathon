"""
Mock Scammer API - Simulates scammer behavior for testing and demos
"""

import random
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


# Scammer message templates by scam type
SCAMMER_TEMPLATES = {
    "lottery": {
        "initial": [
            "🎉 Congratulations! You have been selected as the LUCKY WINNER of ₹50,00,000 in WhatsApp International Lottery! Reply 'YES' to claim your prize!",
            "Dear Customer, Your mobile number has won USD 850,000 in Microsoft Lottery. Contact us immediately to claim.",
            "URGENT: You won ₹25,00,000 in Amazon Lucky Draw! This is your FINAL NOTICE. Contact now!",
        ],
        "followup": [
            "To process your prize, we need a small registration fee of ₹5,000. Please send to our official UPI: lottery_winner@upi",
            "Sir, your prize is waiting. Just pay the processing charges and amount will be transferred within 1 hour.",
            "Time is running out! Pay the fee NOW or your prize will be cancelled. Others are waiting!",
            "I understand your concern. This is 100% genuine. Give me your bank account number for direct transfer.",
        ]
    },
    "tax": {
        "initial": [
            "⚠️ URGENT NOTICE from Income Tax Department: Your PAN Card is linked to suspicious transactions of ₹2 Crore. Call immediately to avoid arrest.",
            "This is IT Department. Your tax returns show discrepancy. Legal action will be taken. Press 1 to connect to officer.",
            "Final Warning: Your Aadhaar-linked accounts will be frozen in 2 hours due to tax evasion. Call now: 9876543210",
        ],
        "followup": [
            "Sir, I am Officer Sharma from Cyber Cell. To clear your name, you must pay penalty of ₹50,000 immediately.",
            "If you don't cooperate, we will issue arrest warrant. Give your Aadhaar number for verification.",
            "This is serious matter. Transfer the fine amount to government account: 1234567890123456 IFSC: SBIN0001234",
            "Your case is very serious. Pay using Google Pay to 9876543210. This is official procedure.",
        ]
    },
    "tech_support": {
        "initial": [
            "⚠️ ALERT: Your computer has been infected with dangerous virus! Microsoft Security detected suspicious activity. Call support: 1800-XXX-XXXX",
            "Warning: Your Windows license has expired. Your PC will be blocked. Call Microsoft Support immediately.",
            "Security Alert: Hackers are accessing your bank account right now! Install remote support software urgently.",
        ],
        "followup": [
            "Please download TeamViewer and share the ID. Our technician will remove the virus.",
            "Sir, the malware is very dangerous. You need premium protection. Cost is only ₹15,000.",
            "I can see hackers in your system right now! Quick, give me your internet banking password to secure it!",
            "To complete the security update, I need your debit card number and CVV for verification.",
        ]
    },
    "job": {
        "initial": [
            "🌟 WORK FROM HOME OPPORTUNITY! Earn ₹50,000-₹1,00,000 monthly. No experience needed. WhatsApp 9876543210",
            "Amazon is hiring! Work from home, flexible hours, guaranteed salary ₹45,000. Limited positions. Apply now!",
            "Congratulations! You are selected for Data Entry job. Salary: ₹60,000/month. Pay ₹2,000 registration fee to join.",
        ],
        "followup": [
            "To process your application, please pay registration fee of ₹3,000 to company UPI: hr_amazon@paytm",
            "Training material cost is ₹5,000. This is refundable after first month. Pay now to confirm your position.",
            "Your interview is scheduled. First transfer the security deposit. Send Aadhaar and PAN copy also.",
            "Congratulations! You're hired. Before we can add you to payroll, complete KYC by paying ₹1,500.",
        ]
    },
    "romance": {
        "initial": [
            "Hi dear! I found your profile on Facebook. You look very nice. Can we be friends?",
            "Hello beautiful! I am Jack from USA, working in oil company. Saw your picture and fell in love.",
            "Darling, I have been watching your profile. You seem like a genuine person. I am very lonely here.",
        ],
        "followup": [
            "I want to send you a gift package worth $50,000. But customs is asking clearance fee. Can you help?",
            "My dear, I am stuck in airport. My cards are blocked. Please send ₹20,000 for emergency. I will repay double!",
            "Love, I am coming to meet you! But my wallet was stolen. Send money for ticket. UPI: jack_usa@ybl",
            "Sweetheart, I have sent you $100,000 through diplomatic bag. Pay ₹30,000 customs fee to receive it.",
        ]
    }
}


def generate_scammer_response(
    scam_type: str = "lottery",
    turn: int = 0,
    victim_response: Optional[str] = None
) -> str:
    """
    Generate a realistic scammer response
    
    Args:
        scam_type: Type of scam (lottery, tax, tech_support, job, romance)
        turn: Conversation turn number (0 = initial)
        victim_response: The victim's last message (for context)
        
    Returns:
        Scammer's message
    """
    templates = SCAMMER_TEMPLATES.get(scam_type, SCAMMER_TEMPLATES["lottery"])
    
    if turn == 0:
        return random.choice(templates["initial"])
    
    # Check victim response for triggers
    if victim_response:
        victim_lower = victim_response.lower()
        
        # If victim is hesitant
        if any(word in victim_lower for word in ["no", "not sure", "don't know", "wait", "later"]):
            urgency_responses = [
                "Sir, this is FINAL chance. After today, your prize/case will be cancelled!",
                "I understand your concern. But time is running out. Others are waiting for this opportunity!",
                "Please sir, don't delay. The system will auto-cancel in 1 hour. You will lose everything!",
                "This is genuine. I am helping you only. Why don't you trust me?",
            ]
            return random.choice(urgency_responses)
        
        # If victim asks questions
        if any(word in victim_lower for word in ["how", "what", "why", "explain", "details"]):
            explanation_responses = [
                "Sir, this is official procedure. Everyone has to pay the processing fee. It's government rule.",
                "Let me explain - your case is very serious. Only way to solve is to pay the fine amount.",
                "I have already told you everything. You just need to trust me and follow instructions.",
                "Don't worry, I will guide you step by step. First, tell me your bank account number.",
            ]
            return random.choice(explanation_responses)
        
        # If victim shares info or seems interested
        if any(word in victim_lower for word in ["ok", "yes", "sure", "tell me", "interested", "help"]):
            extraction_responses = templates["followup"]
            return random.choice(extraction_responses)
    
    # Default followup response
    return random.choice(templates["followup"])


@router.get("/mock/scammer/message")
async def get_scammer_message(
    scam_type: str = Query("lottery", description="Type of scam"),
    turn: int = Query(0, description="Conversation turn"),
    victim_response: Optional[str] = Query(None, description="Victim's last message")
) -> dict:
    """
    Generate a mock scammer message
    
    Used for testing and demos
    """
    message = generate_scammer_response(scam_type, turn, victim_response)
    
    return {
        "scam_type": scam_type,
        "turn": turn,
        "message": message,
        "metadata": {
            "sender": "+91-9876543210",
            "platform": "whatsapp"
        }
    }


@router.get("/mock/scammer/templates")
async def get_templates() -> dict:
    """Get all available scam templates"""
    return {
        scam_type: {
            "initial_count": len(templates["initial"]),
            "followup_count": len(templates["followup"])
        }
        for scam_type, templates in SCAMMER_TEMPLATES.items()
    }


@router.get("/mock/conversation/simulate")
async def simulate_conversation(
    scam_type: str = Query("lottery", description="Type of scam"),
    turns: int = Query(5, description="Number of turns to simulate")
) -> dict:
    """
    Simulate a full scammer conversation
    
    Returns both scammer messages and simulated victim responses
    """
    conversation = []
    
    # Simulated victim responses (naive)
    victim_responses = [
        None,  # First turn, no victim response yet
        "What is this? How did I win?",
        "I'm not sure about this. Is it genuine?",
        "Ok, tell me what to do.",
        "I don't have that much money right now.",
        "Let me think about it.",
        "My son/daughter told me not to pay strangers.",
    ]
    
    for i in range(turns):
        victim_msg = victim_responses[i] if i < len(victim_responses) else "I need to check with my family."
        scammer_msg = generate_scammer_response(scam_type, i, victim_msg if i > 0 else None)
        
        if i > 0:
            conversation.append({
                "turn": i,
                "role": "victim",
                "message": victim_msg
            })
        
        conversation.append({
            "turn": i,
            "role": "scammer",
            "message": scammer_msg
        })
    
    return {
        "scam_type": scam_type,
        "turns": len(conversation),
        "conversation": conversation
    }
