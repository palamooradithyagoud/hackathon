/**
 * auth.js — Role-based authentication guard for FRIP.
 * Import this in any protected page to:
 *  - Redirect unauthenticated users back to index.html
 *  - Inject the role badge + logout button into the sidebar
 */

export const ROLE_KEY    = 'frip_role';
export const ROLE_SET_AT = 'frip_role_set_at';

/**
 * Returns the currently saved role ('student' | 'faculty') or null.
 */
export function getRole() {
  return localStorage.getItem(ROLE_KEY);
}

/**
 * Guard: redirects to index.html if no role is set.
 * Call at the top of your page script.
 */
export function requireRole() {
  const role = getRole();
  if (!role) {
    window.location.replace('index.html');
    return null;
  }
  return role;
}

/**
 * Clears the saved role and redirects to the login page.
 */
export function logout() {
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(ROLE_SET_AT);
  window.location.href = 'index.html';
}

/**
 * Injects a role badge + logout button into an element.
 * @param {string} containerId - The ID of the container element.
 * @param {string} [role]      - Override role; defaults to saved role.
 */
export function injectRoleBadge(containerId = 'sidebar-role-badge', role = getRole()) {
  const container = document.getElementById(containerId);
  if (!container || !role) return;

  const isStudent = role === 'student';
  container.innerHTML = `
    <span style="
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
      background: ${isStudent ? 'rgba(79,70,229,0.15)' : 'rgba(16,185,129,0.15)'};
      border: 1px solid ${isStudent ? 'rgba(79,70,229,0.4)' : 'rgba(16,185,129,0.4)'};
      color: ${isStudent ? '#818cf8' : '#34d399'};
      user-select: none;
    ">
      ${isStudent ? '🎓' : '👨‍🏫'} ${isStudent ? 'Student' : 'Faculty'}
    </span>
    <button
      id="logout-btn"
      title="Sign out"
      style="background: none; border: none; cursor: pointer; padding: 4px; color: var(--text-muted); border-radius: 6px; display: flex; transition: color 0.2s;"
      onmouseover="this.style.color='#ef4444'"
      onmouseout="this.style.color=''"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
        <polyline points="16 17 21 12 16 7"/>
        <line x1="21" y1="12" x2="9" y2="12"/>
      </svg>
    </button>
  `;
  document.getElementById('logout-btn')?.addEventListener('click', logout);
}

/**
 * Full setup: guard + inject badge.
 * One-liner for any page that needs authentication.
 */
export function setupAuth(badgeContainerId = 'sidebar-role-badge') {
  const role = requireRole();
  if (role) {
    document.documentElement.setAttribute('data-user-role', role);
    injectRoleBadge(badgeContainerId, role);
    
    if (role === 'student') {
      // Fallback programmatic hide for cached CSS scenarios
      const hideElements = () => {
        document.querySelectorAll('a[href*="faculty_chat.html"]').forEach(link => {
          link.style.setProperty('display', 'none', 'important');
        });
        const modalChatBtn = document.getElementById('modal-chat-btn');
        if (modalChatBtn) {
          modalChatBtn.style.setProperty('display', 'none', 'important');
        }
      };
      
      hideElements();
      document.addEventListener('DOMContentLoaded', hideElements);
      setTimeout(hideElements, 100);
      setTimeout(hideElements, 500);

      // Guard direct page access for student
      if (window.location.pathname.includes('faculty_chat.html')) {
        window.location.replace('dashboard.html');
      }
    }
  }
  return role;
}
