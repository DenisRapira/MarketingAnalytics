import pandas as pd
import numpy as np
import re
from typing import Dict, Optional, Tuple
from datetime import datetime

from column_mapper import detect_column_types, get_mapped_columns, suggest_date_format


def parse_number(value) -> Optional[float]:
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

class DataProcessor:
    def __init__(self, df: pd.DataFrame):
        self.raw_df = df
        self.df = df.copy()
        self.column_map: Dict[str, str] = {}
        self.metrics: Dict[str, float] = {}
        self.source_report_type: Optional[str] = None
        self.analysis_profile: Dict = {"warnings": [], "available_metrics": [], "unavailable_metrics": []}

    def process(self) -> Tuple[pd.DataFrame, Dict[str, str], Dict[str, float]]:
        if self._normalize_audience_export() or self._normalize_generic_metric_export():
            if not self.column_map:
                self.column_map = {
                    "date": "Дата",
                    "post_name": "Критерий",
                    "views": "Аудитория",
                    "content_type": "Раздел",
                    "platform": "Платформа",
                }
        else:
            detected = detect_column_types(self.df)
            self.column_map = get_mapped_columns(detected, self.df)
            self._apply_semantic_fallbacks()
        self._force_numeric()

        self._clean_duplicates()
        self._clean_empty_rows()
        self._normalize_dates()
        self._normalize_numbers()
        self._engineer_features()

        self.metrics = self._compute_metrics()
        self._build_analysis_profile()
        self.metrics["analysis_profile"] = self.analysis_profile
        if self.source_report_type:
            self.metrics["source_report_type"] = self.source_report_type
        self.vk_breakdown = self._vk_content_breakdown()
        return self.df, self.column_map, self.metrics

    def _apply_semantic_fallbacks(self):
        """Recover common headers even when a vendor export uses an unseen spelling."""
        aliases = {
            "date": ("дата", "date", "time", "время", "period", "период"),
            "views": ("просмотр", "охват", "reach", "impression", "view", "показ"),
            "likes": ("лайк", "like", "reaction", "реакц"),
            "comments": ("комментар", "comment", "reply", "ответ"),
            "shares": ("репост", "share", "forward", "пересыл"),
            "saves": ("сохран", "save", "bookmark"),
            "followers": ("подпис", "follower", "subscriber"),
            "platform": ("платформ", "platform", "channel", "канал", "source", "источник"),
            "post_name": ("заголов", "название", "текст", "title", "message", "content"),
        }
        for canon, variants in aliases.items():
            if canon in self.column_map:
                continue
            for col in self.df.columns:
                normalized = str(col).lower().strip()
                if any(token in normalized for token in variants):
                    self.column_map[canon] = str(col)
                    break

    def _normalize_generic_metric_export(self) -> bool:
        """Accept safe long-format exports without pretending they are post metrics."""
        if self.source_report_type:
            return False
        columns = {str(c).lower().strip(): str(c) for c in self.df.columns}
        date_col = next((original for name, original in columns.items() if name in {"date", "дата", "period", "период"}), None)
        value_col = next((original for name, original in columns.items() if name in {"value", "значение", "count", "количество"}), None)
        metric_col = next((original for name, original in columns.items() if name in {"metric", "метрика", "criterion", "критерий", "parameter", "параметр"}), None)
        if not date_col or not value_col:
            return False

        work = self.df.copy()
        work[value_col] = work[value_col].apply(parse_number)
        if work[value_col].notna().sum() == 0:
            return False
        work = work.dropna(subset=[value_col])
        work["Показатель"] = work[metric_col].astype(str) if metric_col else "Значение"
        grouped = work.groupby([date_col, "Показатель"], dropna=False)[value_col].sum().reset_index()
        grouped = grouped.rename(columns={date_col: "Дата", value_col: "Значение"})
        grouped["Раздел"] = "Метрика"
        grouped["Платформа"] = "Не определена"
        self.df = grouped[["Раздел", "Дата", "Показатель", "Платформа", "Значение"]]
        self.column_map = {
            "date": "Дата", "post_name": "Показатель", "views": "Значение",
            "content_type": "Раздел", "platform": "Платформа",
        }
        self.source_report_type = "metric_series"
        return True

    def _normalize_audience_export(self) -> bool:
        required = {"Дата", "Критерий", "Значение"}
        if not required.issubset(set(map(str, self.df.columns))):
            return False
        if "Аудитория" not in " ".join(map(str, self.df.columns)) and "Подраздел" not in self.df.columns:
            return False

        work = self.df.copy()
        work["Значение"] = work["Значение"].apply(parse_number).fillna(0).astype(float)
        grouped = (
            work.groupby(["Дата", "Критерий"], dropna=False)["Значение"]
            .sum()
            .reset_index()
            .rename(columns={"Значение": "Аудитория"})
        )
        grouped["Раздел"] = "Аудитория"
        grouped["Платформа"] = "VK"
        grouped["Сегмент"] = grouped["Критерий"].astype(str)
        self.df = grouped[["Раздел", "Дата", "Критерий", "Сегмент", "Платформа", "Аудитория"]]
        self.source_report_type = "audience"
        return True

    def _force_numeric(self):
        numeric_canons = {"views", "likes", "comments", "shares", "saves", "followers",
                          "clip_views", "clip_likes", "clip_comments", "clip_shares", "clip_saves"}
        for canon, col_name in self.column_map.items():
            if canon in numeric_canons and col_name in self.df.columns:
                s = self.df[col_name]
                if not pd.api.types.is_numeric_dtype(s):
                    converted = s.apply(parse_number).fillna(0).astype(float)
                    self.df[col_name] = converted

    def _clean_duplicates(self):
        before = len(self.df)
        self.df = self.df.drop_duplicates()
        if before - len(self.df) > 0:
            pass

    def _clean_empty_rows(self):
        needed = {"views", "likes", "date"}
        cols_in_df = [c for k, c in self.column_map.items() if k in needed and c in self.df.columns]
        if cols_in_df:
            self.df = self.df.dropna(subset=cols_in_df, how="all")
        self.df = self.df.dropna(how="all")

    def _normalize_dates(self):
        date_col = None
        for canon, col_name in self.column_map.items():
            if canon == "date":
                date_col = col_name
                break
        if date_col is None or date_col not in self.df.columns:
            return

        fmt = suggest_date_format(self.df[date_col])
        if fmt:
            self.df[date_col] = pd.to_datetime(
                self.df[date_col].astype(str), format=fmt, errors="coerce"
            )
        else:
            self.df[date_col] = pd.to_datetime(
                self.df[date_col], errors="coerce"
            )
        self.df = self.df.dropna(subset=[date_col])
        self.df = self.df.sort_values(date_col).reset_index(drop=True)

    def _normalize_numbers(self):
        numeric_canons = {"views", "likes", "comments", "shares", "saves", "followers",
                          "clip_views", "clip_likes", "clip_comments", "clip_shares", "clip_saves"}
        for canon, col_name in self.column_map.items():
            if canon in numeric_canons and col_name in self.df.columns:
                self.df[col_name] = (
                    pd.to_numeric(self.df[col_name], errors="coerce")
                    .fillna(0)
                    .astype(float)
                )

    def _engineer_features(self):
        v = self._canon_col("views")
        l = self._canon_col("likes")
        c = self._canon_col("comments")
        s = self._canon_col("shares")
        sa = self._canon_col("saves")
        f = self._canon_col("followers")

        def _safe_numeric(col_name):
            if col_name and col_name in self.df.columns:
                s = self.df[col_name]
                if pd.api.types.is_numeric_dtype(s):
                    return s.fillna(0).astype(float)
                return s.apply(parse_number).fillna(0).astype(float)
            return pd.Series(0, index=self.df.index)

        if v and (l or c or s or sa):
            l_data = _safe_numeric(l)
            c_data = _safe_numeric(c)
            s_data = _safe_numeric(s)
            sa_data = _safe_numeric(sa)
            total_eng = l_data + c_data + s_data + sa_data
            denom = pd.to_numeric(self.df[v], errors="coerce").fillna(0).replace(0, np.nan)
            self.df["engagement_rate"] = (total_eng / denom * 100).fillna(0)

        if l or c or s or sa:
            self.df["total_engagement"] = (
                _safe_numeric(l) + _safe_numeric(c) + _safe_numeric(s) + _safe_numeric(sa)
            )

        if v:
            total_v = self.df[v].sum()
            self.df["views_share"] = (self.df[v] / total_v * 100).fillna(0) if total_v > 0 else 0

            median_v = self.df[v].median()
            self.df["is_viral"] = (self.df[v] > median_v * 5).astype(int) if median_v > 0 else 0

        if f:
            fs = _safe_numeric(f)
            self.df["followers_growth_rate"] = fs.pct_change().fillna(0)



    def _vk_content_breakdown(self) -> Optional[Dict]:
        """Detect VK posts vs clips split and return separate DataFrames + metrics."""
        plat_col = self._canon_col("platform")
        is_vk = False
        if plat_col and plat_col in self.df.columns:
            vk_mask = self.df[plat_col].astype(str).str.lower().str.contains("vk|вк|vkontakte|вконтакте", na=False)
            is_vk = vk_mask.any()
        else:
            clip_cols = [self._canon_col(c) for c in
                         ["clip_views", "clip_likes", "clip_comments", "clip_shares", "clip_saves"]]
            is_vk = any(clip_cols)
        if not is_vk:
            # Also check content_type column for known VK content markers
            ct_col = self._canon_col("content_type")
            if ct_col and ct_col in self.df.columns:
                ct_vals = self.df[ct_col].astype(str).str.lower()
                is_vk = ct_vals.str.contains("post|запис|пост|текст|article|статья|clip|клип|video|видео", na=False).any()

        if not is_vk:
            return None

        result = {}
        type_col = self._canon_col("content_type")

        # --- Method 1: Split by content_type column ---
        if type_col and type_col in self.df.columns:
            type_vals = self.df[type_col].astype(str).str.lower()
            post_mask = type_vals.str.contains("post|запис|пост|текст|article|статья", na=False)
            clip_mask = type_vals.str.contains("clip|клип|video|видео|short|reel", na=False)

            if post_mask.any():
                result["posts"] = self.df[post_mask].copy()
            if clip_mask.any():
                result["clips"] = self.df[clip_mask].copy()

        # --- Method 2: Separate clip-prefixed columns ---
        clip_views_c = self._canon_col("clip_views")
        if clip_views_c and clip_views_c in self.df.columns:
            clip_data = {}
            for canon, col in self.column_map.items():
                if canon.startswith("clip_") and col in self.df.columns:
                    plain = canon.replace("clip_", "")
                    clip_data[plain] = self.df[col]
            if clip_data:
                clip_df = pd.DataFrame(clip_data)
                for col in clip_data:
                    clip_df[col] = pd.to_numeric(clip_df[col], errors="coerce").fillna(0).astype(float)
                result["clips"] = clip_df

        # --- Compute metrics for each ---
        for key in ("posts", "clips"):
            if key in result:
                sub_df = result[key]
                sub_metrics = {}
                for canon, col in self.column_map.items():
                    if canon in ("views","likes","comments","shares","saves","followers") and col in sub_df.columns:
                        sub_metrics[canon] = float(pd.to_numeric(sub_df[col], errors="coerce").fillna(0).sum())
                er = 0
                v = sub_metrics.get("views", 0)
                total_e = sum(sub_metrics.get(m, 0) for m in ("likes","comments","shares","saves"))
                if v > 0:
                    er = total_e / v * 100
                sub_metrics["engagement_rate"] = round(er, 2)
                sub_metrics["total_engagement"] = total_e
                sub_metrics["post_count"] = len(sub_df)
                result[key + "_metrics"] = sub_metrics

        return result if result else None

    def _canon_col(self, canon: str) -> Optional[str]:
        for col, c in self.column_map.items():
            if col == canon and c in self.df.columns:
                return c
        return None

    def _compute_metrics(self) -> Dict[str, float]:
        m: Dict[str, float] = {}
        v = self._canon_col("views")
        l = self._canon_col("likes")
        c = self._canon_col("comments")
        s = self._canon_col("shares")
        sa = self._canon_col("saves")
        f = self._canon_col("followers")

        def _num(col_name):
            if col_name and col_name in self.df.columns:
                s = self.df[col_name]
                if pd.api.types.is_numeric_dtype(s):
                    return s.fillna(0).astype(float)
                return s.apply(parse_number).fillna(0).astype(float)
            return pd.Series(0, index=self.df.index)

        if v:
            vs = _num(v)
            m["total_views"] = float(vs.sum())
            m["avg_views"] = float(vs.mean())
            m["median_views"] = float(vs.median())
            m["max_views"] = float(vs.max())
            m["min_views"] = float(vs.min())

        # Aggregate audience and generic metric exports do not contain posts or
        # interactions. Never manufacture ER, posting frequency or health scores.
        if self.source_report_type in {"audience", "metric_series"}:
            if v:
                m["post_count"] = int(len(self.df))
            return m
        if l:
            m["total_likes"] = float(_num(l).sum())
        if c:
            m["total_comments"] = float(_num(c).sum())
        if s:
            m["total_shares"] = float(_num(s).sum())
        if sa:
            m["total_saves"] = float(_num(sa).sum())

        if "engagement_rate" in self.df.columns:
            er = pd.to_numeric(self.df["engagement_rate"], errors="coerce").fillna(0)
            m["avg_engagement_rate"] = float(er.mean())
            m["max_engagement_rate"] = float(er.max())

        if "total_engagement" in self.df.columns:
            te = pd.to_numeric(self.df["total_engagement"], errors="coerce").fillna(0)
            m["total_engagement"] = float(te.sum())

        if v:
            m["post_count"] = int(len(self.df))
            if m.get("avg_engagement_rate", 0) > 0:
                m["virality_score"] = float(
                    m["max_engagement_rate"] / max(m["avg_engagement_rate"], 0.01)
                )
            v_data = _num(v).values
            m["views_trend"] = float(
                np.polyfit(range(len(v_data)), v_data, 1)[0]
                if len(v_data) > 1 else 0
            )

            if len(v_data) > 0 and m.get("total_views", 0) > 0:
                sorted_views = np.sort(v_data)[::-1]
                top_n = max(1, int(np.ceil(len(sorted_views) * 0.2)))
                m["top_20_views_share"] = float(sorted_views[:top_n].sum() / m["total_views"] * 100)
                m["content_efficiency_index"] = float(
                    min(100, (m.get("avg_engagement_rate", 0) * 7) + (m.get("virality_score", 0) * 4))
                )

        if f:
            fs = _num(f)
            if fs.sum() > 0:
                first_f = fs.iloc[0]
                last_f = fs.iloc[-1]
                m["follower_growth"] = float(last_f - first_f)
                m["follower_growth_pct"] = float(
                    ((last_f - first_f) / first_f * 100) if first_f > 0 else 0
                )

        # Engagement quality: comments per like
        if c and l:
            total_c = float(_num(c).sum())
            total_l = float(_num(l).sum())
            m["engagement_quality"] = round(total_c / total_l, 4) if total_l > 0 else 0

        total_eng = m.get("total_engagement", 0)
        total_views = m.get("total_views", 0)
        if total_eng > 0:
            m["conversation_rate"] = float(m.get("total_comments", 0) / total_eng * 100)
            m["amplification_rate"] = float(m.get("total_shares", 0) / total_eng * 100)
            m["save_intent_rate"] = float(m.get("total_saves", 0) / total_eng * 100)
        if total_views > 0:
            m["attention_quality"] = float(total_eng / total_views * 100)

        # Posting density
        date_col = self._canon_col("date")
        if v and date_col and date_col in self.df.columns:
            dates_clean = pd.to_datetime(self.df[date_col], errors="coerce").dropna()
            if not dates_clean.empty:
                days_range = (dates_clean.max() - dates_clean.min()).days
                m["posting_density"] = round(len(self.df) / max(days_range, 1), 2)

        # Best posting day
        if v and date_col and date_col in self.df.columns:
            dates = pd.to_datetime(self.df[date_col], errors="coerce")
            dow = dates.dt.dayofweek
            if not dow.isna().all():
                v_s = _num(v)
                dow_avg = v_s.groupby(dow.values).mean()
                best_dow = int(dow_avg.idxmax())
                day_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
                m["best_posting_day"] = day_names[best_dow]
                m["best_day_views"] = float(dow_avg.max())

        er_score = min(m.get("avg_engagement_rate", 0) / 6 * 35, 35)
        reach_score = min(np.log10(max(total_views, 1)) / 6 * 25, 25)
        trend_score = 15 if m.get("views_trend", 0) > 0 else 7 if m.get("views_trend", 0) == 0 else 2
        consistency_score = min(m.get("posting_density", 0) / 0.7 * 15, 15)
        depth_score = min(
            (m.get("conversation_rate", 0) + m.get("amplification_rate", 0) + m.get("save_intent_rate", 0)) / 20 * 10,
            10
        )
        m["marketing_health_score"] = round(er_score + reach_score + trend_score + consistency_score + depth_score, 1)

        return m

    def _build_analysis_profile(self):
        view_col = self._canon_col("views")
        date_col = self._canon_col("date")
        interaction_fields = [self._canon_col(key) for key in ("likes", "comments", "shares", "saves")]
        available = []
        if view_col:
            available.append("охват/значение")
        if date_col:
            available.append("динамика по датам")
        if any(interaction_fields):
            available.append("вовлечение и ER")
        if self._canon_col("platform"):
            available.append("сравнение платформ")

        unavailable = []
        if not any(interaction_fields):
            unavailable.append("ER и качество вовлечения")
        if self.source_report_type in {"audience", "metric_series"}:
            unavailable.extend(["частота публикаций", "контентные рекомендации", "бенчмарки постов"])

        warnings = []
        if not date_col:
            warnings.append("Дата не распознана: сравнение периодов и динамика отключены.")
        if not view_col:
            warnings.append("Основной показатель не распознан: нужен столбец охвата, просмотров или значения.")
        if len(self.df) < 3:
            warnings.append("В выборке меньше трех строк: тренды и статистические выводы ограничены.")
        if self.source_report_type == "audience":
            warnings.append("Это агрегированная выгрузка аудитории, а не статистика публикаций.")
        if self.source_report_type == "metric_series":
            warnings.append("Тип отчета определен как временной ряд показателей; метрики постов не рассчитываются.")

        report_type = self.source_report_type or ("post_metrics" if any(interaction_fields) else "reach_metrics")
        confidence = "high" if view_col and date_col else "medium" if view_col else "low"
        self.analysis_profile = {
            "report_type": report_type,
            "confidence": confidence,
            "rows": int(len(self.df)),
            "available_metrics": available,
            "unavailable_metrics": unavailable,
            "warnings": warnings,
        }
