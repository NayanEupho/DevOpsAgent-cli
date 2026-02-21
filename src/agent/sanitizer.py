import re

class Sanitizer:
    # ANSI escape sequence regex
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Removes ANSI escape sequences from the given text."""
        if not text:
            return ""
        return cls.ANSI_ESCAPE.sub('', text)
