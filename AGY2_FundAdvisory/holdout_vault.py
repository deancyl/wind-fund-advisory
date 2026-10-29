"""
盲测熔断锁 (holdout_vault.py)
防作弊、防过拟合基建模块 4：
1. 物理/逻辑隔离 2025-07-01 至今的盲测数据
2. 在 evolution.db 中设置硬计数器 holdout_attempts，上限锁死为 3 次
3. 超过 3 次调用直接抛出 HoldoutVaultExhaustedError 强行熔断终止
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, Tuple, Optional

import pandas as pd
from data_loader import DataLoader

DB_PATH = Path("evolution.db")
HOLDOUT_START_DATE = "2025-07-01"
MAX_HOLDOUT_ATTEMPTS = 3


class HoldoutVaultExhaustedError(RuntimeError):
    """盲测调用次数耗尽致命熔断异常"""
    pass


class HoldoutVault:
    """盲测金库安全管理器"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """初始化金库状态表"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        # 初始化 holdout_attempts 计数器
        cur.execute("SELECT value FROM vault_meta WHERE key = 'holdout_attempts'")
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO vault_meta (key, value, updated_at) VALUES ('holdout_attempts', '0', ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
            )
        conn.commit()
        conn.close()

    def get_holdout_attempts(self) -> int:
        """获取已调用的盲测次数"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM vault_meta WHERE key = 'holdout_attempts'")
        row = cur.fetchone()
        conn.close()
        return int(row[0]) if row else 0

    def _increment_attempts(self) -> int:
        """原子递增盲测计数器并检查上限"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM vault_meta WHERE key = 'holdout_attempts'")
        row = cur.fetchone()
        current_attempts = int(row[0]) if row else 0

        if current_attempts >= MAX_HOLDOUT_ATTEMPTS:
            conn.close()
            raise HoldoutVaultExhaustedError(
                f"FATAL: 盲测金库已达到硬性调用上限 ({MAX_HOLDOUT_ATTEMPTS}次)！"
                "为防止向盲测集过拟合与信息泄漏，整个项目已被物理锁死，严禁进一步探索！"
            )

        new_attempts = current_attempts + 1
        cur.execute(
            "UPDATE vault_meta SET value = ?, updated_at = ? WHERE key = 'holdout_attempts'",
            (str(new_attempts), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        return new_attempts

    def evaluate_holdout(
        self,
        strategy_fn: Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, float]],
        params: Dict[str, Any],
        trial_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        申请执行盲测评估（受限物理调用）
        """
        # 1. 检查并扣除盲测额度
        attempt_num = self._increment_attempts()

        # 2. 加载盲测数据 (2025-07-01 至今)
        dl = DataLoader()
        df_full = dl.load_total_return_matrix()
        df_holdout = df_full[df_full['date'] >= pd.to_datetime(HOLDOUT_START_DATE)].copy().reset_index(drop=True)

        if len(df_holdout) == 0:
            raise ValueError(f"盲测区间 ({HOLDOUT_START_DATE} 至今) 数据为空！")

        # 3. 逐日推演盲测区间权重
        dates = df_holdout['date'].tolist()
        weight_rows = []

        for d in dates:
            history_df = df_full[df_full['date'] <= d].copy()
            w_dict = strategy_fn(history_df, params)
            row = {'date': d}
            row.update(w_dict)
            weight_rows.append(row)

        weights_df = pd.DataFrame(weight_rows)
        asset_cols = [c for c in weights_df.columns if c != 'date']

        # 4. 执行真实模拟
        sim_res = dl.simulate_execution(
            weights_df=weights_df,
            prices_df=df_holdout[['date'] + asset_cols]
        )

        nav_s = sim_res['nav']
        daily_ret = sim_res['daily_return']
        years = len(df_holdout) / 252.0
        final_nav = float(nav_s.iloc[-1])
        cagr = (final_nav ** (1.0 / years) - 1.0) if years > 0 and final_nav > 0 else 0.0
        ann_vol = float(daily_ret.std() * (252.0 ** 0.5))
        sharpe = (cagr - 0.02) / ann_vol if ann_vol > 0 else 0.0

        cummax = nav_s.cummax()
        mdd = float(((nav_s - cummax) / cummax).min())

        # 5. 更新 evolution.db 中的盲测状态
        if trial_id is not None:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                UPDATE trials
                SET holdout_tested = 1, holdout_sharpe = ?
                WHERE trial_id = ?
            """, (round(sharpe, 4), trial_id))
            conn.commit()
            conn.close()

        return {
            'attempt_num': attempt_num,
            'remaining_attempts': MAX_HOLDOUT_ATTEMPTS - attempt_num,
            'holdout_start': HOLDOUT_START_DATE,
            'days_tested': len(df_holdout),
            'final_nav': round(final_nav, 4),
            'cagr_pct': round(cagr * 100.0, 2),
            'max_drawdown_pct': round(mdd * 100.0, 2),
            'sharpe_ratio': round(sharpe, 2)
        }
