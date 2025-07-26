import streamlit as st
import pandas as pd
from typing import List, Optional, Dict, Any, Union
import io
import logging

logger = logging.getLogger(__name__)

class FileUploadConfig:
    """ファイルアップロード設定"""
    
    # サポートされるファイルタイプ
    CSV_TYPES = ["csv"]
    EXCEL_TYPES = ["xlsx", "xls"]
    ZIP_TYPES = ["zip"]
    
    # ファイルサイズ制限（MB）
    MAX_FILE_SIZE_MB = 200
    
    # CSVエンコーディング
    CSV_ENCODINGS = ["utf-8", "utf-8-sig", "shift_jis", "euc-jp"]

def create_file_uploader(
    label: str,
    file_types: List[str],
    accept_multiple: bool = False,
    max_size_mb: Optional[int] = None,
    help_text: Optional[str] = None,
    key: Optional[str] = None
) -> Union[st.runtime.uploaded_file_manager.UploadedFile, List, None]:
    """カスタムファイルアップローダーを作成"""
    try:
        # ファイルサイズ制限の設定
        if max_size_mb is None:
            max_size_mb = FileUploadConfig.MAX_FILE_SIZE_MB
        
        # ヘルプテキストの生成
        if help_text is None:
            help_text = f"対応形式: {', '.join(file_types)}（最大{max_size_mb}MB）"
        
        # ファイルアップローダー
        uploaded_file = st.file_uploader(
            label=label,
            type=file_types,
            accept_multiple_files=accept_multiple,
            help=help_text,
            key=key
        )
        
        # ファイルサイズチェック
        if uploaded_file:
            if accept_multiple:
                for file in uploaded_file:
                    if not _validate_file_size(file, max_size_mb):
                        return None
            else:
                if not _validate_file_size(uploaded_file, max_size_mb):
                    return None
        
        return uploaded_file
    except Exception as e:
        logger.error(f"ファイルアップローダー作成エラー: {e}")
        st.error("ファイルアップロード機能でエラーが発生しました")
        return None

def _validate_file_size(file, max_size_mb: int) -> bool:
    """ファイルサイズを検証"""
    try:
        if file.size > max_size_mb * 1024 * 1024:
            st.error(f"❌ ファイル '{file.name}' のサイズが制限（{max_size_mb}MB）を超えています。")
            return False
        return True
    except Exception as e:
        logger.error(f"ファイルサイズ検証エラー: {e}")
        return False

