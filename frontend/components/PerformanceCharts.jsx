import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend, Filler);

const BLUE = '#1c5eaa';
const ORANGE = '#ff4b01';

function formatNumber(value) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value || 0);
}

const sharedOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: 'index' },
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: item => `${item.dataset.label}: ${formatNumber(item.raw)}` } },
  },
  scales: {
    x: { grid: { display: false }, ticks: { color: '#64748b', maxTicksLimit: 10 } },
    y: { beginAtZero: true, grid: { color: '#e8edf3' }, ticks: { color: '#64748b', callback: formatNumber } },
  },
};

export default function PerformanceCharts({ charts, isAudience }) {
  const series = charts?.time_series;
  const platforms = charts?.platforms || [];
  if (!series?.values?.length && !platforms.length) return null;

  const metricLabel = isAudience ? 'Аудитория' : 'Просмотры';
  return (
    <section className="section">
      <div className="section-header">
        <h2>Динамика и каналы</h2>
        <p>Наведите курсор на точку или столбец, чтобы увидеть точное значение</p>
      </div>
      <div className="interactive-charts-grid">
        {series?.values?.length > 0 && (
          <article className="interactive-chart full">
            <h3>{isAudience ? 'Динамика аудитории' : 'Динамика просмотров'}</h3>
            <div className="chart-canvas">
              <Line data={{ labels: series.labels, datasets: [{ label: metricLabel, data: series.values, borderColor: BLUE, backgroundColor: 'rgba(28,94,170,0.10)', fill: true, tension: 0.28, pointRadius: 3, pointHoverRadius: 5, borderWidth: 2.5 }] }} options={sharedOptions} />
            </div>
          </article>
        )}
        {platforms.length > 1 && (
          <article className="interactive-chart">
            <h3>Сравнение платформ</h3>
            <div className="chart-canvas">
              <Bar data={{ labels: platforms.map(item => item.label), datasets: [{ label: metricLabel, data: platforms.map(item => item.views), backgroundColor: platforms.map((_, index) => index === 0 ? BLUE : ORANGE), borderRadius: 4, borderSkipped: false }] }} options={sharedOptions} />
            </div>
          </article>
        )}
      </div>
    </section>
  );
}
