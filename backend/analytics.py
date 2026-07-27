import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from scipy import stats
from dataclasses import dataclass


def _parse_number(value) -> Optional[float]:
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    if pd.isna(value) or value is None:
        return None
    s = str(value).strip().replace(" ", "").replace(",", ".")
    if not s:
        return None
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    suffix = s[-1].lower()
    if suffix in multipliers:
        num_part = s[:-1]
        try:
            return float(num_part) * multipliers[suffix]
        except ValueError:
            pass
    s_clean = re.sub(r"[^\d.\-]", "", s)
    if not s_clean:
        return None
    try:
        return float(s_clean)
    except ValueError:
        return None


@dataclass
class TrendResult:
    direction: str
    slope: float
    p_value: float
    description: str


@dataclass
class PeakResult:
    index: int
    value: float
    date: Optional[str]
    magnitude: float


@dataclass
class AnomalyResult:
    index: int
    value: float
    date: Optional[str]
    z_score: float
    type: str


@dataclass
class PlatformScore:
    platform: str
    total_views: float
    total_engagement: float
    engagement_rate: float
    post_count: int
    score: float


@dataclass
class ContentClass:
    classification: str  # high_impact | medium_impact | low_impact
    threshold: float


class AnalyticsEngine:
    def __init__(self, df: pd.DataFrame, column_map: Dict[str, str]):
        self.df = df
        self.column_map = column_map
        self.date_col = self._find_col("date")
        self.views_col = self._find_col("views")
        self.likes_col = self._find_col("likes")
        self.comments_col = self._find_col("comments")
        self.shares_col = self._find_col("shares")
        self.saves_col = self._find_col("saves")
        self.platform_col = self._find_col("platform")
        self.post_name_col = self._find_col("post_name")

    def _find_col(self, canon: str) -> Optional[str]:
        for col, c in self.column_map.items():
            if col == canon and c in self.df.columns:
                return c
        return None

    def _safe_num(self, series):
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(0).astype(float)
        return series.apply(_parse_number).fillna(0).astype(float)

    # ── Trend with moving average smoothing ──
    def analyze_trend(self, column: str, window: int = 5) -> TrendResult:
        if column not in self.df.columns:
            return TrendResult("unknown", 0, 1, "Недостаточно данных")
        data = self._safe_num(self.df[column]).dropna().values
        if len(data) < 3:
            return TrendResult("stable", 0, 1, "Недостаточно данных для тренда")
        # Apply moving average smoothing
        if len(data) >= window:
            smoothed = np.convolve(data, np.ones(window)/window, mode='valid')
        else:
            smoothed = data
        x = np.arange(len(smoothed))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, smoothed)

        if p_value < 0.05:
            if slope > 0:
                direction = "up"
                desc = f"Уверенный восходящий тренд (наклон: {slope:.2f} ед./период)"
            else:
                direction = "down"
                desc = f"Нисходящий тренд (наклон: {slope:.2f} ед./период)"
        else:
            direction = "stable"
            desc = "Стабильный, без выраженного тренда"

        return TrendResult(direction, slope, p_value, desc)

    # ── Weighted engagement score ──
    def weighted_engagement_score(self) -> float:
        l = self._safe_num(self.df[self.likes_col]) if self.likes_col else pd.Series(0, index=self.df.index)
        c = self._safe_num(self.df[self.comments_col]) if self.comments_col else pd.Series(0, index=self.df.index)
        s = self._safe_num(self.df[self.shares_col]) if self.shares_col else pd.Series(0, index=self.df.index)
        sa = self._safe_num(self.df[self.saves_col]) if self.saves_col else pd.Series(0, index=self.df.index)
        # Weighted: comments > shares > saves > likes (deeper engagement = higher weight)
        score = float((l * 1 + c * 3 + s * 2 + sa * 1.5).mean())
        return round(score, 2)

    # ── Content classification ──
    def classify_content(self, column: str = "views") -> pd.Series:
        if column not in self.df.columns:
            return pd.Series(["unknown"] * len(self.df))
        data = self._safe_num(self.df[column])
        q33 = data.quantile(0.33)
        q66 = data.quantile(0.66)
        def _class(v):
            if v >= q66: return "high_impact"
            if v >= q33: return "medium_impact"
            return "low_impact"
        return data.apply(_class)

    def detect_peaks(self, column: str, threshold: float = 2.0) -> List[PeakResult]:
        if column not in self.df.columns:
            return []
        data = self._safe_num(self.df[column]).values.astype(float)
        mean_v = np.mean(data)
        std_v = np.std(data)
        if std_v == 0:
            return []

        peaks = []
        for i in range(len(data)):
            z = (data[i] - mean_v) / std_v
            if z > threshold:
                date_str = None
                if self.date_col:
                    date_str = str(self.df[self.date_col].iloc[i])
                peaks.append(PeakResult(
                    index=i, value=float(data[i]),
                    date=date_str, magnitude=float(z)
                ))
        return sorted(peaks, key=lambda p: p.magnitude, reverse=True)

    def detect_anomalies(self, column: str, z_threshold: float = 2.5) -> List[AnomalyResult]:
        if column not in self.df.columns:
            return []
        data = self._safe_num(self.df[column]).values.astype(float)
        mean_v = np.mean(data)
        std_v = np.std(data)
        if std_v == 0:
            return []

        anomalies = []
        for i in range(len(data)):
            z = (data[i] - mean_v) / std_v
            if abs(z) > z_threshold:
                date_str = None
                if self.date_col:
                    date_str = str(self.df[self.date_col].iloc[i])
                anomalies.append(AnomalyResult(
                    index=i, value=float(data[i]),
                    date=date_str, z_score=float(z),
                    type="spike" if z > 0 else "drop"
                ))
        return anomalies

    def top_posts(self, column: str = "views", n: int = 10) -> pd.DataFrame:
        if column not in self.df.columns:
            return pd.DataFrame()
        cols = [column]
        if self.post_name_col:
            cols.append(self.post_name_col)
        if self.date_col:
            cols.append(self.date_col)
        if "engagement_rate" in self.df.columns:
            cols.append("engagement_rate")
        available = [c for c in cols if c in self.df.columns]
        result = self.df[available].copy()
        result = result.sort_values(column, ascending=False).head(n)
        return result.reset_index(drop=True)

    def platform_comparison(self) -> List[PlatformScore]:
        if not self.platform_col or self.platform_col not in self.df.columns:
            return []

        results = []
        for plat, group in self.df.groupby(self.platform_col):
            v = self._safe_num(group[self.views_col]) if self.views_col else pd.Series(0, index=group.index)
            l = self._safe_num(group[self.likes_col]) if self.likes_col else pd.Series(0, index=group.index)
            c = self._safe_num(group[self.comments_col]) if self.comments_col else pd.Series(0, index=group.index)
            s = self._safe_num(group[self.shares_col]) if self.shares_col else pd.Series(0, index=group.index)
            sa = self._safe_num(group[self.saves_col]) if self.saves_col else pd.Series(0, index=group.index)

            total_v = float(v.sum())
            total_e = float((l + c + s + sa).sum())
            er = (total_e / total_v * 100) if total_v > 0 else 0

            # Weighted score: views(0.25) + engagement(0.35) + ER(0.25) + consistency(0.15)
            consistency = min(len(group) * 5, 100)
            score = total_v * 0.25 + total_e * 0.35 + er * 10 * 0.25 + consistency * 0.15

            results.append(PlatformScore(
                platform=str(plat),
                total_views=total_v,
                total_engagement=total_e,
                engagement_rate=er,
                post_count=len(group),
                score=score
            ))

        results.sort(key=lambda p: p.score, reverse=True)
        return results

    def growth_over_time(self) -> pd.DataFrame:
        if not self.date_col or self.date_col not in self.df.columns:
            return pd.DataFrame()

        df = self.df.copy()
        df["period"] = df[self.date_col].dt.to_period("D")
        agg = {}
        if self.views_col:
            agg[self.views_col] = "sum"
        if self.likes_col:
            agg[self.likes_col] = "sum"
        if self.comments_col:
            agg[self.comments_col] = "sum"
        if self.shares_col:
            agg[self.shares_col] = "sum"
        if self.saves_col:
            agg[self.saves_col] = "sum"
        if "total_engagement" in df.columns:
            agg["total_engagement"] = "sum"

        if not agg:
            return pd.DataFrame()

        grouped = df.groupby("period").agg(agg).reset_index()
        grouped["period"] = grouped["period"].astype(str)
        return grouped

    def day_of_week_analysis(self) -> pd.DataFrame:
        if not self.date_col or self.date_col not in self.df.columns:
            return pd.DataFrame()
        df = self.df.copy()
        fallback = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
        names = df[self.date_col].dt.dayofweek.map({i: fallback[i] for i in range(7)})
        df["day_name"] = names
        order = {"Понедельник":0,"Вторник":1,"Среда":2,"Четверг":3,"Пятница":4,"Суббота":5,"Воскресенье":6,
                 "Пн":0,"Вт":1,"Ср":2,"Чт":3,"Пт":4,"Сб":5,"Вс":6,
                 "Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
        agg = {}
        if self.views_col:
            agg[self.views_col] = "mean"
        if self.likes_col:
            agg[self.likes_col] = "mean"
        if "engagement_rate" in df.columns:
            agg["engagement_rate"] = "mean"
        if not agg:
            return pd.DataFrame()
        result = df.groupby("day_name").agg(agg).reset_index()
        result["day_order"] = result["day_name"].map(order).fillna(99)
        result = result.sort_values("day_order").drop(columns="day_order")
        return result

    def wow_growth(self) -> Optional[Dict]:
        if not self.date_col or not self.views_col:
            return None
        df = self.df.copy()
        df["week"] = df[self.date_col].dt.isocalendar().week.astype(int)
        weekly = df.groupby("week")[self.views_col].sum()
        if len(weekly) < 2:
            return None
        growths = weekly.pct_change().dropna()
        avg_growth = float(growths.mean())
        return {
            "avg_weekly_growth": round(avg_growth * 100, 1),
            "max_weekly_growth": round(float(growths.max() * 100), 1),
            "min_weekly_growth": round(float(growths.min() * 100), 1),
            "weeks_analyzed": len(weekly),
        }


def vk_content_breakdown(processor) -> Optional[Dict]:
    """Build VK posts vs clips comparison data for PDF section."""
    vk_breakdown = getattr(processor, "vk_breakdown", None) or {}
    if not vk_breakdown:
        return None

    posts_df = vk_breakdown.get("posts")
    clips_df = vk_breakdown.get("clips")
    if posts_df is None and clips_df is None:
        return None

    result = {}
    for key, label in [("posts", "Записи"), ("clips", "Клипы")]:
        df = vk_breakdown.get(key)
        metrics = vk_breakdown.get(key + "_metrics", {})
        if df is not None and not df.empty:
            result[key] = {
                "label": label,
                "count": metrics.get("post_count", len(df)),
                "views": metrics.get("views", 0),
                "likes": metrics.get("likes", 0),
                "comments": metrics.get("comments", 0),
                "shares": metrics.get("shares", 0),
                "saves": metrics.get("saves", 0),
                "engagement": metrics.get("total_engagement", 0),
                "er": metrics.get("engagement_rate", 0),
            }

    # Compare metrics
    if len(result) == 2:
        for metric in ("views", "engagement", "er", "likes", "comments", "shares"):
            p = result["posts"].get(metric, 0) or 0
            c = result["clips"].get(metric, 0) or 0
            total = p + c
            if total > 0:
                result["compare_" + metric] = {
                    "posts_share": round(p / total * 100, 1),
                    "clips_share": round(c / total * 100, 1),
                }

    return result
