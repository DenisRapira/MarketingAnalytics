import KpiCard from './KpiCard';
import InsightsPanel from './InsightsPanel';
import PerformanceCharts from './PerformanceCharts';

function n(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return Number(v).toLocaleString('ru-RU');
}

function pct(v, digits = 1) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `${Number(v).toFixed(digits)}%`;
}

function signedPct(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const num = Number(v);
  return `${num > 0 ? '+' : ''}${num.toFixed(1)}%`;
}

function metricValue(metric, value) {
  if (metric === 'avg_engagement_rate' || metric === 'er') return pct(value, 2);
  if (metric === 'post_count') return Number(value || 0).toLocaleString('ru-RU');
  return n(value);
}

const PROFILE_LABELS = {
  youtube: { label: 'YouTube', icon: '▶' },
  vk_posts: { label: 'VK Записи', icon: '✎' },
  vk_clips: { label: 'VK Клипы', icon: '▣' },
};

const SCORE_LABELS = [
  { key: 'marketing_health_score', label: 'Marketing Score', suffix: '/100' },
  { key: 'attention_quality', label: 'Attention Quality', format: pct },
  { key: 'amplification_rate', label: 'Amplification', format: pct },
  { key: 'conversation_rate', label: 'Conversation', format: pct },
  { key: 'save_intent_rate', label: 'Save Intent', format: pct },
];

const COMPARE_LABELS = {
  total_views: 'Просмотры',
  total_engagement: 'Вовлечения',
  avg_engagement_rate: 'ER',
  post_count: 'Публикации',
  avg_views: 'Ср. просмотры',
};

const STATUS_LABELS = {
  below: 'Ниже нормы',
  normal: 'В норме',
  above: 'Выше нормы',
};

function ScoreItem({ item, value }) {
  const display = item.format ? item.format(value) : `${Number(value || 0).toFixed(1)}${item.suffix || ''}`;
  return (
    <div className="score-item">
      <span>{item.label}</span>
      <strong>{display}</strong>
    </div>
  );
}

