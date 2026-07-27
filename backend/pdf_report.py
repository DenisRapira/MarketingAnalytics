import os
from typing import Dict, List, Optional, Iterable, Tuple
from xml.sax.saxutils import escape
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate,
    Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.platypus.flowables import BalancedColumns
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfbase.ttfonts import TTFont

# ── Font Registration ──
_FONT_REGULAR = "Arial"
_FONT_BOLD = "Arial-Bold"

for _fname, _fpath in [
    (_FONT_REGULAR, "C:\\Windows\\Fonts\\arial.ttf"),
    (_FONT_BOLD, "C:\\Windows\\Fonts\\arialbd.ttf"),
]:
    if os.path.exists(_fpath):
        try:
            registerFont(TTFont(_fname, _fpath))
        except Exception:
            pass

# ── Design Tokens ──
MARGIN = 20 * mm
GUTTER = 8 * mm
PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 2 * MARGIN
HALF_W = (CONTENT_W - GUTTER) / 2

LS_W, LS_H = landscape(A4)
LS_MARGIN = 15 * mm
LS_CONTENT_W = LS_W - 2 * LS_MARGIN
LS_CONTENT_H = LS_H - 2 * LS_MARGIN

ACCENT = HexColor("#1c5eaa")
ACCENT_DARK = HexColor("#1c5eaa")
ACCENT_LIGHT = HexColor("#EAF2FB")
ACCENT_BG = HexColor("#F1F6FC")
INK = HexColor("#151515")
GOLD = HexColor("#ff4b01")
GOLD_SOFT = HexColor("#ff4b01")
PAPER = HexColor("#FBFAF6")
DARK = HexColor("#0F172A")
GRAY_900 = HexColor("#1E293B")
GRAY_700 = HexColor("#334155")
GRAY = HexColor("#64748B")
GRAY_LIGHT = HexColor("#94A3B8")
GRAY_BORDER = HexColor("#E2E8F0")
LIGHT_BG = HexColor("#F8FAFC")
LIGHTER_BG = HexColor("#F1F5F9")
WHITE = white
GREEN = HexColor("#10B981")
RED = HexColor("#EF4444")

# ── Typography ──
styles = getSampleStyleSheet()
for s in styles.byName.values():
    s.fontName = _FONT_REGULAR

def _make_style(name, font, size, leading, color=DARK, align=TA_LEFT, before=0, after=0, indent=0):
    kwargs = dict(fontName=font, fontSize=size, leading=leading, textColor=color, alignment=align,
                  spaceBefore=before, spaceAfter=after, leftIndent=indent)
    styles.add(ParagraphStyle(name, **kwargs))

_make_style("CoverAccent", _FONT_BOLD, 11, 14, GOLD_SOFT, TA_LEFT, 0, 0)
_make_style("CoverTitle", _FONT_BOLD, 34, 40, WHITE, TA_LEFT, 0, 8)
_make_style("CoverSub", _FONT_REGULAR, 13, 19, GOLD_SOFT, TA_LEFT, 0, 4)
_make_style("CoverMeta", _FONT_REGULAR, 10, 14, GRAY_LIGHT, TA_LEFT, 0, 0)
_make_style("CoverKicker", _FONT_BOLD, 9, 12, GOLD_SOFT, TA_LEFT, 0, 0)
_make_style("SecTitle", _FONT_BOLD, 20, 26, DARK, TA_LEFT, 12, 10)
_make_style("SubSec", _FONT_BOLD, 14, 18, DARK, TA_LEFT, 10, 6)
_make_style("Body", _FONT_REGULAR, 10, 16, GRAY_900, TA_LEFT, 0, 6)
_make_style("BodySmall", _FONT_REGULAR, 9, 13, GRAY, TA_LEFT, 0, 0)
_make_style("KPIVal", _FONT_BOLD, 28, 32, DARK, TA_CENTER, 0, 2)
_make_style("KPILab", _FONT_REGULAR, 8, 11, GRAY, TA_CENTER, 0, 0)
_make_style("Insight", _FONT_REGULAR, 10, 15, GRAY_900, TA_LEFT, 0, 4, 14)
_make_style("RecT", _FONT_BOLD, 11, 15, DARK, TA_LEFT, 0, 2, 14)
_make_style("RecD", _FONT_REGULAR, 9, 13, GRAY, TA_LEFT, 0, 6, 28)
_make_style("Foot", _FONT_REGULAR, 7, 10, GRAY_LIGHT, TA_CENTER)
_make_style("FigTitle", _FONT_BOLD, 16, 22, DARK, TA_CENTER, 6, 4)
_make_style("FigDesc", _FONT_REGULAR, 10, 14, GRAY, TA_CENTER, 0, 8)
_make_style("ChartTitle", _FONT_BOLD, 24, 30, DARK, TA_CENTER, 0, 6)
_make_style("ChartDesc", _FONT_REGULAR, 11, 16, GRAY, TA_CENTER, 0, 12)
_make_style("TableHead", _FONT_BOLD, 8, 11, GRAY_700, TA_CENTER, 0, 0)
_make_style("TableCell", _FONT_REGULAR, 8, 11, GRAY_900, TA_LEFT, 0, 0)


def _safe_text(value, fallback="-"):
    if value is None:
        return fallback
    text = str(value)
    return escape(text if text else fallback)


def _format_number(value, precision=0, suffix=""):
    try:
        num = float(value or 0)
    except (TypeError, ValueError):
        return _safe_text(value)
    if precision:
        return f"{num:,.{precision}f}{suffix}"
    return f"{num:,.0f}{suffix}"


def _format_compact(value, precision=1):
    try:
        num = float(value or 0)
    except (TypeError, ValueError):
        return _safe_text(value)
    abs_num = abs(num)
    if abs_num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.{precision}f}B"
    if abs_num >= 1_000_000:
        return f"{num / 1_000_000:.{precision}f}M"
    if abs_num >= 1_000:
        return f"{num / 1_000:.{precision}f}K"
    return f"{num:.0f}"


def _ensure_marketing_metrics(metrics):
    total_views = float(metrics.get("total_views", 0) or 0)
    total_eng = float(metrics.get("total_engagement", 0) or 0)
    if total_views > 0 and not metrics.get("attention_quality"):
        metrics["attention_quality"] = total_eng / total_views * 100
    if total_eng > 0:
        if not metrics.get("conversation_rate"):
            metrics["conversation_rate"] = float(metrics.get("total_comments", 0) or 0) / total_eng * 100
        if not metrics.get("amplification_rate"):
            metrics["amplification_rate"] = float(metrics.get("total_shares", 0) or 0) / total_eng * 100
        if not metrics.get("save_intent_rate"):
            metrics["save_intent_rate"] = float(metrics.get("total_saves", 0) or 0) / total_eng * 100
    if not metrics.get("marketing_health_score"):
        er_score = min(float(metrics.get("avg_engagement_rate", 0) or 0) / 6 * 35, 35)
        reach_score = min(__import__("math").log10(max(total_views, 1)) / 6 * 25, 25)
        trend = float(metrics.get("views_trend", 0) or 0)
        trend_score = 15 if trend > 0 else 7 if trend == 0 else 2
        consistency_score = min(float(metrics.get("posting_density", 0) or 0) / 0.7 * 15, 15)
        depth_score = min(
            (float(metrics.get("conversation_rate", 0) or 0)
             + float(metrics.get("amplification_rate", 0) or 0)
             + float(metrics.get("save_intent_rate", 0) or 0)) / 20 * 10,
            10,
        )
        metrics["marketing_health_score"] = round(er_score + reach_score + trend_score + consistency_score + depth_score, 1)
    return metrics


