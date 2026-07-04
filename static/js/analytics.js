/**
 * analytics.js — Analytics controller
 * Loads logs, computes distributions, and renders HTML/Canvas dashboards.
 */

import { getStats, getLogs } from './api.js';
import { formatDate } from './utils.js';
import { toast } from './toast.js';

const barChartWrap = document.getElementById('analytics-bar-chart');
const logRows = document.getElementById('analytics-log-rows');
const donutLegend = document.getElementById('analytics-donut-legend');

// Faculty mock counts derived from actual authors
const FACULTY_CONTRIBUTIONS = [
  { name: 'Dr. Padmaja', count: 1 },
  { name: 'Dr. Venkateshwara', count: 1 },
  { name: 'Dr. Madhurya', count: 1 },
  { name: 'Dr. Gagandeep', count: 1 },
  { name: 'Dr. Vasantha', count: 1 },
  { name: 'Prof. Srinivas Gongula', count: 1 },
  { name: 'Dr. Ravikumar', count: 1 },
  { name: 'Prof. Manzoor', count: 1 }
];

document.addEventListener('DOMContentLoaded', initAnalytics);

async function initAnalytics() {
  try {
    const [stats, logs] = await Promise.all([getStats(), getLogs()]);

    renderFacultyContribution();
    renderDonutChart(stats.intent_breakdown || {});
    renderAuditLogs(logs);

  } catch (err) {
    console.error('Analytics load failed:', err);
    toast.error('Failed to load analytics data.');
  }
}

/**
 * Render custom CSS bar charts for contributions
 */
function renderFacultyContribution() {
  if (!barChartWrap) return;
  barChartWrap.innerHTML = '';

  const maxVal = 1; // since it is 1 paper per seed

  FACULTY_CONTRIBUTIONS.forEach(item => {
    const pct = (item.count / maxVal) * 100;
    const barEl = document.createElement('div');
    barEl.className = 'bar-item animate-fade-in-up';
    barEl.innerHTML = `
      <span class="bar-label">${item.name}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:${pct}%;"></div>
      </div>
      <span class="bar-value">${item.count}</span>
    `;
    barChartWrap.appendChild(barEl);
  });
}

/**
 * Render standard Donut chart on Canvas + legends
 */
function renderDonutChart(breakdown) {
  const canvas = document.getElementById('analytics-donut-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  canvas.width = 140;
  canvas.height = 140;

  const centerX = 70;
  const centerY = 70;
  const radius = 60;

  const entries = Object.entries(breakdown).map(([label, val]) => ({ label, val }));
  if (entries.length === 0) {
    ctx.fillStyle = '#6B7280';
    ctx.font = '10px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('No data', centerX, centerY);
    return;
  }

  const total = entries.reduce((s, e) => s + e.val, 0);
  let startAngle = 0;
  const colors = ['#4F46E5', '#06B6D4', '#10B981', '#F59E0B', '#EF4444'];

  ctx.clearRect(0, 0, 140, 140);

  entries.forEach((e, idx) => {
    const slice = (e.val / total) * 2 * Math.PI;
    const color = colors[idx % colors.length];

    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, startAngle + slice);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();

    startAngle += slice;
  });

  // Center hole cutout
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius * 0.6, 0, 2 * Math.PI);
  ctx.fillStyle = '#111827';
  ctx.fill();

  // Render Legend
  if (donutLegend) {
    donutLegend.innerHTML = '';
    entries.forEach((e, idx) => {
      const color = colors[idx % colors.length];
      const pct = Math.round((e.val / total) * 100);
      const legItem = document.createElement('div');
      legItem.className = 'donut-legend-item';
      legItem.innerHTML = `
        <div class="donut-legend-label">
          <span class="legend-dot" style="background:${color}; width:8px; height:8px;"></span>
          <span>${e.label.toUpperCase()}</span>
        </div>
        <span class="donut-legend-value">${e.val} (${pct}%)</span>
      `;
      donutLegend.appendChild(legItem);
    });
  }
}

/**
 * Populate Audit logs rows
 */
function renderAuditLogs(logs) {
  if (!logRows) return;
  logRows.innerHTML = '';

  if (logs.length === 0) {
    logRows.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-faint);">No log logs found.</td></tr>';
    return;
  }

  logs.forEach(log => {
    const tr = document.createElement('tr');
    tr.className = 'animate-fade-in';
    tr.innerHTML = `
      <td>${log.id}</td>
      <td style="font-weight:var(--weight-medium); max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${log.query}">${log.query}</td>
      <td><span class="badge ${getIntentBadgeClass(log.mode)}">${log.mode.toUpperCase()}</span></td>
      <td>${formatDate(log.timestamp)}</td>
    `;
    logRows.appendChild(tr);
  });
}

function getIntentBadgeClass(intent) {
  const mapping = {
    rag: 'badge-primary',
    professor: 'badge-accent',
    collaborate: 'badge-success',
    recommend: 'badge-warning'
  };
  return mapping[intent.toLowerCase()] || 'badge-primary';
}
