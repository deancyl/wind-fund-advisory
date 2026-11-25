# -*- coding: utf-8 -*-
import sys
from pathlib import Path

file_path = Path("AGY2_FundAdvisory/portfolio_manager.py")
content = file_path.read_text(encoding="utf-8")

# 1. 替换 calculate_look_through_industry_exposure
old_ind_func = '''    def calculate_look_through_industry_exposure(self) -> pd.DataFrame:
        """
        穿透计算全组合各行业的实际加权暴露比例 (%)
        """
        total_market_val = sum(h.market_value for h in self.holdings.values())
        if total_market_val <= 0:
            return pd.DataFrame(columns=["行业", "暴露金额", "暴露占比(%)"])

        industry_totals: Dict[str, float] = {}

        for code, h in self.holdings.items():
            mv = h.market_value
            if mv <= 0:
                continue

            profile = FUND_LOOK_THROUGH_DATA.get(code)
            if profile and "industries" in profile:
                ind_dict = profile["industries"]
            else:
                # 智能根据名称推断行业
                name = h.fund_name
                if any(k in name for k in ["红利", "低波", "股息"]):
                    ind_dict = {"银行与金融": 35.0, "煤炭与能源": 30.0, "公用事业": 20.0, "其他": 15.0}
                elif any(k in name for k in ["芯片", "半导体", "集成电路", "科创"]):
                    ind_dict = {"电子芯片与半导体": 75.0, "计算机与通信": 15.0, "现金": 10.0}
                elif any(k in name for k in ["债", "回报", "固收"]):
                    ind_dict = {"纯债与固定收益": 85.0, "现金与货币": 15.0}
                elif any(k in name for k in ["黄金"]):
                    ind_dict = {"黄金与贵金属": 96.0, "现金": 4.0}
                elif any(k in name for k in ["标普", "美股", "纳指"]):
                    ind_dict = {"海外科技与信息": 35.0, "海外金融与消费": 35.0, "其他": 30.0}
                else:
                    ind_dict = {"其他大盘蓝筹与成长": 80.0, "现金": 20.0}

            for ind, pct in ind_dict.items():
                amt = mv * (pct / 100.0)
                industry_totals[ind] = industry_totals.get(ind, 0.0) + amt

        rows = []
        for ind, amt in industry_totals.items():
            pct = round(amt / total_market_val * 100.0, 2)
            rows.append({"行业": ind, "暴露金额": round(amt, 2), "暴露占比(%)": pct})

        df_res = pd.DataFrame(rows).sort_values(by="暴露占比(%)", ascending=False).reset_index(drop=True)
        return df_res'''

new_ind_func = '''    def calculate_look_through_industry_exposure(
        self,
        holdings_override: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        穿透计算全组合各行业的实际加权暴露比例 (%)
        支持传入 holdings_override 自定义持仓字典进行动态穿透
        """
        target_holdings = holdings_override if holdings_override is not None else self.holdings
        total_market_val = sum(getattr(h, "market_value", 0.0) for h in target_holdings.values())
        if total_market_val <= 0:
            return pd.DataFrame(columns=["行业", "暴露金额", "暴露占比(%)"])

        industry_totals: Dict[str, float] = {}

        for code, h in target_holdings.items():
            mv = getattr(h, "market_value", 0.0)
            if mv <= 0:
                continue

            profile = FUND_LOOK_THROUGH_DATA.get(code)
            if profile and "industries" in profile and profile["industries"]:
                ind_dict = profile["industries"]
            else:
                ext_res = self._fetch_external_fund_holdings(code)
                if ext_res and "industries" in ext_res and ext_res["industries"]:
                    ind_dict = ext_res["industries"]
                else:
                    # 智能根据名称推断行业
                    name = getattr(h, "fund_name", "") or ""
                    if any(k in name for k in ["红利", "低波", "股息", "银行", "金融"]):
                        ind_dict = {"银行与金融": 50.0, "煤炭与能源": 20.0, "公用事业": 15.0, "其他": 15.0}
                    elif any(k in name for k in ["白酒", "消费", "主要消费", "食品"]):
                        ind_dict = {"主要消费与白酒": 80.0, "食品饮料": 15.0, "现金": 5.0}
                    elif any(k in name for k in ["医药", "医疗", "生物", "健康"]):
                        ind_dict = {"医药生物与健康": 85.0, "医疗器械": 10.0, "现金": 5.0}
                    elif any(k in name for k in ["芯片", "半导体", "集成电路", "科创"]):
                        ind_dict = {"电子芯片与半导体": 75.0, "计算机与通信": 15.0, "现金": 10.0}
                    elif any(k in name for k in ["债", "回报", "固收"]):
                        ind_dict = {"纯债与固定收益": 85.0, "现金与货币": 15.0}
                    elif any(k in name for k in ["黄金"]):
                        ind_dict = {"黄金与贵金属": 96.0, "现金": 4.0}
                    elif any(k in name for k in ["标普", "美股", "纳指"]):
                        ind_dict = {"海外科技与信息": 35.0, "海外金融与消费": 35.0, "其他": 30.0}
                    else:
                        ind_dict = {"其他大盘蓝筹与成长": 80.0, "现金": 20.0}

            for ind, pct in ind_dict.items():
                amt = mv * (pct / 100.0)
                industry_totals[ind] = industry_totals.get(ind, 0.0) + amt

        rows = []
        for ind, amt in industry_totals.items():
            pct = round(amt / total_market_val * 100.0, 2)
            rows.append({"行业": ind, "暴露金额": round(amt, 2), "暴露占比(%)": pct})

        df_res = pd.DataFrame(rows).sort_values(by="暴露占比(%)", ascending=False).reset_index(drop=True)
        return df_res'''

