/**
 * toast.js — Toast Notification Manager
 * @module toast
 */

class ToastManager {
  constructor() {
    this.container = null;
    this._init();
  }

  _init() {
    if (document.getElementById('toast-container')) return;
    this.container = document.createElement('div');
    this.container.id = 'toast-container';
    this.container.setAttribute('aria-live', 'polite');
    this.container.setAttribute('aria-atomic', 'false');
    this.container.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    `;
    document.body.appendChild(this.container);
  }

  /**
   * Show a toast notification.
   * @param {string} message
   * @param {'success'|'error'|'warning'|'info'} type
   * @param {number} duration - ms before auto-dismiss
   */
  show(message, type = 'info', duration = 4000) {
    this._init();

    const icons = {
      success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>`,
      error:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
      warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      info:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    };

    const colors = {
      success: { bg: '#0F2A20', border: '#10B981', color: '#10B981' },
      error:   { bg: '#2A0F0F', border: '#EF4444', color: '#EF4444' },
      warning: { bg: '#2A1F0F', border: '#F59E0B', color: '#F59E0B' },
      info:    { bg: '#0F1A2A', border: '#3B82F6', color: '#3B82F6' },
    };

    const c = colors[type] || colors.info;

    const toast = document.createElement('div');
    toast.setAttribute('role', 'alert');
    toast.style.cssText = `
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 14px 16px;
      background: ${c.bg};
      border: 1px solid ${c.border};
      border-radius: 12px;
      color: #F9FAFB;
      font-family: 'Inter', sans-serif;
      font-size: 14px;
      line-height: 1.5;
      max-width: 360px;
      min-width: 260px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      pointer-events: all;
      animation: toast-in 0.3s cubic-bezier(0.34,1.56,0.64,1) forwards;
      position: relative;
      overflow: hidden;
    `;

    const iconEl = document.createElement('div');
    iconEl.innerHTML = icons[type] || icons.info;
    iconEl.style.cssText = `
      width: 18px; height: 18px; flex-shrink: 0;
      color: ${c.color}; margin-top: 1px;
    `;
    iconEl.querySelector('svg').style.cssText = 'width:18px;height:18px;';

    const msgEl = document.createElement('div');
    msgEl.style.flex = '1';
    msgEl.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
    closeBtn.style.cssText = `
      background: none; border: none; cursor: pointer;
      color: #9CA3AF; padding: 0; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    `;
    closeBtn.onclick = () => this._dismiss(toast);

    // Progress bar
    const progress = document.createElement('div');
    progress.style.cssText = `
      position: absolute; bottom: 0; left: 0;
      height: 2px; width: 100%;
      background: ${c.border};
      transform-origin: left;
      animation: toast-progress ${duration}ms linear forwards;
    `;

    // Add progress keyframe dynamically
    if (!document.getElementById('toast-style')) {
      const style = document.createElement('style');
      style.id = 'toast-style';
      style.textContent = `
        @keyframes toast-in {
          from { opacity: 0; transform: translateY(20px) scale(0.95); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes toast-out {
          from { opacity: 1; transform: translateY(0) scale(1); }
          to   { opacity: 0; transform: translateY(20px) scale(0.95); }
        }
        @keyframes toast-progress {
          from { transform: scaleX(1); }
          to   { transform: scaleX(0); }
        }
      `;
      document.head.appendChild(style);
    }

    toast.append(iconEl, msgEl, closeBtn, progress);
    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => this._dismiss(toast), duration);
    }

    return toast;
  }

  _dismiss(toast) {
    toast.style.animation = 'toast-out 0.25s ease forwards';
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }

  success(message, duration) { return this.show(message, 'success', duration); }
  error(message, duration)   { return this.show(message, 'error',   duration); }
  warning(message, duration) { return this.show(message, 'warning', duration); }
  info(message, duration)    { return this.show(message, 'info',    duration); }
}

export const toast = new ToastManager();
