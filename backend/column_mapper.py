import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
from thefuzz import fuzz

GENERAL = {
    "date": ["date", "дата", "time", "время", "period", "период", "день", "дд.мм.гггг",
             "публикации", "дата публикации", "дата поста", "дата и время"],
    "platform": ["platform", "платформа", "source", "источник", "channel", "канал", "social network"],
    "post_id": ["post_id", "id поста", "post id", "post", "id", "post_url", "url поста",
                "url", "ссылка", "link", "video url", "видео url", "permalink"],
    "post_name": ["post_name", "название", "post title", "title", "заголовок", "name",
                  "текст поста", "текст", "сообщение", "message", "video title",
                  "название видео", "запись", "текст записи", "content",
                  "описание", "description"],
    "views": ["views", "просмотры", "view_count", "views_count", "impressions",
              "охват", "reach", "visitors", "посетители", "view", "просмотр",
              "показы", "количество показов", "impression count", "video views",
              "число просмотров", "прочтения", "reads"],
    "likes": ["likes", "лайки", "like_count", "likes_count", "нравится", "like", "лайк",
              "reactions", "оценки", "like/dislike"],
    "dislikes": ["dislikes", "дизлайки", "dislike", "dislike_count"],
    "comments": ["comments", "комментарии", "comment_count", "comments_count", "comment",
                 "replies", "ответы", "reply count", "число комментариев"],
    "shares": ["shares", "репосты", "share_count", "shares_count", "share", "retweets",
               "ретвиты", "forward", "forwards", "пересылки", "число репостов",
               "retweet count"],
    "saves": ["saves", "сохранения", "save_count", "bookmarks", "закладки", "favorites",
              "избранное", "число сохранений"],
    "followers": ["followers", "подписчики", "follower_count", "subscribers",
                  "подписчиков", "subs", "audience", "число подписчиков",
                  "subscriber count"],
    "content_type": ["type", "тип", "content type", "тип контента", "post type",
                     "video type", "media type", "media", "формат", "content",
                     "контент", "категория", "category", "clip/post",
                     "раздел", "section", "подраздел", "subsection"],
    "clip_id": ["clip_id", "clip id", "id клипа", "клип id", "video clip id"],
    "clip_name": ["clip_name", "clip title", "название клипа", "клип название",
                  "clip name", "title clip", "clip заголовок"],
    "clip_date": ["clip_date", "clip date", "дата клипа", "клип дата",
                  "date clip", "дата видео клип"],
    "clip_views": ["clip_views", "clip просмотры", "clip reach",
                   "клип просмотров", "просмотры клипов", "video views clip",
                   "clip impressions", "clip plays", "video_views",
                   "video views", "просмотры видео", "клип просмотры",
                   "количество просмотров клипа"],
    "clip_likes": ["clip_likes", "clip like", "клип лайки", "лайки клипа",
                   "like clip", "clip likes", "like video"],
    "clip_comments": ["clip_comments", "clip comment", "клип комментарии",
                      "комментарии клипа", "comments clip", "clip replies",
                      "clip ответы", "клип ответы"],
    "clip_shares": ["clip_shares", "clip share", "клип репосты", "репосты клипа",
                    "share clip", "клип share", "clip reposts"],
    "clip_saves": ["clip_saves", "clip save", "клип сохранения", "сохранения клипа",
                   "save clip", "clip bookmarks", "clip favorites"],
}

YOUTUBE_ALIASES = {
    "date": ["дата публикации", "publication date", "published at", "published",
             "дата видео", "video date", "date Published", "Publish date"],
    "post_name": ["название видео", "video title", "заголовок", "title",
                  "видео название", "Video Title"],
    "post_id": ["видео id", "video id", "ссылка на видео", "video url",
                "video link", "URL видео"],
    "views": ["просмотры видео", "video views", "количество просмотров",
              "число просмотров", "Views"],
    "likes": ["лайки", "like count", "число лайков", "likes (👍)"],
    "comments": ["комментарии", "comment count", "число комментариев", "comments count"],
    "saves": ["в избранном", "saved", "число сохранений"],
    "shares": ["репосты", "share count"],
}

VK_ALIASES = {
    "date": ["дата записи", "дата поста", "date", "дата", "время"],
    "post_name": ["текст записи", "запись", "текст поста", "post text",
                  "содержание", "content", "описание", "description"],
    "post_id": ["id записи", "post id", "ссылка", "url"],
    "views": ["просмотры", "охват", "reach", "число просмотров",
              "количество просмотров", "views"],
    "likes": ["лайки", "число лайков", "нравится", "likes", "like count"],
    "comments": ["комментарии", "число комментариев", "comments"],
    "shares": ["репосты", "поделились", "reposts", "share count"],
    "saves": ["закладки", "bookmarks", "сохранения", "saves"],
    "followers": ["подписчики", "участники", "subscribers"],
    "content_type": ["тип", "тип контента", "content type", "формат",
                     "раздел", "section", "подраздел", "subsection", "category"],
    "clip_views": ["просмотры клипов", "video views", "video_views",
                   "клип просмотры", "просмотры видео"],
    "clip_likes": ["лайки клипа", "clip likes", "лайки клипов"],
    "clip_comments": ["комментарии клипа", "clip comments", "комментарии клипов"],
    "clip_shares": ["репосты клипа", "clip shares", "репосты клипов"],
}

