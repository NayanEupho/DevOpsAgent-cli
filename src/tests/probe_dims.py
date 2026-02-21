import asyncio
from langchain_ollama import OllamaEmbeddings
from src.config import config

async def probe_dims():
    embeddings = OllamaEmbeddings(
        model=config.ollama.embedding_model,
        base_url=config.ollama.host
    )
    vec = embeddings.embed_query("test")
    print(f"MODEL: {config.ollama.embedding_model}")
    print(f"DIMENSION: {len(vec)}")

if __name__ == "__main__":
    asyncio.run(probe_dims())
