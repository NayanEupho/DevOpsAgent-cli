import asyncio
from src.intelligence.registry import IntelligenceRegistry
from loguru import logger

async def debug_init():
    logger.info("Starting Registry Initialization Debug...")
    reg = IntelligenceRegistry.get_instance()
    try:
        await reg.initialize()
        logger.info("Registry Initialized Successfully.")
        await reg.shutdown()
    except Exception as e:
        logger.error(f"Registry Initialization Failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_init())
