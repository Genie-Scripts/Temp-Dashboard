# ui/pages/__init__.py
"""
UI ページパッケージ

各分析ページのクラスへの便利なアクセスを提供します。
"""

# 各ページクラスをインポート
from .dashboard_page import DashboardPage
from .data_management_page import DataManagementPage
from .hospital_page import HospitalPage
from .department_page import DepartmentPage
from .surgeon_page import SurgeonPage
from .prediction_page import PredictionPage

# 利用可能なページ一覧
AVAILABLE_PAGES = [
    'ダッシュボード',
    'データアップロード',
    'データ管理', 
    '病院全体分析',
    '診療科別分析',
    '術者分析',
    '将来予測'
]

# ページクラスマッピング
PAGE_CLASSES = {
    'ダッシュボード': DashboardPage,
    'データ管理': DataManagementPage,
    '病院全体分析': HospitalPage,
    '診療科別分析': DepartmentPage,
    '術者分析': SurgeonPage,
    '将来予測': PredictionPage,
}

__all__ = [
    # ページクラス
    'DashboardPage',
    'DataManagementPage', 
    'HospitalPage',
    'DepartmentPage',
    'SurgeonPage',
    'PredictionPage',
    
    # 定数
    'AVAILABLE_PAGES',
    'PAGE_CLASSES',
]

# パッケージ情報
__version__ = "1.0.0"