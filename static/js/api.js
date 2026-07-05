/**
 * api.js — Centralized API Client
 * All backend calls live here. No page should call fetch() directly.
 * @module api
 */

const BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '8000'
  ? 'http://localhost:8000/api'
  : '/api';

/**
 * Core fetch wrapper with loading states and error handling.
 * @param {string} endpoint - API path (e.g. '/chat')
 * @param {Object} options - fetch options
 * @returns {Promise<any>}
 */
async function apiFetch(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = { ...options.headers };
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  const config = {
    ...options,
    headers,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let errMsg = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      errMsg = errBody.detail || errBody.message || errMsg;
    } catch (_) {}
    throw new Error(errMsg);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

// ── Exported API Methods ──────────────────────────────────────

/**
 * Send a chat query to the RAG pipeline.
 * @param {string} query
 * @returns {Promise<{intent: string, response_text: string, data: object}>}
 */
export async function chat(query, role = 'student') {
  return apiFetch('/chat', {
    method: 'POST',
    body: JSON.stringify({ query, role }),
  });
}

/**
 * Get faculty collaboration analysis.
 * @param {string} facultyA
 * @param {string} facultyB
 */
export async function collaborate(facultyA, facultyB) {
  return apiFetch('/collaborate', {
    method: 'POST',
    body: JSON.stringify({ faculty_a: facultyA, faculty_b: facultyB }),
  });
}

/**
 * Professor Intelligence Mode: full analysis report.
 * @param {string} topic
 */
export async function professorAnalyze(topic) {
  return apiFetch('/professor/analyze', {
    method: 'POST',
    body: JSON.stringify({ topic }),
  });
}

/**
 * Confirm a project suggestion and generate email draft.
 * @param {string} topic
 * @param {object} report
 * @param {number} projectIdx
 */
export async function professorConfirm(topic, report, projectIdx) {
  return apiFetch('/professor/confirm', {
    method: 'POST',
    body: JSON.stringify({ topic, report, project_idx: projectIdx }),
  });
}

/**
 * Recommend faculty for a research area.
 * @param {string} query
 */
export async function recommend(query) {
  return apiFetch('/recommend', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

/**
 * Upload a faculty PDF to the knowledge base.
 * @param {File} file
 */
export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch('/upload_pdf', {
    method: 'POST',
    headers: {},  // Let browser set multipart boundary
    body: formData,
  });
}

/**
 * Submit feedback rating for a query.
 * @param {number} queryLogId
 * @param {number} rating - 1-5
 * @param {string} [comments]
 */
export async function submitFeedback(queryLogId, rating, comments = '') {
  return apiFetch('/feedback', {
    method: 'POST',
    body: JSON.stringify({ query_log_id: queryLogId, rating, comments }),
  });
}

/**
 * Get recent query audit logs.
 * @returns {Promise<Array>}
 */
export async function getLogs() {
  return apiFetch('/logs');
}

/**
 * Get system stats for the dashboard.
 * @returns {Promise<object>}
 */
export async function getStats() {
  return apiFetch('/stats');
}

/**
 * Search Semantic Scholar database for papers.
 * @param {string} query
 * @returns {Promise<Array>}
 */
export async function searchSemanticScholar(query) {
  return apiFetch(`/semantic/search?query=${encodeURIComponent(query)}`);
}

/**
 * Fetch dynamic citation graph for a paper ID.
 * @param {string} paperId
 * @returns {Promise<object>}
 */
export async function fetchCitationGraph(paperId) {
  return apiFetch(`/semantic/graph/${paperId}`);
}

/**
 * Post a new announcement.
 */
export async function postAnnouncement(titleOrData, content, facultyName, category, priority, attachment, targetAudience, targetDept, targetYear, targetSec, expiryDate, status) {
  let bodyObj;
  if (typeof titleOrData === 'object' && titleOrData !== null) {
    bodyObj = titleOrData;
  } else {
    bodyObj = {
      title: titleOrData,
      content,
      faculty_name: facultyName,
      category,
      priority: priority || 'Low',
      attachment,
      target_audience: targetAudience || 'All',
      target_dept: targetDept,
      target_year: targetYear,
      target_sec: targetSec,
      expiry_date: expiryDate,
      status: status || 'published'
    };
  }
  return apiFetch('/announcements', {
    method: 'POST',
    body: JSON.stringify(bodyObj),
  });
}

/**
 * Get all announcements with filtering.
 */
export async function getAnnouncements(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.role) searchParams.append('role', params.role);
  if (params.department) searchParams.append('department', params.department);
  if (params.year) searchParams.append('year', params.year);
  if (params.section) searchParams.append('section', params.section);
  
  const query = searchParams.toString();
  return apiFetch(`/announcements${query ? '?' + query : ''}`);
}

/**
 * Update an existing announcement.
 */
export async function updateAnnouncement(id, data) {
  return apiFetch(`/announcements/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Delete an announcement.
 */
export async function deleteAnnouncement(id) {
  return apiFetch(`/announcements/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Upload an attachment file.
 */
export async function uploadAttachment(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch('/announcements/upload_attachment', {
    method: 'POST',
    body: formData,
  });
}

