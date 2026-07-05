/**
 * dashboard.js — Dashboard controller
 * Loads stats, logs, trending domains, and draws charts using HTML5 Canvas.
 */

import { getStats, getLogs, uploadPdf, postAnnouncement, getAnnouncements, updateAnnouncement, deleteAnnouncement, uploadAttachment } from './api.js';
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

async function initDashboard() {
  const role = localStorage.getItem('frip_role');
  let announcementsPromise;

  if (role === 'faculty') {
    const postBtn = document.getElementById('post-announcement-btn');
    if (postBtn) postBtn.style.display = 'block';
    announcementsPromise = getAnnouncements();
  } else {
    const settingsPanel = document.getElementById('student-settings-panel');
    if (settingsPanel) settingsPanel.style.display = 'block';

    const dept = localStorage.getItem('frip_student_dept') || '';
    const year = localStorage.getItem('frip_student_year') || '';
    const sec = localStorage.getItem('frip_student_sec') || '';

    const deptInput = document.getElementById('student-dept');
    const yearInput = document.getElementById('student-year');
    const secInput = document.getElementById('student-sec');
    if (deptInput) deptInput.value = dept;
    if (yearInput) yearInput.value = year;
    if (secInput) secInput.value = sec;

    announcementsPromise = getAnnouncements({ role: 'student', department: dept, year, section: sec });
  }

  try {
    // 1. Fetch Stats, Logs & Announcements in parallel
    const [stats, logs, announcements] = await Promise.all([
      getStats(),
      getLogs(),
      announcementsPromise
    ]);

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

    // 6. Render Announcements
    renderAnnouncements(announcements);

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

// --- Unread Announcements Tracking ---
function getReadAnnouncements() {
  try {
    const list = localStorage.getItem('frip_read_announcements');
    return list ? JSON.parse(list) : [];
  } catch (e) {
    return [];
  }
}

function markAnnouncementAsRead(id) {
  const readList = getReadAnnouncements();
  if (!readList.includes(id)) {
    readList.push(id);
    localStorage.setItem('frip_read_announcements', JSON.stringify(readList));
  }
}

// --- Render Main Feed Announcements ---
function renderAnnouncements(announcements) {
  const announcementsList = document.getElementById('announcements-list');
  if (!announcementsList) return;
  announcementsList.innerHTML = '';

  const role = localStorage.getItem('frip_role');
  const readList = getReadAnnouncements();
  
  // Calculate unread count
  let unreadCount = 0;
  announcements.forEach(ann => {
    if (ann.status === 'published' && !readList.includes(ann.id)) {
      unreadCount++;
    }
  });

  const unreadCountBadge = document.getElementById('unread-count');
  if (unreadCountBadge) {
    if (unreadCount > 0) {
      unreadCountBadge.textContent = unreadCount;
      unreadCountBadge.style.display = 'inline-flex';
    } else {
      unreadCountBadge.style.display = 'none';
    }
  }

  if (announcements.length === 0) {
    announcementsList.innerHTML = '<div class="text-muted" style="font-size: var(--text-sm); padding: var(--space-2) 0; text-align: left;">No announcements posted yet.</div>';
    return;
  }

  announcements.forEach((ann) => {
    const isUnread = ann.status === 'published' && !readList.includes(ann.id);
    const annItem = document.createElement('div');
    annItem.className = `ann-card-item ${isUnread ? 'unread' : ''}`;
    annItem.style.cssText = 'margin-bottom: var(--space-3); text-align: left;';

    const formattedTime = formatRelativeTime(ann.timestamp);
    const pClass = (ann.priority || 'Low').toLowerCase();
    
    const attachHtml = ann.attachment 
      ? `<span style="font-size: 10px; color: var(--color-primary); font-weight: 500; display: inline-flex; align-items: center; gap: 2px;">
           <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg> Attachment
         </span>`
      : '';

    annItem.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; gap: var(--space-2);">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="p-badge ${pClass}">${ann.priority || 'Low'}</span>
          ${ann.category ? `<span class="cat-badge">${ann.category}</span>` : ''}
          ${isUnread ? '<span class="unread-dot"></span>' : ''}
        </div>
        <span style="font-size: 10px; color: var(--text-faint); font-weight: normal; flex-shrink: 0;">${formattedTime}</span>
      </div>
      <h4 style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 0 0 6px 0;">${ann.title}</h4>
      <p style="font-size: var(--text-xs); color: var(--text-secondary); line-height: 1.5; margin: 0 0 8px 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; white-space: pre-wrap;">${ann.content}</p>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 10px; color: var(--text-muted); font-weight: 500;">👨‍🏫 By ${ann.faculty_name}</span>
        ${attachHtml}
      </div>
    `;

    // Click handler to open detail modal and mark as read
    annItem.addEventListener('click', () => {
      if (isUnread) {
        markAnnouncementAsRead(ann.id);
        annItem.classList.remove('unread');
        const dot = annItem.querySelector('.unread-dot');
        if (dot) dot.remove();
        
        const currentCount = parseInt(unreadCountBadge.textContent || '0', 10);
        if (currentCount > 1) {
          unreadCountBadge.textContent = currentCount - 1;
        } else {
          unreadCountBadge.style.display = 'none';
        }
      }

      // Populate & open modal
      const detailTitle = document.getElementById('detail-title');
      const detailPriority = document.getElementById('detail-priority-badge');
      const detailCategory = document.getElementById('detail-category-badge');
      const detailFaculty = document.getElementById('detail-faculty');
      const detailTime = document.getElementById('detail-time');
      const detailContent = document.getElementById('detail-content');
      const detailAttachWrapper = document.getElementById('detail-attachment-wrapper');
      const detailAttachLink = document.getElementById('detail-attachment-link');

      if (detailTitle) detailTitle.textContent = ann.title;
      if (detailPriority) {
        detailPriority.className = `p-badge ${pClass}`;
        detailPriority.textContent = ann.priority || 'Low';
      }
      if (detailCategory) {
        if (ann.category) {
          detailCategory.textContent = ann.category;
          detailCategory.style.display = 'inline-flex';
        } else {
          detailCategory.style.display = 'none';
        }
      }
      if (detailFaculty) detailFaculty.textContent = `👨‍🏫 By ${ann.faculty_name}`;
      if (detailTime) detailTime.textContent = formattedTime;
      if (detailContent) detailContent.textContent = ann.content;
      
      if (detailAttachWrapper && detailAttachLink) {
        if (ann.attachment) {
          detailAttachLink.href = ann.attachment;
          const baseName = ann.attachment.split('/').pop() || 'Download';
          document.getElementById('detail-attachment-text').textContent = baseName;
          detailAttachWrapper.style.display = 'flex';
        } else {
          detailAttachWrapper.style.display = 'none';
        }
      }

      window.openModal('announcement-detail-modal');
    });

    announcementsList.appendChild(annItem);
  });
}

// --- Render Faculty Side Panel Announcements List ---
function renderSidePanelAnnouncements(announcements) {
  const panelList = document.getElementById('side-panel-announcements-list');
  const countLabel = document.getElementById('announcements-count-label');
  if (!panelList) return;
  panelList.innerHTML = '';

  if (countLabel) {
    countLabel.textContent = `${announcements.length} announcement${announcements.length === 1 ? '' : 's'}`;
  }

  if (announcements.length === 0) {
    panelList.innerHTML = '<div class="text-muted" style="font-size: var(--text-xs); padding: var(--space-2) 0;">No announcements created yet.</div>';
    return;
  }

  announcements.forEach((ann) => {
    const item = document.createElement('div');
    item.className = 'panel';
    item.style.cssText = 'padding: var(--space-3); border: 1px solid var(--border-color); background: var(--bg-surface-2); border-radius: var(--radius-md); text-align: left; margin-bottom: 4px;';

    const pClass = (ann.priority || 'Low').toLowerCase();
    const formattedTime = formatRelativeTime(ann.timestamp);
    const isDraft = ann.status === 'draft';

    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2);">
        <div style="display: flex; gap: var(--space-2); align-items: center;">
          <span class="p-badge ${pClass}">${ann.priority || 'Low'}</span>
          ${isDraft ? '<span class="draft-badge">Draft</span>' : '<span class="p-badge low" style="color:var(--color-success);background:rgba(16,185,129,0.15)">Published</span>'}
        </div>
        <span style="font-size: 10px; color: var(--text-faint);">${formattedTime}</span>
      </div>
      <h4 style="font-size: var(--text-sm); font-weight: 600; color: var(--text-primary); margin: 0 0 var(--space-1) 0;">${ann.title}</h4>
      <p style="font-size: 11px; color: var(--text-muted); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin: 0 0 var(--space-3) 0;">${ann.content}</p>
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: var(--space-2);">
        <span style="font-size: 10px; color: var(--text-faint);">By ${ann.faculty_name}</span>
        <div style="display: flex; gap: var(--space-2);">
          <button type="button" class="btn btn-ghost btn-sm edit-ann-btn" style="padding: 2px 6px; font-size: 10px;">Edit</button>
          <button type="button" class="btn btn-ghost btn-sm delete-ann-btn" style="padding: 2px 6px; font-size: 10px; color: var(--color-error);">Delete</button>
        </div>
      </div>
    `;

    // Edit handler
    item.querySelector('.edit-ann-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      openEditForm(ann);
    });

    // Delete handler
    item.querySelector('.delete-ann-btn').addEventListener('click', async (e) => {
      e.stopPropagation();
      if (confirm(`Are you sure you want to delete "${ann.title}"?`)) {
        try {
          await deleteAnnouncement(ann.id);
          toast.success('Announcement deleted!');
          const allAnn = await getAnnouncements();
          renderSidePanelAnnouncements(allAnn);
          renderAnnouncements(allAnn);
        } catch (err) {
          toast.error(err.message || 'Delete failed');
        }
      }
    });

    panelList.appendChild(item);
  });
}

// --- Side Panel Operations ---
const sidePanel = document.getElementById('announcement-side-panel');
const manageBtn = document.getElementById('post-announcement-btn');
const closePanelBtn = document.getElementById('close-side-panel-btn');
const createNewBtn = document.getElementById('create-new-ann-btn');
const backToListBtn = document.getElementById('back-to-list-btn');

const listView = document.getElementById('side-panel-list-view');
const formView = document.getElementById('side-panel-form-view');

const formIdInput = document.getElementById('form-ann-id');
const formFacultyInput = document.getElementById('form-ann-faculty');
const formTitleInput = document.getElementById('form-ann-title');
const formContentInput = document.getElementById('form-ann-content');
const formCategoryInput = document.getElementById('form-ann-category');
const formPriorityInput = document.getElementById('form-ann-priority');
const formAttachmentUrl = document.getElementById('form-ann-attachment-url');
const formAudienceInput = document.getElementById('form-ann-audience');
const formExpiryInput = document.getElementById('form-ann-expiry');
const formFileInput = document.getElementById('form-ann-file');
const uploadFileBtn = document.getElementById('upload-file-btn');
const uploadFileBtnText = document.getElementById('upload-file-btn-text');

const targetDetails = document.getElementById('target-audience-details');
const targetDeptWrapper = document.getElementById('target-dept-wrapper');
const targetYearWrapper = document.getElementById('target-year-wrapper');
const targetSecWrapper = document.getElementById('target-sec-wrapper');

const formDept = document.getElementById('form-ann-target-dept');
const formYear = document.getElementById('form-ann-target-year');
const formSec = document.getElementById('form-ann-target-sec');

const draftBtn = document.getElementById('ann-draft-btn');
const publishBtn = document.getElementById('ann-publish-btn');
const manageForm = document.getElementById('ann-manage-form');

let formStatus = 'published';

function openSidePanel() {
  if (sidePanel) sidePanel.classList.add('active');
  resetForm();
  showListView();
  getAnnouncements().then(renderSidePanelAnnouncements).catch(console.error);
}

function closeSidePanel() {
  if (sidePanel) sidePanel.classList.remove('active');
}

function showListView() {
  if (listView) listView.style.display = 'block';
  if (formView) formView.style.display = 'none';
}

function showFormView(title = 'New Announcement') {
  if (listView) listView.style.display = 'none';
  if (formView) formView.style.display = 'block';
  const titleEl = document.getElementById('form-view-title');
  if (titleEl) titleEl.textContent = title;
}

function resetForm() {
  if (manageForm) manageForm.reset();
  if (formIdInput) formIdInput.value = '';
  if (uploadFileBtnText) uploadFileBtnText.textContent = 'Upload File';
  if (targetDetails) targetDetails.style.display = 'none';
  if (formFacultyInput) formFacultyInput.value = 'Dr. Padmaja';
}

function updateAudienceFields() {
  const audience = formAudienceInput.value;
  if (audience === 'All') {
    targetDetails.style.display = 'none';
  } else {
    targetDetails.style.display = 'flex';
    targetDeptWrapper.style.display = 'flex';
    
    if (audience === 'Department') {
      targetYearWrapper.style.display = 'none';
      targetSecWrapper.style.display = 'none';
    } else if (audience === 'Year') {
      targetYearWrapper.style.display = 'flex';
      targetSecWrapper.style.display = 'none';
    } else if (audience === 'Section') {
      targetYearWrapper.style.display = 'flex';
      targetSecWrapper.style.display = 'flex';
    }
  }
}

function openEditForm(ann) {
  resetForm();
  showFormView('Edit Announcement');
  
  if (formIdInput) formIdInput.value = ann.id;
  if (formFacultyInput) formFacultyInput.value = ann.faculty_name;
  if (formTitleInput) formTitleInput.value = ann.title;
  if (formContentInput) formContentInput.value = ann.content;
  if (formCategoryInput) formCategoryInput.value = ann.category || '';
  if (formPriorityInput) formPriorityInput.value = ann.priority || 'Low';
  if (formAttachmentUrl) formAttachmentUrl.value = ann.attachment || '';
  if (formAudienceInput) formAudienceInput.value = ann.target_audience || 'All';
  if (formExpiryInput) formExpiryInput.value = ann.expiry_date || '';
  
  updateAudienceFields();
  
  if (ann.target_audience !== 'All') {
    if (formDept) formDept.value = ann.target_dept || 'CSE';
    if (formYear) formYear.value = ann.target_year || '1';
    if (formSec) formSec.value = ann.target_sec || 'A';
  }
}

// Attach Side Panel events
if (manageBtn) manageBtn.addEventListener('click', openSidePanel);
if (closePanelBtn) closePanelBtn.addEventListener('click', closeSidePanel);
if (createNewBtn) createNewBtn.addEventListener('click', () => {
  resetForm();
  showFormView('New Announcement');
});
if (backToListBtn) backToListBtn.addEventListener('click', showListView);

if (formAudienceInput) {
  formAudienceInput.addEventListener('change', updateAudienceFields);
}

if (sidePanel) {
  sidePanel.addEventListener('click', (e) => {
    if (e.target === sidePanel) closeSidePanel();
  });
}

// File Upload Trigger
if (uploadFileBtn && formFileInput) {
  uploadFileBtn.addEventListener('click', (e) => {
    e.preventDefault();
    formFileInput.click();
  });
  formFileInput.addEventListener('change', async () => {
    const file = formFileInput.files[0];
    if (!file) return;

    uploadFileBtnText.textContent = 'Uploading...';
    try {
      const res = await uploadAttachment(file);
      if (formAttachmentUrl) formAttachmentUrl.value = res.url;
      uploadFileBtnText.textContent = file.name;
      toast.success('File uploaded successfully!');
    } catch (err) {
      uploadFileBtnText.textContent = 'Upload Failed';
      toast.error(err.message || 'File upload failed');
    }
  });
}

// Handle Form Buttons click (to capture status)
if (draftBtn) {
  draftBtn.addEventListener('click', (e) => {
    e.preventDefault();
    formStatus = 'draft';
    if (manageForm) {
      // Dispatch submit event manually
      const submitEvent = new Event('submit', { cancelable: true, bubbles: true });
      manageForm.dispatchEvent(submitEvent);
    }
  });
}
if (publishBtn) {
  publishBtn.addEventListener('click', () => {
    formStatus = 'published';
  });
}

// Form Submission (Create or Edit)
if (manageForm) {
  manageForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const title = formTitleInput.value.trim();
    const content = formContentInput.value.trim();
    const facultyName = formFacultyInput.value.trim();
    
    if (!title || !content || !facultyName) {
      toast.error('Title, Description and Faculty Name are required.');
      return;
    }

    const idVal = formIdInput.value;
    const isEdit = idVal !== '';

    const payload = {
      title,
      content,
      faculty_name: facultyName,
      category: formCategoryInput.value.trim() || null,
      priority: formPriorityInput.value,
      attachment: formAttachmentUrl.value.trim() || null,
      target_audience: formAudienceInput.value,
      target_dept: formAudienceInput.value !== 'All' ? formDept.value : null,
      target_year: ['Year', 'Section'].includes(formAudienceInput.value) ? formYear.value : null,
      target_sec: formAudienceInput.value === 'Section' ? formSec.value : null,
      expiry_date: formExpiryInput.value || null,
      status: formStatus
    };

    const submitBtn = formStatus === 'draft' ? draftBtn : publishBtn;
    const oldText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
      if (isEdit) {
        await updateAnnouncement(parseInt(idVal, 10), payload);
        toast.success('Announcement updated!');
      } else {
        await postAnnouncement(payload);
        toast.success(formStatus === 'draft' ? 'Announcement saved as draft!' : 'Announcement published!');
      }
      
      resetForm();
      showListView();
      
      const allAnn = await getAnnouncements();
      renderSidePanelAnnouncements(allAnn);
      
      const role = localStorage.getItem('frip_role');
      if (role === 'faculty') {
        renderAnnouncements(allAnn);
      } else {
        const dept = localStorage.getItem('frip_student_dept') || '';
        const year = localStorage.getItem('frip_student_year') || '';
        const sec = localStorage.getItem('frip_student_sec') || '';
        const filteredAnn = await getAnnouncements({ role: 'student', department: dept, year, section: sec });
        renderAnnouncements(filteredAnn);
      }
    } catch (err) {
      toast.error(err.message || 'Operation failed');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = oldText;
    }
  });
}

// --- Student Settings Form Handler ---
const settingsForm = document.getElementById('student-settings-form');
if (settingsForm) {
  settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const dept = document.getElementById('student-dept').value;
    const year = document.getElementById('student-year').value;
    const sec = document.getElementById('student-sec').value;

    localStorage.setItem('frip_student_dept', dept);
    localStorage.setItem('frip_student_year', year);
    localStorage.setItem('frip_student_sec', sec);

    toast.success('Student profile settings updated!');

    try {
      const filteredAnn = await getAnnouncements({ role: 'student', department: dept, year, section: sec });
      renderAnnouncements(filteredAnn);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load targeted announcements');
    }
  });
}

// Window Modal helper mapping for backward compatibility
window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
};
window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
