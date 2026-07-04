/**
 * utils.js — Shared helper functions
 * @module utils
 */

// ── Markdown Renderer ──────────────────────────────────────────
/**
 * Converts a markdown string to sanitized HTML.
 * Handles: headers, bold, italic, code, links, lists, blockquotes, hr.
 * @param {string} text
 * @returns {string} HTML string
 */
export function renderMarkdown(text) {
  if (!text) return '';

  let html = sanitizeHTML(text);

  // Code blocks (must come before inline code)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code class="lang-${lang || 'text'}">${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm,  '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,   '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,    '<h1>$1</h1>');

  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g,         '<em>$1</em>');
  html = html.replace(/__(.+?)__/g,         '<strong>$1</strong>');
  html = html.replace(/_(.+?)_/g,           '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Horizontal rule
  html = html.replace(/^---+$/gm, '<hr>');

  // Unordered lists
  html = html.replace(/((?:^[-*+] .+\n?)+)/gm, (match) => {
    const items = match.trim().split('\n').map(line =>
      `<li>${line.replace(/^[-*+] /, '')}</li>`
    ).join('');
    return `<ul>${items}</ul>`;
  });

  // Ordered lists
  html = html.replace(/((?:^\d+\. .+\n?)+)/gm, (match) => {
    const items = match.trim().split('\n').map(line =>
      `<li>${line.replace(/^\d+\. /, '')}</li>`
    ).join('');
    return `<ol>${items}</ol>`;
  });

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Line breaks → paragraphs
  html = html.split('\n\n').map(block => {
    block = block.trim();
    if (!block) return '';
    if (/^<(h[1-6]|ul|ol|pre|blockquote|hr)/.test(block)) return block;
    return `<p>${block.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');

  return html;
}

// ── Sanitize HTML ──────────────────────────────────────────────
/**
 * Escapes HTML special characters to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
export function sanitizeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── Debounce ──────────────────────────────────────────────────
/**
 * Returns a debounced version of fn that delays execution.
 * @param {Function} fn
 * @param {number} delay - milliseconds
 * @returns {Function}
 */
export function debounce(fn, delay = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// ── Throttle ──────────────────────────────────────────────────
/**
 * Returns a throttled function that runs at most once per interval.
 * @param {Function} fn
 * @param {number} limit
 * @returns {Function}
 */
export function throttle(fn, limit = 100) {
  let lastCall = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      fn.apply(this, args);
    }
  };
}

// ── Date Formatting ───────────────────────────────────────────
/**
 * Format a date string to human-readable relative time.
 * @param {string|Date} date
 * @returns {string}
 */
export function formatRelativeTime(date) {
  const now = new Date();
  const then = new Date(date);
  const diffMs = now - then;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60)   return 'just now';
  if (diffMins < 60)   return `${diffMins}m ago`;
  if (diffHours < 24)  return `${diffHours}h ago`;
  if (diffDays < 7)    return `${diffDays}d ago`;
  return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Format a date to readable string.
 * @param {string|Date} date
 * @returns {string}
 */
export function formatDate(date) {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

// ── String Utilities ──────────────────────────────────────────
/**
 * Truncate a string to maxLen characters.
 * @param {string} str
 * @param {number} maxLen
 * @returns {string}
 */
export function truncate(str, maxLen = 120) {
  if (!str || str.length <= maxLen) return str;
  return str.slice(0, maxLen).trimEnd() + '…';
}

/**
 * Capitalize first letter of each word.
 * @param {string} str
 * @returns {string}
 */
export function titleCase(str) {
  return str.replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Extract initials from a name (up to 2 letters).
 * @param {string} name
 * @returns {string}
 */
export function getInitials(name) {
  return name.split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// ── Clipboard ─────────────────────────────────────────────────
/**
 * Copy text to clipboard.
 * @param {string} text
 * @returns {Promise<void>}
 */
export async function copyToClipboard(text) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
  } else {
    const el = document.createElement('textarea');
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
  }
}

// ── DOM Utilities ──────────────────────────────────────────────
/**
 * Select single element (shorthand).
 * @param {string} selector
 * @param {Element} [root]
 * @returns {Element|null}
 */
export const $ = (selector, root = document) => root.querySelector(selector);

/**
 * Select all elements (shorthand).
 * @param {string} selector
 * @param {Element} [root]
 * @returns {NodeList}
 */
export const $$ = (selector, root = document) => root.querySelectorAll(selector);

/**
 * Create an element with optional properties.
 * @param {string} tag
 * @param {object} props
 * @param {string} [innerHTML]
 * @returns {Element}
 */
export function createElement(tag, props = {}, innerHTML = '') {
  const el = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (k === 'class') el.className = v;
    else if (k === 'data') Object.entries(v).forEach(([dk, dv]) => el.dataset[dk] = dv);
    else el.setAttribute(k, v);
  });
  if (innerHTML) el.innerHTML = innerHTML;
  return el;
}

/**
 * Animate a number from start to end over duration ms.
 * @param {Element} el
 * @param {number} start
 * @param {number} end
 * @param {number} duration
 */
export function animateNumber(el, start, end, duration = 1200) {
  const startTime = performance.now();
  const range = end - start;

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.textContent = Math.round(start + range * eased).toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
}

/**
 * Generate a consistent color from a string (for avatar/node colors).
 * @param {string} str
 * @returns {string} HSL color string
 */
export function stringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}

/**
 * Generate a random ID.
 * @returns {string}
 */
export function uid() {
  return Math.random().toString(36).slice(2, 10);
}
