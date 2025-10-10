import httpx
import asyncio


async def test_api():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"Health: {response.json()}\n")
        
        print("Testing collection info...")
        response = await client.get(f"{base_url}/collection/info")
        print(f"Collection: {response.json()}\n")
        
        print("Testing query endpoint...")
        query = {
            "question": "Vad är årets resultat för BRF Fribergsgatan?",
            "include_sources": True
        }
        response = await client.post(f"{base_url}/query", json=query)
        result = response.json()
        print(f"Question: {result['question']}")
        print(f"Answer: {result['answer'][:200]}...\n")
        if result.get('sources'):
            print("Sources:")
            for source in result['sources'][:3]:
                print(f"  - {source['brf_name']} (Page {source['page_number']})")
        
        print("\n" + "="*80 + "\n")
        
        print("Testing chat endpoint...")
        chat_msg = {
            "message": "Hur ser soliditeten ut?"
        }
        response = await client.post(f"{base_url}/chat", json=chat_msg)
        result = response.json()
        print(f"Message: {result['message']}")
        print(f"Response: {result['response'][:200]}...")


if __name__ == "__main__":
    asyncio.run(test_api())
