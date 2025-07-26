# ui/components/__init__.py
"""
UIコンポーネントパッケージ
再利用可能なUIコンポーネントを提供
"""

# 期間選択コンポーネント
from .period_selector import PeriodSelector

# 既存のコンポーネント（利用可能な場合）
try:
    from .chart_container import ChartContainer
except ImportError:
    ChartContainer = None

try:
    from .data_table import DataTable
except ImportError:
    DataTable = None

try:
    from .file_uploader import FileUploader
except ImportError:
    FileUploader = None

try:
    from .kpi_display import KPIDisplay
except ImportError:
    KPIDisplay = None

try:
    from .progress_indicator import ProgressIndicator
except ImportError:
    ProgressIndicator = None

# 利用可能なコンポーネントのリスト
__all__ = [
    'PeriodSelector'  # 必須コンポーネント
]

# オプショナルコンポーネントを追加
if ChartContainer is not None:
    __all__.append('ChartContainer')

if DataTable is not None:
    __all__.append('DataTable')

if FileUploader is not None:
    __all__.append('FileUploader')

if KPIDisplay is not None:
    __all__.append('KPIDisplay')

if ProgressIndicator is not None:
    __all__.append('ProgressIndicator')

# バージョン情報
__version__ = '1.0.0'

# コンポーネント説明
COMPONENT_DESCRIPTIONS = {
    'PeriodSelector': '期間選択コンポーネント - 複数ページで共通利用可能な期間選択UI',
    'ChartContainer': 'チャートコンテナ - グラフ表示の統一コンテナ',
    'DataTable': 'データテーブル - 表形式データの表示コンポーネント',
    'FileUploader': 'ファイルアップローダー - ファイルアップロード機能',
    'KPIDisplay': 'KPI表示 - 主要指標の統一表示コンポーネント',
    'ProgressIndicator': 'プログレス表示 - 処理進捗の表示コンポーネント'
}

def get_available_components():
    """利用可能なコンポーネントの一覧を取得"""
    return {
        name: COMPONENT_DESCRIPTIONS.get(name, '説明なし')
        for name in __all__
    }

def get_component_info():
    """コンポーネントパッケージの情報を取得"""
    return {
        'version': __version__,
        'total_components': len(__all__),
        'available_components': __all__,
        'descriptions': COMPONENT_DESCRIPTIONS
    }