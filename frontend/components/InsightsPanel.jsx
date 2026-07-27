const ICONS = {
  positive: '✅',
  negative: '🔴',
  warning: '⚠️',
  neutral: '📌',
};

const CAT_LABELS = {
  performance: 'Общая эффективность',
  engagement: 'Вовлечённость',
  trend: 'Тренды',
  viral: 'Вирусный контент',
  platform: 'Платформы',
  anomaly: 'Аномалии',
  growth: 'Рост аудитории',
};

export default function InsightsPanel({ insights }) {
  if (!insights || insights.length === 0) {
    return <p style={{ color: 'var(--gray-400)', fontSize: 14 }}>Инсайты не сгенерированы</p>;
  }

  const grouped = {};
  for (const ins of insights) {
    const cat = ins.category || 'other';
    if (!grouped[cat]) grouped[cat] = [];
    if (grouped[cat].length < 4) grouped[cat].push(ins);
  }

  const order = ['performance', 'engagement', 'trend', 'viral', 'platform', 'growth', 'anomaly'];
  const sorted = order.filter(c => grouped[c]);

  return (
    <div>
      {sorted.map(cat => (
        <div key={cat} style={{ marginBottom: 24 }}>
          <h4 style={{
            fontSize: 12, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: 0.8, color: 'var(--gray-400)', marginBottom: 10
          }}>
            {CAT_LABELS[cat] || cat}
          </h4>
          <div className="insights-list">
            {grouped[cat].map((ins, i) => (
              <div className="insight-item" key={i}>
                <div className="insight-icon">{ICONS[ins.severity] || '📌'}</div>
                <div className="insight-content">
                  <div className="insight-title">{ins.title}</div>
                  <div className="insight-desc">{ins.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
