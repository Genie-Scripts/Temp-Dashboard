# reporting/pdf_exporter.py
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
import plotly.io as pio
import streamlit as st
import pytz
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# --- 新しいモジュール構造に合わせてインポートパスを修正 ---
from analysis import ranking as ranking_analyzer
from config import style_config as sc

# --- 日本語フォント設定 (変更なし) ---
def setup_japanese_font():
    font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSansJP-Regular.ttf')
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('NotoSansJP', font_path))
        return 'NotoSansJP'
    # フォントが見つからない場合のフォールバック
    print("警告: NotoSansJPフォントが見つかりません。")
    return 'Helvetica'

# --- 既存のPDF生成関連関数 (fig_to_image, create_table_for_pdf, etc.) ---
# (元のpdf_exporter.pyから、インポートパス修正以外はほぼ変更なくここに移植)
# 以下、主要な生成関数のみを掲載

def fig_to_image(fig, width=700, height=350):
    if fig is None: return None
    return pio.to_image(fig, format='png', width=width, height=height, scale=1.5)

def create_table_for_pdf(df, japanese_font):
    # ... (元のコードからテーブル作成ロジックを移植)
    if df is None or df.empty:
        return None
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName=japanese_font, fontSize=10, alignment=1)
    header_cells = [Paragraph(str(col), header_style) for col in df.columns]
    table_data = [header_cells] + df.values.tolist()
    
    table = Table(table_data, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('FONTNAME', (0, 0), (-1, -1), japanese_font),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    table.setStyle(style)
    return table

def create_report_section(title, description, japanese_font, chart=None, table_df=None):
    # ... (元のコードからセクション作成ロジックを移植)
    styles = getSampleStyleSheet()
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['h2'], fontName=japanese_font, fontSize=14, spaceAfter=8)
    description_style = ParagraphStyle('Description', parent=styles['Normal'], fontName=japanese_font, fontSize=10, spaceAfter=10, leading=14)
    content = [Paragraph(title, section_title_style), Paragraph(description.replace('\n', '<br/>'), description_style)]
    if chart:
        img_data = fig_to_image(chart)
        if img_data:
            content.append(Image(io.BytesIO(img_data), width=16*cm, height=8*cm))
            content.append(Spacer(1, 10))
    if table_df is not None and not table_df.empty:
        content.append(create_table_for_pdf(table_df, japanese_font))
    return content

def add_footer(canvas, doc, footer_text):
    # ... (元のコードからフッター描画ロジックを移植)
    japanese_font = setup_japanese_font()
    canvas.saveState()
    canvas.setFont(japanese_font, 9)
    creation_date_str = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y/%m/%d')
    center_text = f"{footer_text} | 作成日: {creation_date_str}"
    canvas.drawCentredString(doc.width/2.0 + doc.leftMargin, doc.bottomMargin - 10, center_text)
    canvas.drawRightString(doc.width + doc.leftMargin - 1*cm, doc.bottomMargin - 10, f"- {canvas.getPageNumber()} -")
    canvas.restoreState()

def generate_hospital_report(summary_df, fig, target_dict, period_type):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2.5*cm)
    japanese_font = setup_japanese_font()
    content = []

    # ... (元のgenerate_hospital_weekly_report/monthly_reportのロジックを参考にセクションを作成)
    description = f"{period_type}のサマリーです。"
    section = create_report_section(f"病院全体 {period_type}レポート", description, japanese_font, chart=fig, table_df=summary_df.tail(15))
    content.extend(section)
    
    footer_text = "手術件数分析レポート (c) 医療情報管理部"
    footer_func = lambda canvas, doc: add_footer(canvas, doc, footer_text)
    doc.build(content, onFirstPage=footer_func, onLaterPages=footer_func)
    
    buffer.seek(0)
    return buffer

def add_pdf_report_button(data_type, period_type, df, fig, target_dict=None, department=None):
    """PDFレポートダウンロードボタンのラッパー関数"""
    if df is None or df.empty:
        return

    now = datetime.now().strftime("%Y%m%d")
    filename = f"{now}_{data_type}_{period_type}.pdf"
    
    if st.button("📄 PDFレポートを生成", key=f"pdf_{data_type}_{period_type}_{department}"):
        with st.spinner("PDFレポートを生成中..."):
            # ここでは簡略化のため、汎用のレポート生成関数を呼び出す
            pdf_buffer = generate_hospital_report(df, fig, target_dict, period_type)
            st.download_button(
                label="📥 PDFをダウンロード",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf"
            )