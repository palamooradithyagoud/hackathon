/**
 * faculty.js — Faculty Explorer Controller
 * Manages search, filter categories, switching layout views, and modal popups.
 */

import { recommend } from './api.js';
import { getInitials, stringToColor } from './utils.js';
import { toast } from './toast.js';

// Faculty Seed Data matching paper author profiles
const FACULTY_MEMBERS = [
  {
    name: 'Dr. Padmaja',
    dept: 'cse',
    deptLabel: 'Computer Science & Engineering',
    domain: 'Agriculture AI / Computer Vision',
    bio: 'Specializes in applying deep neural network architectures to detect crop disease patterns early, enhancing agricultural forecasting metrics.',
    paper: 'Agri-Ai-Intelligent-Plant-Disease-Surveillance-and-Predictive-Forecasting_PADMAJA.pdf',
    tags: ['Agriculture AI', 'Computer Vision', 'Deep Learning']
  },
  {
    name: 'Dr. Venkateshwara',
    dept: 'cse',
    deptLabel: 'Computer Science & Engineering',
    domain: 'Machine Learning / Feature Engineering',
    bio: 'Research covers predictive mathematical models, dimensionality reduction pipelines, and customized feature extraction techniques.',
    paper: 'Comprehensive Models Towards for Feature_venkateshwara.pdf',
    tags: ['Machine Learning', 'Feature Selection', 'Mathematics']
  },
  {
    name: 'Dr. Madhurya',
    dept: 'it',
    deptLabel: 'Information Technology',
    domain: 'IoT / Networking Protocols',
    bio: 'Designs low-power named data networking models to optimize bandwidth allocations and edge routing across massive IoT sensor grids.',
    paper: 'Integrating Named Data Networking with IoT-Based Internet _MADHURYA.pdf',
    tags: ['IoT', 'Networking', 'Edge Computing']
  },
  {
    name: 'Dr. Gagandeep',
    dept: 'ece',
    deptLabel: 'Electronics & Communication',
    domain: 'IoT / Healthcare Tech',
    bio: 'Develops connected remote sensory instrumentation, patient telemetry systems, and body sensor networking algorithms.',
    paper: 'IOT based health monitoring_gagandeep.pdf',
    tags: ['Healthcare IT', 'Embedded Systems', 'Telemetry']
  },
  {
    name: 'Dr. Vasantha',
    dept: 'it',
    deptLabel: 'Information Technology',
    domain: 'Network Infrastructure Energy',
    bio: 'Analyzes energy consumption metrics across router nodes, optical trunks, and software defined edge architectures.',
    paper: 'Measuring Internet Energy Consumption at The Edge and Core_vasantha.pdf',
    tags: ['Green Computing', 'Power Optimization', 'Broadband']
  },
  {
    name: 'Prof. Srinivas Gongula',
    dept: 'cse',
    deptLabel: 'Computer Science & Engineering',
    domain: 'Big Data / Accident Detection',
    bio: 'Engineers live streaming analytics architectures using Apache Spark/Kafka to evaluate vehicle crashes and alert medical responders.',
    paper: 'Accident Detection and Alert System Using Big Data Analytics_SRININVAS_GONGULA.pdf',
    tags: ['Big Data', 'Streaming Data', 'Alert Systems']
  },
  {
    name: 'Dr. Ravikumar',
    dept: 'ece',
    deptLabel: 'Electronics & Communication',
    domain: 'IPv6 Network Protocols',
    bio: 'Tracks long-term IPv6 deployment vectors, translation mechanisms, and transition bottlenecks across national network nodes.',
    paper: 'Characterizing Ipv6 Adoption Trends Through Longitudinal _RAVIKUMAR.pdf',
    tags: ['IPv6 Migration', 'Internet Routing', 'Security']
  },
  {
    name: 'Prof. Manzoor',
    dept: 'cse',
    deptLabel: 'Computer Science & Engineering',
    domain: 'Generative Models / CNN',
    bio: 'Studies diffusion models, GANs, generative denoising sequences, and their cross-comparisons against convolutional feature extractors.',
    paper: 'From CNNs to diffusion models_MANZOOR.pdf',
    tags: ['Generative AI', 'CNNs', 'Diffusion Models']
  }
];

