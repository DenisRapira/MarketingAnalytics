const API_BASE = '/api';

export async function uploadFile(file, companyName = '') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('company_name', companyName.trim());

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(err || 'Upload failed');
  }

  return response.json();
}

export async function downloadReport(sessionId, profiles = []) {
  const params = profiles.length ? `?profiles=${profiles.join(',')}` : '';
  const response = await fetch(`${API_BASE}/report/${sessionId}${params}`);
  if (!response.ok) throw new Error('Report generation failed');

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `marketing_report_${sessionId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  return true;
}

export function getChartUrl(sessionId, chartName) {
  return `${API_BASE}/charts/${sessionId}/${chartName}`;
}
