import os
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__), ".matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from textwrap import wrap

# Ensure matplotlib finds system fonts (especially Arial for Cyrillic)
import matplotlib.font_manager as fm
for _f in ["C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf",
           "C:\\Windows\\Fonts\\segoeui.ttf", "C:\\Windows\\Fonts\\tahoma.ttf"]:
    if os.path.exists(_f):
        try:
            fm.fontManager.addfont(_f)
        except Exception:
            pass

sns.set_style("whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Segoe UI", "Tahoma", "DejaVu Sans", "Verdana"],
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.labelsize": 12,
    "figure.facecolor": "white",
    "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#E5E7EB",
    "axes.grid": True,
    "grid.alpha": 0.28,
    "grid.color": "#E5E7EB",
    "legend.frameon": True,
    "legend.fancybox": False,
    "legend.shadow": False,
    "savefig.dpi": 360,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.18,
})

ACCENT = "#1c5eaa"
ACCENT_LIGHT = "#ff4b01"
NEGATIVE = "#EF4444"
POSITIVE = "#10B981"
WARNING = "#F59E0B"
PURPLE = "#1c5eaa"
PINK = "#ff4b01"
COLORS = [ACCENT, ACCENT_LIGHT, POSITIVE, WARNING, NEGATIVE]

CHART_W = 14
CHART_H = 7.5


