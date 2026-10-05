import asyncio, sys, os
sys.path.insert(0, os.getcwd())

async def rescore():
    from app.pipeline.stage2_runner import run_stage2_batch
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
        print('Cleared old heuristic scores.')

    result = await run_stage2_batch(limit=1000)
    print(f"Scored: {result['scored']} / {result['total']} reports")

asyncio.run(rescore())