if old_ind_func in content:
    content = content.replace(old_ind_func, new_ind_func, 1)
    print("1. Successfully replaced calculate_look_through_industry_exposure")
else:
    print("1. FAILED to find calculate_look_through_industry_exposure")

# 2. 替换 calculate_stock_overlap_matrix
old_overlap = '''    def calculate_stock_overlap_matrix(self) -> Dict[str, Any]:
        """
        动态计算持仓基金间的前十大重仓股重合度矩阵与假分散风险预警
        严禁使用假股票名欺骗矩阵；未获取到重仓股的主动基明确标记为待穿透
        """
        active_funds = [code for code, h in self.holdings.items() if h.market_value > 0]'''

new_overlap = '''    def calculate_stock_overlap_matrix(
        self,
        holdings_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        动态计算持仓基金间的前十大重仓股重合度矩阵与假分散风险预警
        严禁使用假股票名欺骗矩阵；未获取到重仓股的主动基明确标记为待穿透
        支持传入 holdings_override
        """
        target_holdings = holdings_override if holdings_override is not None else self.holdings
        active_funds = [code for code, h in target_holdings.items() if getattr(h, "market_value", 0.0) > 0]'''

if old_overlap in content:
    content = content.replace(old_overlap, new_overlap, 1)
    print("2. Successfully replaced calculate_stock_overlap_matrix signature")
else:
    print("2. FAILED to find calculate_stock_overlap_matrix")

# 替换 calculate_stock_overlap_matrix 内部的 self.holdings 为 target_holdings
old_overlap_inner = '''        if len(active_funds) < 2:
            single_alerts = []
            for c in pending_external_funds:
                fund_n = self.holdings[c].fund_name if c in self.holdings else c
                single_alerts.append({
                    "fund1": c,
                    "fund2": "",
                    "overlap": 0.0,
                    "common_stocks": [],
                    "warning_msg": f"ℹ️ **待穿透外部主动基**：标的【{c} {fund_n}】暂未获取到最新前十大重仓股明细，已在重合度矩阵中独立隔离，杜绝假重合。"
                })
            return {
                "funds": active_funds,
                "matrix": np.array([[1.0]]),
                "alerts": single_alerts,
                "pending_external_funds": pending_external_funds,
                "max_non_diag_unexcused": 0.0
            }

        fund_labels = [f"{c} {self.holdings[c].fund_name[:6]}" for c in active_funds]'''

new_overlap_inner = '''        if len(active_funds) < 2:
            single_alerts = []
            for c in pending_external_funds:
                fund_n = getattr(target_holdings[c], "fund_name", c) if c in target_holdings else c
                single_alerts.append({
                    "fund1": c,
                    "fund2": "",
                    "overlap": 0.0,
                    "common_stocks": [],
                    "warning_msg": f"ℹ️ **待穿透外部主动基**：标的【{c} {fund_n}】暂未获取到最新前十大重仓股明细，已在重合度矩阵中独立隔离，杜绝假重合。"
                })
            return {
                "funds": [f"{c} {getattr(target_holdings.get(c), 'fund_name', c)[:6]}" for c in active_funds] if active_funds else [],
                "matrix": np.array([[1.0]]) if active_funds else np.zeros((0, 0)),
                "alerts": single_alerts,
                "pending_external_funds": pending_external_funds,
                "max_non_diag_unexcused": 0.0
            }

        fund_labels = [f"{c} {getattr(target_holdings.get(c), 'fund_name', c)[:6]}" for c in active_funds]'''

