from typing import List
from src.config import config

class IntentParser:
    def __init__(self):
        # Patterns for Phase 3 - Keyword based
        self.approvals = ["y", "yes", "ok", "sure", "go", "do it", "approved", "looks good", "go ahead", "execute", "run it", "confirm", "agreed", "yep", "yup"]
        self.denials = ["n", "no", "skip", "stop", "don't", "hold", "wait", "cancel", "abort", "not yet"]
        self.explanations = ["why", "explain", "what does", "how does", "reason", "tell me", "walk me through", "what's the plan", "what did we do"]

    def parse(self, text: str) -> str:
        text = text.lower().strip()
        
        is_approve = any((word in text.split()) or (word == text) for word in self.approvals)
        is_deny = any((word in text.split()) or (word == text) for word in self.denials)
        is_explain = any(phrase in text for phrase in self.explanations)

        if is_approve and is_explain:
            return "APPROVE_EXPLAIN"
        if is_approve:
            return "APPROVE"
        if is_deny:
            return "DENY"
        if is_explain:
            return "EXPLAIN"
        
        return "AMBIGUOUS"

intent_parser = IntentParser()
