#!/usr/bin/env python3
"""
Demo Script - Simulates a scam conversation with the honeypot
Run this to see the system in action
"""

import asyncio
import json
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.insert(0, '.')

from app.orchestrator.honeypot_orchestrator import get_orchestrator
from app.scoring.ensemble_engine import get_ensemble_engine


# Sample scam messages for demo
DEMO_SCAM_MESSAGES = [
    {
        "scenario": "Lottery Scam",
        "messages": [
            "Congratulations! You have been selected as the lucky winner of ₹50,00,000 in our WhatsApp lottery. Reply YES to claim your prize!",
            "To claim your prize, you need to pay a small processing fee of ₹5,000. Please send it to our official UPI: lottery_dept@upi",
            "Sir, this is urgent. The prize will expire in 24 hours. Please send the fee immediately to avoid losing your winnings.",
            "Once you pay, the full amount will be transferred to your account within 1 hour. What is your bank account number?",
        ]
    },
    {
        "scenario": "Income Tax Scam",
        "messages": [
            "This is an urgent notice from the Income Tax Department. Your PAN card has been flagged for suspicious transactions. Call immediately to avoid arrest.",
            "Sir, I am Officer Sharma from IT Department. Your PAN is linked to ₹2 crore black money. You need to pay penalty of ₹50,000 to clear your name.",
            "If you don't pay now, police will come to your house within 2 hours. Give me your Aadhaar number for verification.",
            "Pay the fine using Google Pay to this number: 9876543210. This is official government procedure.",
        ]
    },
    {
        "scenario": "Tech Support Scam",
        "messages": [
            "Hello, this is Microsoft Technical Support. We detected a virus in your computer that is stealing your bank passwords.",
            "Please download TeamViewer and give us access to remove the virus. Otherwise hackers will empty your bank account.",
            "Sir, the virus is very dangerous. You need to pay ₹15,000 for our premium protection service to save your computer.",
            "I understand you're worried. Just give me your debit card number and CVV and we'll process the payment securely.",
        ]
    }
]


async def run_analysis_demo():
    """Demo: Analyze sample scam messages"""
    print("\n" + "="*60)
    print("🔍 SCAM DETECTION DEMO")
    print("="*60)
    
    engine = get_ensemble_engine()
    
    for scenario in DEMO_SCAM_MESSAGES:
        print(f"\n📋 Scenario: {scenario['scenario']}")
        print("-"*40)
        
        message = scenario['messages'][0]
        print(f"Message: {message[:100]}...")
        
        result = await engine.analyze(message)
        
        print(f"\n⚡ Results:")
        print(f"   Scam Detected: {'🚨 YES' if result.scam_detected else '✅ NO'}")
        print(f"   Risk Score: {result.risk_score:.2f}")
        print(f"   Risk Level: {result.risk_level.upper()}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Scam Type: {result.scam_type or 'Unknown'}")
        print(f"   Processing Time: {result.processing_time_ms}ms")
        
        if result.reasons:
            print(f"   Reasons:")
            for reason in result.reasons[:3]:
                print(f"      • {reason}")
        
        print()


async def run_conversation_demo():
    """Demo: Full honeypot conversation"""
    print("\n" + "="*60)
    print("🍯 HONEYPOT CONVERSATION DEMO")
    print("="*60)
    
    orchestrator = get_orchestrator()
    scenario = DEMO_SCAM_MESSAGES[0]  # Lottery scam
    
    print(f"\n📋 Scenario: {scenario['scenario']}")
    print("-"*40)
    
    # Start engagement
    print("\n🎭 Starting honeypot engagement...")
    
    result = await orchestrator.start_engagement(
        initial_message=scenario['messages'][0],
        scammer_identifier="+91-9876543210"
    )
    
    print(f"\n📱 Scammer: {scenario['messages'][0][:80]}...")
    print(f"\n🤖 Honeypot ({result.persona_used}):")
    print(f"   {result.response}")
    print(f"\n   State: {result.state}")
    print(f"   Risk Score: {result.risk_score:.2f}")
    
    if result.extracted_intel:
        print(f"   Extracted Intel: {json.dumps(result.extracted_intel, indent=6)}")
    
    # Continue conversation
    for i, message in enumerate(scenario['messages'][1:3], 2):
        print(f"\n{'='*40}")
        print(f"Turn {i}")
        print(f"{'='*40}")
        
        result = await orchestrator.continue_engagement(
            conversation_id=result.conversation_id,
            scammer_message=message
        )
        
        print(f"\n📱 Scammer: {message[:80]}...")
        print(f"\n🤖 Honeypot ({result.persona_used}):")
        print(f"   {result.response}")
        print(f"\n   State: {result.state}")
        
        if result.extracted_intel:
            print(f"   Intel Extracted: {list(result.extracted_intel.keys())}")
        
        if not result.should_continue:
            print("\n⚠️ Engagement terminated by safety system")
            break
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 ENGAGEMENT SUMMARY")
    print(f"{'='*60}")
    
    summary = orchestrator.get_conversation_summary(result.conversation_id)
    print(f"   Conversation ID: {summary.get('conversation_id')}")
    print(f"   Total Turns: {summary.get('turn_count')}")
    print(f"   Final State: {summary.get('state')}")
    print(f"   Intel Collected: {summary.get('intel_count')} items")
    print(f"   Duration: {summary.get('duration_seconds', 0):.1f} seconds")


async def run_extraction_demo():
    """Demo: Entity extraction"""
    print("\n" + "="*60)
    print("🔎 ENTITY EXTRACTION DEMO")
    print("="*60)
    
    from app.extractors.regex_extractor import get_regex_extractor
    
    extractor = get_regex_extractor()
    
    sample_text = """
    Please send the money to my UPI: scammer123@paytm or you can transfer to 
    account number 12345678901234 IFSC: SBIN0001234. For any queries call 
    +91-9876543210 or email me at fake.support@scammail.com
    
    Visit our website http://bit.ly/scam123 for more details.
    Total amount: Rs. 50,000
    """
    
    print(f"\nSample Text:\n{sample_text}")
    print(f"\n{'='*40}")
    print("Extracted Entities:")
    print(f"{'='*40}")
    
    result = extractor.extract(sample_text)
    
    for entity_type, values in result.entities.items():
        if values:
            print(f"\n   {entity_type.upper()}:")
            for value in values:
                print(f"      • {value}")
    
    print(f"\n   Overall Confidence: {result.confidence:.2f}")


async def main():
    """Run all demos"""
    print("\n" + "🍯"*30)
    print("\n   AGENTIC HONEYPOT - DEMO MODE")
    print("\n" + "🍯"*30)
    
    print(f"\n⏰ Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run extraction demo (doesn't need LLM)
        await run_extraction_demo()
        
        # Run analysis demo
        await run_analysis_demo()
        
        # Run conversation demo
        await run_conversation_demo()
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        print("   Make sure you have set GEMINI_API_KEY in your .env file")
        print("   For local LLaMA, ensure Ollama is running with llama3.1:8b model")
    
    print(f"\n✅ Demo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "🍯"*30 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
