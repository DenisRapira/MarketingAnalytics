from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Insight:
    category: str
    title: str
    description: str
    severity: str
    recommendation: Optional[str] = None


def _er_label(er: float) -> str:
    if er > 10: return "отличный"
    if er > 5: return "высокий"
    if er > 3: return "хороший"
    if er > 1: return "средний"
    return "низкий"


class RuleEngine:
    def __init__(self, metrics: Dict[str, float], trend_info: Dict, platform_scores: List,
                 anomaly_count: int, peak_count: int, viral_count: int, has_platform: bool):
        self.m = metrics
        self.trend = trend_info
        self.platforms = platform_scores
        self.anomalies = anomaly_count
        self.peaks = peak_count
        self.viral = viral_count
        self.has_platform = has_platform

    def generate(self) -> List[Insight]:
        insights: List[Insight] = []
        insights.extend(self._performance_insights())
        insights.extend(self._trend_insights())
        insights.extend(self._engagement_insights())
        insights.extend(self._viral_insights())
        insights.extend(self._platform_insights())
        insights.extend(self._anomaly_insights())
        insights.extend(self._growth_insights())
        insights.extend(self._recommendations())
        return insights

    def _performance_insights(self) -> List[Insight]:
        res = []
        v = self.m.get("total_views", 0)
        e = self.m.get("total_engagement", 0)
        er = self.m.get("avg_engagement_rate", None)
        pc = self.m.get("post_count", 0)
        avg_v = self.m.get("avg_views", 0)

        if v > 100000:
            res.append(Insight(
                "performance", "Высокий общий охват",
                f"Суммарно {v:,.0f} просмотров — это сильный показатель, говорящий о широком охвате аудитории. "
                f"При среднем охвате {avg_v:,.0f} на пост из {pc} публикаций.",
                "positive",
                "Продолжайте масштабировать успешные форматы и усиливать продвижение."
            ))
        elif v > 10000:
            res.append(Insight(
                "performance", "Умеренный охват",
                f"Суммарно {v:,.0f} просмотров. Аудитория растёт, но есть значительный потенциал для увеличения "
                f"охвата. Средний показатель на пост: {avg_v:,.0f}.",
                "neutral",
                "Проанализируйте топ-посты и усильте продвижение наиболее эффективного контента."
            ))
        else:
            res.append(Insight(
                "performance", "Начальный уровень охвата",
                f"Общий охват — {v:,.0f} просмотров. Это база для дальнейшего роста. "
                f"Рекомендуется сфокусироваться на качестве и регулярности контента.",
                "neutral",
                "Увеличьте частоту публикаций и работайте над вовлекающими форматами."
            ))

        if er is not None:
            el = _er_label(er)
            if er > 5:
                res.append(Insight(
                    "engagement", f"Вовлечённость: {el} уровень",
                    f"Средний engagement rate — {er:.2f}%. Это {el} показатель, значительно превышающий "
                    f"среднерыночные значения ({'3-5% для большинства платформ' if er > 5 else '1-3%'}). "
                    f"Аудитория активно реагирует на контент.",
                    "positive"
                ))
            elif er > 1:
                res.append(Insight(
                    "engagement", f"Вовлечённость: {el} уровень",
                    f"Средний engagement rate — {er:.2f}% ({el} показатель). "
                    f"Аудитория взаимодействует, но есть потенциал для роста. "
                    f"Суммарное вовлечение: {e:,.0f} действий.",
                    "neutral",
                    "Работайте над призывами к действию, добавляйте интерактивные элементы."
                ))
            else:
                res.append(Insight(
                    "engagement", "Низкая вовлечённость",
                    f"Engagement rate всего {er:.2f}%. Аудитория пассивна — это сигнал к пересмотру "
                    f"контент-стратегии. При суммарном охвате {v:,.0f} просмотров получено лишь {e:,.0f} взаимодействий.",
                    "negative",
                    "Пересмотрите контент-стратегию: добавьте опросы, викторины, дискуссионные темы."
                ))

        health = self.m.get("marketing_health_score", 0)
        if health:
            if health >= 72:
                res.append(Insight(
                    "performance", "Сильная маркетинговая система",
                    f"Marketing Health Score — {health:.1f}/100. У проекта уже есть рабочая связка охвата, "
                    "вовлечения и регулярности публикаций.",
                    "positive",
                    "Масштабируйте самые сильные рубрики и закрепите их в контент-плане."
                ))
            elif health >= 45:
                res.append(Insight(
                    "performance", "Маркетинговая система в зоне роста",
                    f"Marketing Health Score — {health:.1f}/100. База есть, но результат зависит от точечных улучшений: "
                    "упаковки, частоты, усиления CTA и повторения лучших форматов.",
                    "neutral",
                    "Выберите 2-3 гипотезы на следующий период и измерьте прирост по ER и охвату."
                ))
            else:
                res.append(Insight(
                    "performance", "Нужна пересборка контент-механики",
                    f"Marketing Health Score — {health:.1f}/100. Текущая система недостаточно стабильно превращает "
                    "публикации в охват и реакции.",
                    "warning",
                    "Начните с аудита позиционирования, рубрик и регулярности публикаций."
                ))

        return res

    def _trend_insights(self) -> List[Insight]:
        res = []
        direction = self.trend.get("direction", "stable")
        slope = self.trend.get("slope", 0)
        desc = self.trend.get("description", "")
        avg_v = self.m.get("avg_views", 0)

        if direction == "up":
            rel_slope = (slope / max(avg_v, 1)) * 100
            res.append(Insight(
                "trend", "Восходящий тренд просмотров",
                desc + (f" Относительный рост составляет {rel_slope:.1f}% от среднего значения за период. "
                        f"Контент-стратегия работает эффективно." if rel_slope > 0.5 else ""),
                "positive"
            ))
            if slope > 100:
                res.append(Insight(
                    "trend", "Ускорение роста",
                    "Темпы роста просмотров значительно выше среднего. Контент находит отклик у аудитории. "
                    "Рекомендуется закрепить успех, увеличив частоту публикаций в успешных форматах.",
                    "positive",
                    "Увеличьте частоту публикаций в успешных форматах."
                ))
        elif direction == "down":
            res.append(Insight(
                "trend", "Нисходящий тренд",
                desc + " Это может быть связано с изменением алгоритмов, сезонностью или усталостью аудитории от формата.",
                "negative",
                "Проведите аудит контента за последний период. Возможно, требуется смена формата или тематики."
            ))
        else:
            res.append(Insight(
                "trend", "Стабильная динамика",
                desc + " Это может говорить как о сформировавшейся аудитории, так и об отсутствии роста. "
                       "Рекомендуется экспериментировать с новыми форматами.",
                "neutral",
                "Экспериментируйте с форматами и временем публикации для поиска точек роста."
            ))
        return res

    def _engagement_insights(self) -> List[Insight]:
        res = []
        total_e = self.m.get("total_engagement", 0)
        if total_e > 10000:
            res.append(Insight(
                "engagement", "Высокий суммарный энгейджмент",
                f"Суммарное вовлечение: {total_e:,.0f} действий. Аудитория активно взаимодействует с контентом, "
                f"что положительно влияет на ранжирование в алгоритмах платформ.",
                "positive"
            ))
        amp = self.m.get("amplification_rate", 0)
        conv = self.m.get("conversation_rate", 0)
        save = self.m.get("save_intent_rate", 0)
        if amp >= 8:
            res.append(Insight(
                "engagement", "Контент хорошо распространяется",
                f"Amplification Rate — {amp:.1f}% от всех взаимодействий. Репосты дают органическое расширение охвата.",
                "positive",
                "Усилите форматы, которыми аудитории удобно делиться: чек-листы, подборки, спорные тезисы."
            ))
        if conv >= 12:
            res.append(Insight(
                "engagement", "Высокая разговорность",
                f"Conversation Rate — {conv:.1f}%. Контент запускает обсуждения, а не только быстрые лайки.",
                "positive",
                "Используйте больше открытых вопросов и тем, где аудитория может добавить личный опыт."
            ))
        if save >= 10:
            res.append(Insight(
                "engagement", "Есть сигнал практической ценности",
                f"Save Intent — {save:.1f}%. Сохранения показывают, что контент воспринимается как полезный ресурс.",
                "positive",
                "Развивайте evergreen-рубрики: инструкции, таблицы, подборки, разборы ошибок."
            ))
        return res

    def _viral_insights(self) -> List[Insight]:
        res = []
        v_score = self.m.get("virality_score", 0)
        if v_score > 5 or self.viral > 0:
            res.append(Insight(
                "viral", "Обнаружен вирусный контент",
                f"Выявлено {self.viral} постов, значительно превышающих средние показатели. "
                f"Virality score: {v_score:.1f}x — это означает, что лучшие посты превосходят средние "
                f"в {v_score:.1f} раза по вовлечённости.",
                "positive",
                "Проанализируйте характеристики вирусных постов (время, формат, тему) и replicate успех."
            ))
        concentration = self.m.get("top_20_views_share", 0)
        if concentration >= 65:
            res.append(Insight(
                "viral", "Охват держится на ограниченном числе хитов",
                f"Топ-20% публикаций дают {concentration:.1f}% всех просмотров. Это хороший сигнал для поиска победных рубрик, "
                "но риск для стабильности результата.",
                "warning",
                "Разберите общие признаки лучших постов и превратите их в повторяемую серию."
            ))
        elif 0 < concentration < 45:
            res.append(Insight(
                "viral", "Охват распределён ровно",
                f"Топ-20% публикаций дают только {concentration:.1f}% просмотров. Система стабильная, но ей не хватает сильных пиков.",
                "neutral",
                "Добавьте один-два более смелых формата в неделю, чтобы искать новые точки взрывного роста."
            ))
        if self.peaks > 2:
            res.append(Insight(
                "viral", "Множественные пики активности",
                f"Зафиксировано {self.peaks} пиков активности. Контент регулярно резонирует с аудиторией — "
                f"это признак устойчивого интереса.",
                "positive"
            ))
        elif self.peaks == 0 and self.m.get("total_views", 0) > 0:
            res.append(Insight(
                "viral", "Отсутствие выраженных пиков",
                "Динамика ровная, без резких всплесков. Это может означать как стабильную аудиторию, "
                "так и отсутствие вирусного потенциала. Рекомендуется экспериментировать с форматами.",
                "neutral",
                "Экспериментируйте с нестандартными форматами для поиска вирусного потенциала."
            ))
        return res

    def _platform_insights(self) -> List[Insight]:
        res = []
        if not self.has_platform or not self.platforms:
            return res

        best = self.platforms[0]
        res.append(Insight(
            "platform", f"Лидер: {best.platform}",
            f"Платформа «{best.platform}» показывает лучшие результаты с интегральным показателем {best.score:.1f}. "
            f"Просмотры: {best.total_views:,.0f}, ER: {best.engagement_rate:.2f}%. "
            f"Это платформа с наибольшей отдачей от контента.",
            "positive",
            f"Увеличьте инвестиции в {best.platform} и адаптируйте успешные форматы для других платформ."
        ))

        if len(self.platforms) > 1:
            worst = self.platforms[-1]
            res.append(Insight(
                "platform", f"Аутсайдер: {worst.platform}",
                f"Платформа «{worst.platform}» показывает наименьшие результаты. "
                f"Score: {worst.score:.1f}, просмотры: {worst.total_views:,.0f}. "
                f"Возможно, контент-стратегия требует адаптации под специфику этой платформы.",
                "warning",
                "Пересмотрите стратегию для этой платформы или рассмотрите перераспределение ресурсов."
            ))
            gap = best.score - worst.score
            if gap > 50:
                res.append(Insight(
                    "platform", "Значительный разрыв между платформами",
                    f"Разница в эффективности между лидером и аутсайдером составляет {gap:.1f} баллов. "
                    f"Это указывает на необходимость разной контент-стратегии для каждой платформы.",
                    "warning",
                    "Адаптируйте контент под специфику каждой платформы."
                ))
        return res

    def _anomaly_insights(self) -> List[Insight]:
        res = []
        if self.anomalies > 0:
            severity = "warning" if self.anomalies > 3 else "neutral"
            res.append(Insight(
                "anomaly", f"Статистические аномалии: {self.anomalies}",
                f"Выявлено {self.anomalies} статистических выбросов в данных. "
                f"Это могут быть как вирусные успехи, так и технические сбои или внешние события. "
                f"Рекомендуется проверить периоды аномалий.",
                severity,
                "Проверьте периоды аномалий: возможно, они связаны с внешними событиями."
            ))
        return res

    def _growth_insights(self) -> List[Insight]:
        res = []
        fg = self.m.get("follower_growth", 0)
        fgp = self.m.get("follower_growth_pct", 0)
        if abs(fgp) >= 0.01 and fg != 0:
            if fg > 0:
                res.append(Insight(
                    "growth", "Рост аудитории",
                    f"Прирост подписчиков: +{fg:,.0f} ({fgp:+.2f}%). Аудитория стабильно растёт — "
                    f"контент привлекает новых подписчиков.",
                    "positive",
                    "Продолжайте привлекать новую аудиторию через успешные форматы."
                ))
            else:
                res.append(Insight(
                    "growth", "Снижение аудитории",
                    f"Изменение подписчиков: {fg:,.0f} ({fgp:+.2f}%). Аудитория сокращается — "
                    f"требуется анализ причин оттока.",
                    "negative",
                    "Проведите анализ причин оттока: возможно, снизилась частота или качество контента."
                ))
        elif self.m.get("follower_growth") is not None and self.m.get("total_views", 0) > 0:
            res.append(Insight(
                "growth", "Стабильная аудитория",
                "Количество подписчиков не изменилось за период. Аудитория стабильна, "
                "что может быть как плюсом (лояльность), так и минусом (отсутствие роста).",
                "neutral"
            ))
        return res

    def _recommendations(self) -> List[Insight]:
        recs = []
        er = self.m.get("avg_engagement_rate", None)
        if er is not None and er < 3:
            recs.append(Insight(
                "recommendation", "Повышение вовлечённости",
                "Внедрите интерактивные элементы: опросы, вопросы в конце постов, стикеры, викторины. "
                "Посты с вопросами получают в среднем в 2 раза больше комментариев.",
                "recommendation"
            ))
        total_v = self.m.get("total_views", 0)
        post_c = self.m.get("post_count", 0)
        if post_c > 0:
            avg_v_per_post = total_v / post_c
            if avg_v_per_post < 500:
                recs.append(Insight(
                    "recommendation", "Улучшение охвата постов",
                    f"Средний охват на пост — всего {avg_v_per_post:.0f}. Работайте над заголовками, "
                    f"обложками и временем публикации. Посты, опубликованные в пиковое время, "
                    f"получают на 30-50% больше охвата.",
                    "recommendation"
                ))
        trend_dir = self.trend.get("direction", "")
        if trend_dir == "down":
            recs.append(Insight(
                "recommendation", "Смена контент-стратегии",
                "При нисходящем тренде рекомендуется: обновить визуальный стиль, протестировать новые "
                "форматы (Reels, Stories, карусели), провести анализ конкурентов.",
                "recommendation"
            ))
        recs.append(Insight(
            "recommendation", "Оптимизация частоты постинга",
            "Публикуйте 3-5 раз в неделю для поддержания вовлечённости. Регулярность важнее объёма: "
            "лучше 3 качественных поста, чем 5 проходных.",
            "recommendation"
        ))
        recs.append(Insight(
            "recommendation", "Анализ лучшего времени",
            "Проанализируйте, в какое время посты получают максимальный отклик. Публикация в пиковые "
            "часы может увеличить охват на 30-50%.",
            "recommendation"
        ))
        recs.append(Insight(
            "recommendation", "Форматный эксперимент",
            "Тестируйте разные форматы: видео, карусели, опросы, пользовательский контент (UGC). "
            "Разнообразие форматов удерживает внимание аудитории.",
            "recommendation"
        ))
        recs.append(Insight(
            "recommendation", "Комьюнити-менеджмент",
            "Отвечайте на комментарии в течение первых часов после публикации — это повышает "
            "ранговый вес поста в алгоритмах и стимулирует дальнейшее обсуждение.",
            "recommendation"
        ))
        return recs[:7]


def generate_report_text(insights: List[Insight]) -> Dict[str, List[Dict]]:
    sections = {}
    for ins in insights:
        if ins.category not in sections:
            sections[ins.category] = []
        sections[ins.category].append({
            "title": ins.title,
            "description": ins.description,
            "severity": ins.severity,
            "recommendation": ins.recommendation
        })
    return sections
