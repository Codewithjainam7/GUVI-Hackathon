import asyncio
from app.llm.groq_client import get_groq_client
from app.llm.local_llama_client import get_local_llama_client

async def test_clients():
    print("Testing Groq...")
    try:
        groq = get_groq_client()
        res = await groq.generate_response("You are a bot.", "Say hi")
        print(f"Groq Success: {res}")
    except Exception as e:
        print(f"Groq Failed: {e}")

    print("\nTesting Local LLaMA...")
    try:
        llama = get_local_llama_client()
        res = await llama.generate("Say hi")
        print(f"LLaMA Success: {res['text']}")
    except Exception as e:
        print(f"LLaMA Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_clients())
