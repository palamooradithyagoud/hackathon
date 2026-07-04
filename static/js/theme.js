/**
 * theme.js — Dark / Light Mode Manager
 * @module theme
 */

class ThemeManager {
  constructor() {
    this.key = 'frip-theme';
    this.current = localStorage.getItem(this.key) || 'dark';
  }

  init() {
    this.apply(this.current);
    document.querySelectorAll('[data-action="theme-toggle"]').forEach(btn => {
      btn.addEventListener('click', () => this.toggle());
      this._updateIcon(btn);
    });
  }

  toggle() {
    this.current = this.current === 'dark' ? 'light' : 'dark';
    localStorage.setItem(this.key, this.current);
    this.apply(this.current);
    document.querySelectorAll('[data-action="theme-toggle"]').forEach(btn =>
      this._updateIcon(btn)
    );
  }

  apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  _updateIcon(btn) {
    const sunIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
    const moonIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>`;
    btn.innerHTML = this.current === 'dark' ? sunIcon : moonIcon;
    btn.setAttribute('aria-label', this.current === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    btn.setAttribute('title', btn.getAttribute('aria-label'));
  }
}

export const theme = new ThemeManager();