class ChartRenderer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _save(self, name: str) -> str:
        path = os.path.join(self.output_dir, name)
        fig = plt.gcf()
        fig.tight_layout(pad=1.8)
        plt.savefig(path, dpi=360, bbox_inches="tight", facecolor="white", pad_inches=0.18)
        plt.close("all")
        return path

    @staticmethod
    def _wrap_label(value: object, width: int = 28, max_lines: int = 3) -> str:
        text = str(value or "").strip()
        if not text:
            return "—"
        lines = wrap(text, width=width, break_long_words=True, break_on_hyphens=False)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(".") + "..."
        return "\n".join(lines)

    @staticmethod
    def _clean_numeric(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()

    @staticmethod
    def _style_axes(ax):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#E5E7EB")
        ax.spines["bottom"].set_color("#E5E7EB")
        ax.tick_params(colors="#475569", labelsize=10)
        ax.title.set_color("#0F172A")
        ax.xaxis.label.set_color("#334155")
        ax.yaxis.label.set_color("#334155")

    def time_series(self, df: pd.DataFrame, date_col: str, metrics: List[str],
                    title: str = "Динамика показателей", filename: str = "timeseries.png") -> str:
        if df.empty or date_col not in df.columns:
            return self._empty_chart(filename)

        plot_df = df.copy()
        if not np.issubdtype(plot_df[date_col].dtype, np.datetime64):
            plot_df[date_col] = pd.to_datetime(plot_df[date_col], errors="coerce")
        plot_df = plot_df.dropna(subset=[date_col]).sort_values(date_col)

        available = [m for m in metrics if m in plot_df.columns]
        if not available:
            return self._empty_chart(filename)

        for metric in available:
            plot_df[metric] = pd.to_numeric(plot_df[metric], errors="coerce").fillna(0)

        plot_df["_day"] = plot_df[date_col].dt.date
        daily = plot_df.groupby("_day")[available].sum().reset_index()
        daily["_day"] = pd.to_datetime(daily["_day"])
        daily = daily.sort_values("_day")

        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
        for i, m in enumerate(available):
            values = daily[m].values.astype(float)
            ax.plot(daily["_day"], values, color=COLORS[i % len(COLORS)],
                    linewidth=2, marker="o", markersize=4, label=self._label(m))
            if len(values) >= 7:
                # A rolling average communicates the real recent direction without
                # turning a one-day spike into a misleading linear forecast.
                smooth = pd.Series(values).rolling(window=7, min_periods=3).median()
                ax.plot(daily["_day"], smooth, linestyle="--", linewidth=1.8,
                        alpha=0.7, color=COLORS[i % len(COLORS)], label="Медиана 7 дней")

        ax.set_title(title, fontweight="bold", pad=18)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Значение")

        # Smart date labels — never overlap
        locator = mdates.AutoDateLocator(minticks=4, maxticks=12)
        formatter = mdates.ConciseDateFormatter(locator, formats=[
            "%Y",    # years
            "%b",    # months
            "%d.%m", # days
            "%H:%M", # hours
            "%H:%M", # minutes
            "%S",    # seconds
        ])
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate(rotation=35, ha="right")

        ax.legend(loc="upper left", fontsize=10, framealpha=0.96, borderpad=0.8)
        self._style_axes(ax)
        return self._save(filename)

    def bar_chart(self, data: pd.DataFrame, x_col: str, y_col: str,
                  title: str = "Топ постов", filename: str = "barchart.png",
                  limit: int = 10) -> str:
        if data.empty or x_col not in data.columns or y_col not in data.columns:
            return self._empty_chart(filename)

        plot_df = data.copy()
        plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors="coerce")
        plot_df = plot_df.dropna(subset=[y_col]).sort_values(y_col, ascending=False).head(limit)
        if plot_df.empty:
            return self._empty_chart(filename)
        plot_df = plot_df.sort_values(y_col, ascending=True)

        labels = plot_df[x_col].astype(str).apply(lambda s: self._wrap_label(s, width=34, max_lines=2))
        fig, ax = plt.subplots(figsize=(CHART_W, max(4.8, len(plot_df) * 0.62 + 1.3)))

        values = plot_df[y_col].values.astype(float)
        bars = ax.barh(range(len(plot_df)), values,
                       color=ACCENT, height=0.6, edgecolor="white", linewidth=0.5)

        ax.set_yticks(range(len(plot_df)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title(title, fontweight="bold", pad=15)
        ax.set_xlabel("Просмотры")

        max_value = max(values) if len(values) else 0
        label_offset = max(max_value * 0.01, 1)
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + label_offset,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:,.0f}", va="center", fontsize=8)

        ax.set_xlim(0, max(max_value * 1.18, 1))
        self._style_axes(ax)
        return self._save(filename)

    def platform_comparison(self, platforms: List, filename: str = "platforms.png") -> str:
        if not platforms:
            return self._empty_chart(filename)

        def _get(p, attr):
            if isinstance(p, dict):
                return p.get(attr, 0)
            return getattr(p, attr, 0)

        names = [self._wrap_label(_get(p, "platform"), width=16, max_lines=2) for p in platforms]
        views = [float(_get(p, "total_views")) for p in platforms]
        engagement = [float(_get(p, "total_engagement")) for p in platforms]
        er = [float(_get(p, "engagement_rate")) for p in platforms]

        chart_specs = [
            (views, "Просмотры", "{:,.0f}"),
            (engagement, "Вовлечение", "{:,.0f}"),
            (er, "ER %", "{:.2f}%"),
        ]
        chart_specs = [(vals, title, fmt) for vals, title, fmt in chart_specs if any(v > 0 for v in vals)]
        if not chart_specs:
            return self._empty_chart(filename, "Недостаточно данных для сравнения платформ")

        fig, axes = plt.subplots(1, len(chart_specs), figsize=(max(6, 5.4 * len(chart_specs)), 6.6))
        axes = np.atleast_1d(axes)
        for ax, (vals, title, fmt) in zip(axes, chart_specs):
            max_val = max(vals) if vals else 0
            colors_bars = [ACCENT if v == max_val else ACCENT_LIGHT for v in vals]
            ax.bar(names, vals, color=colors_bars, edgecolor="white", linewidth=0.5)
            ax.set_title(title, fontweight="bold", fontsize=13)
            ax.tick_params(axis="x", rotation=0)
            for i, v in enumerate(vals):
                ax.text(i, v + max(max_val * 0.015, 1), fmt.format(v), ha="center", fontsize=8)
            ax.set_ylim(0, max(max_val * 1.16, 1))
            self._style_axes(ax)

        return self._save(filename)

    def engagement_distribution(self, df: pd.DataFrame, column: str = "engagement_rate",
                                 filename: str = "distribution.png") -> str:
        if column not in df.columns or df[column].dropna().empty:
            return self._empty_chart(filename)

        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
        data = self._clean_numeric(df[column])
        if data.empty:
            return self._empty_chart(filename)

        n = len(data)
        bins = min(15, max(5, int(np.sqrt(n))))

        sns.histplot(data, bins=bins, color=ACCENT,
                     alpha=0.5, edgecolor="white", linewidth=0.5, ax=ax)

        # KDE overlay for distribution shape
        try:
            sns.kdeplot(data, color=ACCENT, linewidth=2, ax=ax)
        except Exception:
            pass

        ax.axvline(data.mean(), color=NEGATIVE, linestyle="--", linewidth=2,
                   label=f"Среднее: {data.mean():.1f}%")
        ax.axvline(data.median(), color=POSITIVE, linestyle=":", linewidth=2,
                   label=f"Медиана: {data.median():.1f}%")
        ax.axvline(data.quantile(0.25), color=WARNING, linestyle="-.", linewidth=1.5,
                   alpha=0.7, label=f"Q1: {data.quantile(0.25):.1f}%")
        ax.axvline(data.quantile(0.75), color=WARNING, linestyle="-.", linewidth=1.5,
                   alpha=0.7, label=f"Q3: {data.quantile(0.75):.1f}%")

        ax.set_title(f"Распределение Engagement Rate (n={n})", fontweight="bold")
        ax.set_xlabel("Engagement Rate (%)")
        ax.set_ylabel("Количество постов")
        ax.legend(fontsize=9, framealpha=0.96, borderpad=0.8)
        self._style_axes(ax)
        return self._save(filename)

    def day_of_week(self, df: pd.DataFrame, filename: str = "dayofweek.png") -> str:
        if df.empty:
            return self._empty_chart(filename)
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H * 0.8))
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            return self._empty_chart(filename)
        col = numeric_cols[0]
        day_names = df["day_name"].tolist() if "day_name" in df.columns else list(df.index)
        ordered_days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс",
                        "Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье",
                        "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        order_map = {d: i for i, d in enumerate(ordered_days)}
        paired = sorted(zip(day_names, df[col].values), key=lambda x: order_map.get(x[0], 99))
        sorted_names, sorted_vals = zip(*paired) if paired else (day_names, df[col].values)
        colors_bar = [ACCENT if v == max(sorted_vals) else ACCENT_LIGHT for v in sorted_vals]
        bars = ax.bar(range(len(sorted_names)), sorted_vals, color=colors_bar,
                      edgecolor="white", linewidth=0.5)
        ax.set_xticks(range(len(sorted_names)))
        ax.set_xticklabels([self._wrap_label(n, width=12, max_lines=2) for n in sorted_names], fontsize=11)
        for bar, val in zip(bars, sorted_vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f"{val:,.0f}", ha="center", va="bottom", fontsize=9)
        ax.set_title("Средние просмотры по дням недели", fontweight="bold", pad=15)
        ax.set_ylabel("Средние просмотры")
        ax.tick_params(axis="x", rotation=0)
        self._style_axes(ax)
        return self._save(filename)

    def kpi_radar(self, metrics: Dict[str, float], filename: str = "radar.png") -> str:
        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
        categories = ["Общий охват", "Вовлечённость", "Рост", "Вирусность", "Стабильность"]

        total_v = metrics.get("total_views", 0)
        er = metrics.get("avg_engagement_rate", 0)
        fg = abs(metrics.get("follower_growth_pct", 0))
        vs = min(metrics.get("virality_score", 0) * 10, 100)
        trend_val = abs(metrics.get("views_trend", 0))
        stability = max(0, min(100, 100 - trend_val * 0.5))

        values = [
            min(total_v / 50000 * 100, 100),
            min(er * 5, 100),
            min(fg, 100),
            min(vs, 100),
            stability,
        ]
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        ax.plot(angles, values, color=ACCENT, linewidth=2.5)
        ax.fill(angles, values, alpha=0.1, color=ACCENT)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11, fontweight="bold")
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color="#999")
        ax.set_title("Профиль эффективности", fontweight="bold", pad=25, fontsize=14)
        plt.tight_layout()
        return self._save(filename)

    def engagement_composition(self, df: pd.DataFrame, likes_col: str, comments_col: str,
                                shares_col: str, saves_col: str,
                                filename: str = "engagement_comp.png") -> str:
        cols = [c for c in [likes_col, comments_col, shares_col, saves_col] if c in df.columns]
        if not cols:
            return self._empty_chart(filename)
        values = [pd.to_numeric(df[c], errors="coerce").sum() for c in cols]
        if sum(values) == 0:
            return self._empty_chart(filename)
        labels = {"likes": "Лайки", "comments": "Комментарии", "shares": "Репосты", "saves": "Сохранения"}
        lbls = [labels.get(c, c) for c in cols]
        colors_pie = [ACCENT, POSITIVE, WARNING, PURPLE, PINK][:len(cols)]
        fig, ax = plt.subplots(figsize=(8, 6))
        wedges, texts, autotexts = ax.pie(
            values, labels=None, autopct="%1.1f%%", colors=colors_pie,
            startangle=90, pctdistance=0.78,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5})
        for t in autotexts:
            t.set_fontsize(10); t.set_fontweight("bold")
        ax.set_title("Состав вовлечения", fontweight="bold", pad=20, fontsize=14)
        ax.legend(wedges, lbls, loc="center left", bbox_to_anchor=(1.02, 0.5),
                  fontsize=10, framealpha=0.96)
        return self._save(filename)

    def monthly_trend(self, df: pd.DataFrame, date_col: str, views_col: str,
                      filename: str = "monthly_trend.png") -> str:
        if date_col not in df.columns or views_col not in df.columns:
            return self._empty_chart(filename)
        plot_df = df.copy()
        if not np.issubdtype(plot_df[date_col].dtype, np.datetime64):
            plot_df[date_col] = pd.to_datetime(plot_df[date_col], errors="coerce")
        plot_df = plot_df.dropna(subset=[date_col])
        plot_df["_month"] = plot_df[date_col].dt.to_period("M").dt.to_timestamp()
        monthly = plot_df.groupby("_month")[views_col].sum().reset_index().sort_values("_month")
        if monthly.empty:
            return self._empty_chart(filename)
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H * 0.8))
        vals = monthly[views_col].values.astype(float)
        ax.bar(range(len(monthly)), vals, color=ACCENT, edgecolor="white", linewidth=0.5, width=0.6)
        ax.set_xticks(range(len(monthly)))
        ax.set_xticklabels([d.strftime("%b %Y") for d in monthly["_month"]], rotation=30, ha="right", fontsize=9)
        ax.set_title("Просмотры по месяцам", fontweight="bold", pad=15)
        ax.set_ylabel("Просмотры")
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8)
        self._style_axes(ax)
        return self._save(filename)

    def views_distribution(self, df: pd.DataFrame, views_col: str,
                           filename: str = "views_dist.png") -> str:
        if views_col not in df.columns:
            return self._empty_chart(filename)
        data = self._clean_numeric(df[views_col])
        if data.empty:
            return self._empty_chart(filename)
        n = len(data)
        bins = min(15, max(5, int(np.sqrt(n))))
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H * 0.8))
        ax.hist(data, bins=bins, color=ACCENT, alpha=0.6, edgecolor="white", linewidth=0.5)
        ax.axvline(data.mean(), color=NEGATIVE, linestyle="--", linewidth=2,
                   label=f"Среднее: {data.mean():,.0f}")
        ax.axvline(data.median(), color=POSITIVE, linestyle=":", linewidth=2,
                   label=f"Медиана: {data.median():,.0f}")
        ax.axvline(data.quantile(0.25), color=WARNING, linestyle="-.", linewidth=1.5,
                   alpha=0.7, label=f"Q1: {data.quantile(0.25):,.0f}")
        ax.axvline(data.quantile(0.75), color=WARNING, linestyle="-.", linewidth=1.5,
                   alpha=0.7, label=f"Q3: {data.quantile(0.75):,.0f}")
        ax.set_title(f"Распределение просмотров (n={n})", fontweight="bold")
        ax.set_xlabel("Просмотры")
        ax.set_ylabel("Количество постов")
        ax.legend(fontsize=9, framealpha=0.96, borderpad=0.8)
        self._style_axes(ax)
        return self._save(filename)

    def er_trend(self, df: pd.DataFrame, date_col: str, er_col: str = "engagement_rate",
                 filename: str = "er_trend.png") -> str:
        if er_col not in df.columns or date_col not in df.columns:
            return self._empty_chart(filename)
        plot_df = df.copy()
        if not np.issubdtype(plot_df[date_col].dtype, np.datetime64):
            plot_df[date_col] = pd.to_datetime(plot_df[date_col], errors="coerce")
        plot_df = plot_df.dropna(subset=[date_col, er_col]).sort_values(date_col)
        if len(plot_df) < 3:
            return self._empty_chart(filename)
        vals = self._clean_numeric(plot_df[er_col])
        if vals.empty:
            return self._empty_chart(filename)
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H * 0.8))
        ax.plot(range(len(vals)), vals.values, color=ACCENT, marker="o", markersize=5,
                linewidth=1.5, label="ER %")
        if len(vals) >= 5:
            roll = vals.rolling(window=3, min_periods=1).mean()
            ax.plot(range(len(vals)), roll.values, color=NEGATIVE, linewidth=2.5,
                    linestyle="--", label="Средняя (3 поста)")
        ax.set_title("Динамика Engagement Rate", fontweight="bold", pad=15)
        ax.set_xlabel("Посты по порядку")
        ax.set_ylabel("ER %")
        ax.legend(fontsize=9, framealpha=0.96, borderpad=0.8)
        self._style_axes(ax)
        return self._save(filename)

    def pareto_chart(self, df: pd.DataFrame, views_col: str, name_col: Optional[str] = None,
                     filename: str = "pareto.png") -> str:
        if views_col not in df.columns:
            return self._empty_chart(filename)
        data = self._clean_numeric(df[views_col])
        if data.empty:
            return self._empty_chart(filename)
        sorted_vals = np.sort(data.values)[::-1]
        total = sorted_vals.sum()
        if total <= 0:
            return self._empty_chart(filename)
        cumulative = np.cumsum(sorted_vals) / total * 100
        post_pct = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals) * 100
        fig, ax1 = plt.subplots(figsize=(CHART_W, CHART_H * 0.8))
        ax1.bar(range(len(sorted_vals)), sorted_vals, color=ACCENT_LIGHT, alpha=0.6,
                edgecolor="white", linewidth=0.3, label="Просмотры")
        ax1.set_ylabel("Просмотры", color=ACCENT)
        ax2 = ax1.twinx()
        ax2.plot(range(len(sorted_vals)), cumulative, color=NEGATIVE, linewidth=2.5,
                 marker="D", markersize=4, label="Накопленный %")
        ax2.axhline(80, color=WARNING, linestyle="--", alpha=0.6, linewidth=1)
        ax2.set_ylabel("Накопленный %", color=NEGATIVE)
        ax2.set_ylim(0, 105)
        pct_80 = np.searchsorted(cumulative, 80) + 1
        ax1.set_title(f"Кривая Парето: {pct_80} постов ({pct_80/len(sorted_vals)*100:.0f}%) "
                      f"дают 80% просмотров", fontweight="bold")
        ax1.set_xlabel("Посты (от лучшего к худшему)")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, framealpha=0.96, loc="upper right")
        self._style_axes(ax1)
        self._style_axes(ax2)
        return self._save(filename)

    def _empty_chart(self, filename: str, msg: str = "Нет данных") -> str:
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H * 0.8))
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=14, color="#999")
        ax.set_frame_on(False)
        ax.set_xticks([])
        ax.set_yticks([])
        return self._save(filename)

    @staticmethod
    def _label(m: str) -> str:
        mapping = {
            "views": "Просмотры", "likes": "Лайки", "comments": "Комментарии",
            "shares": "Репосты", "saves": "Сохранения",
            "followers": "Подписчики", "total_engagement": "Вовлечение",
            "engagement_rate": "ER %",
            "Просмотры видео": "Просмотры", "Просмотры": "Просмотры",
            "Лайки": "Лайки", "Комментарии": "Комментарии",
            "Репосты": "Репосты", "Охват": "Охват",
        }
        return mapping.get(m, m)
