# data_persistence.py - データ永続化機能（プロジェクト統合版）

import pickle
import os
import pandas as pd
import streamlit as st
from datetime import datetime
import json
import shutil  # 標準ライブラリ
import logging
from pathlib import Path  # 標準ライブラリ（pathlib2不要）

# ===== 設定 =====
DATA_DIR = "saved_data"
MAIN_DATA_FILE = os.path.join(DATA_DIR, "main_data.pkl")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_data_directory():
    """データディレクトリの存在確認・作成"""
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            logger.info(f"データディレクトリを作成: {DATA_DIR}")
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            logger.info(f"バックアップディレクトリを作成: {BACKUP_DIR}")
        return True
    except Exception as e:
        if 'st' in globals():
            st.error(f"ディレクトリ作成エラー: {e}")
        logger.error(f"ディレクトリ作成エラー: {e}")
        return False

def create_backup(force_create=False):
    """現在のデータのバックアップを作成
    
    Args:
        force_create (bool): Trueの場合、ファイルが存在しなくてもエラーにしない
    """
    try:
        if not os.path.exists(MAIN_DATA_FILE):
            if force_create:
                # 現在のセッションデータからバックアップを作成
                if hasattr(st, 'session_state') and st.session_state.get('processed_df') is not None:
                    df = st.session_state.get('processed_df')
                    target_data = st.session_state.get('target_dict')
                    if df is not None and not df.empty:
                        # 一時的にファイルに保存してからバックアップ
                        temp_success = save_data_to_file(df, target_data)
                        if not temp_success:
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"main_data_backup_{timestamp}.pkl")
        shutil.copy2(MAIN_DATA_FILE, backup_file)
        
        # メタデータファイルもバックアップ
        if os.path.exists(METADATA_FILE):
            backup_metadata_file = os.path.join(BACKUP_DIR, f"metadata_backup_{timestamp}.json")
            shutil.copy2(METADATA_FILE, backup_metadata_file)
        
        # 古いバックアップファイルを削除（最新10個まで保持）
        backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("main_data_backup_")]
        backup_files.sort(reverse=True)
        
        for old_backup in backup_files[10:]:
            try:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                # 対応するメタデータファイルも削除
                metadata_backup = old_backup.replace("main_data_backup_", "metadata_backup_").replace(".pkl", ".json")
                metadata_path = os.path.join(BACKUP_DIR, metadata_backup)
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
            except Exception as cleanup_error:
                logger.warning(f"古いバックアップ削除エラー: {cleanup_error}")
        
        logger.info(f"バックアップ作成完了: {backup_file}")
        return True
    except Exception as e:
        if 'st' in globals():
            st.warning(f"バックアップ作成エラー: {e}")
        logger.error(f"バックアップ作成エラー: {e}")
        return False

