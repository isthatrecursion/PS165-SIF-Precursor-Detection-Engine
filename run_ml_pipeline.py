"""
Run after ML packages are installed.
Executes the full Stage 2 ML training pipeline then re-scores all reports.
Run from Prototype 165 root:
    backend\\venv\\Scripts\\python run_ml_pipeline.py
"""
import sys, os, subprocess, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ROOT, "backend", "venv", "Scripts", "python.exe")

# ── 1. Train the model ────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  STEP 1: Training Stage 2 DistilBERT + XGBoost pipeline")
print("=" * 60)
train_result = subprocess.run(
    [PYTHON, os.path.join(ROOT, "ml", "scripts", "train_stage2.py")],
    cwd=ROOT,
    encoding="utf-8",
    errors="replace",
)

if train_result.returncode != 0:
    print("\n[ERROR] Training failed. Check output above.")
    sys.exit(1)

print("\n[OK] Training complete.")

# ── 2. Re-score all reports with trained model ────────────────────────────────
print()
print("=" * 60)
print("  STEP 2: Re-scoring all reports with trained model")
print("=" * 60)

import asyncio
import os
sys.path.insert(0, os.path.join(ROOT, "backend"))

async def rescore():
    from app.pipeline.stage2_runner import run_stage2_batch
    # Clear existing Stage 2 scores first
    from app.db.database import AsyncSessionLocal
    from app.db.models import Prediction
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Prediction)
            .where(Prediction.stage1_flagged == True)
            .values(sif_flag=None, calibrated_prob=None, confidence_band=None,
                    operational_state=None, shap_values=None, ig_spans=None,
                    ood_score=None)
        )
        await db.commit()
        print("  Cleared old heuristic scores.")

    result = await run_stage2_batch(limit=1000)
    print(f"  Scored: {result['scored']} / {result['total']} reports")

# Change directory to backend so sqlite db path resolves correctly
os.chdir(os.path.join(ROOT, "backend"))
asyncio.run(rescore())

print()
print("=" * 60)
print("  DONE. Refresh http://localhost:5173 to see ML-powered scores.")
print("=" * 60)
