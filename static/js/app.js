/**
 * app.js — App Shell Initialization
 * Handles: sidebar toggle, mobile nav, active page, breadcrumb
 * @module app
 */

import { theme } from './theme.js';

// ── Sidebar State ──────────────────────────────────────────────
function initSidebar() {
  const sidebar     = document.querySelector('.sidebar');
  const toggleBtn   = document.querySelector('.sidebar-toggle');
  const overlay     = document.querySelector('.sidebar-overlay');
  const hamburger   = document.querySelector('.hamburger');

  if (!sidebar) return;

  // Restore collapsed state
  const collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
  if (collapsed) sidebar.classList.add('collapsed');

  // Desktop collapse toggle
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
    });
  }

  // Mobile hamburger
  if (hamburger) {
    hamburger.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
      if (overlay) overlay.classList.toggle('active');
    });
  }

  // Close on overlay click
  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      overlay.classList.remove('active');
    });
  }

  // Close mobile sidebar on nav link click
  sidebar.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('mobile-open');
        if (overlay) overlay.classList.remove('active');
      }
    });
  });
}

// ── Active Nav Item ────────────────────────────────────────────
function setActiveNavItem() {
  const currentPath = window.location.pathname;
  const filename = currentPath.split('/').pop() || 'index.html';

  document.querySelectorAll('.nav-item[href]').forEach(item => {
    const href = item.getAttribute('href');
    const hrefFile = (href || '').split('/').pop();

    if (hrefFile === filename ||
        (filename === '' && hrefFile === 'index.html') ||
        (filename === 'index.html' && hrefFile === '')) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
}

// ── Page Entrance Animation ────────────────────────────────────
function initPageAnimation() {
  const content = document.querySelector('.page-content');
  if (content) {
    content.style.opacity = '0';
    content.style.transform = 'translateY(12px)';
    content.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    requestAnimationFrame(() => {
      content.style.opacity = '1';
      content.style.transform = 'translateY(0)';
    });
  }
}

// ── Keyboard Navigation ────────────────────────────────────────
function initKeyboardNav() {
  document.addEventListener('keydown', (e) => {
    // Escape: close modals
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.open').forEach(modal => {
        modal.classList.remove('open');
      });
    }

    // Ctrl+K: focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const search = document.querySelector('.navbar-search input');
      if (search) search.focus();
    }
  });
}

// ── Global Search Bar ──────────────────────────────────────────
function initGlobalSearch() {
  const searchInput = document.querySelector('.navbar-search input');
  if (!searchInput) return;

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchInput.value.trim();
      if (q) {
        window.location.href = `chat.html?q=${encodeURIComponent(q)}`;
      }
    }
  });
}

// ── Ripple Effect on Buttons ───────────────────────────────────
function initRipple() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn, .nav-item');
    if (!btn || !btn.classList.contains('ripple')) return;

    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top  - size / 2;

    const wave = document.createElement('span');
    wave.classList.add('ripple-wave');
    wave.style.cssText = `width:${size}px;height:${size}px;left:${x}px;top:${y}px;`;
    btn.appendChild(wave);
    wave.addEventListener('animationend', () => wave.remove(), { once: true });
  });
}

// ── Modal Helpers (exported globally) ─────────────────────────
window.openModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('open');
};

window.closeModal = function(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
};

// ── App Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  theme.init();
  initSidebar();
  setActiveNavItem();
  initPageAnimation();
  initKeyboardNav();
  initGlobalSearch();
  initRipple();
});