def save_data_to_file(df, target_data=None, metadata=None):
    """データをファイルに保存（強化版）"""
    try:
        if not ensure_data_directory():
            return False
        
        # 既存データのバックアップ
        create_backup()
        
        # メインデータの保存
        data_to_save = {
            'df': df,
            'target_data': target_data,
            'saved_at': datetime.now(),
            'data_shape': df.shape if df is not None else None,
            'version': '6.0',  # アプリバージョンに合わせて更新
            'data_source': st.session_state.get('data_source', 'unknown') if hasattr(st, 'session_state') else 'unknown',
            'session_info': {
                'filter_config': st.session_state.get('current_unified_filter_config', {}) if hasattr(st, 'session_state') else {},
                'performance_metrics': st.session_state.get('performance_metrics', {}) if hasattr(st, 'session_state') else {},
                'validation_results': st.session_state.get('validation_results', {}) if hasattr(st, 'session_state') else {}
            }
        }
        
        with open(MAIN_DATA_FILE, 'wb') as f:
            pickle.dump(data_to_save, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # メタデータの保存（強化版）
        if metadata is None:
            metadata = {}
        
        enhanced_metadata = {
            'last_saved': datetime.now().isoformat(),
            'data_rows': len(df) if df is not None else 0,
            'data_columns': list(df.columns) if df is not None else [],
            'file_size_mb': round(os.path.getsize(MAIN_DATA_FILE) / (1024 * 1024), 2),
            'data_source': st.session_state.get('data_source', 'unknown') if hasattr(st, 'session_state') else 'unknown',
            'app_version': '6.0',
            'save_count': metadata.get('save_count', 0) + 1,
            'date_range': {},
            'statistics': {}
        }
        
        # データ統計情報を追加
        if df is not None and not df.empty:
            # 日付列の検出（複数の可能性のある列名に対応）
            date_columns = ['日付', '手術実施日_dt', '手術実施日', 'date']
            date_col = None
            for col in date_columns:
                if col in df.columns:
                    date_col = col
                    break
            
            if date_col:
                try:
                    enhanced_metadata['date_range'] = {
                        'min_date': df[date_col].min().isoformat(),
                        'max_date': df[date_col].max().isoformat(),
                        'total_days': (df[date_col].max() - df[date_col].min()).days + 1,
                        'unique_dates': df[date_col].nunique()
                    }
                except Exception as date_error:
                    logger.warning(f"日付範囲計算エラー: {date_error}")
            
            # 基本統計（複数の可能性のある列名に対応）
            dept_columns = ['診療科名', '実施診療科', '診療科', 'department']
            ward_columns = ['病棟コード', '病棟', 'ward']
            
            dept_col = None
            ward_col = None
            
            for col in dept_columns:
                if col in df.columns:
                    dept_col = col
                    break
                    
            for col in ward_columns:
                if col in df.columns:
                    ward_col = col
                    break
            
            enhanced_metadata['statistics'] = {
                'departments': df[dept_col].nunique() if dept_col else 0,
                'wards': df[ward_col].nunique() if ward_col else 0,
                'total_records': len(df),
                'columns_count': len(df.columns)
            }
        
        # 元のメタデータと結合
        enhanced_metadata.update(metadata)
        
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(enhanced_metadata, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"データ保存完了: {len(df) if df is not None else 0}件")
        return True
        
    except Exception as e:
        if 'st' in globals():
            st.error(f"データ保存エラー: {e}")
        logger.error(f"データ保存エラー: {e}")
        return False

def load_data_from_file():
    """ファイルからデータを読み込み（強化版）"""
    try:
        if not os.path.exists(MAIN_DATA_FILE):
            logger.info("保存ファイルが見つかりません")
            return None, None, None
        
        # メインデータの読み込み
        with open(MAIN_DATA_FILE, 'rb') as f:
            saved_data = pickle.load(f)
        
        # メタデータの読み込み
        metadata = None
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # データの妥当性チェック
        df = saved_data.get('df')
        if df is not None and isinstance(df, pd.DataFrame):
            # 日付列の型確認・修正（複数の可能性に対応）
            date_columns = ['日付', '手術実施日_dt', '手術実施日', 'date']
            for col in date_columns:
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except Exception as date_convert_error:
                        logger.warning(f"日付列変換警告 {col}: {date_convert_error}")
        
        # セッション情報の復元（可能な場合）
        if hasattr(st, 'session_state'):
            session_info = saved_data.get('session_info', {})
            if session_info:
                # フィルター設定の復元
                if session_info.get('filter_config'):
                    st.session_state['restored_filter_config'] = session_info['filter_config']
                
                # パフォーマンス情報の復元
                if session_info.get('performance_metrics'):
                    st.session_state['performance_metrics'] = session_info['performance_metrics']
        
        logger.info(f"データ読み込み完了: {len(df) if df is not None else 0}件")
        return df, saved_data.get('target_data'), metadata
        
    except Exception as e:
        if 'st' in globals():
            st.error(f"データ読み込みエラー: {e}")
        logger.error(f"データ読み込みエラー: {e}")
        return None, None, None

def save_settings_to_file(settings):
    """設定をファイルに保存"""
    try:
        if not ensure_data_directory():
            return False
        
        settings_to_save = {
            'saved_at': datetime.now().isoformat(),
            'settings': settings,
            'version': '6.0'
        }
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_to_save, f, ensure_ascii=False, indent=2)
        
        logger.info("設定保存完了")
        return True
        
    except Exception as e:
        if 'st' in globals():
            st.error(f"設定保存エラー: {e}")
        logger.error(f"設定保存エラー: {e}")
        return False

def load_settings_from_file():
    """ファイルから設定を読み込み"""
    try:
        if not os.path.exists(SETTINGS_FILE):
            return None
        
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            saved_settings = json.load(f)
        
        return saved_settings.get('settings')
        
    except Exception as e:
        if 'st' in globals():
            st.error(f"設定読み込みエラー: {e}")
        logger.error(f"設定読み込みエラー: {e}")
        return None

