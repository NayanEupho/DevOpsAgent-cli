import ollama
from loguru import logger
from src.config import config

class OllamaClient:
    def __init__(self):
        self.client = ollama.AsyncClient(host=config.ollama.host)
        self.model = config.ollama.model
        
    async def chat(self, messages: list, stream: bool = True):
        try:
            return await self.client.chat(
                model=self.model,
                messages=messages,
                stream=stream,
                options={
                    "temperature": config.ollama.temperature,
                    "num_ctx": config.ollama.context_size
                }
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def check_health(self):
        try:
            # Check host reachability and model availability in a single call
            models_response = await self.client.list()
            logger.info("Ollama host is reachable.")
            model_names = [m.model for m in models_response.models]
            
            # Check main LLM
            if self.model not in model_names:
                if ":" not in self.model and f"{self.model}:latest" in model_names:
                    self.model = f"{self.model}:latest"
                else:
                    logger.error(f"LLM Model '{self.model}' not found in Ollama.")
                    return False
            
            logger.info(f"Ollama model ready: LLM={self.model}")
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

ollama_client = OllamaClient()
