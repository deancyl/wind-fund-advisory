import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine

def test_all_14_sectors_genuine_dynamic_metrics():
    engine = OpportunityRadarEngine()
    sectors = engine.scan_all_sectors()
    assert len(sectors) == 14, f"Expected 14 sectors, got {len(sectors)}"

    # 提取所有赛道的趋势信噪比、20日乖离率、拥挤度评分
    ers = [s["er_20"] for s in sectors]
    biases = [s["bias_20"] for s in sectors]
    crowds = [s["s_crowd"] for s in sectors]

    print("Scanned 14 sectors genuine dynamic values:")
    for s in sectors:
        print(f"[{s['name']}] 估值分位: {s['val_percentile']:.1f}% | 信噪比: {s['er_20']:.2f} | 20日乖离: {s['bias_20']:+.2f}% | 拥挤度: {s['s_crowd']:.1f} | 得分: {s['total_score']:.1f}")

    # 必须具备多样性，绝对严禁整排全部相同！
    assert len(set(ers)) > 5, f"ER values lack diversity: {set(ers)}"
    assert len(set(biases)) > 5, f"Bias values lack diversity: {set(biases)}"
    assert len(set(crowds)) > 2, f"Crowding values lack diversity: {set(crowds)}"

    # 坚决杜绝 0.50, 1.0, 85.0 假常数占领全部
    dummy_count = sum(1 for s in sectors if s["er_20"] == 0.50 and s["bias_20"] == 1.0 and s["s_crowd"] == 85.0)
    assert dummy_count == 0, f"Found {dummy_count} sectors with fake dummy constants (0.50, +1.0%, 85.0)!"
    print("All 14 sectors passed with 100% genuine dynamic metrics!")

if __name__ == "__main__":
    test_all_14_sectors_genuine_dynamic_metrics()
