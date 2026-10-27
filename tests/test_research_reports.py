"""
卖方研报采集、PDF 原文链接与‘听话听音’潜台词量化分析单元测试套件
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.parsers.research_report_collector import (
    ResearchReportCollector,
    ResearchReportItem
)
from src.analysis.between_the_lines_analyzer import (
    BetweenTheLinesAnalyzer,
    BetweenTheLinesResult,
    SUBTEXT_LEXICON
)
from src.storage.lakehouse import LakehouseManager


class TestResearchReportCollector:
    """研报采集与湖仓持久化测试"""

    def test_collector_init(self, tmp_path):
        lakehouse = LakehouseManager(data_dir=tmp_path)
        collector = ResearchReportCollector(lakehouse=lakehouse)
        assert collector.reports_path == tmp_path / "research" / "research_reports.parquet"
        assert collector.research_dir.exists()

    def test_safe_float_conversion(self):
        collector = ResearchReportCollector()
        assert collector._safe_float("12.34") == 12.34
        assert collector._safe_float(5.6) == 5.6
        assert collector._safe_float("") is None
        assert collector._safe_float(None) is None
        assert collector._safe_float("invalid") is None

    @patch("requests.get")
    def test_fetch_stock_reports_mock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "infoCode": "AP20261027001",
                    "stockCode": "600519",
                    "stockName": "贵州茅台",
                    "title": "贵州茅台：三季度经营稳健，超预期展现强劲韧性",
                    "orgSName": "中金公司",
                    "researcher": "王汉锋, 樊俊豪",
                    "sRatingName": "跑赢行业",
                    "publishDate": "2026-10-25 18:00:00",
                    "predictThisYearEps": "68.5",
                    "predictThisYearPe": "24.5",
                    "predictNextYearEps": "78.2",
                    "predictNextYearPe": "21.5",
                    "count": 12,
                    "indvInduName": "白酒"
                }
            ]
        }
        mock_get.return_value = mock_resp

        collector = ResearchReportCollector()
        items = collector.fetch_stock_reports("600519", limit=1)

        assert len(items) == 1
        item = items[0]
        assert item.report_id == "AP20261027001"
        assert item.symbol == "600519"
        assert item.wind_code == "600519.SH"
        assert item.stock_name == "贵州茅台"
        assert item.org_name == "中金公司"
        assert item.predict_eps_this_year == 68.5
        assert item.pdf_url == "https://pdf.dfcfw.com/pdf/H3_AP20261027001_1.pdf"

    def test_sync_reports_to_lakehouse(self, tmp_path):
        lakehouse = LakehouseManager(data_dir=tmp_path)
        collector = ResearchReportCollector(lakehouse=lakehouse)

        sample_reports = [
            ResearchReportItem(
                report_id="TEST001",
                symbol="600519",
                wind_code="600519.SH",
                stock_name="贵州茅台",
                title="三季度经营承压，静待复苏拐点",
                org_name="中信证券",
                analyst_name="测试分析师",
                rating="买入",
                publish_date="2026-10-26",
                predict_eps_this_year=65.0,
                predict_pe_this_year=25.0,
                predict_eps_next_year=72.0,
                predict_pe_next_year=22.5,
                recent_month_reports_count=5,
                pdf_url="https://pdf.dfcfw.com/pdf/H3_TEST001_1.pdf",
                industry="白酒"
            )
        ]

        with patch.object(collector, "fetch_latest_market_reports", return_value=[]):
            with patch.object(collector, "fetch_stock_reports", return_value=sample_reports):
                count = collector.sync_reports_to_lakehouse(symbols=["600519"])
                assert count == 1
                assert collector.reports_path.exists()

                # 校验 Lakehouse 读取
                df = lakehouse.get_stock_reports("600519")
                assert not df.empty
                assert df.iloc[0]["symbol"] == "600519"
                assert df.iloc[0]["pdf_url"] == "https://pdf.dfcfw.com/pdf/H3_TEST001_1.pdf"


class TestBetweenTheLinesAnalyzer:
    """‘听话听音’语义与一致预期量化模型测试"""

    def test_subtext_lexicon_integrity(self):
        """校验潜台词词典完整性与权重符号约定"""
        cautious_rules = [r for r in SUBTEXT_LEXICON if r.category == "cautious"]
        bullish_rules = [r for r in SUBTEXT_LEXICON if r.category == "bullish"]
        neutral_rules = [r for r in SUBTEXT_LEXICON if r.category == "neutral"]

        assert len(cautious_rules) >= 15
        assert len(bullish_rules) >= 10
        assert len(neutral_rules) >= 3

        # 警示词权重必须严格为负，做多词必须严格为正
        for r in cautious_rules:
            assert r.weight < 0, f"警示词 {r.keyword} 权重必须为负"
        for r in bullish_rules:
            assert r.weight > 0, f"做多词 {r.keyword} 权重必须为正"

    def test_subtext_analysis_cautious_warning(self, tmp_path):
        """测试表面给予买入，但标题密集踩刹车的潜台词识别"""
        lakehouse = LakehouseManager(data_dir=tmp_path)
        # 写入包含踩刹车特征的虚拟研报数据
        df_fake = pd.DataFrame([
            {
                "report_id": "R001",
                "symbol": "300750",
                "wind_code": "300750.SZ",
                "stock_name": "宁德时代",
                "title": "宁德时代：出货量维持高增，短期盈利承压，静待拐点",
                "org_name": "某知名券商",
                "analyst_name": "张三",
                "rating": "买入",
                "publish_date": "2026-10-26",
                "predict_eps_this_year": 12.0,
                "predict_pe_this_year": 20.0,
                "predict_eps_next_year": 14.5,
                "predict_pe_next_year": 16.5,
                "recent_month_reports_count": 8,
                "pdf_url": "https://pdf.dfcfw.com/pdf/H3_R001_1.pdf",
                "industry": "动力电池"
            },
            {
                "report_id": "R002",
                "symbol": "300750",
                "wind_code": "300750.SZ",
                "stock_name": "宁德时代",
                "title": "行业进入去库周期，短期毛利承压，关注后续验证",
                "org_name": "另一家头部券商",
                "analyst_name": "李四",
                "rating": "增持",
                "publish_date": "2026-10-25",
                "predict_eps_this_year": 11.5,
                "predict_pe_this_year": 21.0,
                "predict_eps_next_year": 13.8,
                "predict_pe_next_year": 17.5,
                "recent_month_reports_count": 8,
                "pdf_url": "https://pdf.dfcfw.com/pdf/H3_R002_1.pdf",
                "industry": "动力电池"
            }
        ])

        reports_path = lakehouse.research_dir / "research_reports.parquet"
        df_fake.to_parquet(reports_path, index=False)

        analyzer = BetweenTheLinesAnalyzer(lakehouse=lakehouse)
        res = analyzer.analyze("300750", auto_fetch=False)

        # 潜台词得分应当显著为负
        assert res.subtext_tone_score < 0
        assert "表面买入实则谨慎" in res.tone_level or "预警" in res.tone_level
        assert len(res.cautious_hits) >= 2
        # 检验是否命中'盈利承压'、'静待拐点'或'去库周期'
        hit_keywords = [h["keyword"] for h in res.cautious_hits]
        assert "盈利承压" in hit_keywords or "静待拐点" in hit_keywords or "去库周期" in hit_keywords
        # 检验买方人话预警
        assert len(res.subtext_warnings) > 0
        assert "听话听音预警" in res.subtext_warnings[0]
        # 检验一致预期与分歧度
        assert res.consensus_eps_this_year == 11.75
        assert res.eps_divergence_std is not None

    def test_subtext_analysis_bullish(self, tmp_path):
        """测试真金白银超预期做多信号识别"""
        lakehouse = LakehouseManager(data_dir=tmp_path)
        df_fake = pd.DataFrame([
            {
                "report_id": "R003",
                "symbol": "600519",
                "wind_code": "600519.SH",
                "stock_name": "贵州茅台",
                "title": "业绩大超预期，量价齐升拐点确立，重申买入",
                "org_name": "旗舰券商",
                "analyst_name": "首席",
                "rating": "强烈推荐",
                "publish_date": "2026-10-26",
                "predict_eps_this_year": 70.0,
                "predict_pe_this_year": 22.0,
                "predict_eps_next_year": 82.0,
                "predict_pe_next_year": 18.5,
                "recent_month_reports_count": 15,
                "pdf_url": "https://pdf.dfcfw.com/pdf/H3_R003_1.pdf",
                "industry": "白酒"
            }
        ])

        reports_path = lakehouse.research_dir / "research_reports.parquet"
        df_fake.to_parquet(reports_path, index=False)

        analyzer = BetweenTheLinesAnalyzer(lakehouse=lakehouse)
        res = analyzer.analyze("600519", auto_fetch=False)

        assert res.subtext_tone_score > 30
        assert "极度看多" in res.tone_level or "真看多" in res.tone_level
        assert len(res.bullish_hits) >= 2
        hit_keywords = [h["keyword"] for h in res.bullish_hits]
        assert "大超预期" in hit_keywords or "量价齐升" in hit_keywords or "拐点确立" in hit_keywords
        assert "真金白银看好" in res.subtext_warnings[0]
