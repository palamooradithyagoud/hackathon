/**
 * dashboard.js — Dashboard controller
 * Loads stats, logs, trending domains, and draws charts using HTML5 Canvas.
 */

import { getStats, getLogs, uploadPdf } from './api.js';
import { animateNumber, formatRelativeTime } from './utils.js';
import { toast } from './toast.js';

// Elements
const papersEl = document.getElementById('dashboard-total-papers');
const facultyEl = document.getElementById('dashboard-total-faculty');
const chunksEl = document.getElementById('dashboard-total-chunks');
const queriesEl = document.getElementById('dashboard-total-queries');
const activityEl = document.getElementById('dashboard-activity-list');
const trendingEl = document.getElementById('dashboard-trending-list');
const modelBadge = document.getElementById('navbar-model-badge');
const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('pdf-file-input');
const uploadTrigger = document.getElementById('upload-pdf-trigger');

/**
 * Initialize all dashboard elements
 */
async function initDashboard() {
  try {
    // 1. Fetch Stats & Logs in parallel
    const [stats, logs] = await Promise.all([getStats(), getLogs()]);

    // 2. Render counter statistics
    if (papersEl) animateNumber(papersEl, 0, stats.paper_count);
    if (facultyEl) animateNumber(facultyEl, 0, stats.faculty_count);
    if (chunksEl) animateNumber(chunksEl, 0, stats.chunk_count);
    if (queriesEl) animateNumber(queriesEl, 0, stats.total_queries);
    if (modelBadge && stats.model) modelBadge.textContent = stats.model;

    // 3. Render Intent Breakdown Chart
    drawIntentChart(stats.intent_breakdown || {});

    // 4. Render Trending Domains list
    renderTrending(stats.domains || []);

    // 5. Render Activity Logs feed
    renderActivity(logs);

  } catch (err) {
    console.error('Dashboard init failed:', err);
    toast.error('Failed to load dashboard statistics.');
  }
}

/**
 * Draws a donut/pie chart of query intents on canvas
 */
function drawIntentChart(breakdown) {
  const canvas = document.getElementById('intent-chart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  // Set dimensions based on client bounding rect
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;

  const width = canvas.width;
  const height = canvas.height;
  const centerX = width * 0.35;
  const centerY = height * 0.5;
  const radius = Math.min(width, height) * 0.35;

  const data = Object.entries(breakdown).map(([label, val]) => ({ label, val }));
  if (data.length === 0) {
    // Draw empty state
    ctx.fillStyle = '#6B7280';
    ctx.font = '14px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('No query logs recorded yet', centerX, centerY);
    return;
  }

  const total = data.reduce((sum, item) => sum + item.val, 0);
  let startAngle = 0;

  const colors = ['#4F46E5', '#06B6D4', '#10B981', '#F59E0B', '#EF4444'];

  ctx.clearRect(0, 0, width, height);

  // Draw chart slices
  data.forEach((item, index) => {
    const sliceAngle = (item.val / total) * 2 * Math.PI;
    const color = colors[index % colors.length];

    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();

    startAngle += sliceAngle;
  });

  // Inner cutout to make it a donut chart
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius * 0.6, 0, 2 * Math.PI);
  ctx.fillStyle = '#111827'; // Matches surface color
  ctx.fill();

  // Draw Legend beside chart
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.font = '12px Inter';

  let legendY = height * 0.2;
  data.forEach((item, index) => {
    const color = colors[index % colors.length];
    const percentage = Math.round((item.val / total) * 100);

    // Color marker
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(width * 0.72, legendY, 5, 0, 2 * Math.PI);
    ctx.fill();

    // Text Label
    ctx.fillStyle = '#9CA3AF';
    ctx.fillText(`${item.label} (${percentage}%)`, width * 0.76, legendY);

    legendY += 30;
  });
}

/**
 * Render trending domains progress bars
 */
function renderTrending(domains) {
  if (!trendingEl) return;
  trendingEl.innerHTML = '';

  const sample = domains.slice(0, 4);
  const maxBarWidth = 100; // percent

  sample.forEach((domain, idx) => {
    const percent = 100 - (idx * 20); // visual representation
    const item = document.createElement('div');
    item.className = 'trending-item';
    item.innerHTML = `
      <span class="trending-rank">${idx + 1}</span>
      <span class="trending-name">${domain}</span>
      <div class="trending-bar-wrapper">
        <div class="trending-bar animate-glow" style="width: ${percent}%;"></div>
      </div>
    `;
    trendingEl.appendChild(item);
  });
}

/**
 * Render recent queries activity list
 */
function renderActivity(logs) {
  if (!activityEl) return;
  activityEl.innerHTML = '';

  if (logs.length === 0) {
    activityEl.innerHTML = '<div style="color:var(--text-faint);font-size:var(--text-xs);padding:var(--space-3) 0;">No query logs recorded.</div>';
    return;
  }

  logs.slice(0, 5).forEach((log) => {
    const item = document.createElement('div');
    item.className = 'activity-item';

    const cleanMode = log.mode.toLowerCase();
    const modeLabels = {
      rag: 'RAG Chat',
      professor: 'Professor Gap',
      collaborate: 'Collaborate',
      recommend: 'Recommend'
    };

    item.innerHTML = `
      <div class="activity-dot ${cleanMode}"></div>
      <div class="activity-content">
        <div class="activity-query" title="${log.query}">${log.query}</div>
        <div class="activity-meta">
          <span class="activity-mode" style="color: ${getModeColor(cleanMode)};">${modeLabels[cleanMode] || 'Query'}</span>
          <span style="color: var(--text-faint); font-size:10px;">•</span>
          <span class="activity-time">${formatRelativeTime(log.timestamp)}</span>
        </div>
      </div>
    `;
    activityEl.appendChild(item);
  });
}

function getModeColor(mode) {
  const colors = {
    rag: 'var(--color-primary)',
    professor: 'var(--color-accent)',
    collaborate: 'var(--color-success)',
    recommend: 'var(--color-warning)'
  };
  return colors[mode] || 'var(--text-faint)';
}

// ── Ingest modal handlers ──
if (uploadTrigger) {
  uploadTrigger.addEventListener('click', () => {
    window.openModal('upload-modal');
  });
}

if (uploadForm) {
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;

    const submitBtn = document.getElementById('upload-submit-btn');
    const oldText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Ingesting...';

    try {
      const res = await uploadPdf(file);
      toast.success(res.message || 'Ingestion completed successfully.');
      window.closeModal('upload-modal');
      uploadForm.reset();
      // Reload stats
      initDashboard();
    } catch (err) {
      toast.error(err.message || 'PDF ingestion failed.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = oldText;
    }
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