class PDFReport:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.story: List = []
        self.gen_time = datetime.now()
        self._starts_on_new_page = False

    # ── Footers ──
    @staticmethod
    def _footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(GRAY_BORDER)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)
        canvas_obj.setFont(_FONT_REGULAR, 7)
        canvas_obj.setFillColor(GRAY_LIGHT)
        canvas_obj.drawCentredString(PAGE_W / 2, 8 * mm,
                                     f"{getattr(doc, 'company_name', 'Marketing Analytics')}  |  {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  Page {doc.page}")
        canvas_obj.restoreState()

    @staticmethod
    def _footer_landscape(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(GRAY_BORDER)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(LS_MARGIN, 10 * mm, LS_W - LS_MARGIN, 10 * mm)
        canvas_obj.setFont(_FONT_REGULAR, 7)
        canvas_obj.setFillColor(GRAY_LIGHT)
        canvas_obj.drawCentredString(LS_W / 2, 6 * mm,
                                     f"Приложение А  |  {getattr(doc, 'company_name', 'Marketing Analytics')}  |  Page {doc.page}")
        canvas_obj.restoreState()

    # ── Helpers ──
    def _divider(self):
        self.story.append(Table([[""]], colWidths=[CONTENT_W], rowHeights=[1],
                                style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, GRAY_BORDER)])))
        self.story.append(Spacer(1, 6))

    def _spacer(self, h=8):
        self.story.append(Spacer(1, h * mm))

    def _safe_image(self, path, max_w, max_ratio=0.6):
        if not path or not os.path.exists(path):
            return None
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as img:
                img_w, img_h = img.size
            ratio = img_h / img_w if img_w else 0.75
            w = max_w
            h = w * ratio
            max_h = max_w * max_ratio
            if h > max_h:
                h = max_h
                w = h / ratio
            return Image(path, width=w, height=h)
        except Exception:
            return None

    def _image_for_box(self, path, max_w, max_h):
        if not path or not os.path.exists(path) or max_w <= 0 or max_h <= 0:
            return None
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as img:
                img_w, img_h = img.size
            if not img_w or not img_h:
                return None
            scale = min(max_w / img_w, max_h / img_h)
            width = img_w * scale
            height = img_h * scale
            flowable = Image(path, width=width, height=height)
            flowable.hAlign = "CENTER"
            return flowable
        except Exception:
            return None

    def _paragraph_table(self, rows, col_widths, header=True, align=None):
        align = align or {}
        body = []
        for row_index, row in enumerate(rows):
            rendered = []
            for col_index, value in enumerate(row):
                style = styles["TableHead"] if header and row_index == 0 else styles["TableCell"]
                if col_index in align:
                    style = ParagraphStyle(
                        f"tbl_{row_index}_{col_index}_{align[col_index]}",
                        parent=style,
                        alignment=align[col_index],
                    )
                rendered.append(value if isinstance(value, Paragraph) else Paragraph(_safe_text(value), style))
            body.append(rendered)
        table = Table(body, colWidths=col_widths, repeatRows=1 if header else 0, splitByRow=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHTER_BG if header else WHITE),
            ("TEXTCOLOR", (0, 0), (-1, 0), GRAY_700),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, GRAY_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ]))
        return table

    def _chart_catalog(self, data) -> List[Tuple[str, str, str, str]]:
        charts = data.get("charts", {}) or {}
        vk_charts = data.get("vk_post_charts", {}) or {}
        chart_defs = [
            ("timeseries", "Динамика просмотров", "Временной ряд ключевых метрик с трендовой линией."),
            ("barchart", "Топ постов по просмотрам", "Публикации с максимальным вкладом в охват за анализируемый период."),
            ("platforms", "Сравнение платформ", "Сопоставление платформ по просмотрам, вовлеченности и ER."),
            ("distribution", "Распределение вовлеченности", "Форма распределения Engagement Rate с квартилями и центральными значениями."),
            ("dayofweek", "Активность по дням недели", "Средние просмотры по дням недели для планирования публикаций."),
        ]
        vk_defs = [
            ("vk_engagement_comp", "Состав вовлеченности VK", "Распределение взаимодействий VK по типам."),
            ("vk_monthly", "Просмотры VK по месяцам", "Месячная динамика просмотров VK-записей."),
            ("vk_views_dist", "Распределение просмотров VK", "Гистограмма просмотров по VK-записям."),
            ("vk_er_trend", "Динамика ER VK", "Изменение Engagement Rate по VK-записям."),
            ("vk_pareto", "Кривая Парето VK", "Доля записей, формирующая основной объём просмотров."),
        ]
        result = []
        for key, title, desc in chart_defs:
            path = charts.get(key)
            if path and os.path.exists(path):
                result.append((key, path, title, desc))
        for key, title, desc in vk_defs:
            path = vk_charts.get(key)
            if path and os.path.exists(path):
                result.append((key, path, title, desc))
        return result

    # ── BUILD ──
    def build(self, data: Dict):
        self.company_name = str(data.get("company_name") or "Marketing Analytics")[:100]
        self._cover_page(data)
        chart_entries = self._chart_catalog(data)
        self._summary_and_kpi_page(data, has_charts=bool(chart_entries))
        has_charts = self._chart_pages(data, chart_entries) if chart_entries else False
        if has_charts:
            self.story.append(NextPageTemplate("Portrait"))
            self.story.append(PageBreak())
            self._starts_on_new_page = True
        self._period_and_benchmark_section(data)
        self._profile_sections(data)
        self._insights_section(data)
        self._action_plan(data)

        # Appendix A — full-page charts on landscape pages
        portrait_frame = Frame(MARGIN, 12 * mm, PAGE_W - 2 * MARGIN, PAGE_H - MARGIN - 12 * mm, id='portrait')
        landscape_frame = Frame(LS_MARGIN, 12 * mm, LS_CONTENT_W, LS_CONTENT_H - 8 * mm,
                                id='landscape', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

        doc = BaseDocTemplate(self.output_path, pagesize=A4)
        doc.company_name = self.company_name
        doc.addPageTemplates([
            PageTemplate(id='Portrait', frames=portrait_frame, onPage=self._footer, pagesize=A4),
            PageTemplate(id='Landscape', frames=landscape_frame, onPage=self._footer_landscape, pagesize=landscape(A4)),
        ])
        doc.build(self.story)

    # ════════════════════════════════════════════════════════════
    # 1. COVER PAGE
    # ════════════════════════════════════════════════════════════
    def _cover_page(self, data):
        metrics = _ensure_marketing_metrics(data.get("metrics", {}) or {})
        period = data.get("period", "\u2014")
        platforms = data.get("platforms", [])
        pc = data.get("post_count", 0)
        health = metrics.get("marketing_health_score", 0)
        total_views = metrics.get("total_views", 0)
        avg_er = metrics.get("avg_engagement_rate", 0)

        hero_rows = [
            [Paragraph(_safe_text(self.company_name).upper(), styles["CoverKicker"])],
            [Paragraph("Аналитика<br/>маркетинговой эффективности", styles["CoverTitle"])],
            [Paragraph("Отчет по данным социальных сетей: KPI, выводы и план действий для следующего периода.", styles["CoverSub"])],
        ]
        hero = Table(hero_rows, colWidths=[CONTENT_W], rowHeights=[16 * mm, 42 * mm, 26 * mm])
        hero.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), INK),
            ("BOX", (0, 0), (-1, -1), 1.2, INK),
            ("LINEABOVE", (0, 0), (-1, 0), 5, GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 18 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 8 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self.story.append(hero)
        self._spacer(12)

        kpi_cells = [
            Paragraph(f"<font size='22'><b>{_format_compact(total_views)}</b></font><br/><font size='8' color='#64748B'>ПРОСМОТРЫ</font>", styles["BodySmall"]),
            Paragraph(f"<font size='22'><b>{_format_number(avg_er, 2, '%')}</b></font><br/><font size='8' color='#64748B'>СРЕДНИЙ ER</font>", styles["BodySmall"]),
            Paragraph(f"<font size='22'><b>{_format_number(health, 1)}</b></font><br/><font size='8' color='#64748B'>MARKETING SCORE</font>", styles["BodySmall"]),
        ]
        cover_kpis = Table([kpi_cells], colWidths=[CONTENT_W / 3] * 3)
        cover_kpis.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.7, GRAY_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, GRAY_BORDER),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        self.story.append(cover_kpis)
        self._spacer(18)

        meta_rows = [["Период анализа", period], ["Платформы", ", ".join(platforms[:5]) if platforms else "-"],
                     ["Публикаций в выборке", _format_number(pc)], ["Дата генерации", self.gen_time.strftime("%d.%m.%Y")]]
        meta = Table(meta_rows, colWidths=[CONTENT_W * 0.34, CONTENT_W * 0.66])
        meta.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
            ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
            ("TEXTCOLOR", (1, 0), (1, -1), DARK),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, -1), 0.35, GRAY_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        self.story.append(meta)
        self._spacer(24)

        bottom_line = Table([[""]], colWidths=[90], rowHeights=[3],
                            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD)]))
        self.story.append(bottom_line)
        self.story.append(PageBreak())

    # ════════════════════════════════════════════════════════════
    # 2. EXECUTIVE SUMMARY
    # ════════════════════════════════════════════════════════════
    def _summary_and_kpi_page(self, data, has_charts=True):
        self.story.append(Paragraph("Executive Summary", styles["SecTitle"]))
        self._divider()

        metrics = _ensure_marketing_metrics(data.get("metrics", {}) or {})
        trend = data.get("trend", {}) or {}
        total_views = metrics.get("total_views", 0)
        total_engagement = metrics.get("total_engagement", 0)
        avg_er = metrics.get("avg_engagement_rate", 0)
        post_count = metrics.get("post_count", data.get("post_count", 0))

        kpi_defs = [
            ("Просмотры", _format_compact(total_views)),
            ("Вовлечения", _format_compact(total_engagement)),
            ("Средний ER", _format_number(avg_er, 2, "%")),
            ("Постов", _format_number(post_count)),
        ]
        kpi_width = CONTENT_W / 4
        kpi_cells = []
        for label, value in kpi_defs:
            kpi_cells.append(Paragraph(
                f"<font size='23'><b>{_safe_text(value)}</b></font><br/>"
                f"<font size='8' color='#64748B'>{_safe_text(label).upper()}</font>",
                ParagraphStyle(f"kpi_{label}", fontName=_FONT_REGULAR, fontSize=10,
                               leading=28, textColor=DARK, alignment=TA_CENTER)))
        kpi_table = Table([kpi_cells], colWidths=[kpi_width] * 4, hAlign="CENTER")
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.6, GRAY_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, GRAY_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.story.append(kpi_table)
        self._spacer(8)

        direction = trend.get("direction", "stable")
        trend_text = {
            "up": "наблюдается устойчивый рост ключевых метрик",
            "down": "виден нисходящий тренд, требующий корректировки стратегии",
            "stable": "динамика стабильная, без резких отклонений",
        }.get(direction, "динамика требует дополнительной проверки")
        platforms = data.get("platform_scores", []) or []
        best_platform = ""
        if platforms:
            first = platforms[0]
            best_platform = first.get("platform", "") if isinstance(first, dict) else getattr(first, "platform", "")
        narrative = (
            f"За анализируемый период набрано <b>{_format_number(total_views)}</b> просмотров и "
            f"<b>{_format_number(total_engagement)}</b> взаимодействий. Средний Engagement Rate составил "
            f"<b>{_format_number(avg_er, 2, '%')}</b>; {trend_text}."
        )
        if best_platform:
            narrative += f" Лучшая платформа по совокупному скору: <b>{_safe_text(best_platform)}</b>."
        self.story.append(Paragraph(narrative, styles["Body"]))

        formula_rows = [["Маркетинговый показатель", "Формула", "Значение"]]
        formula_rows.extend([
            ["Marketing Health Score", "ER + reach + trend + consistency + depth", f"{metrics.get('marketing_health_score', 0):.1f}/100"],
            ["Attention Quality", "вовлечения / просмотры", _format_number(metrics.get("attention_quality", 0), 2, "%")],
            ["Amplification", "репосты / все вовлечения", _format_number(metrics.get("amplification_rate", 0), 1, "%")],
            ["Conversation", "комментарии / все вовлечения", _format_number(metrics.get("conversation_rate", 0), 1, "%")],
            ["Save Intent", "сохранения / все вовлечения", _format_number(metrics.get("save_intent_rate", 0), 1, "%")],
        ])
        self._spacer(5)
        self.story.append(Paragraph("Маркетинговая модель", styles["SubSec"]))
        self.story.append(self._paragraph_table(
            formula_rows,
            [CONTENT_W * 0.32, CONTENT_W * 0.43, CONTENT_W * 0.25],
            align={2: TA_RIGHT},
        ))

        insights = data.get("insights", []) or []
        if insights:
            self._spacer(4)
            self.story.append(Paragraph("Ключевые выводы", styles["SubSec"]))
            for item in insights[:5]:
                title = _safe_text(item.get("title", "Вывод"))
                description = _safe_text(item.get("description", ""))
                self.story.append(Paragraph(f"<b>{title}:</b> {description}", styles["Insight"]))

        self.story.append(NextPageTemplate("Landscape" if has_charts else "Portrait"))
        self.story.append(PageBreak())

    def _chart_pages(self, data, charts=None) -> bool:
        charts = charts or self._chart_catalog(data)
        if not charts:
            self.story.append(NextPageTemplate("Portrait"))
            return False

        max_image_w = LS_CONTENT_W * 0.94
        max_image_h = LS_CONTENT_H - 58 * mm
        for index, (_, path, title, desc) in enumerate(charts, 1):
            self.story.append(Paragraph(f"Диаграмма {index}. {_safe_text(title)}", styles["ChartTitle"]))
            self.story.append(Paragraph(_safe_text(desc), styles["ChartDesc"]))
            img = self._image_for_box(path, max_image_w, max_image_h)
            if img:
                chart_box = Table([[img]], colWidths=[LS_CONTENT_W], rowHeights=[max_image_h + 4 * mm])
                chart_box.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                self.story.append(chart_box)
            else:
                self.story.append(Paragraph("Диаграмма недоступна для отображения.", styles["FigDesc"]))
            if index != len(charts):
                self.story.append(PageBreak())
        return True

    def _executive_summary(self, data):
        self.story.append(Paragraph("Executive Summary", styles["SecTitle"]))
        self._divider()

        m = data.get("metrics", {})
        trend = data.get("trend", {})
        total_v = m.get("total_views", 0)
        total_e = m.get("total_engagement", 0)
        er = m.get("avg_engagement_rate", 0)
        td = trend.get("direction", "stable")

        # KPI highlights table \u2013 2x2
        kpi_block = [
            [Paragraph(f"<font size='28'><b>{total_v:,.0f}</b></font><br/><font size='9' color='#64748B'>\u041f\u0420\u041e\u0421\u041c\u041e\u0422\u0420\u041e\u0412</font>",
                       ParagraphStyle("h1", fontName=_FONT_REGULAR, fontSize=10, leading=32, textColor=DARK, alignment=TA_CENTER)),
             Paragraph(f"<font size='28'><b>{total_e:,.0f}</b></font><br/><font size='9' color='#64748B'>\u0412\u041e\u0412\u041b\u0415\u0427\u0415\u041d\u0418\u0419</font>",
                       ParagraphStyle("h2", fontName=_FONT_REGULAR, fontSize=10, leading=32, textColor=DARK, alignment=TA_CENTER))],
            [Paragraph(f"<font size='28'><b>{er:.2f}%</b></font><br/><font size='9' color='#64748B'>\u0421\u0420\u0415\u0414\u041d\u0418\u0419 ER</font>",
                       ParagraphStyle("h3", fontName=_FONT_REGULAR, fontSize=10, leading=32, textColor=DARK, alignment=TA_CENTER)),
             Paragraph(f"<font size='28'><b>{m.get('post_count', 0)}</b></font><br/><font size='9' color='#64748B'>\u041f\u041e\u0421\u0422\u041e\u0412</font>",
                       ParagraphStyle("h4", fontName=_FONT_REGULAR, fontSize=10, leading=32, textColor=DARK, alignment=TA_CENTER))],
        ]
        kw = (CONTENT_W - 4) / 2
        tbl = Table(kpi_block, colWidths=[kw, kw], hAlign="CENTER")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHTER_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        self.story.append(tbl)
        self._spacer(6)

        # Narrative
        parts = [
            f"\u0417\u0430 \u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u043c\u044b\u0439 \u043f\u0435\u0440\u0438\u043e\u0434 \u043d\u0430\u0431\u0440\u0430\u043d\u043e <b>{total_v:,.0f}</b> \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432 \u0438 <b>{total_e:,.0f}</b> \u0432\u0437\u0430\u0438\u043c\u043e\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439. ",
            f"\u0421\u0440\u0435\u0434\u043d\u0438\u0439 engagement rate \u0441\u043e\u0441\u0442\u0430\u0432\u0438\u043b <b>{er:.2f}%</b>. ",
        ]
        tmap = {"up": "\u041d\u0430\u0431\u043b\u044e\u0434\u0430\u0435\u0442\u0441\u044f <b>\u0432\u043e\u0441\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u0442\u0440\u0435\u043d\u0434</b> \u2014 \u043a\u043e\u043d\u0442\u0435\u043d\u0442 \u043d\u0430\u0431\u0438\u0440\u0430\u0435\u0442 \u043f\u043e\u043f\u0443\u043b\u044f\u0440\u043d\u043e\u0441\u0442\u044c.",
                "down": "\u0412\u044b\u044f\u0432\u043b\u0435\u043d <b>\u043d\u0438\u0441\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u0442\u0440\u0435\u043d\u0434</b> \u2014 \u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u043a\u0430 \u0441\u0442\u0440\u0430\u0442\u0435\u0433\u0438\u0438.",
                "stable": "\u0414\u0438\u043d\u0430\u043c\u0438\u043a\u0430 <b>\u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u0430\u044f</b>, \u0431\u0435\u0437 \u0440\u0435\u0437\u043a\u0438\u0445 \u043a\u043e\u043b\u0435\u0431\u0430\u043d\u0438\u0439."}
        parts.append(tmap.get(td, ""))
        platforms = data.get("platform_scores", [])
        if platforms:
            best = platforms[0]
            bn = best.get("platform", "") if isinstance(best, dict) else getattr(best, "platform", "")
            parts.append(f" \u041b\u0443\u0447\u0448\u0430\u044f \u043f\u043b\u0430\u0442\u0444\u043e\u0440\u043c\u0430: <b>{bn}</b>.")
        self.story.append(Paragraph("".join(parts), styles["Body"]))

        # Top insights
        ins_list = data.get("insights", [])
        if ins_list:
            self._spacer(6)
            self.story.append(Paragraph("\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0445\u043e\u0434\u043a\u0438", styles["SubSec"]))
            icons = {"positive": "\u2705", "negative": "\U0001f534", "warning": "\u26a0\ufe0f"}
            for ins in ins_list[:4]:
                icon = icons.get(ins.get("severity"), "\U0001f4cc")
                self.story.append(Paragraph(f"{icon} <b>{ins.get('title')}:</b> {ins.get('description')}", styles["Insight"]))
        self.story.append(PageBreak())

    # ════════════════════════════════════════════════════════════
    # 3. KPI SECTION \u2013 1x4 grid
    # ════════════════════════════════════════════════════════════
    def _kpi_section(self, data):
        self.story.append(Paragraph("KPI Dashboard", styles["SecTitle"]))
        self._divider()

        m = data.get("metrics", {})
        kpi_defs = [
            ("\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u044b", f"{m.get('total_views', 0):,.0f}"),
            ("\u0412\u043e\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u044f", f"{m.get('total_engagement', 0):,.0f}"),
            ("\u0421\u0440\u0435\u0434\u043d\u0438\u0439 ER", f"{m.get('avg_engagement_rate', 0):.2f}%"),
            ("\u041f\u043e\u0441\u0442\u043e\u0432", str(m.get('post_count', 0))),
        ]
        kw = CONTENT_W / 4
        kpi_cells = [
            Paragraph(f"<b>{v}</b><br/><font size='8' color='#64748B'>{l}</font>",
                      ParagraphStyle("kc", fontName=_FONT_REGULAR, fontSize=28,
                                     leading=34, textColor=DARK, alignment=TA_CENTER,
                                     spaceBefore=8, spaceAfter=4))
            for l, v in kpi_defs
        ]
        kpi_table = Table([kpi_cells], colWidths=[kw] * 4, hAlign="CENTER")
        kpi_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ]))
        self.story.append(KeepTogether(kpi_table))

        # Extra KPIs
        extra = data.get("metrics_extra", {})
        if extra:
            items = list(extra.items())[:8]
            n = min(len(items), 4)
            ew = CONTENT_W / n
            flat_rows = []
            for i in range(0, len(items), n):
                chunk = items[i:i + n]
                row_cells = []
                for k, v in chunk:
                    row_cells.append(
                        Paragraph(f"<b>{v}</b><br/><font size='8' color='#64748B'>{k}</font>",
                                  ParagraphStyle("ek", fontName=_FONT_REGULAR, fontSize=22,
                                                 leading=26, textColor=DARK, alignment=TA_CENTER,
                                                 spaceBefore=6, spaceAfter=6)))
                while len(row_cells) < n:
                    row_cells.append(Paragraph("", styles["BodySmall"]))
                flat_rows.append(row_cells)
            flat_tbl = Table(flat_rows, colWidths=[ew] * n)
            flat_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ]))
            self.story.append(KeepTogether(flat_tbl))

        self.story.append(PageBreak())

    # ════════════════════════════════════════════════════════════
    # 3b. VK CONTENT BREAKDOWN
    # ════════════════════════════════════════════════════════════
    def _vk_content_section(self, data):
        vk = data.get("vk_breakdown")
        if not vk:
            return
        has_posts = "posts" in vk
        has_clips = "clips" in vk
        if not has_posts and not has_clips:
            return

        self.story.append(PageBreak())
        self.story.append(Paragraph("\u0412\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u0435: \u0417\u0430\u043f\u0438\u0441\u0438 \u0438 \u041a\u043b\u0438\u043f\u044b", styles["SecTitle"]))
        self._divider()

        block_items = []
        for key in ("posts", "clips"):
            item = vk.get(key)
            if item is None:
                continue
            label = item["label"]
            count = item["count"]
            views = item["views"]
            er = item["er"]
            eng = item["engagement"]

            cell_text = (
                f"<b>{label}</b><br/>"
                f"<font size='26'>{views:,.0f}</font><br/>"
                f"<font size='8' color='#64748B'>\u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432</font><br/>"
                f"<font size='10' color='#64748B'>{count} \u043f\u043e\u0441\u0442\u043e\u0432 \u00b7 ER {er:.1f}%</font>"
            )
            block_items.append(
                Paragraph(cell_text,
                          ParagraphStyle("vkcell", fontName=_FONT_REGULAR, fontSize=10,
                                         leading=14, textColor=DARK, alignment=TA_CENTER,
                                         spaceBefore=8, spaceAfter=8)))

        if block_items:
            n = len(block_items)
            kw = CONTENT_W / n
            tbl = Table([block_items], colWidths=[kw] * n)
            tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ]))
            self.story.append(KeepTogether(tbl))
            self._spacer(6)

        if has_posts and has_clips:
            p = vk["posts"]
            c = vk["clips"]
            labels = [
                ("\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u044b", "views"),
                ("\u041b\u0430\u0439\u043a\u0438", "likes"),
                ("\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0438", "comments"),
                ("\u0420\u0435\u043f\u043e\u0441\u0442\u044b", "shares"),
                ("\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f", "saves"),
                ("\u0412\u043e\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435", "engagement"),
                ("ER (%)", "er"),
            ]
            comp_data = [["\u041c\u0435\u0442\u0440\u0438\u043a\u0430", "\u0417\u0430\u043f\u0438\u0441\u0438", "\u041a\u043b\u0438\u043f\u044b", "\u0414\u043e\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0435\u0439"]]
            for label, key in labels:
                pv = p.get(key, 0) or 0
                cv = c.get(key, 0) or 0
                compare_key = "compare_" + key
                share = vk.get(compare_key, {}).get("posts_share", 50) if compare_key in vk else 50
                if isinstance(pv, float):
                    pv_s = f"{pv:,.1f}" if key == "er" else f"{pv:,.0f}"
                    cv_s = f"{cv:,.1f}" if key == "er" else f"{cv:,.0f}"
                else:
                    pv_s = str(pv)
                    cv_s = str(cv)
                comp_data.append([label, pv_s, cv_s, f"{share:.0f}%"])

            cw = CONTENT_W
            comp_tbl = Table(comp_data, colWidths=[cw * 0.30, cw * 0.22, cw * 0.22, cw * 0.26])
            comp_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHTER_BG]),
            ]))
            self.story.append(KeepTogether(comp_tbl))

    def _period_and_benchmark_section(self, data):
        comparison = data.get("period_comparison") or {}
        benchmarks = data.get("benchmarks") or {}
        if not comparison and not benchmarks:
            return

        if self._starts_on_new_page:
            self._starts_on_new_page = False
        else:
            self.story.append(PageBreak())
        self.story.append(Paragraph("Сравнение периодов и бенчмарки", styles["SecTitle"]))
        self._divider()

        metric_labels = {
            "total_views": "Просмотры",
            "total_engagement": "Вовлечения",
            "avg_engagement_rate": "ER",
            "post_count": "Публикации",
            "avg_views": "Ср. просмотры",
        }
        for key in ("month", "quarter"):
            item = comparison.get(key)
            if not item:
                continue
            self.story.append(Paragraph(_safe_text(item.get("label", "")), styles["SubSec"]))
            rows = [["Метрика", "Текущий период", "Предыдущий период", "Изменение"]]
            current = item.get("current", {})
            previous = item.get("previous", {})
            deltas = item.get("deltas", {})
            for metric, label in metric_labels.items():
                cur = current.get(metric, 0)
                prev = previous.get(metric, 0)
                delta = deltas.get(metric, {})
                if metric == "avg_engagement_rate":
                    cur_s = _format_number(cur, 2, "%")
                    prev_s = _format_number(prev, 2, "%")
                else:
                    cur_s = _format_number(cur)
                    prev_s = _format_number(prev)
                rows.append([label, cur_s, prev_s, f"{delta.get('percent', 0):+.1f}%"])
            self.story.append(self._paragraph_table(
                rows,
                [CONTENT_W * 0.28, CONTENT_W * 0.24, CONTENT_W * 0.24, CONTENT_W * 0.24],
                align={1: TA_RIGHT, 2: TA_RIGHT, 3: TA_RIGHT},
            ))
            drivers = item.get("drivers") or []
            if drivers:
                self.story.append(Paragraph("Причины изменений: " + "; ".join(drivers) + ".", styles["BodySmall"]))
            self._spacer(4)

        rows = benchmarks.get("rows") or []
        if rows:
            status_labels = {"below": "ниже нормы", "normal": "в норме", "above": "выше нормы"}
            self.story.append(Paragraph(f"Бенчмарки: {_safe_text(benchmarks.get('platform_label', 'Соцсети'))}", styles["SubSec"]))
            b_rows = [["Показатель", "Значение", "Норма", "Статус"]]
            for row in rows:
                value = row.get("value", 0)
                low = row.get("low", 0)
                high = row.get("high", 0)
                if row.get("metric") == "er":
                    value_s = _format_number(value, 2, "%")
                    norm_s = f"{low:g}-{high:g}%"
                else:
                    value_s = _format_number(value, 1) if row.get("metric") == "posting_per_week" else _format_number(value)
                    norm_s = f"{_format_number(low, 1) if row.get('metric') == 'posting_per_week' else _format_number(low)} - {_format_number(high, 1) if row.get('metric') == 'posting_per_week' else _format_number(high)}"
                b_rows.append([row.get("label", ""), value_s, norm_s, status_labels.get(row.get("status"), "")])
            self.story.append(self._paragraph_table(
                b_rows,
                [CONTENT_W * 0.32, CONTENT_W * 0.22, CONTENT_W * 0.24, CONTENT_W * 0.22],
                align={1: TA_RIGHT, 2: TA_RIGHT},
            ))
            summary = benchmarks.get("summary")
            if summary:
                self.story.append(Paragraph("Вывод: " + _safe_text(summary) + ".", styles["Body"]))

    # ════════════════════════════════════════════════════════════
    # 4. PROFILE SECTIONS (YouTube, VK Posts, VK Clips)
    # ════════════════════════════════════════════════════════════
    def _profile_sections(self, data):
        pm = data.get("profile_metrics", {})
        if not pm:
            return

        for pid, info in pm.items():
            if self._starts_on_new_page:
                self._starts_on_new_page = False
            else:
                self.story.append(PageBreak())
            self.story.append(Paragraph(_safe_text(info.get("label", pid)), styles["SecTitle"]))
            self._divider()

            pc = info.get("post_count", 0)
            views = info.get("views", 0)
            eng = info.get("engagement", 0)
            er = info.get("er", 0)

            # KPI row
            kpi_items = [
                ("\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u044b", f"{views:,.0f}" if views else "0"),
                ("\u0412\u043e\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u044f", f"{eng:,.0f}" if eng else "0"),
                ("ER", f"{er:.2f}%" if er else "0%"),
                ("\u041f\u043e\u0441\u0442\u043e\u0432", str(pc)),
            ]
            kw = CONTENT_W / 4
            cells = [
                Paragraph(f"<b>{v}</b><br/><font size='8' color='#64748B'>{l}</font>",
                          ParagraphStyle(f"pk_{pid}_{l}", fontName=_FONT_REGULAR, fontSize=26,
                                         leading=32, textColor=DARK, alignment=TA_CENTER,
                                         spaceBefore=6, spaceAfter=4))
                for l, v in kpi_items
            ]
            tbl = Table([cells], colWidths=[kw]*4)
            tbl.setStyle(TableStyle([
                ("BOX", (0,0),(-1,-1), 0.5, GRAY_BORDER),
                ("INNERGRID", (0,0),(-1,-1), 0.5, GRAY_BORDER),
                ("TOPPADDING", (0,0),(-1,-1), 8),
                ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ("BACKGROUND", (0,0),(-1,-1), WHITE),
            ]))
            self.story.append(KeepTogether(tbl))
            self._spacer(4)

            # Extra metrics (likes, comments, shares, saves)
            extras = []
            for key, label in [("likes","\u041b\u0430\u0439\u043a\u0438"),("comments","\u041a\u043e\u043c\u043c."),
                               ("shares","\u0420\u0435\u043f\u043e\u0441\u0442\u044b"),("saves","\u0421\u043e\u0445\u0440.")]:
                val = info.get(key, 0)
                if val:
                    extras.append((label, f"{val:,.0f}"))
            if extras:
                n = min(len(extras), 4)
                ew = CONTENT_W / n
                ecells = [
                    Paragraph(f"<b>{v}</b><br/><font size='8' color='#64748B'>{l}</font>",
                              ParagraphStyle(f"pe_{pid}_{l}", fontName=_FONT_REGULAR, fontSize=20,
                                             leading=24, textColor=DARK, alignment=TA_CENTER,
                                             spaceBefore=4, spaceAfter=2))
                    for l, v in extras[:n]
                ]
                while len(ecells) < n:
                    ecells.append(Paragraph("", styles["BodySmall"]))
                etbl = Table([ecells], colWidths=[ew]*n)
                etbl.setStyle(TableStyle([
                    ("BOX", (0,0),(-1,-1), 0.5, GRAY_BORDER),
                    ("INNERGRID", (0,0),(-1,-1), 0.5, GRAY_BORDER),
                    ("TOPPADDING", (0,0),(-1,-1), 6),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                    ("BACKGROUND", (0,0),(-1,-1), WHITE),
                ]))
                self.story.append(KeepTogether(etbl))
                self._spacer(4)

            # Narrative
            ct = info.get("content_type", "")
            pub_word = "\u043a\u043b\u0438\u043f\u043e\u0432" if ct == "clips" else \
                       "\u0437\u0430\u043f\u0438\u0441\u0435\u0439" if ct == "posts" else \
                       "\u0432\u0438\u0434\u0435\u043e"
            parts = []
            if views:
                parts.append(f"\u041d\u0430\u0431\u0440\u0430\u043d\u043e <b>{views:,.0f}</b> \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432 \u0438 <b>{eng:,.0f}</b> \u0432\u0437\u0430\u0438\u043c\u043e\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439. ")
            if er:
                parts.append(f"Engagement rate: <b>{er:.2f}%</b>. ")
            if pc:
                parts.append(f"\u0412\u0441\u0435\u0433\u043e <b>{pc}</b> {pub_word}.")
            if parts:
                self.story.append(Paragraph("".join(parts), styles["Body"]))

            # Reference to appendix charts for VK Posts
            if pid == "vk_posts":
                vk_charts = data.get("vk_post_charts", {})
                if any(vk_charts.get(k) for k in ["vk_engagement_comp","vk_monthly","vk_views_dist","vk_er_trend","vk_pareto"]):
                    self._spacer(6)
                    self.story.append(Paragraph(
                        "\u0414\u0435\u0442\u0430\u043b\u044c\u043d\u044b\u0435 \u0433\u0440\u0430\u0444\u0438\u043a\u0438 \u0441\u043c. \u0432 "
                        "\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0438 \u0410.",
                        styles["Body"]))

        # VK comparison (if both posts and clips)
        vk = data.get("vk_breakdown")
        if vk and vk.get("posts") and vk.get("clips"):
            self._spacer(6)
            self.story.append(Paragraph("\u0421\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 \u0417\u0430\u043f\u0438\u0441\u0435\u0439 \u0438 \u041a\u043b\u0438\u043f\u043e\u0432", styles["SubSec"]))
            p = vk["posts"]
            c = vk["clips"]
            labels = [
                ("\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u044b","views"),
                ("\u041b\u0430\u0439\u043a\u0438","likes"),
                ("\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0438","comments"),
                ("\u0420\u0435\u043f\u043e\u0441\u0442\u044b","shares"),
                ("\u0412\u043e\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435","engagement"),
                ("ER (%)","er"),
            ]
            comp = [["\u041c\u0435\u0442\u0440\u0438\u043a\u0430","\u0417\u0430\u043f\u0438\u0441\u0438","\u041a\u043b\u0438\u043f\u044b"]]
            for label, key in labels:
                pv = p.get(key, 0) or 0
                cv_val = c.get(key, 0) or 0
                pv_s = f"{pv:,.0f}" if not isinstance(pv, str) else pv
                cv_s = f"{cv_val:,.0f}" if not isinstance(cv_val, str) else cv_val
                if key == "er":
                    pv_s = f"{pv:.2f}%"
                    cv_s = f"{cv_val:.2f}%"
                comp.append([label, pv_s, cv_s])
            cw = CONTENT_W
            comp_tbl = Table(comp, colWidths=[cw*0.3, cw*0.35, cw*0.35], hAlign="CENTER")
            comp_tbl.setStyle(TableStyle([
                ("FONTNAME", (0,0),(-1,0), _FONT_BOLD),
                ("FONTSIZE", (0,0),(-1,-1), 10),
                ("ALIGN", (0,0),(-1,-1), "CENTER"),
                ("GRID", (0,0),(-1,-1), 0.5, GRAY_BORDER),
                ("BACKGROUND", (0,0),(-1,0), ACCENT_BG),
                ("TOPPADDING", (0,0),(-1,-1), 6),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, LIGHTER_BG]),
            ]))
            self.story.append(KeepTogether(comp_tbl))

    # ════════════════════════════════════════════════════════════
    # 5. CHARTS SECTION \u2013 references to Appendix A
    # ════════════════════════════════════════════════════════════
    def _charts_section(self, data):
        self.story.append(Paragraph("\u0414\u0435\u0442\u0430\u043b\u044c\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u0434\u0430\u043d\u043d\u044b\u0445", styles["SecTitle"]))
        self._divider()

        refs = [
            ("\u0414\u0438\u043d\u0430\u043c\u0438\u043a\u0430 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432",
             "\u0412\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u0439 \u0440\u044f\u0434 \u0441 \u0442\u0440\u0435\u043d\u0434\u043e\u0432\u043e\u0439 \u043b\u0438\u043d\u0438\u0435\u0439 \u0437\u0430 \u043f\u0435\u0440\u0438\u043e\u0434. (\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0410, \u0420\u0438\u0441. 1)"),
            ("\u0422\u043e\u043f \u043f\u043e\u0441\u0442\u043e\u0432 \u043f\u043e \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430\u043c",
             "\u041d\u0430\u0438\u0431\u043e\u043b\u0435\u0435 \u043f\u043e\u043f\u0443\u043b\u044f\u0440\u043d\u044b\u0435 \u043f\u0443\u0431\u043b\u0438\u043a\u0430\u0446\u0438\u0438. (\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0410, \u0420\u0438\u0441. 2)"),
            ("\u0421\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 \u043f\u043b\u0430\u0442\u0444\u043e\u0440\u043c",
             "\u0421\u0440\u0430\u0432\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u043f\u043e \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430\u043c, \u0432\u043e\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u044e \u0438 ER. (\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0410, \u0420\u0438\u0441. 3)"),
            ("\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u0432\u043e\u0432\u043b\u0435\u0447\u0451\u043d\u043d\u043e\u0441\u0442\u0438",
             "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 engagement rate \u0441 \u043a\u0432\u0430\u0440\u0442\u0438\u043b\u044f\u043c\u0438. (\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0410, \u0420\u0438\u0441. 4)"),
        ]

        for label, desc in refs:
            self.story.append(KeepTogether([
                Paragraph(label, styles["SubSec"]),
                Paragraph(desc, styles["BodySmall"]),
                Spacer(1, 4 * mm),
            ]))

        self.story.append(PageBreak())

    # ════════════════════════════════════════════════════════════
    # 5. INSIGHTS SECTION
    # ════════════════════════════════════════════════════════════
    def _insights_section(self, data):
        self.story.append(Paragraph("\u0418\u043d\u0441\u0430\u0439\u0442\u044b \u0438 \u0432\u044b\u0432\u043e\u0434\u044b", styles["SecTitle"]))
        self._divider()

        insights = data.get("insights", [])
        if not insights:
            self.story.append(Paragraph("\u0418\u043d\u0441\u0430\u0439\u0442\u044b \u043d\u0435 \u0441\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b.", styles["Body"]))
            self.story.append(PageBreak())
            return

        cat_labels = {
            "performance": "\u041e\u0431\u0449\u0430\u044f \u044d\u0444\u0444\u0435\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u044c", "trend": "\u0422\u0440\u0435\u043d\u0434\u044b",
            "engagement": "\u0412\u043e\u0432\u043b\u0435\u0447\u0451\u043d\u043d\u043e\u0441\u0442\u044c", "viral": "\u0412\u0438\u0440\u0443\u0441\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0435\u043d\u0442",
            "platform": "\u041f\u043b\u0430\u0442\u0444\u043e\u0440\u043c\u044b", "anomaly": "\u0410\u043d\u043e\u043c\u0430\u043b\u0438\u0438", "growth": "\u0420\u043e\u0441\u0442 \u0430\u0443\u0434\u0438\u0442\u043e\u0440\u0438\u0438",
        }
        icons = {"positive": "PLUS", "negative": "RISK", "warning": "CHECK", "neutral": "NOTE"}
        seen = set()

        for ins in insights:
            cat = ins.get("category", "")
            if cat not in seen and cat in cat_labels:
                self.story.append(Paragraph(cat_labels[cat], styles["SubSec"]))
                seen.add(cat)

            icon = icons.get(ins.get("severity"), "\U0001f4cc")
            text = f"<font color='#ff4b01'><b>{icon}</b></font>  <b>{ins.get('title')}:</b> {ins.get('description')}"
            self.story.append(Paragraph(text, styles["Insight"]))

            rec = ins.get("recommendation")
            if rec and ins.get("category") != "recommendation":
                self.story.append(Paragraph(f"<i>\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u044f:</i> {rec}",
                                            ParagraphStyle("rt2", fontName=_FONT_REGULAR, fontSize=9,
                                                           leading=13, textColor=GRAY, alignment=TA_LEFT,
                                                           leftIndent=24, spaceAfter=2)))
            self._spacer(1)

        self.story.append(PageBreak())

    # ════════════════════════════════════════════════════════════
    # 6. ACTION PLAN
    # ════════════════════════════════════════════════════════════
    def _action_plan(self, data):
        self.story.append(Paragraph("\u041f\u043b\u0430\u043d \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439", styles["SecTitle"]))
        self._divider()

        recs = data.get("recommendations", [])
        if not recs:
            recs = [ins for ins in data.get("insights", []) if ins.get("category") == "recommendation"]

        if recs:
            for i, rec in enumerate(recs, 1):
                title = rec.get("title", "\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u044f")
                desc = rec.get("recommendation") or rec.get("description", "")
                self.story.append(Paragraph(f"{i}. <b>{title}</b>", styles["RecT"]))
                if desc:
                    self.story.append(Paragraph(desc, styles["RecD"]))
        else:
            defaults = [
                "\u041f\u0443\u0431\u043b\u0438\u043a\u0443\u0439\u0442\u0435 \u043a\u043e\u043d\u0442\u0435\u043d\u0442 \u0440\u0435\u0433\u0443\u043b\u044f\u0440\u043d\u043e (3-5 \u0440\u0430\u0437 \u0432 \u043d\u0435\u0434\u0435\u043b\u044e)",
                "\u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439\u0442\u0435 \u043b\u0443\u0447\u0448\u0435\u0435 \u0432\u0440\u0435\u043c\u044f \u0434\u043b\u044f \u043f\u0443\u0431\u043b\u0438\u043a\u0430\u0446\u0438\u0439",
                "\u0422\u0435\u0441\u0442\u0438\u0440\u0443\u0439\u0442\u0435 \u0440\u0430\u0437\u043d\u044b\u0435 \u0444\u043e\u0440\u043c\u0430\u0442\u044b: \u0432\u0438\u0434\u0435\u043e, \u043a\u0430\u0440\u0443\u0441\u0435\u043b\u0438, \u043e\u043f\u0440\u043e\u0441\u044b",
                "\u041e\u0442\u0432\u0435\u0447\u0430\u0439\u0442\u0435 \u043d\u0430 \u043a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0438 \u0432 \u043f\u0435\u0440\u0432\u044b\u0435 \u0447\u0430\u0441\u044b",
                "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 \u043f\u0440\u0438\u0437\u044b\u0432\u044b \u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044e \u0432 \u043a\u0430\u0436\u0434\u043e\u043c \u043f\u043e\u0441\u0442\u0435",
            ]
            for i, rec in enumerate(defaults, 1):
                self.story.append(Paragraph(f"{i}. {rec}", styles["RecT"]))

        self._spacer(16)
        bar = Table([[""]], colWidths=[80], rowHeights=[3],
                    style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
        self.story.append(bar)
        self._spacer(6)
        self.story.append(Paragraph(
            f"Данный отчет подготовлен для {_safe_text(getattr(self, 'company_name', 'Marketing Analytics'))} на основе загруженных данных.",
            ParagraphStyle("disp", fontName=_FONT_REGULAR, fontSize=8, leading=11,
                           textColor=GRAY_LIGHT, alignment=TA_CENTER)))

    # ════════════════════════════════════════════════════════════
    # APPENDIX A \u2013 FULL-PAGE LANDSCAPE CHARTS
    # ════════════════════════════════════════════════════════════
    def _appendix_a(self, data):
        charts = data.get("charts", {})
        chart_defs = [
            ("timeseries", "\u0414\u0438\u043d\u0430\u043c\u0438\u043a\u0430 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432",
             "\u0412\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u0439 \u0440\u044f\u0434 \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u0435\u0439 \u0441 \u0442\u0440\u0435\u043d\u0434\u043e\u0432\u043e\u0439 \u043b\u0438\u043d\u0438\u0435\u0439."),
            ("barchart", "\u0422\u043e\u043f \u043f\u043e\u0441\u0442\u043e\u0432 \u043f\u043e \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430\u043c",
             "\u041d\u0430\u0438\u0431\u043e\u043b\u0435\u0435 \u043f\u043e\u043f\u0443\u043b\u044f\u0440\u043d\u044b\u0435 \u043f\u0443\u0431\u043b\u0438\u043a\u0430\u0446\u0438\u0438 \u0437\u0430 \u043f\u0435\u0440\u0438\u043e\u0434."),
            ("platforms", "\u0421\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 \u043f\u043b\u0430\u0442\u0444\u043e\u0440\u043c",
             "\u0421\u0440\u0430\u0432\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u043f\u043b\u0430\u0442\u0444\u043e\u0440\u043c \u043f\u043e \u043a\u043b\u044e\u0447\u0435\u0432\u044b\u043c \u043c\u0435\u0442\u0440\u0438\u043a\u0430\u043c."),
            ("distribution", "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u0432\u043e\u0432\u043b\u0435\u0447\u0451\u043d\u043d\u043e\u0441\u0442\u0438",
             "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 engagement rate \u0441 \u043a\u0432\u0430\u0440\u0442\u0438\u043b\u044f\u043c\u0438 \u0438 \u043f\u043b\u043e\u0442\u043d\u043e\u0441\u0442\u044c\u044e \u0440\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u044f."),
            ("dayofweek", "\u0410\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u044c \u043f\u043e \u0434\u043d\u044f\u043c \u043d\u0435\u0434\u0435\u043b\u0438",
             "\u0421\u0440\u0435\u0434\u043d\u0438\u0435 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u044b \u043f\u043e \u043a\u0430\u0436\u0434\u043e\u043c\u0443 \u0434\u043d\u044e \u043d\u0435\u0434\u0435\u043b\u0438."),
        ]

        fi = [0]

        def _fig_num():
            fi[0] += 1
            return fi[0]

        self.story.append(NextPageTemplate("Landscape"))
        self.story.append(PageBreak())

        self.story.append(Paragraph("\u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0410", styles["SecTitle"]))
        self.story.append(Paragraph("\u0412\u0438\u0437\u0443\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0434\u0430\u043d\u043d\u044b\u0445", ParagraphStyle(
            "AppSub", fontName=_FONT_REGULAR, fontSize=14, leading=18, textColor=GRAY, alignment=TA_LEFT, spaceAfter=12)))
        self.story.append(Paragraph(
            "\u041d\u0438\u0436\u0435 \u043f\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u044b \u0433\u0440\u0430\u0444\u0438\u043a\u0438 \u0438 \u0434\u0438\u0430\u0433\u0440\u0430\u043c\u043c\u044b, "
            "\u0443\u043f\u043e\u043c\u044f\u043d\u0443\u0442\u044b\u0435 \u0432 \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u043c \u0440\u0430\u0437\u0434\u0435\u043b\u0435 \u043e\u0442\u0447\u0451\u0442\u0430. \u041a\u0430\u0436\u0434\u044b\u0439 \u0433\u0440\u0430\u0444\u0438\u043a "
            "\u0440\u0430\u0437\u043c\u0435\u0449\u0451\u043d \u043d\u0430 \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u043e\u0439 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0435 \u0432 \u0430\u043b\u044c\u0431\u043e\u043c\u043d\u043e\u0439 \u043e\u0440\u0438\u0435\u043d\u0442\u0430\u0446\u0438\u0438.",
            styles["Body"]))
        self.story.append(PageBreak())

        # Global charts
        for key, label, desc in chart_defs:
            path = charts.get(key)
            if not path or not os.path.exists(path):
                continue
            n = _fig_num()
            self.story.append(Paragraph(f"\u0420\u0438\u0441. {n}. {label}", styles["FigTitle"]))
            self.story.append(Paragraph(desc, styles["FigDesc"]))
            self._spacer(2)
            img = self._safe_image(path, LS_CONTENT_W * 0.92, max_ratio=0.65)
            if img:
                self.story.append(img)
            self.story.append(PageBreak())

        # Radar
        radar_path = charts.get("radar")
        if radar_path and os.path.exists(radar_path):
            n = _fig_num()
            self.story.append(Paragraph(f"\u0420\u0438\u0441. {n}. \u041f\u0440\u043e\u0444\u0438\u043b\u044c \u044d\u0444\u0444\u0435\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u0438", styles["FigTitle"]))
            self.story.append(Paragraph("\u041b\u0435\u043f\u0435\u0441\u0442\u043a\u043e\u0432\u0430\u044f \u0434\u0438\u0430\u0433\u0440\u0430\u043c\u043c\u0430 \u043a\u043b\u044e\u0447\u0435\u0432\u044b\u0445 KPI.", styles["FigDesc"]))
            self._spacer(2)
            img = self._safe_image(radar_path, LS_CONTENT_W * 0.6, max_ratio=0.8)
            if img:
                self.story.append(img)
            self.story.append(PageBreak())

        # VK Post charts (if present)
        vk_charts = data.get("vk_post_charts", {})
        print(f"[PDF APPENDIX] vk_post_charts keys={list(vk_charts.keys())}", flush=True)
        vk_defs = [
            ("vk_engagement_comp", "\u0421\u043e\u0441\u0442\u0430\u0432 \u0432\u043e\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u044f VK",
             "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u0432\u0437\u0430\u0438\u043c\u043e\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439 \u043f\u043e \u0442\u0438\u043f\u0430\u043c."),
            ("vk_monthly", "\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u044b VK \u043f\u043e \u043c\u0435\u0441\u044f\u0446\u0430\u043c",
             "\u0414\u0438\u043d\u0430\u043c\u0438\u043a\u0430 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432 \u043f\u043e \u043c\u0435\u0441\u044f\u0446\u0430\u043c."),
            ("vk_views_dist", "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432 VK",
             "\u0413\u0438\u0441\u0442\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432 \u043f\u043e \u0437\u0430\u043f\u0438\u0441\u044f\u043c."),
            ("vk_er_trend", "\u0414\u0438\u043d\u0430\u043c\u0438\u043a\u0430 ER VK",
             "\u0418\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0435 Engagement Rate \u043f\u043e \u0437\u0430\u043f\u0438\u0441\u044f\u043c."),
            ("vk_pareto", "\u041a\u0440\u0438\u0432\u0430\u044f \u041f\u0430\u0440\u0435\u0442\u043e VK",
             "\u041a\u0430\u043a\u0430\u044f \u0434\u043e\u043b\u044f \u0437\u0430\u043f\u0438\u0441\u0435\u0439 \u043f\u0440\u0438\u043d\u043e\u0441\u0438\u0442 80% \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u043e\u0432."),
        ]
        for ck, cl, cd in vk_defs:
            cp = vk_charts.get(ck)
            if not cp or not os.path.exists(cp):
                continue
            n = _fig_num()
            self.story.append(Paragraph(f"\u0420\u0438\u0441. {n}. {cl}", styles["FigTitle"]))
            self.story.append(Paragraph(cd, styles["FigDesc"]))
            self._spacer(2)
            img = self._safe_image(cp, LS_CONTENT_W * 0.92, max_ratio=0.62)
            if img:
                self.story.append(img)
            self.story.append(PageBreak())
