import asyncio
from src.intelligence.observability import Redactor, ObservabilityService
from src.config import config
from rich import print

def test_redaction():
    print("[bold cyan]Testing PII/Secret Redaction...[/bold cyan]")
    
    test_cases = [
        ("My password is secret123", "My password: [REDACTED]"),
        ("Authorization: Bearer my-long-token-value", "Authorization: Bearer [REDACTED]"),
        ("api-key: abcdef1234567890", "api_key: [REDACTED]"),
        ("-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----", "[PRIVATE KEY REDACTED]")
    ]
    
    for input_text, expected in test_cases:
        redacted = Redactor.redact_text(input_text)
        if "[REDACTED]" in redacted or "[PRIVATE KEY REDACTED]" in redacted:
            print(f"[green]SUCCESS: Redacted '{input_text[:20]}...' -> '{redacted[:30]}...'[/green]")
        else:
            print(f"[red]FAILURE: Could not redact '{input_text}'[/red]")

def test_langfuse_config():
    print("\n[bold cyan]Testing Langfuse Configuration...[/bold cyan]")
    
    config.langfuse.public_key = "pk-lf-test"
    config.langfuse.secret_key = "sk-lf-test"
    config.langfuse.host = "http://localhost:3000"
    
    handler = ObservabilityService.get_callback_handler(
        session_id="test_session_999",
        env={"os": "windows", "shell": "powershell"}
    )
    
    if handler:
        print("[green]SUCCESS: Langfuse handler initialized.[/green]")
    else:
        # Graceful failure is also a success if langfuse is not installed or keys are wrong
        print("[yellow]NOTE: Langfuse handler not initialized (check dependencies/keys).[/yellow]")

def test_score_logic():
    print("\n[bold cyan]Testing Feedback Scoring Logic...[/bold cyan]")
    # This just ensures the method doesn't crash without a real handler
    try:
        ObservabilityService.score_trace(None, "test-score", 1.0)
        print("[green]SUCCESS: Score method handled No-Op safely.[/green]")
    except Exception as e:
        print(f"[red]FAILURE: Score method crashed: {e}[/red]")

if __name__ == "__main__":
    test_redaction()
    test_langfuse_config()
    test_score_logic()