export default function Dashboard({ data, onExport, onReset, onProfilesChange, selectedProfiles }) {
  const m = data.metrics || {};
  const trend = data.trend || {};
  const trendDir = trend.direction === 'up' ? 'up' : trend.direction === 'down' ? 'down' : 'stable';
  const trendLabels = { up: 'Рост', down: 'Падение', stable: 'Стабильно' };
  const hasData = m.total_views > 0;
  const topRecommendations = data.recommendations?.slice(0, 3) || [];
  const health = Number(m.marketing_health_score || 0);
  const isAggregate = ['audience', 'metric_series'].includes(m.source_report_type);
  const isAudience = m.source_report_type === 'audience';
  const reachLabel = isAudience ? 'Аудитория' : isAggregate ? 'Показатель' : 'Общий охват';
  const reachUnit = isAudience ? 'значений аудитории' : isAggregate ? 'значений' : 'просмотров';

  if (!hasData) {
    return (
      <div className="onboarding-section">
        <div className="onboarding-icon">▦</div>
        <h2>Нет данных для анализа</h2>
        <p>Загрузите файл с социальными метриками</p>
      </div>
    );
  }

  return (
    <div className={`dashboard ${isAggregate ? 'aggregate-report' : ''}`}>
      <div className="status-bar">
        <div className="status-left">
          {data.company_name && <span className="company-badge">{data.company_name}</span>}
          <span className="status-badge success">✓ Анализ завершен</span>
          <span className="status-info">{data.post_count} постов · {data.period || '—'}</span>
          {data.platforms?.length > 0 && (
            <div className="platform-badges">
              {data.platforms.map((p, i) => <span className="platform-badge" key={i}>{p}</span>)}
            </div>
          )}
        </div>
        <div className="status-actions">
          <button className="btn btn-secondary" onClick={onReset}>Новый файл</button>
          <button className="btn btn-primary" onClick={onExport}>PDF отчет</button>
        </div>
      </div>

      {data.available_profiles?.length > 0 && (
        <div className="profile-toolbar">
          <span>Профили отчета</span>
          {data.available_profiles.map(pid => {
            const info = PROFILE_LABELS[pid] || { label: pid, icon: '•' };
            const active = selectedProfiles?.includes(pid);
            return (
              <button
                key={pid}
                className={`profile-chip ${active ? 'active' : ''}`}
                onClick={() => onProfilesChange?.(
                  active ? selectedProfiles.filter(p => p !== pid) : [...(selectedProfiles || []), pid]
                )}
              >
                <b>{info.icon}</b>{info.label}
              </button>
            );
          })}
        </div>
      )}

      <section className="command-center">
        <div className="command-copy">
          <span className="eyebrow">Executive Control Room</span>
          <h1>Маркетинговая эффективность за период</h1>
          <p>
            Охват, вовлеченность и сигналы намерения сведены в одну картину, чтобы быстрее понять,
            какие форматы масштабировать и где теряется рост.
          </p>
        </div>
        <div className="health-card">
          <span>Marketing Health</span>
          <strong>{health ? health.toFixed(1) : '—'}</strong>
          <div className="health-track"><i style={{ width: `${Math.min(100, health)}%` }} /></div>
          <small>{trendLabels[trendDir]} · {pct(m.avg_engagement_rate, 2)} ER</small>
        </div>
      </section>

      <div className="score-strip">
        {SCORE_LABELS.filter(item => Number(m[item.key]) > 0).map(item => (
          <ScoreItem key={item.key} item={item} value={m[item.key]} />
        ))}
      </div>

      <div className="executive-grid premium-grid">
        <div className="executive-card full dark-card">
          <h3>{reachLabel}</h3>
          <div className="big-number">{n(m.total_views)}<span className="unit">{reachUnit}</span></div>
          <div className="desc">
            {isAudience ? 'Суммарное значение' : 'Вовлечений'}: <span className="highlight">{n(isAudience ? m.total_views : m.total_engagement)}</span> ·
            топ-20% строк дают <span className="highlight">{pct(m.top_20_views_share)}</span> объема ·
            тренд: <span className="highlight">{trendLabels[trendDir]}</span>
          </div>
        </div>
        {!isAggregate && <div className="executive-card">
          <h3>Глубина реакции</h3>
          <div className="big-number">{pct(m.attention_quality, 2)}<span className="unit">AQ</span></div>
          <div className="desc">Комментарии: {n(m.total_comments)} · Репосты: {n(m.total_shares)} · Сохранения: {n(m.total_saves)}</div>
        </div>}
        {!isAggregate && <div className="executive-card">
          <h3>Эффективность</h3>
          <div className="big-number">{pct(m.avg_engagement_rate, 2)}<span className="unit">ER</span></div>
          <div className="desc">Макс. ER: {pct(m.max_engagement_rate, 2)} · Постов: {m.post_count}</div>
        </div>}
      </div>

      {data.analysis_profile && (
        <section className={`section data-quality ${data.analysis_profile.confidence || 'medium'}`}>
          <div className="section-header">
            <h2>Надежность анализа</h2>
            <p>Система определила тип выгрузки и отключила показатели, для которых нет исходных данных.</p>
          </div>
          <div className="quality-grid">
            <div><span>Тип данных</span><strong>{data.analysis_profile.report_type || 'не определен'}</strong></div>
            <div><span>Уверенность</span><strong>{data.analysis_profile.confidence === 'high' ? 'высокая' : data.analysis_profile.confidence === 'medium' ? 'средняя' : 'низкая'}</strong></div>
            <div><span>Строк в анализе</span><strong>{data.analysis_profile.rows || 0}</strong></div>
          </div>
          {data.analysis_profile.warnings?.map((warning, index) => <p className="quality-warning" key={index}>{warning}</p>)}
        </section>
      )}

      {topRecommendations.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2>Приоритеты на следующий период</h2>
            <p>Самые важные действия из аналитики</p>
          </div>
          <div className="priority-grid">
            {topRecommendations.map((rec, i) => (
              <article className="priority-card" key={i}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                <h3>{rec.title}</h3>
                <p>{rec.recommendation || rec.description}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {(data.period_comparison?.month || data.period_comparison?.quarter) && (
        <section className="section">
          <div className="section-header">
            <h2>Сравнение периодов</h2>
            <p>Рост, просадка и основные причины изменений</p>
          </div>
          <div className="comparison-grid">
            {['month', 'quarter'].filter(key => data.period_comparison?.[key]).map(key => {
              const item = data.period_comparison[key];
              return (
                <article className="comparison-card" key={key}>
                  <h3>{item.label}</h3>
                  <div className="comparison-metrics">
                    {Object.entries(item.deltas).slice(0, 4).map(([metric, delta]) => (
                      <div className={`comparison-metric ${delta.direction}`} key={metric}>
                        <span>{COMPARE_LABELS[metric] || metric}</span>
                        <strong>{signedPct(delta.percent)}</strong>
                        <small>{metricValue(metric, item.current[metric])} сейчас</small>
                      </div>
                    ))}
                  </div>
                  {item.drivers?.length > 0 && (
                    <ul className="driver-list">
                      {item.drivers.map((driver, i) => <li key={i}>{driver}</li>)}
                    </ul>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}

      {data.benchmarks?.rows?.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2>Бенчмарки</h2>
            <p>{data.benchmarks.platform_label}: {data.benchmarks.summary}</p>
          </div>
          <div className="benchmark-grid">
            {data.benchmarks.rows.map(row => (
              <article className={`benchmark-card ${row.status}`} key={row.metric}>
                <span>{row.label}</span>
                <strong>{row.metric === 'er' ? pct(row.value, 2) : n(row.value)}</strong>
                <small>Норма: {row.metric === 'er' ? `${row.low}-${row.high}%` : `${n(row.low)}-${n(row.high)}`}</small>
                <em>{STATUS_LABELS[row.status] || row.status}</em>
              </article>
            ))}
          </div>
        </section>
      )}

      {data.benchmarks && data.benchmarks.is_applicable === false && (
        <section className="section benchmark-note">
          <div className="section-header">
            <h2>Бенчмарки</h2>
            <p>{data.benchmarks.summary}</p>
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-header">
          <h2>KPI Dashboard</h2>
          <p>Детальные показатели и маркетинговые индексы</p>
        </div>
        <div className="kpi-grid">
          <KpiCard label={isAudience ? 'Аудитория' : 'Просмотры'} value={n(m.total_views)} trend={trendDir} trendLabel={trendLabels[trendDir]} />
          <KpiCard label="Вовлечения" value={n(m.total_engagement)} trend={trendDir === 'up' ? 'up' : 'stable'} />
          <KpiCard label="Средний ER" value={pct(m.avg_engagement_rate, 2)} small />
          <KpiCard label="Макс. ER" value={pct(m.max_engagement_rate, 2)} small accent="positive" />
          <KpiCard label={isAudience ? 'Ср. значение' : 'Ср. просмотров'} value={n(m.avg_views)} small />
          <KpiCard label="Efficiency Index" value={Number(m.content_efficiency_index || 0).toFixed(1)} small />
        </div>
        {data.metrics_extra && Object.keys(data.metrics_extra).length > 0 && (
          <div className="kpi-grid dense" style={{ marginTop: 16 }}>
            {Object.entries(data.metrics_extra).map(([k, v]) => <KpiCard key={k} label={k} value={v} small />)}
          </div>
        )}
      </section>

      <PerformanceCharts charts={data.dashboard_charts} isAudience={isAggregate} />

      {data.top_posts?.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2>Контент</h2>
            <p>Лучшие публикации по просмотрам</p>
          </div>
          <div className="top-posts-card">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  {Object.keys(data.top_posts[0]).filter(k => k !== 'is_viral' && k !== 'views_share').slice(0, 3).map(k => <th key={k}>{k}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.top_posts.map((post, i) => (
                  <tr key={i}>
                    <td className="rank">{i + 1}</td>
                    {Object.entries(post).filter(([k]) => k !== 'is_viral' && k !== 'views_share').slice(0, 3).map(([k, v], j) => (
                      <td key={j}>{typeof v === 'number' ? n(v) : String(v).substring(0, 72)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data.insights?.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2>Инсайты</h2>
            <p>Выводы на основе данных</p>
          </div>
          <InsightsPanel insights={data.insights} />
        </section>
      )}
    </div>
  );
}
