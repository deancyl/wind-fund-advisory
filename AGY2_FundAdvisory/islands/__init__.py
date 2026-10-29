"""
四岛正交策略进化库 (islands package)
包含四大经典量化策略流派：
1. island_erp: 宏观股债性价比
2. island_momentum: 跨资产截面动量
3. island_breadth: 市场宽度与偏离度择时
4. island_ensemble: 低相关性正交集成
"""

from . import island_erp
from . import island_momentum
from . import island_breadth
from . import island_ensemble

__all__ = [
    'island_erp',
    'island_momentum',
    'island_breadth',
    'island_ensemble'
]
