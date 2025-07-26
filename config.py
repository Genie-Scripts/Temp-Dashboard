# config.py - アプリケーション設定値の管理（更新版）

# ===== 基本設定 =====
APP_VERSION = "1.1"  # バージョンアップ
APP_TITLE = "入退院分析ダッシュボード"
APP_ICON = "🏥"

# ===== デフォルト値 =====
DEFAULT_TOTAL_BEDS = 633
DEFAULT_OCCUPANCY_RATE = 0.9  # 90%
DEFAULT_AVG_LENGTH_OF_STAY = 12.0  # 日
DEFAULT_ADMISSION_FEE = 55000  # 円/日
DEFAULT_TARGET_PATIENT_DAYS = 17000  # 人日/月
DEFAULT_TARGET_ADMISSIONS = 1700  # 人/月

# ===== 除外設定 =====
EXCLUDED_WARDS = ['03B']  # 表示・分析から除外する病棟のリスト

# ===== UI設定 =====
CHART_HEIGHT = 400
FONT_SCALE = 1.0  # style.pyで使用

# ===== 期間設定 =====
PERIOD_OPTIONS = ["直近30日", "前月完了分", "今年度"]
DEFAULT_ANALYSIS_DAYS = 90  # 直近90日

# ===== カラーパレット =====
DASHBOARD_COLORS = {
    'primary_blue': '#3498db',
    'success_green': '#27ae60',
    'warning_orange': '#f39c12',
    'danger_red': '#e74c3c',
    'info_purple': '#9b59b6',
    'secondary_teal': '#16a085',
    'dark_gray': '#2c3e50',
    'light_gray': '#6c757d'
}

# ===== 数値フォーマット設定 =====
NUMBER_FORMAT = {
    'decimal_places': 1,
    'thousand_separator': ',',
    'currency_symbol': '円',
    'percentage_symbol': '%'
}

# ===== メッセージ設定 =====
MESSAGES = {
    'data_not_loaded': "⚠️ データが読み込まれていません。サイドバーから保存データを読み込むか、データ処理タブでファイルをアップロードしてください。",
    'data_processing_complete': "✅ データ処理が完了しました。",
    'insufficient_data': "📊 データを読み込み後に利用可能になります。サイドバーの「データ設定」をご確認ください。",
    'forecast_libs_missing': "📋 予測機能を使用するには必要なライブラリをインストールしてください。",
    'auto_load_success': "💾 保存されたデータを自動読み込みしました。",
    'data_save_success': "✅ データが保存されました。次回起動時に自動読み込みされます。",
    'data_save_error': "❌ データ保存に失敗しました。"
}

# ===== ファイル設定 =====
SUPPORTED_FILE_TYPES = ['.xlsx', '.xls', '.csv']
MAX_FILE_SIZE_MB = 100

# ===== データ永続化設定 =====
DATA_PERSISTENCE = {
    'auto_load_enabled': True,  # 自動読み込み機能
    'auto_save_on_process': True,  # 処理後自動保存
    'max_saved_versions': 5,  # 最大保存バージョン数（将来の拡張用）
    'compression_enabled': True,  # 圧縮保存（将来の拡張用）
}

# ===== 予測機能設定 =====
FORECAST_SETTINGS = {
    'max_forecast_days': 365,
    'min_historical_days': 30,
    'confidence_interval': 0.95
}

# ===== 病院設備設定 =====
HOSPITAL_SETTINGS = {
    'max_beds': 2000,
    'min_beds': 10,
    'max_occupancy_rate': 1.0,
    'min_occupancy_rate': 0.3,
    'max_avg_stay': 30.0,
    'min_avg_stay': 1.0
}

# 既存の設定に追加
HOSPITAL_DEFAULT_TARGETS = {
    'daily_census': 580,
    'daily_admissions': 80
}

# アクション判断の閾値設定
ACTION_THRESHOLDS = {
    'early_intervention_census': 0.05,  # 5%
    'early_intervention_los': 0.03,     # 3%
    'urgent_threshold': 0.15,           # 15%
    'achievement_threshold': 0.95       # 95%
}

# ===== 分析設定 =====
ANALYSIS_SETTINGS = {
    'trend_min_periods': 12,  # トレンド分析に必要な最小期間数
    'seasonal_min_periods': 24,  # 季節性分析に必要な最小期間数
    'statistical_significance': 0.05  # 統計的有意水準
}

