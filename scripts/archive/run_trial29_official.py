import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from judge_engine import JudgeEngine, DB_PATH
import islands.island_ensemble as ensemble_mod

def run_official():
    print(f"Target DB: {DB_PATH.resolve()}")
    judge = JudgeEngine(db_path=DB_PATH)
    
    strat_fn = ensemble_mod.strategy_fn
    params = ensemble_mod.PARAMS
    
    res = judge.run_judge(
        strategy_fn=strat_fn,
        strategy_name="Trial29_Ensemble_PureEndogenous",
        island_name="ensemble",
        params=params
    )
    print("\nOfficial Run Result:")
    print(res)

if __name__ == '__main__':
    run_official()
