import asyncio
import os
import sys

# Add backend to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))

async def reset_db():
    from app.db.database import engine, Base
    async with engine.begin() as conn:
        print("Dropping tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database reset complete.")

async def ingest_synthetic():
    from app.db.database import AsyncSessionLocal
    from app.pipeline.ingestion_service import ingestion_service
    
    file_path = os.path.abspath(os.path.join("..", "data", "synthetic", "synthetic_oilgas_3000.jsonl"))
    print(f"Reading {file_path}...")
    with open(file_path, "rb") as f:
        content = f.read()
        
    print(f"Ingesting {len(content)} bytes...")
    async with AsyncSessionLocal() as db:
        res = await ingestion_service.ingest_file(
            file_content=content,
            filename="synthetic_oilgas_3000.jsonl",
            db=db,
        )
        print(f"Ingested! Result: {res}")

async def main():
    await reset_db()
    await ingest_synthetic()
    print("Done. Now you should run run_ml_pipeline.py to compute stage 2 scores.")

if __name__ == "__main__":
    asyncio.run(main())
