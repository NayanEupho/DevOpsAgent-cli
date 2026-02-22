from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional
from loguru import logger

class OllamaConfig(BaseSettings):
    host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    model: str = Field(default="devstral:24b", alias="OLLAMA_MODEL")
    temperature: float = Field(default=0.3, alias="OLLAMA_TEMPERATURE")
    context_size: int = Field(default=32768, alias="OLLAMA_CONTEXT_SIZE")
    timeout: int = Field(default=120, alias="OLLAMA_TIMEOUT")
    use_proxy: bool = Field(default=False, alias="USE_PROXY")
    http_proxy: Optional[str] = Field(default=None, alias="HTTP_PROXY")
    https_proxy: Optional[str] = Field(default=None, alias="HTTPS_PROXY")
    no_proxy: str = Field(default="localhost,127.0.0.1", alias="NO_PROXY")
    
    # FastPath / Reflexive Model Configuration
    fast_path_enabled: bool = Field(default=True, alias="FAST_PATH_ENABLED")
    fast_path_model: str = Field(default="llama3.2:3b", alias="FAST_PATH_MODEL")
    fast_path_host: str = Field(default="http://localhost:11434", alias="FAST_PATH_HOST")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class AgentConfig(BaseSettings):
    name: str = Field(default="devops-agent", alias="AGENT_NAME")
    gcc_base_path: str = Field(default="./.GCC", alias="GCC_BASE_PATH")
    skills_path: str = Field(default="./skills", alias="SKILLS_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class LangfuseConfig(BaseSettings):
    public_key: Optional[str] = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    secret_key: Optional[str] = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    host: str = Field(default="http://localhost:3000", alias="LANGFUSE_HOST")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class Config:
    def __init__(self):
        self.ollama = OllamaConfig()
        self.agent = AgentConfig()
        self.langfuse = LangfuseConfig()
        
        # Ensure GCC path exists
        Path(self.agent.gcc_base_path).mkdir(parents=True, exist_ok=True)
        
        # Configure Proxy Settings
        import os
        if self.ollama.use_proxy:
            if self.ollama.http_proxy:
                os.environ["HTTP_PROXY"] = self.ollama.http_proxy
            if self.ollama.https_proxy:
                os.environ["HTTPS_PROXY"] = self.ollama.https_proxy
            os.environ["NO_PROXY"] = self.ollama.no_proxy
            logger.info("Proxy enabled. HTTP_PROXY and HTTPS_PROXY set.")
        else:
            # Clear proxy environment variables if they were set in the parent process
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)
            # We still set NO_PROXY as it's harmless even without a proxy
            os.environ["NO_PROXY"] = self.ollama.no_proxy
            logger.info("Proxy disabled. Cleared HTTP_PROXY and HTTPS_PROXY.")
        
        logger.info(f"Config: Set NO_PROXY={self.ollama.no_proxy}")

config = Config()
