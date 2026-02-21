import asyncio
from src.intelligence.registry import IntelligenceRegistry

async def sync_helm():
    print("Syncing Intelligence with new Helm skill...")
    registry = IntelligenceRegistry.get_instance()
    await registry.initialize()
    
    # 1. Sync Metadata (SQLite) - This will trigger skill discovery
    await registry.metadata.sync_skills()
    
    # 2. Vectorize the new skill
    import os
    from pathlib import Path
    helm_skill = Path("skills/helm/SKILL.md")
    if helm_skill.exists():
        with open(helm_skill, 'r') as f:
            content = f.read()
            # For simplicity, we manually trigger the vectorized context if needed, 
            # though Shadow Indexing usually catches log entries.
            # Here we want the SKILL documentation to be vectorized.
            await registry.vector.add_texts(
                [content], 
                [{"skill_name": "helm", "type": "skill_documentation"}]
            )
            print("Successfully vectorized Helm SKILL.md")
    
    await registry.shutdown()
    print("Sync complete.")

if __name__ == "__main__":
    asyncio.run(sync_helm())