def preview_csv_file(
    uploaded_file,
    max_preview_rows: int = 10,
    encoding_options: List[str] = None
) -> Optional[pd.DataFrame]:
    """CSVファイルをプレビュー"""
    try:
        if uploaded_file is None:
            return None
        
        if encoding_options is None:
            encoding_options = FileUploadConfig.CSV_ENCODINGS
        
        # エンコーディング選択
        selected_encoding = st.selectbox(
            "文字エンコーディング",
            encoding_options,
            help="ファイルの文字エンコーディングを選択してください"
        )
        
        try:
            # CSVファイルの読み込み
            df = pd.read_csv(uploaded_file, encoding=selected_encoding, nrows=max_preview_rows)
            
            st.success(f"✅ ファイルを正常に読み込みました（プレビュー: 先頭{len(df)}行）")
            
            # プレビュー表示
            with st.expander("📄 ファイルプレビュー", expanded=True):
                st.dataframe(df, use_container_width=True)
                
                # ファイル情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("列数", len(df.columns))
                with col2:
                    st.metric("プレビュー行数", len(df))
                with col3:
                    st.metric("ファイルサイズ", f"{uploaded_file.size / 1024:.1f} KB")
            
            # ファイルポインタをリセット
            uploaded_file.seek(0)
            
            return df
            
        except UnicodeDecodeError:
            st.error(f"❌ 選択したエンコーディング '{selected_encoding}' でファイルを読み込めません。")
            return None
        except Exception as e:
            st.error(f"❌ ファイル読み込みエラー: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"CSVプレビューエラー: {e}")
        st.error("CSVプレビュー中にエラーが発生しました")
        return None

def analyze_file_structure(uploaded_file) -> Dict[str, Any]:
    """ファイル構造を分析"""
    try:
        if uploaded_file is None:
            return {}
        
        # 基本情報
        file_info = {
            "filename": uploaded_file.name,
            "size_bytes": uploaded_file.size,
            "size_mb": uploaded_file.size / (1024 * 1024),
            "type": uploaded_file.type
        }
        
        # CSVファイルの場合の詳細分析
        if uploaded_file.name.lower().endswith('.csv'):
            file_info.update(_analyze_csv_structure(uploaded_file))
        
        return file_info
        
    except Exception as e:
        logger.error(f"ファイル分析エラー: {e}")
        st.warning(f"ファイル分析中にエラーが発生しました: {str(e)}")
        return {"error": str(e)}

def _analyze_csv_structure(uploaded_file) -> Dict[str, Any]:
    """CSV構造の詳細分析"""
    analysis = {}
    
    try:
        # 複数のエンコーディングで試行
        for encoding in FileUploadConfig.CSV_ENCODINGS:
            try:
                # ファイルポインタをリセット
                uploaded_file.seek(0)
                
                # サンプル読み込み
                sample_df = pd.read_csv(uploaded_file, encoding=encoding, nrows=100)
                
                analysis.update({
                    "encoding": encoding,
                    "total_columns": len(sample_df.columns),
                    "column_names": list(sample_df.columns),
                    "sample_rows": len(sample_df),
                    "data_types": sample_df.dtypes.to_dict(),
                    "has_header": True,  # pandas assumes header by default
                    "missing_values": sample_df.isnull().sum().to_dict()
                })
                break
                
            except UnicodeDecodeError:
                continue
            except Exception:
                continue
        
        # ファイルポインタをリセット
        uploaded_file.seek(0)
        
    except Exception as e:
        analysis["analysis_error"] = str(e)
    
    return analysis

def display_file_analysis(file_info: Dict[str, Any]) -> None:
    """ファイル分析結果を表示"""
    try:
        if not file_info:
            return
        
        st.subheader("📊 ファイル分析結果")
        
        # 基本情報
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("ファイル名", file_info.get("filename", "不明"))
        
        with col2:
            size_mb = file_info.get("size_mb", 0)
            st.metric("ファイルサイズ", f"{size_mb:.2f} MB")
        
        with col3:
            st.metric("ファイル形式", file_info.get("type", "不明"))
        
        # CSV詳細情報
        if "total_columns" in file_info:
            st.subheader("📋 CSV詳細情報")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**構造情報**")
                st.write(f"• エンコーディング: {file_info.get('encoding', '不明')}")
                st.write(f"• 列数: {file_info.get('total_columns', 0)}")
                st.write(f"• サンプル行数: {file_info.get('sample_rows', 0)}")
            
            with col2:
                st.write("**列名一覧**")
                columns = file_info.get("column_names", [])
                for i, col in enumerate(columns[:10]):  # 最初の10列のみ表示
                    st.write(f"• {col}")
                
                if len(columns) > 10:
                    st.write(f"... その他 {len(columns) - 10} 列")
            
            # データ型情報
            if "data_types" in file_info:
                with st.expander("🔍 データ型詳細"):
                    data_types = file_info["data_types"]
                    type_df = pd.DataFrame([
                        {"列名": col, "データ型": str(dtype)}
                        for col, dtype in data_types.items()
                    ])
                    st.dataframe(type_df, hide_index=True, use_container_width=True)
            
            # 欠損値情報
            if "missing_values" in file_info:
                missing_values = file_info["missing_values"]
                missing_columns = {k: v for k, v in missing_values.items() if v > 0}
                
                if missing_columns:
                    with st.expander("⚠️ 欠損値情報"):
                        missing_df = pd.DataFrame([
                            {"列名": col, "欠損数": count}
                            for col, count in missing_columns.items()
                        ])
                        st.dataframe(missing_df, hide_index=True, use_container_width=True)
                else:
                    st.success("✅ 欠損値は検出されませんでした")
    except Exception as e:
        logger.error(f"ファイル分析表示エラー: {e}")
        st.error("ファイル分析表示中にエラーが発生しました")

def create_drag_drop_uploader(
    label: str,
    file_types: List[str],
    help_text: Optional[str] = None
) -> None:
    """ドラッグ&ドロップ対応のアップローダーUI"""
    try:
        if help_text is None:
            help_text = f"ファイルをドラッグ&ドロップするか、クリックして選択してください\n対応形式: {', '.join(file_types)}"
        
        # カスタムCSS（ドラッグ&ドロップエリアのスタイル）
        st.markdown("""
        <style>
        .uploadedFile {
            border: 2px dashed #cccccc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin: 10px 0;
            background-color: #fafafa;
            transition: all 0.3s ease;
        }
        .uploadedFile:hover {
            border-color: #1f77b4;
            background-color: #f0f8ff;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # アップロード領域
        st.markdown(f'<div class="uploadedFile">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            label,
            type=file_types,
            help=help_text,
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        return uploaded_file
    except Exception as e:
        logger.error(f"ドラッグドロップアップローダー作成エラー: {e}")
        st.error("ファイルアップロード機能でエラーが発生しました")
        return None

def validate_csv_columns(
    df: pd.DataFrame, 
    required_columns: List[str],
    display_validation: bool = True
) -> bool:
    """CSV列の妥当性検証"""
    try:
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if display_validation:
            if missing_columns:
                st.error(f"❌ 必要な列が不足しています: {', '.join(missing_columns)}")
                
                with st.expander("📋 列名の対応表"):
                    st.write("**必要な列:**")
                    for col in required_columns:
                        status = "✅" if col in df.columns else "❌"
                        st.write(f"{status} {col}")
                    
                    st.write("**ファイル内の列:**")
                    for col in df.columns:
                        st.write(f"• {col}")
                
                return False
            else:
                st.success("✅ 必要な列が全て含まれています")
                return True
        
        return len(missing_columns) == 0
    except Exception as e:
        logger.error(f"CSV列検証エラー: {e}")
        st.error("CSV列検証中にエラーが発生しました")
        return False