def get_data_info():
    """保存されたデータの情報を取得（強化版）"""
    try:
        if not os.path.exists(METADATA_FILE):
            return None
        
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return metadata
        
    except Exception as e:
        logger.error(f"データ情報取得エラー: {e}")
        return None

def delete_saved_data():
    """保存されたデータを削除"""
    try:
        files_to_delete = [MAIN_DATA_FILE, METADATA_FILE, SETTINGS_FILE]
        deleted_files = []
        
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(os.path.basename(file_path))
        
        # バックアップディレクトリも削除
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
            deleted_files.append("backup/")
        
        logger.info(f"データ削除完了: {deleted_files}")
        return True, deleted_files
        
    except Exception as e:
        logger.error(f"データ削除エラー: {e}")
        return False, str(e)

def auto_load_data():
    """アプリ起動時の自動データ読み込み（シンプル確実版）"""
    
    # セッション状態がない場合はスキップ
    if not hasattr(st, 'session_state'):
        return False
    
    # 既にデータが処理済みの場合はスキップ
    if st.session_state.get('processed_df') is not None and not st.session_state.get('processed_df').empty:
        return False
    
    # データファイルが存在しない場合はスキップ
    if not os.path.exists(MAIN_DATA_FILE):
        return False
    
    try:
        # データ読み込み実行
        df, target_data, metadata = load_data_from_file()
        
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            # セッション状態に設定
            st.session_state['processed_df'] = df
            st.session_state['target_dict'] = target_data or {}
            st.session_state['data_source'] = 'auto_loaded'
            st.session_state['data_metadata'] = metadata
            
            # 最新データ日付の設定（複数の可能性のある列名に対応）
            date_columns = ['日付', '手術実施日_dt', '手術実施日', 'date']
            for col in date_columns:
                if col in df.columns and not df[col].empty:
                    try:
                        latest_date = df[col].max()
                        st.session_state['latest_date'] = latest_date
                        break
                    except Exception:
                        continue
            
            logger.info(f"自動読み込み完了: {len(df)}件")
            return True
        else:
            return False
            
    except Exception as e:
        # エラーが発生した場合は自動読み込みを無効化
        logger.error(f"自動データ読み込みエラー: {e}")
        if 'st' in globals():
            st.error(f"自動データ読み込みエラー: {str(e)}")
        return False

def get_file_sizes():
    """保存ファイルのサイズ情報を取得（強化版）"""
    try:
        sizes = {}
        files = [
            ('main_data', MAIN_DATA_FILE, 'メインデータ'),
            ('metadata', METADATA_FILE, 'メタデータ'), 
            ('settings', SETTINGS_FILE, '設定ファイル')
        ]
        
        total_size = 0
        
        for name, filepath, display_name in files:
            if os.path.exists(filepath):
                size_bytes = os.path.getsize(filepath)
                total_size += size_bytes
                
                if size_bytes < 1024:
                    sizes[display_name] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    sizes[display_name] = f"{size_bytes / 1024:.1f} KB"
                else:
                    sizes[display_name] = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                sizes[display_name] = "未保存"
        
        # バックアップフォルダのサイズも追加
        if os.path.exists(BACKUP_DIR):
            backup_size = sum(
                os.path.getsize(os.path.join(BACKUP_DIR, f)) 
                for f in os.listdir(BACKUP_DIR) 
                if os.path.isfile(os.path.join(BACKUP_DIR, f))
            )
            total_size += backup_size
            
            if backup_size > 0:
                if backup_size < 1024 * 1024:
                    sizes['バックアップ'] = f"{backup_size / 1024:.1f} KB"
                else:
                    sizes['バックアップ'] = f"{backup_size / (1024 * 1024):.1f} MB"
        
        # 合計サイズ
        if total_size > 0:
            if total_size < 1024 * 1024:
                sizes['合計'] = f"{total_size / 1024:.1f} KB"
            else:
                sizes['合計'] = f"{total_size / (1024 * 1024):.1f} MB"
        
        return sizes
        
    except Exception as e:
        logger.error(f"ファイルサイズ取得エラー: {e}")
        return {}

