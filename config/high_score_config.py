# config/high_score_config.py
"""
ハイスコア機能の設定
"""

# スコア配点設定
SCORE_WEIGHTS = {
    'gas_surgery_total': 70,      # 全身麻酔手術評価の総点数
    'total_cases_total': 15,      # 全手術件数評価の総点数  
    'total_hours_total': 15,      # 総手術時間評価の総点数
    
    # 全身麻酔手術評価の内訳
    'gas_achievement': 30,        # 直近週達成度
    'gas_improvement': 20,        # 改善度
    'gas_stability': 15,          # 安定性
    'gas_trend': 5,              # 持続性
}

# グレード判定基準
GRADE_THRESHOLDS = {
    'S': 85,
    'A': 75, 
    'B': 65,
    'C': 50,
    'D': 0
}

# 評価期間オプション
PERIOD_OPTIONS = [
    "直近4週",
    "直近8週", 
    "直近12週"
]

# 最小データ要件
MIN_DATA_REQUIREMENTS = {
    'min_weeks': 2,              # 最小週数
    'min_cases_per_week': 1,     # 週あたり最小症例数
    'min_total_cases': 3,        # 期間全体の最小症例数
}

# 表示設定
DISPLAY_CONFIG = {
    'show_top_n': 3,             # TOP N位まで詳細表示
    'show_all_ranking': True,     # 全ランキング表示
    'enable_csv_download': True,  # CSVダウンロード機能
    'enable_details_view': True,  # 詳細ビュー
}

# HTML出力設定
HTML_CONFIG = {
    'button_label': '🏆 手術ハイスコア',
    'section_title': '🏆 診療科別手術ハイスコア TOP3',
    'view_id': 'view-surgery-high-score',
    'enable_weekly_insights': True,
}

