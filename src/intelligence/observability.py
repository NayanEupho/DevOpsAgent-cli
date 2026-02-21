import re
import os
from typing import Any, Dict, List, Optional
from loguru import logger
from src.config import config

class Redactor:
    """Masks secrets and PII from strings and dicts. Uses hybrid Trie+Regex for performance."""
    PATTERNS = [
        (re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-\._~+/]+=*"), "Bearer [REDACTED]"),
        (re.compile(r"(?i)api[-_]?key[\"']?[:=]\s*[\"']?([a-zA-Z0-9\-_]{10,})[\"']?"), "api_key: [REDACTED]"),
        (re.compile(r"(?i)password\s+(?:is\s+)?[\"']?([^\"'\s}]+)[\"']?"), "password: [REDACTED]"),
        (re.compile(r"(?i)password[\"']?[:=]\s*[\"']?([^\"'\s}]+)[\"']?"), "password: [REDACTED]"),
        (re.compile(r"(?i)token[\"']?[:=]\s*[\"']?([a-zA-Z0-9\-_]{10,})[\"']?"), "token: [REDACTED]"),
        (re.compile(r"-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----.*?-----END ([A-Z ]+ )?PRIVATE KEY-----", re.DOTALL), "[PRIVATE KEY REDACTED]"),
        # Phase 16 Specific: Multi-line obfuscation hardening (Run before generic)
        (re.compile(r"(?i)(?:key|secret|token)\s*[\n\r]+\s*[:=]\s*[^\s]+"), "[OBFUSCATED_SECRET_REDACTED]"),
        # Phase 13 Hardening
        (re.compile(r"(?P<key>[A-Za-z0-9+/]{100,}=*)"), "[BASE64_BLOB_REDACTED]"), 
        (re.compile(r"(?i)(?:SECRET|PASSWORD|TOKEN|KEY|CREDENTIALS|ACCESS_KEY|SECRET_KEY)\s*[:=]\s*[^\s,]+"), "credentials: [REDACTED]"),
        (re.compile(r"(?i)[\"']?client[-_]secret[\"']?\s*[:=]\s*[\"']?[^\"'\s,]+[\"']?"), "client_secret: [REDACTED]")
    ]

    @classmethod
    def redact_text(cls, text: str) -> str:
        if not text: return text
        
        # Expert Hardening: Iterative redaction for nested patterns
        for _ in range(2): # Double pass for nested secrets
            for pattern, replacement in cls.PATTERNS:
                text = pattern.sub(replacement, text)
        return text

    @classmethod
    def redact_dict(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: cls.redact_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact_dict(i) for i in data]
        elif isinstance(data, str):
            return cls.redact_text(data)
        return data

class Sanitizer:
    """Neutralizes adversarial content in tool outputs (Prompt Injection prevention)."""
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    ADVERSARIAL_PATTERNS = [
        re.compile(r"(?i)ignore\s+previous\s+instructions"),
        re.compile(r"(?i)system\s+prompt\s+override"),
        re.compile(r"(?i)you\s+are\s+now"),
        re.compile(r"(?i)instead\s+of"),
        re.compile(r"(?i)disregard\s+all\s+rules"),
        re.compile(r"(?i)new\s+role\s+assigned"),
        re.compile(r"(?i)<script\b[^>]*>.*?</script>"), # Basic HTML injection
        re.compile(r"(?i)DAN\s*mode") # Common jailbreak keyword
    ]
    
    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text: return text
        
        # 1. Expert Hardening: Strip ANSI escape sequences (ANSI Log Poisoning prevention)
        text = cls.ANSI_ESCAPE.sub('', text)
        
        # 2. Adversarial Pattern Neutralization
        for pattern in cls.ADVERSARIAL_PATTERNS:
            if pattern.search(text):
                logger.warning(f"Sanitization: Adversarial pattern detected: '{pattern.pattern}'")
                text = pattern.sub(lambda m: f"[ADVERSARIAL_FILTERED: {m.group(0)}]", text)
        
        # 3. Expert Hardening: Neutralize shell command injection in reports
        text = text.replace("$(", "$_(").replace("`", "'")
        
        return text

class ObservabilityService:
    @classmethod
    def get_callback_handler(cls, session_id: str, env: Dict[str, Any]):
        """Returns a Langfuse callback handler with fallback and PII protection."""
        if not config.langfuse.public_key or not config.langfuse.secret_key:
            logger.warning("Observability: Langfuse keys missing. Tracing disabled.")
            return None

        try:
            # Set environment variables so the internal Langfuse client picks them up
            os.environ["LANGFUSE_PUBLIC_KEY"] = config.langfuse.public_key or ""
            os.environ["LANGFUSE_SECRET_KEY"] = config.langfuse.secret_key or ""
            os.environ["LANGFUSE_HOST"] = config.langfuse.host
            
            from langfuse.langchain import CallbackHandler
            
            # Initialize handler - it reads from env vars automatically
            handler = CallbackHandler(
                public_key=config.langfuse.public_key
            )
            
            # Implementation of robust PII masking for Langfuse
            original_on_llm_end = handler.on_llm_end
            
            def safe_on_llm_end(response, *args, **kwargs):
                # Redact before Langfuse processes the output
                redacted_response = Redactor.redact_dict(response)
                return original_on_llm_end(redacted_response, *args, **kwargs)
            
            handler.on_llm_end = safe_on_llm_end
            
            logger.info(f"Observability: Langfuse tracing active for session {session_id}")
            return handler
            
        except ImportError as e:
            logger.error(f"Observability: 'langfuse' package or its dependencies not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Observability: Failed to initialize Langfuse: {e}")
            return None

    @staticmethod
    def score_trace(handler, name: str, value: float, comment: Optional[str] = None):
        """Send feedback scores to Langfuse."""
        if not handler:
            return
            
        try:
            # Langfuse LangChain handler (CallbackHandler) uses .client instead of .langfuse
            client = getattr(handler, "client", None) or getattr(handler, "langfuse", None)
            
            if client:
                # Try multiple possible method names for different Langfuse SDK versions
                score_method = getattr(client, "score", getattr(client, "score_trace", getattr(client, "create_score", None)))
                if score_method:
                    score_method(
                        name=name,
                        value=value,
                        comment=comment,
                        trace_id=handler.get_trace_id() if hasattr(handler, 'get_trace_id') else None
                    )
                    logger.info(f"Observability: Logged feedback '{name}' = {value}")
                else:
                    logger.warning(f"Observability: Found Langfuse client but no score/score_trace/create_score method. Methods: {dir(client)}")
            else:
                logger.warning("Observability: Could not find Langfuse client on handler.")
        except Exception as e:
            logger.error(f"Observability: Failed to score trace: {e}")
