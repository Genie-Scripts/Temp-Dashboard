# config/hospital_targets.py
"""
病院全体目標値設定ファイル
病院レベルの目標値を一元管理
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class HospitalTargets:
    """病院全体目標値管理クラス"""
    
    # 病院全体目標値（平日ベース）
    HOSPITAL_DAILY_TARGET = {
        'weekday_gas_surgeries': 21.0,  # 平日1日あたり全身麻酔手術目標件数
        'total_surgeries': 25.0,        # 平日1日あたり全手術目標件数（参考値）
    }
    
    # 週次目標値（自動計算）
    HOSPITAL_WEEKLY_TARGET = {
        'weekday_gas_surgeries': HOSPITAL_DAILY_TARGET['weekday_gas_surgeries'] * 5,  # 平日のみ
        'total_surgeries': HOSPITAL_DAILY_TARGET['total_surgeries'] * 5,
    }
    
    @classmethod
    def get_daily_target(cls, target_type: str = 'weekday_gas_surgeries') -> float:
        """日次目標値を取得
        
        Args:
            target_type: 目標タイプ ('weekday_gas_surgeries', 'total_surgeries')
            
        Returns:
            float: 日次目標値
        """
        return cls.HOSPITAL_DAILY_TARGET.get(target_type, 0.0)
    
    @classmethod
    def get_weekly_target(cls, target_type: str = 'weekday_gas_surgeries') -> float:
        """週次目標値を取得
        
        Args:
            target_type: 目標タイプ ('weekday_gas_surgeries', 'total_surgeries')
            
        Returns:
            float: 週次目標値
        """
        return cls.HOSPITAL_WEEKLY_TARGET.get(target_type, 0.0)
    
    @classmethod
    def get_target_info(cls) -> Dict[str, Dict[str, float]]:
        """全ての目標値情報を取得
        
        Returns:
            Dict: 目標値情報の辞書
        """
        return {
            'daily_targets': cls.HOSPITAL_DAILY_TARGET.copy(),
            'weekly_targets': cls.HOSPITAL_WEEKLY_TARGET.copy()
        }
    
    @classmethod
    def calculate_achievement_rate(cls, actual_value: float, 
                                 target_type: str = 'weekday_gas_surgeries',
                                 period: str = 'daily') -> float:
        """達成率を計算
        
        Args:
            actual_value: 実績値
            target_type: 目標タイプ
            period: 期間 ('daily', 'weekly')
            
        Returns:
            float: 達成率（%）
        """
        try:
            if period == 'daily':
                target = cls.get_daily_target(target_type)
            elif period == 'weekly':
                target = cls.get_weekly_target(target_type)
            else:
                logger.warning(f"未知の期間タイプ: {period}")
                return 0.0
            
            if target == 0:
                logger.warning(f"目標値が0です: {target_type}")
                return 0.0
            
            return (actual_value / target) * 100
            
        except Exception as e:
            logger.error(f"達成率計算エラー: {e}")
            return 0.0
    
    @classmethod
    def update_target(cls, target_type: str, daily_value: float) -> bool:
        """目標値を更新（動的更新用）
        
        Args:
            target_type: 目標タイプ
            daily_value: 新しい日次目標値
            
        Returns:
            bool: 更新成功フラグ
        """
        try:
            if target_type in cls.HOSPITAL_DAILY_TARGET:
                cls.HOSPITAL_DAILY_TARGET[target_type] = daily_value
                cls.HOSPITAL_WEEKLY_TARGET[target_type] = daily_value * 5
                logger.info(f"目標値更新: {target_type} = {daily_value}/日")
                return True
            else:
                logger.warning(f"未知の目標タイプ: {target_type}")
                return False
                
        except Exception as e:
            logger.error(f"目標値更新エラー: {e}")
            return False


# 便利関数（後方互換性のため）
def get_hospital_daily_target() -> float:
    """病院全体の平日日次目標を取得（便利関数）"""
    return HospitalTargets.get_daily_target('weekday_gas_surgeries')


def get_hospital_weekly_target() -> float:
    """病院全体の平日週次目標を取得（便利関数）"""
    return HospitalTargets.get_weekly_target('weekday_gas_surgeries')


# 設定値の検証
def validate_targets() -> bool:
    """目標値設定の妥当性をチェック"""
    try:
        daily_target = HospitalTargets.get_daily_target()
        weekly_target = HospitalTargets.get_weekly_target()
        
        # 基本的な妥当性チェック
        if daily_target <= 0:
            logger.error("日次目標値が0以下です")
            return False
        
        if abs(weekly_target - daily_target * 5) > 0.01:
            logger.error("週次目標値の整合性エラー")
            return False
        
        logger.info(f"目標値設定検証完了: {daily_target}/日, {weekly_target}/週")
        return True
        
    except Exception as e:
        logger.error(f"目標値検証エラー: {e}")
        return False


# モジュール読み込み時の初期化
if __name__ == "__main__":
    # テスト用
    print("病院目標値設定:")
    print(f"日次目標: {get_hospital_daily_target()}件/日")
    print(f"週次目標: {get_hospital_weekly_target()}件/週")
    print(f"検証結果: {validate_targets()}")
    
    # 達成率計算テスト（汎用的な例）
    test_cases = [15.0, 21.0, 25.0]  # 様々な実績値でテスト
    for actual in test_cases:
        achievement = HospitalTargets.calculate_achievement_rate(actual)
        print(f"達成率テスト: 実績{actual} → 達成率{achievement:.1f}%")
else:
    # 通常の初期化時に検証実行
    validate_targets()