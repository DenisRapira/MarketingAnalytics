import { useState, useCallback } from 'react';
import Head from 'next/head';
import FileUpload from '../components/FileUpload';
import Dashboard from '../components/Dashboard';
import { uploadFile, downloadReport } from '../utils/api';

const PROFILE_LABELS = {
  youtube: { label: 'YouTube', icon: '▶️', desc: 'Видео-контент' },
  vk_posts: { label: 'VK Записи', icon: '📝', desc: 'Посты и статьи' },
  vk_clips: { label: 'VK Клипы', icon: '🎬', desc: 'Короткие видео' },
};

export default function Home() {
  const [state, setState] = useState('upload'); // upload | loading | profiles | dashboard | error
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedProfiles, setSelectedProfiles] = useState([]);
  const [companyName, setCompanyName] = useState('');

  const handleUpload = useCallback(async (file) => {
    setState('loading');
    setError(null);
    try {
      const result = await uploadFile(file, companyName);
      setData(result);
      const avail = result.available_profiles || [];
      if (avail.length > 0) {
        setSelectedProfiles(avail);
        setState('profiles');
      } else {
        setState('dashboard');
      }
    } catch (err) {
      setError(err.message || 'Ошибка при обработке файла');
      setState('error');
    }
  }, []);

  const toggleProfile = useCallback((pid) => {
    setSelectedProfiles(prev =>
      prev.includes(pid) ? prev.filter(p => p !== pid) : [...prev, pid]
    );
  }, []);

  const handleProceed = useCallback(() => {
    setState('dashboard');
  }, []);

  const handleExport = useCallback(async () => {
    if (!data?.session_id) return;
    try {
      await downloadReport(data.session_id, selectedProfiles);
    } catch (err) {
      setError(err.message || 'Ошибка при генерации PDF');
    }
  }, [data, selectedProfiles]);

  const handleReset = useCallback(() => {
    setState('upload');
    setData(null);
    setError(null);
    setSelectedProfiles([]);
  }, []);

  return (
    <div>
      <Head>
        <title>Marketing Analytics</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>
      {/* ── Header ── */}
      <header className="header">
        <div className="container header-inner">
          <div className="header-left">
            <img className="brand-mark" src="/marketing-logo.jpg" alt="" />
            <div className="header-logo">
              <span>Marketing</span> Analytics
            </div>
            <span className="header-badge">Pro</span>
          </div>
          <div className="header-right">
            {state === 'dashboard' && (
              <button className="btn btn-primary" onClick={handleExport} style={{ padding: '8px 16px', fontSize: 13 }}>
                📄 PDF
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="container">
        {/* UPLOAD */}
        {state === 'upload' && (
          <div className="upload-section">
            <div className="upload-hero">
              <h1>Marketing Analytics</h1>
              <p>
                Загрузите Excel или CSV с метриками YouTube, VK или Telegram. Система соберет
                executive dashboard, маркетинговые индексы, рекомендации и печатный PDF для клиента.
              </p>
            </div>
            <div className="report-company-field">
              <label htmlFor="company-name">Компания в отчете</label>
              <input
                id="company-name"
                value={companyName}
                onChange={event => setCompanyName(event.target.value.slice(0, 100))}
                placeholder="Например, ООО «Альфа»"
                autoComplete="organization"
              />
              <small>Название появится на обложке, в колонтитулах и имени PDF.</small>
            </div>
            <FileUpload onUpload={handleUpload} />
            <div className="upload-features">
              <div className="upload-feature">
                <div className="upload-feature-icon">01</div>
                <div className="upload-feature-title">Умный импорт</div>
                <div className="upload-feature-desc">Автоопределение колонок, чистка чисел, дат и дублей</div>
              </div>
              <div className="upload-feature">
                <div className="upload-feature-icon">02</div>
                <div className="upload-feature-title">Маркетинговые формулы</div>
                <div className="upload-feature-desc">ER, Health Score, Amplification, Conversation, Save Intent</div>
              </div>
              <div className="upload-feature">
                <div className="upload-feature-icon">03</div>
                <div className="upload-feature-title">Печатный PDF</div>
                <div className="upload-feature-desc">Обложка, KPI, графики, выводы и план действий</div>
              </div>
            </div>
          </div>
        )}

        {/* LOADING */}
        {state === 'loading' && (
          <div className="loading-section">
            <div className="loading-spinner" />
            <div className="loading-text">Анализируем данные...</div>
            <div className="loading-steps">
              <div className="loading-step done"><span>✓</span> Файл загружен</div>
              <div className="loading-step active"><span>○</span> Определение колонок</div>
              <div className="loading-step"><span>○</span> Очистка и расчёт метрик</div>
              <div className="loading-step"><span>○</span> Построение графиков</div>
            </div>
          </div>
        )}

        {/* PROFILE SELECTION */}
        {state === 'profiles' && data && (
          <div className="upload-section">
            <div className="upload-hero">
              <h1>Выберите профили для отчёта</h1>
              <p>Отметьте какие источники данных включить в аналитику</p>
            </div>
            <div className="upload-features" style={{ maxWidth: 500, margin: '0 auto' }}>
              {(data.available_profiles || []).map(pid => {
                const info = PROFILE_LABELS[pid] || { label: pid, icon: '📊', desc: '' };
                const active = selectedProfiles.includes(pid);
                return (
                  <div
                    key={pid}
                    onClick={() => toggleProfile(pid)}
                    className="upload-feature"
                    style={{
                      cursor: 'pointer',
                      border: active ? '2px solid var(--accent)' : '2px solid var(--gray-200)',
                      background: active ? 'var(--accent-bg)' : 'white',
                      transition: 'all 0.2s',
                      marginBottom: 8,
                    }}
                  >
                    <div className="upload-feature-icon">
                      {active ? '✅ ' : ''}{info.icon}
                    </div>
                    <div className="upload-feature-title">{info.label}</div>
                    <div className="upload-feature-desc">{info.desc}</div>
                  </div>
                );
              })}
            </div>
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleProceed}
                disabled={selectedProfiles.length === 0}
              >
                Сформировать отчёт ({selectedProfiles.length})
              </button>
            </div>
          </div>
        )}

        {/* DASHBOARD */}
        {state === 'dashboard' && data && (
          <Dashboard
            data={data}
            onExport={handleExport}
            onReset={handleReset}
            onProfilesChange={setSelectedProfiles}
            selectedProfiles={selectedProfiles}
          />
        )}

        {/* ERROR */}
        {state === 'error' && (
          <div className="error-section">
            <div className="error-icon">⚠️</div>
            <h2>Ошибка обработки</h2>
            <p>{error || 'Не удалось обработать файл. Проверьте формат данных и попробуйте снова.'}</p>
            <button className="btn btn-primary btn-lg" onClick={handleReset}>
              Попробовать снова
            </button>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        Marketing Analytics — автономная аналитическая система • Все данные обрабатываются локально
      </footer>
    </div>
  );
}
