from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd


BENCHMARKS = {
    "youtube": {
        "label": "YouTube",
        "er": (1.5, 4.0),
        "posting_per_week": (1.0, 3.0),
        "avg_views": (1000, 10000),
    },
    "vk": {
        "label": "VK",
        "er": (2.0, 6.0),
        "posting_per_week": (3.0, 7.0),
        "avg_views": (800, 8000),
    },
    "telegram": {
        "label": "Telegram",
        "er": (8.0, 20.0),
        "posting_per_week": (4.0, 14.0),
        "avg_views": (500, 5000),
    },
    "generic": {
        "label": "Соцсети",
        "er": (2.0, 5.0),
        "posting_per_week": (3.0, 7.0),
        "avg_views": (700, 7000),
    },
}


def _canon_col(column_map: Dict[str, str], canon: str, df: pd.DataFrame) -> Optional[str]:
    col = column_map.get(canon)
    return col if col in df.columns else None


def _num(df: pd.DataFrame, col: Optional[str]) -> pd.Series:
    if not col or col not in df.columns:
        return pd.Series(0, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)


def _metrics_for(df: pd.DataFrame, column_map: Dict[str, str]) -> Dict[str, float]:
    views_col = _canon_col(column_map, "views", df)
    likes_col = _canon_col(column_map, "likes", df)
    comments_col = _canon_col(column_map, "comments", df)
    shares_col = _canon_col(column_map, "shares", df)
    saves_col = _canon_col(column_map, "saves", df)

    views = _num(df, views_col)
    likes = _num(df, likes_col)
    comments = _num(df, comments_col)
    shares = _num(df, shares_col)
    saves = _num(df, saves_col)
    engagement = likes + comments + shares + saves
    total_views = float(views.sum())
    total_engagement = float(engagement.sum())
    return {
        "post_count": int(len(df)),
        "total_views": total_views,
        "total_engagement": total_engagement,
        "avg_views": float(views.mean()) if len(views) else 0,
        "avg_engagement_rate": float(total_engagement / total_views * 100) if total_views > 0 else 0,
    }


def _delta(current: float, previous: float) -> Dict[str, float | str]:
    absolute = float(current - previous)
    percent = float(absolute / previous * 100) if previous else 0
    if percent > 3:
        direction = "up"
    elif percent < -3:
        direction = "down"
    else:
        direction = "flat"
    return {"absolute": absolute, "percent": percent, "direction": direction}


def _period_summary(label: str, current: pd.DataFrame, previous: pd.DataFrame, column_map: Dict[str, str]) -> Dict:
    current_metrics = _metrics_for(current, column_map)
    previous_metrics = _metrics_for(previous, column_map)
    deltas = {
        key: _delta(current_metrics.get(key, 0), previous_metrics.get(key, 0))
        for key in ("total_views", "total_engagement", "avg_engagement_rate", "post_count", "avg_views")
    }
    drivers = []
    if deltas["total_views"]["direction"] == "up":
        drivers.append("охват вырос относительно предыдущего периода")
    elif deltas["total_views"]["direction"] == "down":
        drivers.append("основная просадка пришлась на охват")
    if deltas["avg_engagement_rate"]["direction"] == "up":
        drivers.append("качество вовлечения улучшилось")
    elif deltas["avg_engagement_rate"]["direction"] == "down":
        drivers.append("ER снизился, аудитория реагирует слабее")
    if deltas["post_count"]["direction"] == "up":
        drivers.append("частота публикаций выше прошлого периода")
    elif deltas["post_count"]["direction"] == "down":
        drivers.append("частота публикаций ниже прошлого периода")

    platform_col = _canon_col(column_map, "platform", current)
    if platform_col and platform_col in current.columns and platform_col in previous.columns:
        current_by_platform = current.groupby(platform_col).apply(
            lambda part: _metrics_for(part, column_map)["total_views"]
        )
        previous_by_platform = previous.groupby(platform_col).apply(
            lambda part: _metrics_for(part, column_map)["total_views"]
        )
        contribution = current_by_platform.subtract(previous_by_platform, fill_value=0)
        if not contribution.empty and contribution.abs().max() > 0:
            leader = contribution.abs().idxmax()
            change = contribution.loc[leader]
            verb = "рост" if change > 0 else "снижение"
            drivers.append(f"{leader}: наибольший вклад в изменение охвата ({verb} на {abs(change):,.0f})")
    return {
        "label": label,
        "current": current_metrics,
        "previous": previous_metrics,
        "deltas": deltas,
        "drivers": drivers[:3],
    }


