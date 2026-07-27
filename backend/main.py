import os
import uuid
import json
import shutil
import re
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import traceback

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np

from data_processor import DataProcessor
from analytics import AnalyticsEngine, vk_content_breakdown
from insights import Insight, RuleEngine, generate_report_text
from visualizer import ChartRenderer
from pdf_report import PDFReport
from marketing_intelligence import compute_benchmarks, compute_period_comparison

app = FastAPI(title="Тракдрайв Маркетинг")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get("TRACKDRIVE_DATA_DIR", BASE_DIR))
UPLOAD_DIR = Path(os.environ.get("TRACKDRIVE_UPLOADS_DIR", DATA_DIR / "uploads"))
REPORTS_DIR = Path(os.environ.get("TRACKDRIVE_REPORTS_DIR", DATA_DIR / "reports"))
CHARTS_DIR = Path(os.environ.get("TRACKDRIVE_CHARTS_DIR", DATA_DIR / "charts"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_COMPANY_NAME = "Marketing Analytics"


def _company_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())
    return cleaned[:100] or DEFAULT_COMPANY_NAME


def _company_filename(value: str) -> str:
    safe = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("._")
    return safe[:64] or "company"


def _dashboard_chart_data(df: pd.DataFrame, analytics: AnalyticsEngine, platform_scores) -> Dict:
    """Small, session-safe datasets for interactive dashboard charts."""
    result: Dict = {}
    if analytics.date_col and analytics.views_col:
        work = df[[analytics.date_col, analytics.views_col]].copy()
        work[analytics.date_col] = pd.to_datetime(work[analytics.date_col], errors="coerce")
        work[analytics.views_col] = pd.to_numeric(work[analytics.views_col], errors="coerce").fillna(0)
        work = work.dropna(subset=[analytics.date_col])
        if not work.empty:
            daily = work.groupby(work[analytics.date_col].dt.date)[analytics.views_col].sum()
            result["time_series"] = {
                "labels": [d.strftime("%d.%m") for d in daily.index],
                "values": [float(v) for v in daily.values],
            }

    platform_rows = []
    for score in platform_scores or []:
        views = float(score.total_views or 0)
        engagement = float(score.total_engagement or 0)
        er = float(score.engagement_rate or 0)
        if views > 0 or engagement > 0 or er > 0:
            platform_rows.append({"label": score.platform, "views": views, "engagement": engagement, "er": er})
    if platform_rows:
        result["platforms"] = platform_rows
    return result


# ── Helpers ──

def _detect_profiles(processed_df: pd.DataFrame, column_map: Dict, vk_break: Optional[Dict]) -> List[str]:
    profiles = []
    plat_col = None
    for c, canon in column_map.items():
        if canon == "platform":
            plat_col = c
            break
    if plat_col and plat_col in processed_df.columns:
        platforms = processed_df[plat_col].astype(str).str.lower().unique()
        if any("youtube" in p or "ютуб" in p for p in platforms):
            profiles.append("youtube")
        has_vk = any("vk" in p or "вк" in p or "vkontakte" in p or "вконтакте" in p for p in platforms)
        if has_vk:
            profiles.append("vk_posts")
            if vk_break and vk_break.get("clips") is not None:
                profiles.append("vk_clips")
    else:
        # No platform column — check vk_break for any VK content
        if vk_break:
            if vk_break.get("posts") is not None:
                profiles.append("vk_posts")
            if vk_break.get("clips") is not None:
                profiles.append("vk_clips")
    return profiles


def _filter_report_data(report_data: Dict, profiles: List[str], column_map: Dict) -> Dict:
    """Filter report_data sections based on selected profiles."""
    platforms_included = []
    if "youtube" in profiles:
        platforms_included.append("youtube")
    has_vk = "vk_posts" in profiles or "vk_clips" in profiles
    if has_vk:
        platforms_included.append("vk")

    # Filter platform_scores
    if "platform_scores" in report_data:
        filtered = []
        for ps in report_data["platform_scores"]:
            pname = ps.get("platform", "").lower()
            if "youtube" in pname and "youtube" in profiles:
                filtered.append(ps)
            elif ("vk" in pname or "вк" in pname or "vkontakte" in pname or "вконтакте" in pname) and has_vk:
                filtered.append(ps)
        report_data["platform_scores"] = filtered

    # Filter vk_breakdown
    vk = report_data.get("vk_breakdown")
    if vk:
        filtered_vk = {}
        if "vk_posts" in profiles and "posts" in vk:
            filtered_vk["posts"] = vk["posts"]
            filtered_vk["posts_metrics"] = vk.get("posts_metrics", {})
        if "vk_clips" in profiles and "clips" in vk:
            filtered_vk["clips"] = vk["clips"]
            filtered_vk["clips_metrics"] = vk.get("clips_metrics", {})
        report_data["vk_breakdown"] = filtered_vk if filtered_vk else None

    # Adjust post_count
    report_data["post_count"] = 0
    for ps in report_data.get("platform_scores", []):
        report_data["post_count"] += ps.get("post_count", 0)

    # Build per-profile metrics sections
    profile_metrics = {}
    for ps in report_data.get("platform_scores", []):
        pname = ps.get("platform", "").lower()
        if "youtube" in pname and "youtube" in profiles:
            profile_metrics["youtube"] = {
                "label": "YouTube",
                "icon": "▶️",
                "content_type": "video",
                "views": ps.get("total_views", 0),
                "engagement": ps.get("total_engagement", 0),
                "er": ps.get("engagement_rate", 0),
                "post_count": ps.get("post_count", 0),
            }
    vk = report_data.get("vk_breakdown") or {}
    if "vk_posts" in profiles:
        if vk.get("posts"):
            p = vk["posts"]
        else:
            # Fallback: use platform_scores for VK
            p = next((ps for ps in report_data.get("platform_scores", [])
                      if "vk" in ps.get("platform","").lower()), {})
        if p:
            profile_metrics["vk_posts"] = {
                "label": "VK Записи",
                "icon": "📝",
                "content_type": "posts",
                "views": p.get("views", 0) or p.get("total_views", 0),
                "likes": p.get("likes", 0),
                "comments": p.get("comments", 0),
                "shares": p.get("shares", 0),
                "saves": p.get("saves", 0),
                "engagement": p.get("engagement", 0) or p.get("total_engagement", 0),
                "er": p.get("er", 0) or p.get("engagement_rate", 0),
                "post_count": p.get("count", 0) or p.get("post_count", 0),
            }
    if "vk_clips" in profiles and vk.get("clips"):
        c = vk["clips"]
        profile_metrics["vk_clips"] = {
            "label": "VK Клипы",
            "icon": "🎬",
            "content_type": "clips",
            "views": c.get("views", 0),
            "likes": c.get("likes", 0),
            "comments": c.get("comments", 0),
            "shares": c.get("shares", 0),
            "saves": c.get("saves", 0),
            "engagement": c.get("engagement", 0),
            "er": c.get("er", 0),
            "post_count": c.get("count", 0),
        }
    report_data["profile_metrics"] = profile_metrics

    # Pass through VK posts charts (only if vk_posts profile is selected)
    report_data["vk_post_charts"] = report_data.get("vk_post_charts", {})

    return report_data


# ── Endpoints ──

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), company_name: str = Form("")):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(400, "Only Excel (.xlsx, .xls) and CSV files are supported")

    session_id = str(uuid.uuid4())[:8]
    company_name = _company_name(company_name)
    ext = os.path.splitext(file.filename)[1]
    temp_path = UPLOAD_DIR / f"{session_id}{ext}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(413, "Файл превышает допустимый размер 100 МБ")
        f.write(content)

    try:
        if ext.lower() == ".csv":
            df = pd.read_csv(temp_path)
        else:
            readers = []
            if ext.lower() == ".xls":
                readers.append(("xlrd", lambda: pd.read_excel(temp_path, engine="xlrd")))
            readers.append(("openpyxl", lambda: pd.read_excel(temp_path, engine="openpyxl")))
            last_err = None
            for label, reader in readers:
                try:
                    df = reader()
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    continue
            if last_err is not None:
                # Fallback: try CSV with multiple encodings
                encodings = ["utf-8-sig", "cp1251", "windows-1251", "latin-1", "utf-16"]
                csv_ok = False
                for enc in encodings:
                    try:
                        df = pd.read_csv(temp_path, sep=None, engine="python", encoding=enc)
                        csv_ok = True
                        break
                    except Exception:
                        continue
                if not csv_ok:
                    raise last_err

        processor = DataProcessor(df)
        processed_df, column_map, metrics = processor.process()

        if processed_df.empty:
            raise HTTPException(400, "No valid data found after processing")

        # Save processed data for filtered re-generation
        processed_df.to_csv(UPLOAD_DIR / f"{session_id}_data.csv", index=False)
        col_map_file = UPLOAD_DIR / f"{session_id}_column_map.json"
        with open(col_map_file, "w", encoding="utf-8") as f:
            json.dump(column_map, f, ensure_ascii=False, default=str)

        analytics = AnalyticsEngine(processed_df, column_map)

        trend = analytics.analyze_trend(analytics.views_col) if analytics.views_col else None
        peaks = analytics.detect_peaks(analytics.views_col) if analytics.views_col else []
        anomalies = analytics.detect_anomalies(analytics.views_col) if analytics.views_col else []
        top_posts_df = analytics.top_posts(analytics.views_col, 10) if analytics.views_col else pd.DataFrame()
        platform_scores = analytics.platform_comparison()
        growth_df = analytics.growth_over_time()

        viral_count = int((processed_df["is_viral"]).sum()) if "is_viral" in processed_df.columns else int(
            len(peaks)
        )

        trend_info = {
            "direction": trend.direction if trend else "unknown",
            "slope": trend.slope if trend else 0,
            "p_value": trend.p_value if trend else 1,
            "description": trend.description if trend else "",
        }

        profile = metrics.get("analysis_profile", {})
        if metrics.get("source_report_type") in {"audience", "metric_series"}:
            label = "аудитории" if metrics.get("source_report_type") == "audience" else "временного ряда"
            insights = [Insight(
                "data_quality",
                f"Режим анализа {label}",
                "Отчет построен только по доступным значениям и датам. Метрики публикаций, ER и рекомендации по контенту отключены, чтобы не делать ложных выводов.",
                "neutral",
            )]
        else:
            insight_engine = RuleEngine(
                metrics=metrics,
                trend_info=trend_info,
                platform_scores=platform_scores,
                anomaly_count=len(anomalies),
                peak_count=len(peaks),
                viral_count=viral_count,
                has_platform=bool(analytics.platform_col),
            )
            insights = insight_engine.generate()
        insight_sections = generate_report_text(insights)

        session_charts_dir = CHARTS_DIR / session_id
        charts = ChartRenderer(str(session_charts_dir))

        chart_paths = {}
        if analytics.date_col and analytics.views_col:
            ts_metrics = [analytics.views_col]
            if analytics.likes_col:
                ts_metrics.append(analytics.likes_col)
            chart_paths["timeseries"] = charts.time_series(
                processed_df, analytics.date_col, ts_metrics
            )

        if not top_posts_df.empty:
            name_col = analytics.post_name_col or top_posts_df.columns[0]
            val_col = analytics.views_col or top_posts_df.columns[0]
            chart_paths["barchart"] = charts.bar_chart(
                top_posts_df, name_col, val_col
            )

        if platform_scores:
            chart_paths["platforms"] = charts.platform_comparison(platform_scores)

        if "engagement_rate" in processed_df.columns:
            chart_paths["distribution"] = charts.engagement_distribution(processed_df)

        # Day of week analysis
        dow_df = analytics.day_of_week_analysis()
        if not dow_df.empty:
            chart_paths["dayofweek"] = charts.day_of_week(dow_df)

        # WoW growth
        wow = analytics.wow_growth()

        metrics_extra = {}
        source_type = metrics.get("source_report_type")
        if source_type == "audience":
            metrics_extra["Тип отчета"] = "Аудитория"
        elif source_type == "metric_series":
            metrics_extra["Тип отчета"] = "Временной ряд показателей"
        if wow:
            metrics_extra["WoW рост"] = f"{wow.get('avg_weekly_growth', 0):+.1f}%"
        if metrics.get("engagement_quality", 0):
            metrics_extra["Качество вовлеч."] = f"{metrics['engagement_quality']:.2f} комм/лайк"
        if metrics.get("marketing_health_score", 0):
            metrics_extra["Marketing Score"] = f"{metrics['marketing_health_score']:.1f}/100"
        if metrics.get("attention_quality", 0):
            metrics_extra["Attention Quality"] = f"{metrics['attention_quality']:.2f}%"
        if metrics.get("amplification_rate", 0):
            metrics_extra["Amplification"] = f"{metrics['amplification_rate']:.1f}%"
        if metrics.get("conversation_rate", 0):
            metrics_extra["Conversation"] = f"{metrics['conversation_rate']:.1f}%"
        if metrics.get("save_intent_rate", 0):
            metrics_extra["Save Intent"] = f"{metrics['save_intent_rate']:.1f}%"
        if metrics.get("top_20_views_share", 0):
            metrics_extra["Доля топ-20%"] = f"{metrics['top_20_views_share']:.1f}% охвата"
        if metrics.get("posting_density", 0):
            metrics_extra["Постов/день"] = f"{metrics['posting_density']:.2f}"
        if metrics.get("best_posting_day", ""):
            metrics_extra["Лучший день"] = f"{metrics['best_posting_day']} ({metrics.get('best_day_views', 0):,.0f} просм.)"
        if metrics.get("follower_growth_pct", 0) != 0:
            metrics_extra["Рост подписчиков"] = f"{metrics.get('follower_growth', 0):+.0f}"
        if metrics.get("max_engagement_rate", 0):
            metrics_extra["Макс. ER"] = f"{metrics.get('max_engagement_rate', 0):.2f}%"
        if metrics.get("virality_score", 0):
            metrics_extra["Вирусность"] = f"{metrics.get('virality_score', 0):.1f}x"
        if metrics.get("views_trend", 0):
            metrics_extra["Тренд просмотров"] = f"{metrics.get('views_trend', 0):+.1f}/день"
        if metrics.get("total_saves", 0):
            metrics_extra["Сохранения"] = f"{metrics.get('total_saves', 0):,.0f}"
        if metrics.get("total_shares", 0):
            metrics_extra["Репосты"] = f"{metrics.get('total_shares', 0):,.0f}"
        if metrics.get("total_comments", 0):
            metrics_extra["Комментарии"] = f"{metrics.get('total_comments', 0):,.0f}"

        date_col_name = analytics.date_col
        period = "—"
        if date_col_name and date_col_name in processed_df.columns:
            dates = processed_df[date_col_name].dropna()
            if not dates.empty:
                period = f"{dates.min().strftime('%d.%m.%Y')} — {dates.max().strftime('%d.%m.%Y')}"

        platforms_list = []
        if platform_scores:
            platforms_list = [p.platform for p in platform_scores]

        period_comparison = compute_period_comparison(processed_df, column_map)
        benchmarks = compute_benchmarks(
            metrics, platforms_list, metrics.get("source_report_type", "")
        )
        dashboard_charts = _dashboard_chart_data(processed_df, analytics, platform_scores)

        recommendations = [
            ins for ins in insights if ins.category == "recommendation"
        ]

        vk_break = vk_content_breakdown(processor)
        available_profiles = _detect_profiles(processed_df, column_map, vk_break)

        # ── VK Posts per-profile charts ──
        vk_post_charts = {}
        posts_df = processor.vk_breakdown.get("posts") if processor.vk_breakdown else None
        if posts_df is None or posts_df.empty:
            plat_col = column_map.get("platform")
            ct_col = column_map.get("content_type")
            if plat_col and plat_col in processed_df.columns:
                vk_mask = processed_df[plat_col].astype(str).str.lower().str.contains("vk|вк|vkontakte|вконтакте", na=False)
                vk_df = processed_df[vk_mask]
                if ct_col and ct_col in vk_df.columns:
                    posts_df = vk_df[vk_df[ct_col].astype(str).str.lower().str.contains("post|запис|пост|текст|article|статья", na=False)]
                else:
                    posts_df = vk_df
            elif ct_col and ct_col in processed_df.columns:
                # No platform column — detect VK posts by content_type values
                ct_vals = processed_df[ct_col].astype(str).str.lower()
                post_mask = ct_vals.str.contains("post|запис|пост|текст|article|статья", na=False)
                if post_mask.any():
                    posts_df = processed_df[post_mask]
        if posts_df is not None and not posts_df.empty and analytics.date_col and analytics.views_col:
            dc, vc = analytics.date_col, analytics.views_col
            vk_post_charts["vk_er_trend"] = charts.er_trend(posts_df, dc, filename="vk_er_trend.png")
            vk_post_charts["vk_monthly"] = charts.monthly_trend(posts_df, dc, vc, filename="vk_monthly.png")
            vk_post_charts["vk_views_dist"] = charts.views_distribution(posts_df, vc, filename="vk_views_dist.png")
            vk_post_charts["vk_pareto"] = charts.pareto_chart(posts_df, vc, filename="vk_pareto.png")
            lc = (analytics.likes_col or ""); cc = (analytics.comments_col or "")
            sc = (analytics.shares_col or ""); sv = (analytics.saves_col or "")
            if any([lc, cc, sc, sv]):
                vk_post_charts["vk_engagement_comp"] = charts.engagement_composition(posts_df, lc, cc, sc, sv, filename="vk_engagement_comp.png")
            print(f"[VK CHARTS] Generated {len(vk_post_charts)} charts for session {session_id}: {list(vk_post_charts.keys())}", flush=True)
        else:
            print(f"[VK CHARTS] Skipped — posts_df={posts_df.shape if posts_df is not None else None}, date_col={analytics.date_col}, views_col={analytics.views_col}", flush=True)

        report_data = {
            "vk_breakdown": vk_break,
            "session_id": session_id,
            "company_name": company_name,
            "available_profiles": available_profiles,
            "period": period,
            "platforms": platforms_list,
            "post_count": metrics.get("post_count", 0),
            "metrics": metrics,
            "metrics_extra": metrics_extra,
            "analysis_profile": profile,
            "trend": trend_info,
            "platform_scores": [
                {"platform": p.platform, "total_views": p.total_views,
                 "total_engagement": p.total_engagement,
                 "engagement_rate": p.engagement_rate, "post_count": p.post_count,
                 "score": p.score}
                for p in platform_scores
            ],
            "period_comparison": period_comparison,
            "benchmarks": benchmarks,
            "dashboard_charts": dashboard_charts,
            "insights": [
                {"category": i.category, "title": i.title,
                 "description": i.description, "severity": i.severity,
                 "recommendation": i.recommendation}
                for i in insights
            ],
            "recommendations": [
                {"title": r.title, "description": r.description,
                 "recommendation": r.recommendation}
                for r in recommendations
            ],
            "charts": chart_paths,
            "vk_post_charts": vk_post_charts,
            "top_posts": top_posts_df.head(10).to_dict(orient="records") if not top_posts_df.empty else [],
            "column_map": column_map,
            "data_preview": processed_df.head(20).to_dict(orient="records"),
        }

        data_file = UPLOAD_DIR / f"{session_id}_data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, default=str)

        preview_data = {
            "session_id": session_id,
            "company_name": company_name,
            "available_profiles": available_profiles,
            "period": period,
            "platforms": platforms_list,
            "post_count": metrics.get("post_count", 0),
            "metrics": {
                "total_views": metrics.get("total_views", 0),
                "total_likes": metrics.get("total_likes", 0),
                "total_engagement": metrics.get("total_engagement", 0),
                "avg_engagement_rate": metrics.get("avg_engagement_rate", 0),
                "max_engagement_rate": metrics.get("max_engagement_rate", 0),
                "avg_views": metrics.get("avg_views", 0),
                "marketing_health_score": metrics.get("marketing_health_score", 0),
                "attention_quality": metrics.get("attention_quality", 0),
                "amplification_rate": metrics.get("amplification_rate", 0),
                "conversation_rate": metrics.get("conversation_rate", 0),
                "save_intent_rate": metrics.get("save_intent_rate", 0),
                "top_20_views_share": metrics.get("top_20_views_share", 0),
                "content_efficiency_index": metrics.get("content_efficiency_index", 0),
                "source_report_type": metrics.get("source_report_type", ""),
            },
            "metrics_extra": metrics_extra,
            "analysis_profile": profile,
            "trend": trend_info,
            "platform_scores": [
                {"platform": p.platform, "score": p.score}
                for p in platform_scores
            ],
            "period_comparison": period_comparison,
            "benchmarks": benchmarks,
            "dashboard_charts": dashboard_charts,
            "insights": [
                {"title": i.title, "description": i.description,
                 "severity": i.severity} for i in insights[:8]
            ],
            "recommendations": [
                {"title": r.title, "recommendation": r.recommendation}
                for r in recommendations[:5]
            ],
            "chart_urls": {
                k: f"/api/charts/{session_id}/{os.path.basename(v)}"
                for k, v in chart_paths.items()
            },
            "top_posts": top_posts_df.head(10).to_dict(orient="records") if not top_posts_df.empty else [],
        }

        return preview_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD ERROR] {traceback.format_exc()}", flush=True)
        raise HTTPException(500, f"Не удалось обработать файл: {str(e)}")