let activeView = 'grid';
let activeDept = 'all';
let searchFilter = '';

const gridBtn = document.getElementById('view-grid-btn');
const listBtn = document.getElementById('view-list-btn');
const searchInput = document.getElementById('faculty-search-input');
const displayGrid = document.getElementById('faculty-display-grid');

// Modal Elements
const modalAvatar = document.getElementById('modal-avatar');
const modalName = document.getElementById('modal-name');
const modalDomain = document.getElementById('modal-domain');
const modalBio = document.getElementById('modal-bio');
const modalPaper = document.getElementById('modal-paper-title');

document.addEventListener('DOMContentLoaded', () => {
  renderFaculty();

  // Listeners
  if (gridBtn) gridBtn.addEventListener('click', () => setView('grid'));
  if (listBtn) listBtn.addEventListener('click', () => setView('list'));

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchFilter = e.target.value.toLowerCase().trim();
      renderFaculty();
    });
  }

  // Dept filter tabs
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeDept = chip.dataset.dept;
      renderFaculty();
    });
  });
});

function setView(view) {
  activeView = view;
  if (view === 'grid') {
    gridBtn.classList.add('active');
    listBtn.classList.remove('active');
    displayGrid.className = 'faculty-grid';
  } else {
    listBtn.classList.add('active');
    gridBtn.classList.remove('active');
    displayGrid.className = 'faculty-list-view';
  }
  renderFaculty();
}

/**
 * Filter and render faculty cards or lists
 */
function renderFaculty() {
  if (!displayGrid) return;
  displayGrid.innerHTML = '';

  const filtered = FACULTY_MEMBERS.filter(member => {
    // Dept check
    if (activeDept !== 'all' && member.dept !== activeDept) return false;
    // Search check
    if (searchFilter) {
      return (
        member.name.toLowerCase().includes(searchFilter) ||
        member.domain.toLowerCase().includes(searchFilter) ||
        member.tags.some(t => t.toLowerCase().includes(searchFilter))
      );
    }
    return true;
  });

  if (filtered.length === 0) {
    displayGrid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1;">
        <div class="empty-state-icon">🔍</div>
        <h3>No Faculty Found</h3>
        <p>Try clearing filters or checking spelling.</p>
      </div>
    `;
    return;
  }

  filtered.forEach(member => {
    const cardColor = stringToColor(member.name);
    const initials = getInitials(member.name);

    let element;
    if (activeView === 'grid') {
      element = document.createElement('div');
      element.className = 'faculty-card animate-scale-in';
      element.innerHTML = `
        <div class="faculty-card-header">
          <div class="faculty-avatar" style="background:${cardColor};">${initials}</div>
          <div>
            <h4 class="faculty-name">${member.name}</h4>
            <div class="faculty-department">${member.deptLabel}</div>
          </div>
        </div>
        <p style="font-size: var(--text-xs); color:var(--text-muted); line-height:1.5;">${member.domain}</p>
        <div class="faculty-tags">
          ${member.tags.map(t => `<span class="tag">${t}</span>`).join('')}
        </div>
      `;
    } else {
      element = document.createElement('div');
      element.className = 'faculty-list-item animate-fade-in-up';
      element.innerHTML = `
        <div class="faculty-avatar" style="background:${cardColor}; width:40px; height:40px; font-size:var(--text-sm);">${initials}</div>
        <div style="flex:1;">
          <h4 class="faculty-name">${member.name}</h4>
          <span style="font-size: var(--text-xs); color: var(--text-muted);">${member.deptLabel} • ${member.domain}</span>
        </div>
        <div class="faculty-tags" style="margin-top:0;">
          ${member.tags.map(t => `<span class="tag">${t}</span>`).join('')}
        </div>
      `;
    }

    element.addEventListener('click', () => showDetails(member));
    displayGrid.appendChild(element);
  });
}

function showDetails(member) {
  modalAvatar.textContent = getInitials(member.name);
  modalAvatar.style.background = stringToColor(member.name);
  modalName.textContent = member.name;
  modalDomain.textContent = member.domain;
  modalBio.textContent = member.bio;
  modalPaper.textContent = member.paper;

  window.openModal('faculty-detail-modal');
}