TELEGRAM_ALIASES = {
    "date": ["дата", "дата сообщения", "date", "message date"],
    "post_name": ["сообщение", "текст", "текст сообщения", "message",
                  "message text", "content"],
    "post_id": ["id сообщения", "message id", "ссылка", "url"],
    "views": ["просмотры", "число просмотров", "views count", "views",
              "количество просмотров"],
    "comments": ["комментарии", "replies", "ответы", "reply count",
                 "число комментариев"],
    "shares": ["репосты", "forwards", "пересылки", "forward count",
               "число пересылок"],
    "saves": ["сохранения", "bookmarks", "saves"],
    "followers": ["подписчики", "subscribers", "число подписчиков"],
}

PLATFORM_DICT = {
    "youtube": {
        "markers": ["youtube", "ютуб", "ютюб", "video", "видео"],
        "aliases": YOUTUBE_ALIASES,
    },
    "vk": {
        "markers": ["vk", "вк", "vkontakte", "вконтакте"],
        "aliases": VK_ALIASES,
    },
    "telegram": {
        "markers": ["telegram", "телеграм", "тг", "tg"],
        "aliases": TELEGRAM_ALIASES,
    },
}

MERGE_DICT: Dict[str, List[str]] = {}
for canon, aliases in GENERAL.items():
    MERGE_DICT[canon] = list(aliases)

def _merge_platform_aliases(platform: Optional[str] = None):
    merged = {}
    for canon, aliases in GENERAL.items():
        merged[canon] = list(aliases)
    if platform and platform in PLATFORM_DICT:
        for canon, aliases in PLATFORM_DICT[platform]["aliases"].items():
            if canon in merged:
                merged[canon].extend(a for a in aliases if a not in merged[canon])
            else:
                merged[canon] = list(aliases)
    return merged

def _detect_platform_from_columns(columns: List[str]) -> Optional[str]:
    col_text = " ".join(str(c).lower() for c in columns)
    scores = {}
    for plat_name, plat_info in PLATFORM_DICT.items():
        score = 0
        for marker in plat_info["markers"]:
            if marker in col_text:
                score += 10
        for canon, aliases in plat_info["aliases"].items():
            for alias in aliases:
                if alias.lower() in col_text:
                    score += 1
        scores[plat_name] = score
    if max(scores.values()) >= 3:
        return max(scores, key=scores.get)
    return None

def detect_column_types(df: pd.DataFrame) -> Dict[str, str]:
    platform = _detect_platform_from_columns(list(df.columns))
    merged = _merge_platform_aliases(platform)

    result = {}
    for col in df.columns:
        col_str = str(col).lower().strip()
        best_match = None
        best_score = 0

        for canonical, aliases in merged.items():
            for alias in aliases:
                score = fuzz.ratio(col_str, alias.lower())
                if score > best_score:
                    best_score = score
                    best_match = canonical
                if col_str == alias.lower():
                    best_score = 100
                    best_match = canonical
                    break
            if best_score == 100:
                break

        if best_score >= 65:
            result[str(col)] = best_match
        elif best_score >= 40:
            result[str(col)] = f"unknown:{best_match if best_match else col}"
        else:
            result[str(col)] = "ignore"

    return result

def get_mapped_columns(detected: Dict[str, str], df: Optional[pd.DataFrame] = None) -> Dict[str, str]:
    reverse: Dict[str, str] = {}
    duplicates: Dict[str, list] = {}
    for col, canon in detected.items():
        if canon != "ignore" and not canon.startswith("unknown"):
            if canon in reverse:
                if canon not in duplicates:
                    duplicates[canon] = [reverse[canon], col]
                else:
                    duplicates[canon].append(col)
            else:
                reverse[canon] = col

    for canon, cols in duplicates.items():
        best = _pick_best_column(cols, canon, df)
        if best:
            reverse[canon] = best

    for col, canon in detected.items():
        if canon.startswith("unknown"):
            _, hint = canon.split(":", 1)
            if hint not in reverse:
                reverse[hint] = col
    return reverse


def _pick_best_column(cols: List[str], canon: str, df: Optional[pd.DataFrame]) -> Optional[str]:
    if not cols:
        return None
    if len(cols) == 1:
        return cols[0]
    if df is not None:
        numeric_cols = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            return numeric_cols[0]
    PRIORITY = {
        "views": ["просмотры", "views", "impressions", "показы"],
        "followers": ["подписчики", "followers", "subscribers"],
        "shares": ["репосты", "reposts", "shares", "forwards"],
    }
    canon_lower = canon.lower()
    if canon_lower in PRIORITY:
        for preferred in PRIORITY[canon_lower]:
            for c in cols:
                if preferred in c.lower():
                    return c
    return cols[0]

def suggest_date_format(series: pd.Series) -> Optional[str]:
    sample = series.dropna().head(20).astype(str)
    patterns = [
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{2}\.\d{2}\.\d{4}", "%d.%m.%Y"),
        (r"\d{2}/\d{2}/\d{4}", "%m/%d/%Y"),
        (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
        (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y"),
        (r"\d{2}\.\d{2}\.\d{2}", "%d.%m.%y"),
    ]
    for val in sample:
        for pattern, fmt in patterns:
            if re.match(pattern, val):
                return fmt
    return None

def get_column_report(df: pd.DataFrame) -> Dict:
    detected = detect_column_types(df)
    mapped = get_mapped_columns(detected)
    platform = _detect_platform_from_columns(list(df.columns))
    return {
        "platform_detected": platform,
        "detected_types": detected,
        "column_map": mapped,
        "unmapped": [c for c, v in detected.items() if v == "ignore" or v.startswith("unknown")],
    }