@app.get("/api/report/{session_id}")
async def generate_report(session_id: str, profiles: str = Query("", description="Comma-separated profiles: youtube,vk_posts,vk_clips")):
    data_file = UPLOAD_DIR / f"{session_id}_data.json"
    if not data_file.exists():
        raise HTTPException(404, "Session not found")

    with open(data_file, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    # Lazy-generate VK post charts from saved CSV if missing or using old generic names
    stored_vk_charts = report_data.get("vk_post_charts") or {}
    needs_regeneration = not stored_vk_charts
    if not needs_regeneration:
        # Check if at least one path uses the vk_ prefix
        vk_paths = list(stored_vk_charts.values())
        needs_regeneration = not any("vk_" in os.path.basename(p) for p in vk_paths if p)
    if needs_regeneration:
        csv_path = UPLOAD_DIR / f"{session_id}_data.csv"
        cm_path = UPLOAD_DIR / f"{session_id}_column_map.json"
        if csv_path.exists() and cm_path.exists():
            try:
                cm = json.loads(open(cm_path, encoding="utf-8").read())
                df = pd.read_csv(csv_path)
                dc = cm.get("date")
                if dc and dc in df.columns:
                    df[dc] = pd.to_datetime(df[dc], errors="coerce")
                # Detect VK data
                pc = cm.get("platform")
                has_vk = False
                if pc and pc in df.columns:
                    vk_mask = df[pc].astype(str).str.contains("VK|vk|ВК", case=False, na=False)
                    has_vk = vk_mask.any()
                    df = df[vk_mask]
                if not has_vk:
                    cc = cm.get("content_type")
                    if cc and cc in df.columns:
                        ct_vals = df[cc].astype(str).str.lower()
                        has_vk = ct_vals.str.contains("post|запис|пост|clip|клип|video|видео", na=False).any()
                if has_vk:
                    cc = cm.get("content_type")
                    if cc and cc in df.columns:
                        df = df[df[cc].astype(str).str.contains("post|запис|пост|текст|article|статья", case=False, na=False)]
                    if not df.empty and dc and dc in df.columns:
                        ae = AnalyticsEngine(df, cm)
                        vc = ae.views_col
                        if vc and vc in df.columns:
                            cr = ChartRenderer(str(CHARTS_DIR / session_id))
                            ch = {}
                            ch["vk_er_trend"] = cr.er_trend(df, dc, filename="vk_er_trend.png")
                            ch["vk_monthly"] = cr.monthly_trend(df, dc, vc, filename="vk_monthly.png")
                            ch["vk_views_dist"] = cr.views_distribution(df, vc, filename="vk_views_dist.png")
                            ch["vk_pareto"] = cr.pareto_chart(df, vc, filename="vk_pareto.png")
                            lc = (ae.likes_col or ""); cc2 = (ae.comments_col or "")
                            sc = (ae.shares_col or ""); sv = (ae.saves_col or "")
                            if any([lc, cc2, sc, sv]):
                                ch["vk_engagement_comp"] = cr.engagement_composition(df, lc, cc2, sc, sv, filename="vk_engagement_comp.png")
                            report_data["vk_post_charts"] = ch
                            print(f"[VK CHARTS LAZY] Generated {len(ch)} charts for session {session_id}", flush=True)
                            with open(data_file, "w", encoding="utf-8") as fw:
                                json.dump(report_data, fw, ensure_ascii=False, default=str)
            except Exception as e:
                print(f"[VK CHARTS LAZY] Error: {e}", flush=True)

    if profiles:
        selected = [p.strip() for p in profiles.split(",") if p.strip()]
        report_data = _filter_report_data(report_data, selected, report_data.get("column_map", {}))

    output_path = REPORTS_DIR / f"report_{session_id}.pdf"
    pdf = PDFReport(str(output_path))
    pdf.build(report_data)

    return FileResponse(
        str(output_path),
        media_type="application/pdf",
        filename=f"{_company_filename(report_data.get('company_name', DEFAULT_COMPANY_NAME))}_marketing_report.pdf"
    )


@app.get("/api/charts/{session_id}/{chart_name}")
async def get_chart(session_id: str, chart_name: str):
    if not session_id.isalnum() or chart_name != os.path.basename(chart_name):
        raise HTTPException(404, "Chart not found")
    chart_path = CHARTS_DIR / session_id / chart_name
    if not chart_path.exists():
        raise HTTPException(404, "Chart not found")
    return FileResponse(str(chart_path), media_type="image/png")


@app.post("/api/cleanup/{session_id}")
async def cleanup(session_id: str):
    for ext in [".xlsx", ".xls", ".csv"]:
        p = UPLOAD_DIR / f"{session_id}{ext}"
        if p.exists():
            p.unlink()
    data_file = UPLOAD_DIR / f"{session_id}_data.json"
    if data_file.exists():
        data_file.unlink()
    for fname in [f"{session_id}_data.csv", f"{session_id}_column_map.json"]:
        p = UPLOAD_DIR / fname
        if p.exists():
            p.unlink()
    report_file = REPORTS_DIR / f"report_{session_id}.pdf"
    if report_file.exists():
        report_file.unlink()
    charts_dir = CHARTS_DIR / session_id
    if charts_dir.exists():
        shutil.rmtree(charts_dir)
    return {"status": "cleaned"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
