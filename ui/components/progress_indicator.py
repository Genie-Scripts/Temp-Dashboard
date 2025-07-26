# ui/components/progress_indicator.py
"""プログレス表示コンポーネント"""

import streamlit as st
import time
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class ProgressIndicator:
    """プログレス表示クラス"""
    
    def __init__(self):
        self.progress_bar = None
        self.status_text = None
        self.current_progress = 0.0
    
    def initialize(self, title: str = "処理中...") -> None:
        """プログレスバーを初期化"""
        try:
            self.status_text = st.empty()
            self.progress_bar = st.progress(0.0)
            self.status_text.text(title)
            self.current_progress = 0.0
        except Exception as e:
            logger.error(f"プログレス初期化エラー: {e}")
    
    def update(self, progress: float, message: str = "") -> None:
        """プログレスを更新"""
        try:
            if self.progress_bar is None:
                self.initialize()
            
            self.current_progress = min(max(progress, 0.0), 1.0)
            self.progress_bar.progress(self.current_progress)
            
            if message and self.status_text:
                self.status_text.text(message)
        except Exception as e:
            logger.error(f"プログレス更新エラー: {e}")
    
    def complete(self, message: str = "完了しました") -> None:
        """プログレス完了"""
        try:
            if self.progress_bar:
                self.progress_bar.progress(1.0)
            if self.status_text:
                self.status_text.success(message)
            
            # 少し待ってからクリア
            time.sleep(1)
            self.clear()
        except Exception as e:
            logger.error(f"プログレス完了エラー: {e}")
    
    def clear(self) -> None:
        """プログレス表示をクリア"""
        try:
            if self.progress_bar:
                self.progress_bar.empty()
            if self.status_text:
                self.status_text.empty()
            
            self.progress_bar = None
            self.status_text = None
            self.current_progress = 0.0
        except Exception as e:
            logger.error(f"プログレスクリアエラー: {e}")

# グローバルインスタンス
_global_progress = ProgressIndicator()

def show_progress(message: str, progress: float = 0.0) -> None:
    """プログレスを表示（簡易版）"""
    try:
        _global_progress.update(progress, message)
    except Exception as e:
        logger.error(f"プログレス表示エラー: {e}")

def complete_progress(message: str = "処理が完了しました") -> None:
    """プログレス完了（簡易版）"""
    try:
        _global_progress.complete(message)
    except Exception as e:
        logger.error(f"プログレス完了エラー: {e}")

def clear_progress() -> None:
    """プログレス表示をクリア（簡易版）"""
    try:
        _global_progress.clear()
    except Exception as e:
        logger.error(f"プログレスクリアエラー: {e}")

class StepProgress:
    """ステップ式プログレス表示"""
    
    def __init__(self, steps: List[str], title: str = "処理中..."):
        try:
            self.steps = steps
            self.current_step = 0
            self.title = title
            self.progress_indicator = ProgressIndicator()
            self.progress_indicator.initialize(title)
        except Exception as e:
            logger.error(f"ステッププログレス初期化エラー: {e}")
    
    def next_step(self, message: str = "") -> None:
        """次のステップに進む"""
        try:
            if self.current_step < len(self.steps):
                step_name = self.steps[self.current_step]
                progress = (self.current_step + 1) / len(self.steps)
                display_message = message or f"ステップ {self.current_step + 1}/{len(self.steps)}: {step_name}"
                
                self.progress_indicator.update(progress, display_message)
                self.current_step += 1
        except Exception as e:
            logger.error(f"ステップ進行エラー: {e}")
    
    def complete(self, message: str = "全ての処理が完了しました") -> None:
        """全ステップ完了"""
        try:
            self.progress_indicator.complete(message)
        except Exception as e:
            logger.error(f"ステップ完了エラー: {e}")

class LoadingSpinner:
    """ローディングスピナー"""
    
    def __init__(self, message: str = "読み込み中..."):
        self.message = message
        self.spinner_placeholder = None
    
    def __enter__(self):
        try:
            self.spinner_placeholder = st.empty()
            self.spinner_placeholder.info(f"🔄 {self.message}")
            return self
        except Exception as e:
            logger.error(f"ローディングスピナー開始エラー: {e}")
            return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.spinner_placeholder:
                self.spinner_placeholder.empty()
        except Exception as e:
            logger.error(f"ローディングスピナー終了エラー: {e}")
    
    def update_message(self, message: str) -> None:
        """メッセージを更新"""
        try:
            self.message = message
            if self.spinner_placeholder:
                self.spinner_placeholder.info(f"🔄 {message}")
        except Exception as e:
            logger.error(f"スピナーメッセージ更新エラー: {e}")

def show_loading(message: str = "読み込み中...") -> LoadingSpinner:
    """ローディング表示を開始"""
    return LoadingSpinner(message)

def show_step_progress(steps: List[str], title: str = "処理中...") -> StepProgress:
    """ステップ式プログレス表示を開始"""
    return StepProgress(steps, title)