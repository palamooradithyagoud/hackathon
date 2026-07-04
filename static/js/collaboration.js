/**
 * collaboration.js — Collaboration Finder Controller
 * Manages drop-down selections, form queries, and displaying co-authorship evaluations.
 */

import { collaborate } from './api.js';
import { renderMarkdown } from './utils.js';
import { toast } from './toast.js';

// Pre-seeded faculty profiles list
const PROFS = [
  'Dr. Padmaja',
  'Dr. Venkateshwara',
  'Dr. Madhurya',
  'Dr. Gagandeep',
  'Dr. Vasantha',
  'Prof. Srinivas Gongula',
  'Dr. Ravikumar',
  'Prof. Manzoor'
];

const selectA = document.getElementById('collab-a');
const selectB = document.getElementById('collab-b');
const form = document.getElementById('collab-form');
const submitBtn = document.getElementById('collab-submit-btn');
const loadingEl = document.getElementById('collab-loading');
const resultPanel = document.getElementById('collab-result-panel');
const responseText = document.getElementById('collab-response-text');
const resetBtn = document.getElementById('collab-reset-btn');

document.addEventListener('DOMContentLoaded', () => {
  populateDropdowns();

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const pA = selectA.value;
      const pB = selectB.value;

      if (pA === pB) {
        toast.warning('Please select two different faculty members.');
        return;
      }

      // Hide results, show loader
      resultPanel.style.display = 'none';
      loadingEl.style.display = 'block';
      submitBtn.disabled = true;

      try {
        const data = await collaborate(pA, pB);
        
        // Render co-authorship evaluation markdown
        responseText.innerHTML = renderMarkdown(data.synergy_reason || data.project_idea);
        
        loadingEl.style.display = 'none';
        resultPanel.style.display = 'block';
      } catch (err) {
        loadingEl.style.display = 'none';
        toast.error(err.message || 'Collaboration search failed.');
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      selectA.selectedIndex = 0;
      selectB.selectedIndex = 1;
      resultPanel.style.display = 'none';
    });
  }
});

function populateDropdowns() {
  if (!selectA || !selectB) return;
  
  selectA.innerHTML = '';
  selectB.innerHTML = '';

  PROFS.forEach((prof, idx) => {
    const optA = document.createElement('option');
    optA.value = prof;
    optA.textContent = prof;
    selectA.appendChild(optA);

    const optB = document.createElement('option');
    optB.value = prof;
    optB.textContent = prof;
    // Offset default values
    if (idx === 1) optB.selected = true;
    selectB.appendChild(optB);
  });
}