if old_overlap_inner in content:
    content = content.replace(old_overlap_inner, new_overlap_inner, 1)
    print("3. Successfully replaced calculate_stock_overlap_matrix inner")
else:
    print("3. FAILED to find calculate_stock_overlap_matrix inner")

# 替换 pending_external_funds 循环中的 self.holdings
old_ext_loop = '''        for c in pending_external_funds:
            fund_n = self.holdings[c].fund_name if c in self.holdings else c'''
new_ext_loop = '''        for c in pending_external_funds:
            fund_n = getattr(target_holdings[c], "fund_name", c) if c in target_holdings else c'''
if old_ext_loop in content:
    content = content.replace(old_ext_loop, new_ext_loop, 1)
    print("4. Successfully replaced pending_external_funds loop")

# 3. 替换 get_portfolio_look_through_stocks & get_portfolio_look_through_stocks_df
old_stocks_func = '''    def get_portfolio_look_through_stocks(self, as_df: bool = False) -> Any:
        """
        生成组合底层重仓股穿透排雷大宽表（按股票代码聚合去重）
        - 按股票代码/标的聚合为唯一行
        - “所属基金”列改为“关联持仓基金（列出持有该股的所有基金代码）”
        - 新增“占组合总市值比例(%)”列，按组合持仓占比降序排列
        """
        active_holdings = [h for h in self.holdings.values() if h.market_value > 0]'''

new_stocks_func = '''    def get_portfolio_look_through_stocks(
        self,
        as_df: bool = False,
        holdings_override: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        生成组合底层重仓股穿透排雷大宽表（按股票代码聚合去重）
        - 按股票代码/标的聚合为唯一行
        - “所属基金”列改为“关联持仓基金（列出持有该股的所有基金代码）”
        - 新增“占组合总市值比例(%)”列，按组合持仓占比降序排列
        """
        target_holdings = holdings_override if holdings_override is not None else self.holdings
        active_holdings = [h for h in target_holdings.values() if getattr(h, "market_value", 0.0) > 0]'''

if old_stocks_func in content:
    content = content.replace(old_stocks_func, new_stocks_func, 1)
    print("5. Successfully replaced get_portfolio_look_through_stocks")
else:
    print("5. FAILED to find get_portfolio_look_through_stocks")

old_stocks_df = '''    def get_portfolio_look_through_stocks_df(self) -> pd.DataFrame:
        """返回 DataFrame 格式的底层重仓股穿透排雷大宽表"""
        return self.get_portfolio_look_through_stocks(as_df=True)'''

new_stocks_df = '''    def get_portfolio_look_through_stocks_df(
        self,
        holdings_override: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """返回 DataFrame 格式的底层重仓股穿透排雷大宽表"""
        return self.get_portfolio_look_through_stocks(as_df=True, holdings_override=holdings_override)'''

if old_stocks_df in content:
    content = content.replace(old_stocks_df, new_stocks_df, 1)
    print("6. Successfully replaced get_portfolio_look_through_stocks_df")

# 4. 替换 calculate_portfolio_penetration_risk
old_risk = '''    def calculate_portfolio_penetration_risk(self) -> Dict[str, Any]:
        """
        计算当前持仓投资组合的整体加权穿透风险指数 (Portfolio Penetration Risk Index: 0.0 ~ 100.0)

        计算规则:
        - 按各持仓基金在组合总市值中的实际权重进行加权平均:
          portfolio_risk_index = sum(weight * fund_risk_score)
        - 穿透风控分级标准:
          * <= 20.0 且无 🔴 预警标的: 🟢 健康 (Safe)
          * 20.0 ~ 45.0 或存在 1 只 🔴 预警标的: 🟡 关注 (Watch)
          * > 45.0 或存在 >= 2 只 🔴 预警标的: 🔴 预警 (Danger)
        """
        active_holdings = [h for h in self.holdings.values() if h.market_value > 0]'''