def compute_period_comparison(df: pd.DataFrame, column_map: Dict[str, str]) -> Optional[Dict]:
    date_col = _canon_col(column_map, "date", df)
    if not date_col:
        return None
    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    if work.empty:
        return None

    last_date = work[date_col].max()
    current_month_start = last_date.replace(day=1).normalize()
    previous_month_end = current_month_start - pd.Timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1).normalize()

    current_month = work[(work[date_col] >= current_month_start) & (work[date_col] <= last_date)]
    # Compare the same number of elapsed calendar days. A partial current month
    # must never be compared with a full previous month.
    elapsed_days = int((last_date.normalize() - current_month_start).days) + 1
    comparable_previous_end = min(
        previous_month_start + pd.Timedelta(days=elapsed_days - 1), previous_month_end
    )
    previous_month = work[(work[date_col] >= previous_month_start) & (work[date_col] <= comparable_previous_end)]

    current_quarter = last_date.to_period("Q")
    previous_quarter = current_quarter - 1
    current_quarter_df = work[work[date_col].dt.to_period("Q") == current_quarter]
    previous_quarter_df = work[work[date_col].dt.to_period("Q") == previous_quarter]

    result = {}
    if not current_month.empty and not previous_month.empty:
        result["month"] = _period_summary(
            f"Этот месяц по {elapsed_days}-й день vs прошлый месяц", current_month, previous_month, column_map
        )
    if not current_quarter_df.empty and not previous_quarter_df.empty:
        result["quarter"] = _period_summary("Этот квартал vs прошлый", current_quarter_df, previous_quarter_df, column_map)
    return result or None


def _platform_key(platforms: List[str]) -> str:
    text = " ".join(platforms).lower()
    if "youtube" in text or "ютуб" in text:
        return "youtube"
    if "telegram" in text or "телеграм" in text:
        return "telegram"
    if "vk" in text or "вк" in text or "vkontakte" in text:
        return "vk"
    return "generic"


def _benchmark_status(value: float, low: float, high: float) -> str:
    if value < low:
        return "below"
    if value > high:
        return "above"
    return "normal"


def compute_benchmarks(metrics: Dict[str, float], platforms: List[str], source_report_type: str = "") -> Dict:
    if source_report_type == "audience":
        return {
            "is_applicable": False,
            "platform_label": "Выгрузка аудитории",
            "rows": [],
            "summary": "Нормы ER, частоты публикаций и просмотров не применяются к агрегированным данным аудитории.",
        }
    key = _platform_key(platforms)
    bench = BENCHMARKS[key]
    post_count = float(metrics.get("post_count", 0) or 0)
    posting_density = float(metrics.get("posting_density", 0) or 0)
    posting_per_week = posting_density * 7 if posting_density else 0
    values = {
        "er": float(metrics.get("avg_engagement_rate", 0) or 0),
        "posting_per_week": posting_per_week,
        "avg_views": float(metrics.get("avg_views", 0) or 0),
    }
    rows = []
    labels = {
        "er": "Engagement Rate",
        "posting_per_week": "Публикаций в неделю",
        "avg_views": "Средние просмотры",
    }
    units = {"er": "%", "posting_per_week": "", "avg_views": ""}
    for metric, value in values.items():
        low, high = bench[metric]
        rows.append({
            "metric": metric,
            "label": labels[metric],
            "value": value,
            "unit": units[metric],
            "low": low,
            "high": high,
            "status": _benchmark_status(value, low, high),
        })
    summary_bits = []
    below = [row["label"] for row in rows if row["status"] == "below"]
    above = [row["label"] for row in rows if row["status"] == "above"]
    if below:
        summary_bits.append("ниже нормы: " + ", ".join(below))
    if above:
        summary_bits.append("выше нормы: " + ", ".join(above))
    if not summary_bits:
        summary_bits.append("ключевые показатели находятся в рабочем диапазоне")
    return {
        "is_applicable": True,
        "platform_key": key,
        "platform_label": bench["label"],
        "post_count": post_count,
        "rows": rows,
        "summary": "; ".join(summary_bits),
    }
