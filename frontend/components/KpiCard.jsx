export default function KpiCard({ label, value, trend, trendLabel, small, accent }) {
  const trendDir = trend === 'up' ? 'up' : trend === 'down' ? 'down' : 'stable';
  const arrows = { up: '↑', down: '↓', stable: '→' };

  return (
    <div className={`kpi-card ${accent || ''}`}>
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${small ? 'small' : ''}`}>{value}</div>
      {trend && (
        <div className={`kpi-trend ${trendDir}`}>
          {arrows[trendDir]} {trendLabel || trend}
        </div>
      )}
    </div>
  );
}