def get_backup_info():
    """バックアップファイルの情報を取得（強化版）"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return []
        
        backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("main_data_backup_")]
        backup_info = []
        
        for backup_file in sorted(backup_files, reverse=True):
            file_path = os.path.join(BACKUP_DIR, backup_file)
            timestamp_str = backup_file.replace("main_data_backup_", "").replace(".pkl", "")
            
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                formatted_time = timestamp.strftime("%Y/%m/%d %H:%M:%S")
                file_size = os.path.getsize(file_path)
                
                if file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # 対応するメタデータファイルがあるかチェック
                metadata_file = os.path.join(BACKUP_DIR, f"metadata_backup_{timestamp_str}.json")
                has_metadata = os.path.exists(metadata_file)
                
                backup_info.append({
                    'filename': backup_file,
                    'timestamp': formatted_time,
                    'size': size_str,
                    'path': file_path,
                    'has_metadata': has_metadata,
                    'age_days': (datetime.now() - timestamp).days
                })
            except Exception as parse_error:
                logger.warning(f"バックアップファイル解析エラー {backup_file}: {parse_error}")
                continue
        
        return backup_info[:10]  # 最新10個まで
        
    except Exception as e:
        logger.error(f"バックアップ情報取得エラー: {e}")
        return []

def restore_from_backup(backup_filename):
    """バックアップからデータを復元（強化版）"""
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        if not os.path.exists(backup_path):
            return False, "バックアップファイルが見つかりません"
        
        # 現在のファイルをバックアップ
        create_backup()
        
        # バックアップファイルを復元
        shutil.copy2(backup_path, MAIN_DATA_FILE)
        
        # 対応するメタデータファイルも復元
        timestamp_str = backup_filename.replace("main_data_backup_", "").replace(".pkl", "")
        metadata_backup_path = os.path.join(BACKUP_DIR, f"metadata_backup_{timestamp_str}.json")
        
        if os.path.exists(metadata_backup_path):
            shutil.copy2(metadata_backup_path, METADATA_FILE)
        
        # セッション状態をクリア（Streamlit環境の場合のみ）
        if hasattr(st, 'session_state'):
            keys_to_clear = ['processed_df', 'target_dict', 'latest_date', 'data_source', 'data_metadata',
                            'current_unified_filter_config', 'performance_metrics',
                            'validation_results', 'all_results']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
        
        logger.info(f"バックアップ復元完了: {backup_filename}")
        return True, "復元完了"
        
    except Exception as e:
        logger.error(f"バックアップ復元エラー: {e}")
        return False, f"復元エラー: {e}"

def export_data_package(export_path=None):
    """データパッケージのエクスポート（他端末への移行用）"""
    try:
        if export_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"data_export_{timestamp}.zip"
        
        import zipfile
        
        with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_to_export = [
                (MAIN_DATA_FILE, "main_data.pkl"),
                (METADATA_FILE, "metadata.json"),
                (SETTINGS_FILE, "settings.json")
            ]
            
            for source_path, archive_name in files_to_export:
                if os.path.exists(source_path):
                    zipf.write(source_path, archive_name)
            
            # 最新のバックアップも含める
            backup_info = get_backup_info()
            if backup_info:
                latest_backup = backup_info[0]
                zipf.write(latest_backup['path'], f"backup_{latest_backup['filename']}")
        
        logger.info(f"データエクスポート完了: {export_path}")
        return True, export_path
        
    except Exception as e:
        logger.error(f"データエクスポートエラー: {e}")
        return False, str(e)

def import_data_package(import_file):
    """データパッケージのインポート"""
    try:
        import zipfile
        
        if not ensure_data_directory():
            return False, "ディレクトリ作成失敗"
        
        # 現在のデータをバックアップ
        create_backup(force_create=True)
        
        with zipfile.ZipFile(import_file, 'r') as zipf:
            zipf.extractall(DATA_DIR)
        
        # セッション状態をクリア（Streamlit環境の場合のみ）
        if hasattr(st, 'session_state'):
            keys_to_clear = ['processed_df', 'target_dict', 'latest_date', 'data_source', 'data_metadata',
                            'current_unified_filter_config', 'performance_metrics',
                            'validation_results', 'all_results']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
        
        logger.info("データインポート完了")
        return True, "インポート完了"
        
    except Exception as e:
        logger.error(f"データインポートエラー: {e}")
        return False, f"インポートエラー: {e}"

def toggle_auto_load(enabled=True):
    """自動読み込み機能の有効/無効切り替え"""
    if hasattr(st, 'session_state'):
        st.session_state['disable_auto_load'] = not enabled
        return not st.session_state.get('disable_auto_load', False)
    return enabled