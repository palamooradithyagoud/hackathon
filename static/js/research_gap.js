/**
 * research_gap.js — Research Gap Analysis Controller
 * Manages analyzer requests, rendering project suggestions with
 * workload warnings, and submitting confirmations to generate email drafts.
 */

import { professorAnalyze, professorConfirm, submitFeedback } from './api.js';
import { renderMarkdown } from './utils.js';
import { toast } from './toast.js';

// DOM Elements
const form = document.getElementById('gap-form');
const topicInput = document.getElementById('gap-topic-input');
const submitBtn = document.getElementById('gap-submit-btn');
const loadingArea = document.getElementById('gap-loading');
const resultsArea = document.getElementById('gap-results');

const trendsEl = document.getElementById('result-trends');
const gapsEl = document.getElementById('result-gaps');
const projectsEl = document.getElementById('result-projects');
const confirmBtn = document.getElementById('confirm-project-btn');

const actionResultEl = document.getElementById('gap-action-result');
const emailPreviewEl = document.getElementById('email-preview');
const resetBtn = document.getElementById('gap-reset-btn');
const starRow = document.getElementById('gap-feedback-stars');

let currentReport = null;
let currentTopic = '';
let selectedProjectIndex = -1;
let currentQueryLogId = null;

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const topic = topicInput.value.trim();
    if (!topic) return;

    // Reset previous states
    resultsArea.style.display = 'none';
    actionResultEl.style.display = 'none';
    confirmBtn.disabled = true;
    selectedProjectIndex = -1;

    // Set Loading state
    loadingArea.style.display = 'block';
    submitBtn.disabled = true;

    try {
      const report = await professorAnalyze(topic);
      currentReport = report;
      currentTopic = topic;

      // Render results
      renderReport(report);

      loadingArea.style.display = 'none';
      resultsArea.style.display = 'flex';

    } catch (err) {
      loadingArea.style.display = 'none';
      toast.error(err.message || 'Analysis failed.');
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function renderReport(report) {
  // 1. Render Trends
  const trendItemsHTML = (report.trend_analysis.trends || []).map(t => `
    <div style="margin-bottom:var(--space-2); border-bottom:1px solid var(--border-color); padding-bottom:var(--space-2);">
      <strong>${t.title}</strong> (${t.source}, Confidence: ${(t.confidence * 100).toFixed(0)}%)
      <p style="color:var(--text-secondary); margin-top:2px;">${t.summary}</p>
    </div>
  `).join('');

  trendsEl.innerHTML = `
    <div style="display:flex; flex-direction:column; gap: var(--space-2);">
      ${trendItemsHTML || '<p>No specific trends identified.</p>'}
      <div style="margin-top: var(--space-2);">
        <strong>Emerging Areas:</strong>
        <p style="color:var(--text-secondary); margin-top:2px;">${(report.trend_analysis.emerging_areas || []).join(', ') || 'None'}</p>
      </div>
    </div>
  `;

  // 2. Render Gaps
  const opportunityGapsHTML = (report.gap_analysis.opportunity_gaps || []).map(g => `
    <li style="margin-bottom:var(--space-2);">
      <strong>${g.gap}:</strong> ${g.why_it_matters}
    </li>
  `).join('');

  gapsEl.innerHTML = `
    <p><strong>Covered Domains:</strong> ${(report.gap_analysis.covered_areas || []).join(', ') || 'None'}</p>
    <p style="margin-top:var(--space-2);"><strong>Missing Gaps:</strong> ${(report.gap_analysis.missing_areas || []).join(', ') || 'None'}</p>
    <div style="margin-top:var(--space-3);">
      <strong>Opportunity Gaps:</strong>
      <ul style="margin-top:var(--space-1); padding-left:20px; color:var(--text-secondary);">
        ${opportunityGapsHTML || '<li>No opportunity gaps identified.</li>'}
      </ul>
    </div>
  `;

  // 3. Render Projects List
  projectsEl.innerHTML = '';
  const suggestions = report.project_suggestions || [];

  suggestions.forEach((proj, idx) => {
    const item = document.createElement('div');
    item.className = 'project-suggestion-item animate-fade-in-up';
    item.style.cursor = 'pointer';
    item.style.marginBottom = 'var(--space-2)';

    // Workload check indicators
    let workloadHTML = '';
    const assigned = proj.faculty || [];
    assigned.forEach(mentor => {
      const stats = report.workload_analysis && report.workload_analysis[mentor];
      if (stats) {
        const isOverloaded = stats.active_projects >= 3;
        const color = isOverloaded ? 'var(--color-error)' : 'var(--color-success)';
        const text = isOverloaded ? 'HIGH LOAD' : 'AVAILABLE';
        workloadHTML += `
          <div style="font-size:11px; margin-top:4px; color:${color}; font-weight:var(--weight-medium);">
            • Mentor: ${mentor} (${stats.active_projects} active projects) - [${text}]
          </div>
        `;
        
        // Find warnings for this mentor
        const warning = (proj.workload_warnings || []).find(w => w.faculty === mentor);
        if (warning && warning.suggested_alternatives && warning.suggested_alternatives.length > 0) {
          const subs = warning.suggested_alternatives.join(', ');
          workloadHTML += `
            <div style="font-size:10px; color:var(--text-faint); margin-left:10px;">
              Substitute suggestion: ${subs}
            </div>
          `;
        }
      }
    });

    item.innerHTML = `
      <input type="radio" name="selected-suggestion" class="select-project-radio" value="${idx}">
      <h5 style="color:var(--text-primary); font-weight:var(--weight-semibold); padding-right:30px;">${proj.title}</h5>
      <p style="font-size:12px; color:var(--text-secondary); margin-top:6px;">${proj.description}</p>
      <div style="font-size:11px; color:var(--color-accent); font-weight:var(--weight-medium); margin-top:8px;">
        Alignment: ${proj.gap_alignment} (${proj.trend_alignment})
      </div>
      ${workloadHTML}
    `;

    // Radio click listener
    const radio = item.querySelector('.select-project-radio');
    item.addEventListener('click', () => {
      radio.checked = true;
      selectedProjectIndex = idx;
      confirmBtn.disabled = false;
    });

    projectsEl.appendChild(item);
  });
}

// Confirm Selection Button
if (confirmBtn) {
  confirmBtn.addEventListener('click', async () => {
    if (selectedProjectIndex === -1 || !currentReport) return;

    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner"></span> Confirming...';

    try {
      const res = await professorConfirm(currentTopic, currentReport, selectedProjectIndex);
      currentQueryLogId = res.query_log_id;

      // Render Email draft
      if (res.email_draft && res.email_draft.subject) {
        emailPreviewEl.textContent = `Subject: ${res.email_draft.subject}\n\n${res.email_draft.body}`;
      } else {
        emailPreviewEl.textContent = typeof res.email_draft === 'string' ? res.email_draft : JSON.stringify(res.email_draft, null, 2);
      }
      actionResultEl.style.display = 'block';

      // Scroll to email
      actionResultEl.scrollIntoView({ behavior: 'smooth' });
      toast.success('Recommendation confirmed and logged to database.');

    } catch (err) {
      toast.error(err.message || 'Confirmation failed.');
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.innerHTML = 'Confirm Selected Suggestion';
    }
  });
}

// Reset view
if (resetBtn) {
  resetBtn.addEventListener('click', () => {
    topicInput.value = '';
    resultsArea.style.display = 'none';
    actionResultEl.style.display = 'none';
    currentReport = null;
    selectedProjectIndex = -1;
    currentQueryLogId = null;
    // Enable stars
    starRow.querySelectorAll('.feedback-btn').forEach(b => {
      b.disabled = false;
      b.style.opacity = '1';
    });
  });
}

// Feedback ratings listener
if (starRow) {
  starRow.querySelectorAll('.feedback-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!currentQueryLogId) return;
      const rating = parseInt(btn.dataset.val);

      try {
        await submitFeedback(currentQueryLogId, rating, 'Gap analysis feedback');
        toast.success('Feedback logged, thank you!');
        // Disable row
        starRow.querySelectorAll('.feedback-btn').forEach(b => {
          b.disabled = true;
          b.style.opacity = '0.4';
        });
      } catch (err) {
        toast.error('Feedback failed to record.');
      }
    });
  });
}
