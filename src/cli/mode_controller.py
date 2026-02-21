import os
import subprocess
import time
import signal
from loguru import logger
from src.gcc.session import Session
from src.gcc.log import GCCLogger

class ModeController:
    def __init__(self, session: Session):
        self.session = session
        self.logger = GCCLogger(session.path)

    def enter_manual_mode(self):
        """Drops the user to a raw shell and listens for Ctrl+R to summon AI."""
        shell = "powershell.exe" if os.name == "nt" else "bash"
        logger.info(f"Entering MANUAL mode ({shell})")
        
        print("\n" + "─" * 50)
        print(f"  MANUAL MODE  ·  {self.session.id}  ·  commands are logged")
        print("  Tip: Press Ctrl+R to instantly summon the AI agent")
        print("─" * 50 + "\n")

        try:
            # Start the shell process
            process = subprocess.Popen([shell], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            
            # Listen for Ctrl+R (ASCII 18) while process is alive
            while process.poll() is None:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # Ctrl+R is ASCII 18
                    if ord(key) == 18:
                        logger.info("Ctrl+R detected. Summoning AI...")
                        process.terminate() # Kill shell
                        break
                time.sleep(0.1)
                
            process.wait() # Ensure cleanup
        except Exception as e:
            logger.error(f"Error in manual mode: {e}")
        
        self.exit_manual_mode()

    def exit_manual_mode(self):
        """Logic to run when returning to CHAT mode."""
        logger.info("Returning to CHAT mode. Running environment probes...")
        # TODO: Implement probes (Phase 5)
        print("\n" + "─" * 50)
        print("  CHAT MODE  ·  agent reviewing your manual actions")
        print("─" * 50 + "\n")