new_risk = '''    def calculate_portfolio_penetration_risk(
        self,
        holdings_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算当前持仓投资组合的整体加权穿透风险指数 (Portfolio Penetration Risk Index: 0.0 ~ 100.0)

        计算规则:
        - 按各持仓基金在组合总市值中的实际权重进行加权平均:
          portfolio_risk_index = sum(weight * fund_risk_score)
        - 穿透风控分级标准:
          * <= 20.0 且无 🔴 预警标的: 🟢 健康 (Safe)
          * 20.0 ~ 45.0 或存在 1 只 🔴 预警标的: 🟡 关注 (Watch)
          * > 45.0 或存在 >= 2 只 🔴 预警标的: 🔴 预警 (Danger)
        """
        target_holdings = holdings_override if holdings_override is not None else self.holdings
        active_holdings = [h for h in target_holdings.values() if getattr(h, "market_value", 0.0) > 0]'''

if old_risk in content:
    content = content.replace(old_risk, new_risk, 1)
    print("7. Successfully replaced calculate_portfolio_penetration_risk")

# 5. 替换 classify_fund_asset_class 统一为 classmethod
old_classify_header = '''    def classify_fund_asset_class(
        self,
        fund_code: Optional[str] = None,
        fund_name: Optional[str] = None
    ) -> str:
        """
        全局统一资产分类解析器 (Unified Fund Asset Class Classifier)
        根据基金代码、基金名称、跟踪指数、投资类型与底层重仓行业，
        自动将任意基金动态归类至 9 大标准资产类别之一：
        - "纯债固收"
        - "黄金对冲"
        - "美股海外对冲"
        - "A股红利高股息"
        - "A股红利低波"
        - "科技成长进攻"
        - "中小盘成长"
        - "中盘均衡"
        - "核心蓝筹"
        无法识别兜底为 "其他权益资产"（严禁输出 "其他存量资产"）。
        支持类级别与实例级别灵活调用。
        """
        if not isinstance(self, PortfolioManager):
            actual_code = str(self)
            actual_name = fund_code if isinstance(fund_code, str) else None
            return PortfolioManager()._do_classify_asset_class(actual_code, actual_name)
        return self._do_classify_asset_class(str(fund_code or ""), fund_name)

    def _do_classify_asset_class(
        self,
        fund_code: str,
        fund_name: Optional[str] = None
    ) -> str:
        code = str(fund_code or "").strip().zfill(6) if fund_code else ""
        name = str(fund_name or "").strip()
        cache_key = (code, name)
        if cache_key in _CLASSIFY_ASSET_CLASS_CACHE:
            return _CLASSIFY_ASSET_CLASS_CACHE[cache_key]

        res = self._compute_asset_class_category(code, name)
        _CLASSIFY_ASSET_CLASS_CACHE[cache_key] = res
        if code and (code, "") not in _CLASSIFY_ASSET_CLASS_CACHE:
            _CLASSIFY_ASSET_CLASS_CACHE[(code, "")] = res
        return res

    def _compute_asset_class_category(
        self,
        code: str,
        name: str
    ) -> str:'''

new_classify_header = '''    @classmethod
    def classify_fund_asset_class(
        cls,
        fund_code: Optional[str] = None,
        fund_name: Optional[str] = None
    ) -> str:
        """
        全局统一资产分类解析器 (Unified Fund Asset Class Classifier)
        根据基金代码、基金名称、跟踪指数、投资类型与底层重仓行业，
        自动将任意基金动态归类至标准资产类别。
        支持类级别与实例级别灵活调用。
        """
        return cls._do_classify_asset_class(str(fund_code or ""), fund_name)

    @classmethod
    def _do_classify_asset_class(
        cls,
        fund_code: str,
        fund_name: Optional[str] = None
    ) -> str:
        code = str(fund_code or "").strip().zfill(6) if fund_code else ""
        name = str(fund_name or "").strip()
        cache_key = (code, name)
        if cache_key in _CLASSIFY_ASSET_CLASS_CACHE:
            return _CLASSIFY_ASSET_CLASS_CACHE[cache_key]

        res = cls._compute_asset_class_category(code, name)
        _CLASSIFY_ASSET_CLASS_CACHE[cache_key] = res
        if code and (code, "") not in _CLASSIFY_ASSET_CLASS_CACHE:
            _CLASSIFY_ASSET_CLASS_CACHE[(code, "")] = res
        return res

    @classmethod
    def _compute_asset_class_category(
        cls,
        code: str,
        name: str
    ) -> str:'''

if old_classify_header in content:
    content = content.replace(old_classify_header, new_classify_header, 1)
    print("8. Successfully replaced classify_fund_asset_class header")
else:
    print("8. FAILED to find classify_fund_asset_class header")

file_path.write_text(content, encoding="utf-8")
print("All done!")
