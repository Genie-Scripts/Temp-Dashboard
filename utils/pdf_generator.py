# utils/pdf_generator.py
"""
PDF レポート生成モジュール
ダッシュボードの内容をPDF形式で出力
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import base64
from io import BytesIO

# PDF生成ライブラリ
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """PDF レポート生成クラス"""
    
    def __init__(self):
        self.styles = None
        self.setup_styles()
    
    def setup_styles(self):
        """PDFスタイルを設定"""
        if not REPORTLAB_AVAILABLE:
            return
        
        self.styles = getSampleStyleSheet()
        
        # カスタムスタイル
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.darkblue,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
    
    def generate_dashboard_report(self, 
                                kpi_data: Dict[str, Any],
                                performance_data: pd.DataFrame,
                                period_info: Dict[str, Any],
                                charts: Dict[str, go.Figure] = None) -> BytesIO:
        """ダッシュボードレポートPDFを生成"""
        
        if not REPORTLAB_AVAILABLE:
            st.error("PDF生成にはreportlabライブラリが必要です")
            return None
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # タイトルページ
        story.extend(self._create_title_page(period_info))
        
        # ページブレイク
        story.append(PageBreak())
        
        # 概要セクション
        story.extend(self._create_summary_section(kpi_data, period_info))
        
        # KPI セクション
        story.extend(self._create_kpi_section(kpi_data))
        
        # パフォーマンスセクション
        if not performance_data.empty:
            story.extend(self._create_performance_section(performance_data))
        
        # グラフセクション
        if charts:
            story.extend(self._create_charts_section(charts))
        
        # フッター情報
        story.extend(self._create_footer_section())
        
        # PDF生成
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _create_title_page(self, period_info: Dict[str, Any]) -> List:
        """タイトルページを作成"""
        story = []
        
        # メインタイトル
        title = Paragraph("🏥 手術分析ダッシュボード", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.5*inch))
        
        # サブタイトル
        subtitle = Paragraph("管理者向けサマリーレポート", self.styles['Heading2'])
        story.append(subtitle)
        story.append(Spacer(1, 0.5*inch))
        
        # 期間情報
        period_text = f"""
        <b>分析期間:</b> {period_info.get('period_name', 'N/A')}<br/>
        <b>対象日:</b> {period_info.get('start_date', 'N/A')} ～ {period_info.get('end_date', 'N/A')}<br/>
        <b>分析日数:</b> {period_info.get('total_days', 'N/A')}日間 (平日: {period_info.get('weekdays', 'N/A')}日)<br/>
        """
        period_para = Paragraph(period_text, self.styles['CustomNormal'])
        story.append(period_para)
        story.append(Spacer(1, 1*inch))
        
        # 生成情報
        generated_text = f"""
        <b>レポート生成日時:</b> {datetime.now().strftime('%Y年%m月%d日 %H:%M')}<br/>
        <b>生成システム:</b> 手術分析ダッシュボード v1.0
        """
        generated_para = Paragraph(generated_text, self.styles['CustomNormal'])
        story.append(generated_para)
        
        return story
    
    def _create_summary_section(self, kpi_data: Dict[str, Any], period_info: Dict[str, Any]) -> List:
        """概要セクションを作成"""
        story = []
        
        # セクションタイトル
        story.append(Paragraph("📊 エグゼクティブサマリー", self.styles['CustomHeading']))
        
        # 主要指標サマリー
        gas_cases = kpi_data.get('gas_cases', 0)
        total_cases = kpi_data.get('total_cases', 0)
        daily_avg = kpi_data.get('daily_avg_gas', 0)
        utilization = kpi_data.get('utilization_rate', 0)
        
        summary_text = f"""
        選択期間（{period_info.get('period_name', 'N/A')}）における手術実績の概要：<br/><br/>
        
        • <b>全身麻酔手術件数:</b> {gas_cases:,}件<br/>
        • <b>全手術件数:</b> {total_cases:,}件<br/>
        • <b>平日1日あたり全身麻酔手術:</b> {daily_avg:.1f}件/日<br/>
        • <b>手術室稼働率:</b> {utilization:.1f}%<br/><br/>
        
        手術室稼働率は OP-1〜OP-12（OP-11A, OP-11B除く）11室の平日9:00〜17:15における
        実際の稼働時間を基準として算出されています。
        """
        
        summary_para = Paragraph(summary_text, self.styles['CustomNormal'])
        story.append(summary_para)
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_kpi_section(self, kpi_data: Dict[str, Any]) -> List:
        """KPI セクションを作成"""
        story = []
        
        # セクションタイトル
        story.append(Paragraph("📈 主要業績指標 (KPI)", self.styles['CustomHeading']))
        
        # KPI テーブルデータ
        kpi_table_data = [
            ['指標', '値', '単位', '備考'],
            [
                '全身麻酔手術件数',
                f"{kpi_data.get('gas_cases', 0):,}",
                '件',
                '20分以上の全身麻酔手術'
            ],
            [
                '全手術件数',
                f"{kpi_data.get('total_cases', 0):,}",
                '件',
                '全ての手術（全身麻酔以外も含む）'
            ],
            [
                '平日1日あたり全身麻酔手術',
                f"{kpi_data.get('daily_avg_gas', 0):.1f}",
                '件/日',
                '平日（月〜金）の平均'
            ],
            [
                '手術室稼働率',
                f"{kpi_data.get('utilization_rate', 0):.1f}",
                '%',
                'OP-1〜12の実稼働時間ベース'
            ]
        ]
        
        # テーブル作成
        kpi_table = Table(kpi_table_data, colWidths=[4*cm, 2.5*cm, 1.5*cm, 4*cm])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 稼働時間詳細
        actual_minutes = kpi_data.get('actual_minutes', 0)
        max_minutes = kpi_data.get('max_minutes', 0)
        
        detail_text = f"""
        <b>手術室稼働詳細:</b><br/>
        • 実際稼働時間: {actual_minutes:,}分 ({actual_minutes/60:.1f}時間)<br/>
        • 最大稼働時間: {max_minutes:,}分 ({max_minutes/60:.1f}時間)<br/>
        • 平日数: {kpi_data.get('weekdays', 0)}日<br/>
        """
        
        detail_para = Paragraph(detail_text, self.styles['CustomNormal'])
        story.append(detail_para)
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_performance_section(self, performance_data: pd.DataFrame) -> List:
        """パフォーマンスセクションを作成"""
        story = []
        
        # セクションタイトル
        story.append(Paragraph("🏆 診療科別パフォーマンス", self.styles['CustomHeading']))
        
        # パフォーマンステーブル
        perf_table_data = [['診療科', '期間平均', '直近週実績', '週次目標', '達成率(%)']]
        
        for _, row in performance_data.iterrows():
            perf_table_data.append([
                str(row['診療科']),
                f"{row['期間平均']:.1f}",
                f"{row['直近週実績']:.0f}",
                f"{row['週次目標']:.1f}",
                f"{row['達成率(%)']:.1f}"
            ])
        
        perf_table = Table(perf_table_data, colWidths=[3*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9)
        ]))
        
        story.append(perf_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 達成率分析
        high_performers = performance_data[performance_data['達成率(%)'] >= 100]
        low_performers = performance_data[performance_data['達成率(%)'] < 80]
        
        analysis_text = f"""
        <b>達成率分析:</b><br/>
        • 目標達成科数: {len(high_performers)}科 / {len(performance_data)}科<br/>
        • 要注意科数: {len(low_performers)}科 (達成率80%未満)<br/>
        """
        
        if len(high_performers) > 0:
            top_dept = high_performers.iloc[0]
            analysis_text += f"• 最高達成率: {top_dept['診療科']} ({top_dept['達成率(%)']:.1f}%)<br/>"
        
        analysis_para = Paragraph(analysis_text, self.styles['CustomNormal'])
        story.append(analysis_para)
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def _create_charts_section(self, charts: Dict[str, go.Figure]) -> List:
        """グラフセクションを作成"""
        story = []
        
        # セクションタイトル
        story.append(Paragraph("📊 グラフ・チャート", self.styles['CustomHeading']))
        
        for chart_name, fig in charts.items():
            try:
                # Plotlyグラフを画像に変換
                img_bytes = pio.to_image(fig, format="png", width=800, height=400)
                img_buffer = BytesIO(img_bytes)
                
                # レポートラブImage作成
                img = Image(img_buffer, width=6*inch, height=3*inch)
                story.append(img)
                
                # キャプション
                caption = Paragraph(f"図: {chart_name}", self.styles['CustomNormal'])
                story.append(caption)
                story.append(Spacer(1, 0.2*inch))
                
            except Exception as e:
                logger.error(f"グラフ変換エラー ({chart_name}): {e}")
                error_text = Paragraph(f"グラフ '{chart_name}' の生成でエラーが発生しました", self.styles['CustomNormal'])
                story.append(error_text)
        
        return story
    
    def _create_footer_section(self) -> List:
        """フッターセクションを作成"""
        story = []
        
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("ーーーーーーーーーーーーーーーーーーーーーーーーーーーー", self.styles['CustomNormal']))
        
        footer_text = f"""
        <b>レポート生成情報:</b><br/>
        • システム: 手術分析ダッシュボード v1.0<br/>
        • 生成日時: {datetime.now().strftime('%Y年%m月%d日 %H時%M分')}<br/>
        • 注意事項: このレポートに含まれる情報は分析対象期間のデータに基づいています<br/>
        """
        
        footer_para = Paragraph(footer_text, self.styles['CustomNormal'])
        story.append(footer_para)
        
        return story


# Streamlit用のPDF出力インターフェース
class StreamlitPDFExporter:
    """Streamlit用PDF出力インターフェース"""
    
    @staticmethod
    def add_pdf_download_button(kpi_data: Dict[str, Any],
                               performance_data: pd.DataFrame,
                               period_info: Dict[str, Any],
                               charts: Dict[str, go.Figure] = None,
                               button_label: str = "📄 PDFレポートをダウンロード"):
        """PDFダウンロードボタンを追加"""
        
        if not REPORTLAB_AVAILABLE:
            st.error("📋 PDF出力機能を使用するには以下のライブラリのインストールが必要です:")
            st.code("pip install reportlab")
            return
        
        try:
            # PDF生成
            generator = PDFReportGenerator()
            pdf_buffer = generator.generate_dashboard_report(
                kpi_data, performance_data, period_info, charts
            )
            
            if pdf_buffer:
                # ファイル名生成
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"手術分析レポート_{period_info.get('period_name', 'report')}_{timestamp}.pdf"
                
                # ダウンロードボタン
                st.download_button(
                    label=button_label,
                    data=pdf_buffer.getvalue(),
                    file_name=filename,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                
                st.success(f"✅ PDFレポートの準備が完了しました。ボタンをクリックしてダウンロードしてください。")
                
            else:
                st.error("PDFの生成に失敗しました")
                
        except Exception as e:
            st.error(f"PDF生成エラー: {e}")
            logger.error(f"PDF生成エラー: {e}")
    
    @staticmethod
    def create_period_info(period_name: str, start_date, end_date, total_days: int, weekdays: int) -> Dict[str, Any]:
        """期間情報辞書を作成"""
        return {
            'period_name': period_name,
            'start_date': start_date.strftime('%Y/%m/%d') if start_date else 'N/A',
            'end_date': end_date.strftime('%Y/%m/%d') if end_date else 'N/A',
            'total_days': total_days,
            'weekdays': weekdays
        }