# ===== セッション管理設定 =====
SESSION_SETTINGS = {
    'persistent_keys': [  # 永続化するセッション状態のキー
        'total_beds',
        'bed_occupancy_rate', 
        'bed_occupancy_rate_percent',
        'avg_length_of_stay',
        'avg_admission_fee',
        'monthly_target_patient_days',
        'monthly_target_admissions'
    ],
    'auto_clear_on_new_data': False,  # 新データ時の自動クリア
}

# =============================
# ハイスコア機能関連設定
# =============================

# スコアリング基準
HIGH_SCORE_CONFIG = {
    # 直近週達成度基準（50点満点）
    'achievement_thresholds': {
        110: 50,  # 110%以上 → 50点
        105: 45,  # 105-110% → 45点
        100: 40,  # 100-105% → 40点
        98: 35,   # 98-100% → 35点
        95: 25,   # 95-98% → 25点
        90: 15,   # 90-95% → 15点
        85: 5,    # 85-90% → 5点
        0: 0      # 85%未満 → 0点
    },
    
    # 改善度基準（25点満点）
    'improvement_thresholds': {
        15: 25,   # +15%以上 → 25点
        10: 20,   # +10%〜+15% → 20点
        5: 15,    # +5%〜+10% → 15点
        2: 10,    # +2%〜+5% → 10点
        -2: 5,    # -2%〜+2% → 5点
        -5: 3,    # -5%〜-2% → 3点
        -10: 1,   # -10%〜-5% → 1点
        -999: 0   # -10%未満 → 0点
    },
    
    # 安定性基準（15点満点）- 変動係数
    'stability_thresholds': {
        5: 15,    # 5%未満 → 15点
        10: 12,   # 5-10% → 12点
        15: 8,    # 10-15% → 8点
        20: 4,    # 15-20% → 4点
        999: 0    # 20%以上 → 0点
    },
    
    # 持続性基準（10点満点）
    'sustainability_scores': {
        'consecutive_improvement_4': 10,  # 4週連続改善
        'consecutive_improvement_3': 7,   # 3週連続改善
        'consecutive_improvement_2': 4,   # 2週連続改善
        'consecutive_achievement_4': 10,  # 4週連続目標達成
        'consecutive_achievement_3': 7,   # 3週連続目標達成
        'consecutive_achievement_2': 4,   # 2週連続目標達成
        'avg_achievement_98': 6,          # 直近4週平均98%以上
        'high_success_rate': 4,           # 直近4週で3回以上目標達成
        'stable_performance': 3           # 直近4週で1度も90%未満なし
    },
    
    # 病床効率基準（5点満点）
    'bed_efficiency_scores': {
        'utilization_95_with_achievement': 5,  # 利用率95%以上かつ目標達成
        'utilization_90_with_achievement': 3,  # 利用率90-95%かつ目標達成
        'utilization_improvement_10': 3        # 利用率向上+10%以上
    },
    
    # 表示設定
    'display': {
        'top_count': 3,                    # TOP表示数
        'min_score_for_highlight': 80,     # ハイライト表示の最低スコア
        'min_weeks_required': 2,           # 計算に必要な最低週数
        'target_achievement_threshold': 98  # 目標達成の基準（%）
    }
}

# ランキング表示用設定
RANKING_CONFIG = {
    'medals': ['🥇', '🥈', '🥉'],
    'rank_colors': {
        1: '#FFD700',  # ゴールド
        2: '#C0C0C0',  # シルバー
        3: '#CD7F32'   # ブロンズ
    },
    'grade_colors': {
        'S': '#10B981',  # エメラルドグリーン
        'A': '#3B82F6',  # ブルー
        'B': '#6B7280',  # グレー
        'C': '#F59E0B',  # アンバー
        'D': '#EF4444'   # レッド
    }
}

# ハイスコア機能の有効/無効
ENABLE_HIGH_SCORE = True

# デバッグ用設定
HIGH_SCORE_DEBUG = {
    'log_calculations': False,  # 計算過程をログ出力
    'show_detailed_breakdown': False,  # 詳細な内訳を表示
    'mock_data_mode': False     # モックデータ使用
}