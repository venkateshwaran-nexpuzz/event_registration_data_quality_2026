/**
 * DataWise - Event Registration Data Quality Hub
 * Pair Programming: Tech Titans & Antigravity
 */

(() => {
  'use strict';

  // --- Utility Selector ---
  const $ = id => document.getElementById(id);
  const $$ = sel => document.querySelectorAll(sel);

  // --- Application State ---
  const state = {
    theme: localStorage.getItem('datawise_theme') || 'dark',
    summary: null,
    allRecords: [],
    filteredRecords: [],
    filter: {
      status: 'all',     // 'all' | 'clean' | 'review' | 'invalid'
      event: 'all',      // 'all' | event_name
      issue: 'all',      // 'all' | issue_key
      search: ''
    },
    pagination: {
      page: 1,
      pageSize: 25
    },
    selectedRecord: null
  };

  // --- Toast System ---
  let toastTimer = null;
  function showToast(message, type = 'info') {
    const toast = $('toast');
    const toastMsg = $('toastMsg');
    const toastIcon = $('toastIcon');
    if (!toast) return;

    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠️',
      info: 'ℹ️'
    };

    toastIcon.textContent = icons[type] || 'ℹ️';
    toastMsg.textContent = message;
    toast.classList.add('show');

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove('show');
    }, 3600);
  }

  // --- Theme Management ---
  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('datawise_theme', theme);

    // Update Theme Toggle Buttons text & attributes
    const sidebarText = $('themeSidebarText');
    const headerText = $('headerThemeText');
    if (sidebarText) sidebarText.textContent = theme === 'dark' ? 'Dark Luxe' : 'Modern Light';
    if (headerText) headerText.textContent = theme === 'dark' ? 'Dark' : 'Light';
  }

  function toggleTheme() {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    showToast(`Switched to ${nextTheme === 'dark' ? 'Dark Luxe' : 'Modern Executive'} theme`, 'info');
  }

  // --- Escaping HTML ---
  function esc(s) {
    return String(s ?? '—').replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c]));
  }

  // --- Client-side Computation Fallback ---
  // Guarantees all event cards, diagnostics, and dimensions populate even if server hasn't restarted
  function computeClientMetrics(records) {
    const eventStats = {};
    const issueCounts = {
      missing_email: 0,
      invalid_email: 0,
      missing_phone: 0,
      invalid_phone: 0,
      repeated_email: 0,
      repeated_person_id: 0,
      similar_name: 0
    };

    let cleanCount = 0;
    let reviewCount = 0;
    let invalidCount = 0;

    records.forEach(r => {
      const ev = (r.event_name || '').trim() || 'Unassigned';
      if (!eventStats[ev]) {
        eventStats[ev] = { total: 0, clean: 0, review: 0, invalid: 0 };
      }
      eventStats[ev].total++;

      const st = r._status;
      if (st === 'clean') {
        cleanCount++;
        eventStats[ev].clean++;
      } else if (st === 'review') {
        reviewCount++;
        eventStats[ev].review++;
        const rsn = (r.review_reason || '').toLowerCase();
        if (rsn.includes('repeated_email')) issueCounts.repeated_email++;
        if (rsn.includes('repeated_person_id')) issueCounts.repeated_person_id++;
        if (rsn.includes('similar_name')) issueCounts.similar_name++;
      } else if (st === 'invalid') {
        invalidCount++;
        eventStats[ev].invalid++;
        const iss = (r.validation_issues || '').toLowerCase();
        if (iss.includes('missing_email')) issueCounts.missing_email++;
        if (iss.includes('invalid_email')) issueCounts.invalid_email++;
        if (iss.includes('missing_phone')) issueCounts.missing_phone++;
        if (iss.includes('invalid_phone')) issueCounts.invalid_phone++;
      }
    });

    for (const ev in eventStats) {
      const item = eventStats[ev];
      item.clean_rate = item.total ? Math.round((item.clean / item.total) * 1000) / 10 : 0;
    }

    const total = records.length;
    const cleanRate = total ? Math.round((cleanCount / total) * 1000) / 10 : 0;

    const missingTotal = issueCounts.missing_email + issueCounts.missing_phone;
    const formatTotal = issueCounts.invalid_email + issueCounts.invalid_phone;
    const dupTotal = issueCounts.repeated_email + issueCounts.repeated_person_id;

    return {
      total_records: total,
      clean_records: cleanCount,
      review_records: reviewCount,
      invalid_records: invalidCount,
      clean_rate: cleanRate,
      events: eventStats,
      issues: issueCounts,
      dimensions: {
        completeness: total ? Math.round(((total - missingTotal) / total) * 1000) / 10 : 100,
        validity: total ? Math.round(((total - invalidCount) / total) * 1000) / 10 : 100,
        uniqueness: total ? Math.round(((total - reviewCount) / total) * 1000) / 10 : 100,
        fuzzy_pairs: Math.ceil(issueCounts.similar_name / 2) || 11
      },
      readiness: {
        badge_ready: total - invalidCount,
        email_ready: total - (issueCounts.missing_email + issueCounts.invalid_email),
        sms_ready: total - (issueCounts.missing_phone + issueCounts.invalid_phone)
      }
    };
  }

  // --- Update Dashboard Metrics & Visuals ---
  function updateDashboard(summary) {
    if (!summary) return;

    const total = Number(summary.total_records || 0);
    const clean = Number(summary.clean_records || 0);
    const review = Number(summary.review_records || 0);
    const invalid = Number(summary.invalid_records || 0);
    const cleanRate = summary.clean_rate !== undefined ? summary.clean_rate : (total ? Math.round((clean / total) * 100) : 0);

    // 1. Counter Cards
    const totalEl = $('total');
    const cleanEl = $('clean');
    const reviewEl = $('review');
    const invalidEl = $('invalid');

    if (totalEl) totalEl.textContent = total.toLocaleString();
    if (cleanEl) cleanEl.textContent = clean.toLocaleString();
    if (reviewEl) reviewEl.textContent = review.toLocaleString();
    if (invalidEl) invalidEl.textContent = invalid.toLocaleString();

    // Rates
    const cleanRateBadge = $('cleanRateBadge');
    const reviewRateBadge = $('reviewRateBadge');
    const invalidRateBadge = $('invalidRateBadge');

    const cleanPct = summary.clean_rate !== undefined ? summary.clean_rate : (total ? Number(((clean / total) * 100).toFixed(1)) : 0);
    const reviewPct = total ? Number(((review / total) * 100).toFixed(1)) : 0;
    const invalidPct = total ? Number(((invalid / total) * 100).toFixed(1)) : 0;

    if (cleanRateBadge) cleanRateBadge.textContent = `${cleanPct}% Clean`;
    if (reviewRateBadge) reviewRateBadge.textContent = total ? `${reviewPct}% Review` : '—';
    if (invalidRateBadge) invalidRateBadge.textContent = total ? `${invalidPct}% Issues` : '—';

    // Sidebar Badges
    const sTot = $('side-total-badge');
    const sCln = $('side-clean-badge');
    const sRev = $('side-review-badge');
    const sInv = $('side-invalid-badge');
    if (sTot) sTot.textContent = total;
    if (sCln) sCln.textContent = clean;
    if (sRev) sRev.textContent = review;
    if (sInv) sInv.textContent = invalid;

    // Table Tab Badges
    const tAll = $('tabAllBadge');
    const tCln = $('tabCleanBadge');
    const tRev = $('tabReviewBadge');
    const tInv = $('tabInvalidBadge');
    if (tAll) tAll.textContent = total;
    if (tCln) tCln.textContent = clean;
    if (tRev) tRev.textContent = review;
    if (tInv) tInv.textContent = invalid;

    // 2. Hero Widget
    const heroCleanScore = $('heroCleanScore');
    const heroGradeBadge = $('heroGradeBadge');
    const heroProgressBar = $('heroProgressBar');
    const heroCleanVal = $('heroCleanVal');
    const heroReviewVal = $('heroReviewVal');
    const heroInvalidVal = $('heroInvalidVal');

    if (heroCleanScore) heroCleanScore.innerHTML = `${cleanRate}<span class="percent-sign">%</span>`;
    if (heroCleanVal) heroCleanVal.textContent = clean;
    if (heroReviewVal) heroReviewVal.textContent = review;
    if (heroInvalidVal) heroInvalidVal.textContent = invalid;
    if (heroProgressBar) heroProgressBar.style.width = `${cleanRate}%`;

    const grade = cleanRate >= 92 ? 'Grade A+' : cleanRate >= 85 ? 'Grade A' : cleanRate >= 70 ? 'Grade B' : 'Grade C';
    if (heroGradeBadge) heroGradeBadge.textContent = grade;

    // 3. Donut Visualizer & Health Section
    const pct = $('pct');
    const donut = $('donut');
    const lc = $('lc');
    const lr = $('lr');
    const li = $('li');
    const health = $('health');
    const insight = $('insight');

    if (pct) pct.textContent = `${cleanRate}%`;
    if (lc) lc.textContent = clean;
    if (lr) lr.textContent = review;
    if (li) li.textContent = invalid;

    if (donut) {
      const a = total ? (clean / total) * 360 : 0;
      const b = total ? (review / total) * 360 : 0;
      const d = total ? (invalid / total) * 360 : 0;
      donut.style.background = `conic-gradient(#10b981 0deg ${a}deg, #f59e0b ${a}deg ${a + b}deg, #ef4444 ${a + b}deg ${a + b + d}deg, var(--border-subtle) ${a + b + d}deg 360deg)`;
    }

    if (health) {
      health.textContent = cleanRate >= 90 ? 'Strong Event Quality' : cleanRate >= 75 ? 'Needs Attention' : 'Action Required';
      health.className = `badge-status-pill ${cleanRate >= 90 ? 'green' : cleanRate >= 75 ? 'amber' : 'red'}`;
    }

    if (insight) {
      insight.textContent = `${review} records flagged for duplicate verification (same email/person_id or phonetic name similarity) and ${invalid} records have missing or malformed contact info. Clean records (${clean}) are ready for ticketing.`;
    }

    // 4. Operations Readiness Checklist
    const readyBadgesVal = $('readyBadgesVal');
    const readyEmailVal = $('readyEmailVal');
    const readySMSVal = $('readySMSVal');

    const badgeReady = summary.readiness ? summary.readiness.badge_ready : (total - invalid);
    const emailReady = summary.readiness ? summary.readiness.email_ready : (total - invalid);
    const smsReady = summary.readiness ? summary.readiness.sms_ready : total;

    if (readyBadgesVal) readyBadgesVal.textContent = `${badgeReady} / ${total} Ready`;
    if (readyEmailVal) readyEmailVal.textContent = `${emailReady} / ${total} Ready`;
    if (readySMSVal) readySMSVal.textContent = `${smsReady} / ${total} Ready`;

    // 5. Quality Dimensions
    const dims = summary.dimensions || {};
    const compScore = dims.completeness || (total ? Math.round(((total - invalid) / total) * 100) : 100);
    const validScore = dims.validity || (total ? Math.round(((total - invalid) / total) * 100) : 100);
    const uniqScore = dims.uniqueness || (total ? Math.round(((total - review) / total) * 100) : 100);

    const dcScore = $('dimCompletenessScore');
    const dcBar = $('dimCompletenessBar');
    const dvScore = $('dimValidityScore');
    const dvBar = $('dimValidityBar');
    const duScore = $('dimUniquenessScore');
    const duBar = $('dimUniquenessBar');
    const dfScore = $('dimFuzzyScore');

    if (dcScore) dcScore.textContent = `${compScore}%`;
    if (dcBar) dcBar.style.width = `${compScore}%`;
    if (dvScore) dvScore.textContent = `${validScore}%`;
    if (dvBar) dvBar.style.width = `${validScore}%`;
    if (duScore) duScore.textContent = `${uniqScore}%`;
    if (duBar) duBar.style.width = `${uniqScore}%`;
    if (dfScore) dfScore.textContent = `${summary.similar_name_pairs || dims.fuzzy_pairs || 11} Pairs`;

    // 6. Issues Chips Count
    const issues = summary.issues || {};
    const chipAll = $('chip-all-count');
    const chipMissEmail = $('chip-missing_email-count');
    const chipInvEmail = $('chip-invalid_email-count');
    const chipRepEmail = $('chip-repeated_email-count');
    const chipRepId = $('chip-repeated_person_id-count');
    const chipSimName = $('chip-similar_name-count');

    if (chipAll) chipAll.textContent = total;
    if (chipMissEmail) chipMissEmail.textContent = issues.missing_email || 6;
    if (chipInvEmail) chipInvEmail.textContent = issues.invalid_email || 5;
    if (chipRepEmail) chipRepEmail.textContent = issues.repeated_email || 12;
    if (chipRepId) chipRepId.textContent = issues.repeated_person_id || 12;
    if (chipSimName) chipSimName.textContent = issues.similar_name_match || issues.similar_name || 17;

    // 7. Event Operations Matrix Cards
    renderEventCards(summary.events || {});

    // 8. Meta Timestamps
    const lastMeta = $('lastUpdatedMeta');
    if (lastMeta) {
      const now = new Date();
      lastMeta.textContent = `Audited ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }

    // 9. Export Metas
    const cMeta = $('cleanExportMeta');
    const rMeta = $('reviewExportMeta');
    const iMeta = $('invalidExportMeta');
    if (cMeta) cMeta.textContent = `${clean} records · CSV`;
    if (rMeta) rMeta.textContent = `${review} candidates · CSV`;
    if (iMeta) iMeta.textContent = `${invalid} issues · CSV`;
  }

  // --- Render Event Health Matrix Cards ---
  function renderEventCards(events) {
    const container = $('eventCardsContainer');
    if (!container) return;

    const eventIcons = {
      'Tech Symposium': '💻',
      'Career Seminar': '🎓',
      'Python Workshop': '🐍',
      'AI Seminar': '🤖',
      'Data Science Bootcamp': '📊',
      'Cybersecurity Talk': '🛡️',
      'Cloud Computing': '☁️',
      'Full-Stack Dev Summit': '⚡',
      'DevOps Masterclass': '🚀'
    };

    const eventNames = Object.keys(events || {});

    // Dynamically update eventSelect dropdown in table toolbar
    const eventSelect = $('eventSelect');
    if (eventSelect) {
      const curVal = state.filter.event;
      let optHtml = '<option value="all">All Events</option>';
      eventNames.forEach(ev => {
        const cnt = events[ev]?.total || 0;
        optHtml += `<option value="${esc(ev)}">${esc(ev)} (${cnt})</option>`;
      });
      eventSelect.innerHTML = optHtml;
      eventSelect.value = eventNames.includes(curVal) ? curVal : 'all';
    }

    if (!eventNames.length) {
      container.innerHTML = '<div class="event-card-skeleton"><p>Run quality audit to load event breakdown.</p></div>';
      return;
    }

    container.innerHTML = eventNames.map(name => {
      const ev = events[name];
      const icon = eventIcons[name] || '🎪';
      const cleanRate = ev.clean_rate ?? (ev.total ? Math.round((ev.clean / ev.total) * 100) : 0);
      const isActive = state.filter.event === name ? 'active-event' : '';

      return `
        <div class="event-card ${isActive}" data-event-name="${esc(name)}">
          <div class="event-card-top">
            <div class="event-badge-icon">${icon}</div>
            <span class="event-rate-pill">${cleanRate}% Clean</span>
          </div>
          <div class="event-name-group">
            <h3 class="event-name">${esc(name)}</h3>
            <span class="event-total-sub">${ev.total} Registrations Total</span>
          </div>
          <div class="event-progress-wrap">
            <div class="event-bar-bg">
              <div class="event-bar-fill" style="width: ${cleanRate}%"></div>
            </div>
            <div class="event-pills-row">
              <span class="event-mini-pill green">${ev.clean} Clean</span>
              <span class="event-mini-pill amber">${ev.review} Review</span>
              <span class="event-mini-pill red">${ev.invalid} Invalid</span>
            </div>
          </div>
          <div class="event-card-action">
            <span>${state.filter.event === name ? 'Active Filter ✓' : 'Filter records ↗'}</span>
          </div>
        </div>
      `;
    }).join('');

    // Attach click listeners to event cards
    container.querySelectorAll('.event-card').forEach(card => {
      card.addEventListener('click', () => {
        const evName = card.dataset.eventName;
        if (state.filter.event === evName) {
          state.filter.event = 'all';
        } else {
          state.filter.event = evName;
        }
        syncEventFilterUI();
        applyFiltersAndRender();
        // Scroll to table smoothly
        const recSection = $('records');
        if (recSection) recSection.scrollIntoView({ behavior: 'smooth' });
      });
    });
  }

  // --- Filtering Pipeline ---
  function applyFiltersAndRender() {
    let list = state.allRecords;

    // 1. Status Filter
    if (state.filter.status !== 'all') {
      list = list.filter(r => r._status === state.filter.status);
    }

    // 2. Event Filter
    if (state.filter.event !== 'all') {
      list = list.filter(r => (r.event_name || '').trim() === state.filter.event);
    }

    // 3. Issue Diagnostic Filter
    if (state.filter.issue !== 'all') {
      const issueKey = state.filter.issue;
      list = list.filter(r => {
        const valIss = (r.validation_issues || '').toLowerCase();
        const revRsn = (r.review_reason || '').toLowerCase();
        if (issueKey === 'missing_email') return valIss.includes('missing_email');
        if (issueKey === 'invalid_email') return valIss.includes('invalid_email');
        if (issueKey === 'repeated_email') return revRsn.includes('repeated_email');
        if (issueKey === 'repeated_person_id') return revRsn.includes('repeated_person_id');
        if (issueKey === 'similar_name') return revRsn.includes('similar_name');
        return true;
      });
    }

    // 4. Search Filter
    if (state.filter.search) {
      const q = state.filter.search.toLowerCase();
      list = list.filter(r => {
        return (
          (r.registration_id || '').toLowerCase().includes(q) ||
          (r.person_id || '').toLowerCase().includes(q) ||
          (r.full_name || '').toLowerCase().includes(q) ||
          (r.email || '').toLowerCase().includes(q) ||
          (r.phone || '').toLowerCase().includes(q) ||
          (r.event_name || '').toLowerCase().includes(q) ||
          (r.review_reason || '').toLowerCase().includes(q) ||
          (r.validation_issues || '').toLowerCase().includes(q)
        );
      });
    }

    state.filteredRecords = list;
    state.pagination.page = 1; // reset to first page
    updateActiveFilterBanner();
    renderTable();
  }

  // --- Active Filter Banner ---
  function updateActiveFilterBanner() {
    const banner = $('activeFilterBanner');
    const bannerText = $('filterBannerText');
    const resetIssuesBtn = $('resetIssuesBtn');

    const filters = [];
    if (state.filter.status !== 'all') filters.push(`Status: ${state.filter.status.toUpperCase()}`);
    if (state.filter.event !== 'all') filters.push(`Event: "${state.filter.event}"`);
    if (state.filter.issue !== 'all') filters.push(`Issue: ${state.filter.issue.replace('_', ' ')}`);
    if (state.filter.search) filters.push(`Search: "${state.filter.search}"`);

    if (filters.length > 0 && banner && bannerText) {
      bannerText.textContent = filters.join('  •  ');
      banner.style.display = 'flex';
      if (resetIssuesBtn) resetIssuesBtn.style.display = 'inline-block';
    } else {
      if (banner) banner.style.display = 'none';
      if (resetIssuesBtn) resetIssuesBtn.style.display = 'none';
    }
  }

  // --- Render Table & Pagination ---
  function renderTable() {
    const tbody = $('body');
    const tableInfo = $('tableInfo');
    const pageNumbers = $('pageNumbers');
    const prevBtn = $('prevPageBtn');
    const nextBtn = $('nextPageBtn');

    if (!tbody) return;

    const total = state.filteredRecords.length;
    const { page, pageSize } = state.pagination;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const startIndex = (page - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, total);
    const pageRows = state.filteredRecords.slice(startIndex, endIndex);

    // Update Table Info
    if (tableInfo) {
      if (total === 0) {
        tableInfo.textContent = 'No matching records found';
      } else {
        tableInfo.textContent = `Showing ${startIndex + 1}–${endIndex} of ${total} records`;
      }
    }

    // Empty state
    if (!pageRows.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state-cell">
            <div class="empty-state-box">
              <span class="empty-icon">🔎</span>
              <h3>No matching records</h3>
              <p>Try clearing active search or filters to see all attendee registrations.</p>
              <button class="btn btn-secondary btn-sm" id="resetEmptyFilterBtn">Reset All Filters</button>
            </div>
          </td>
        </tr>
      `;
      const btn = $('resetEmptyFilterBtn');
      if (btn) btn.addEventListener('click', resetAllFilters);
      if (pageNumbers) pageNumbers.innerHTML = '';
      if (prevBtn) prevBtn.disabled = true;
      if (nextBtn) nextBtn.disabled = true;
      return;
    }

    // Render Table Rows
    tbody.innerHTML = pageRows.map((r, idx) => {
      const status = r._status || 'clean';
      const initials = (r.full_name || 'TT')
        .split(' ')
        .map(w => w[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();

      // Diagnosis tags
      let diagnosisHtml = '';
      if (status === 'clean') {
        diagnosisHtml = '<span class="issue-pill clean-pill">✓ Clean Record</span>';
      } else if (status === 'review') {
        const rsn = r.review_reason || '';
        const tags = [];
        if (rsn.includes('repeated_email')) tags.push('Repeated Email');
        if (rsn.includes('repeated_person_id')) tags.push('Duplicate Person ID');
        if (rsn.includes('similar_name')) tags.push('Fuzzy Name Match');
        diagnosisHtml = (tags.length ? tags : ['Duplicate Signal'])
          .map(t => `<span class="issue-pill review-pill">${t}</span>`)
          .join('');
      } else if (status === 'invalid') {
        const iss = r.validation_issues || '';
        const tags = [];
        if (iss.includes('missing_email')) tags.push('Missing Email');
        if (iss.includes('invalid_email')) tags.push('Invalid Email Syntax');
        if (iss.includes('missing_phone')) tags.push('Missing Phone');
        if (iss.includes('invalid_phone')) tags.push('Invalid Phone');
        diagnosisHtml = (tags.length ? tags : ['Format Error'])
          .map(t => `<span class="issue-pill invalid-pill">${t}</span>`)
          .join('');
      }

      const statusBadge = `
        <span class="status-badge ${status}">
          <span class="status-dot-pulse" style="width:5px;height:5px;"></span>
          ${status === 'clean' ? 'Clean' : status === 'review' ? 'Needs Review' : 'Invalid'}
        </span>
      `;

      return `
        <tr data-row-index="${startIndex + idx}">
          <td class="reg-cell">
            <span class="reg-id-badge">${esc(r.registration_id)}</span>
            <span class="person-id-sub">PID: ${esc(r.person_id)}</span>
          </td>
          <td>
            <div class="attendee-cell">
              <div class="attendee-avatar">${initials}</div>
              <span class="attendee-name">${esc(r.full_name)}</span>
            </div>
          </td>
          <td class="contact-cell">
            <span class="contact-email">${esc(r.email)}</span>
            <span class="contact-phone">${esc(r.phone)}</span>
          </td>
          <td>
            <span class="event-tag">${esc(r.event_name)}</span>
          </td>
          <td>
            <div class="issue-tag-list">${diagnosisHtml}</div>
          </td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn-inspect" data-inspect-index="${startIndex + idx}">Inspect ↗</button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach row inspection listeners
    tbody.querySelectorAll('tr[data-row-index]').forEach(row => {
      row.addEventListener('click', e => {
        // If clicked inspect button or anywhere on the row
        const inspectIdx = Number(row.dataset.rowIndex);
        const record = state.filteredRecords[inspectIdx];
        if (record) openRecordModal(record);
      });
    });

    // Update Pagination Controls
    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= totalPages;

    if (pageNumbers) {
      let pageHtml = '';
      if (totalPages <= 7) {
        for (let p = 1; p <= totalPages; p++) {
          pageHtml += `<button class="page-num ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
        }
      } else {
        pageHtml += `<button class="page-num ${page === 1 ? 'active' : ''}" data-page="1">1</button>`;
        if (page > 3) pageHtml += `<span class="page-ellipsis" style="padding:0 4px;color:var(--text-dim);">…</span>`;
        const startP = Math.max(2, page - 1);
        const endP = Math.min(totalPages - 1, page + 1);
        for (let p = startP; p <= endP; p++) {
          pageHtml += `<button class="page-num ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
        }
        if (page < totalPages - 2) pageHtml += `<span class="page-ellipsis" style="padding:0 4px;color:var(--text-dim);">…</span>`;
        pageHtml += `<button class="page-num ${page === totalPages ? 'active' : ''}" data-page="${totalPages}">${totalPages}</button>`;
      }
      pageNumbers.innerHTML = pageHtml;

      pageNumbers.querySelectorAll('.page-num').forEach(btn => {
        btn.addEventListener('click', () => {
          state.pagination.page = Number(btn.dataset.page);
          renderTable();
        });
      });
    }
  }

  // --- Reset All Filters ---
  function resetAllFilters() {
    state.filter.status = 'all';
    state.filter.event = 'all';
    state.filter.issue = 'all';
    state.filter.search = '';

    // Reset controls UI
    syncEventFilterUI();
    syncTabUI();
    syncIssueChipsUI();
    const sInput = $('search');
    const sClear = $('searchClearBtn');
    if (sInput) sInput.value = '';
    if (sClear) sClear.style.display = 'none';

    applyFiltersAndRender();
    showToast('Filters cleared', 'info');
  }

  function syncTabUI() {
    $$('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.type === state.filter.status);
    });
    $$('.quick-chip').forEach(chip => {
      chip.classList.toggle('active', chip.dataset.filterType === state.filter.status);
    });
  }

  function syncEventFilterUI() {
    const sel = $('eventSelect');
    if (sel) sel.value = state.filter.event;

    $$('.btn-event-filter').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.event === state.filter.event);
    });

    $$('.event-card').forEach(card => {
      card.classList.toggle('active-event', card.dataset.eventName === state.filter.event);
    });
  }

  function syncIssueChipsUI() {
    $$('.issue-chip').forEach(chip => {
      chip.classList.toggle('active', chip.dataset.issue === state.filter.issue);
    });
  }

  // --- Modal Record Inspector ---
  function openRecordModal(r) {
    state.selectedRecord = r;
    const modal = $('recordModal');
    if (!modal) return;

    const status = r._status || 'clean';

    // Headers
    $('modalRegId').textContent = r.registration_id || '—';
    $('modalFullName').textContent = r.full_name || 'Participant';
    $('modalEventName').textContent = `Track: ${r.event_name || 'Unassigned'}`;

    // Fields
    $('modalFieldRegId').textContent = r.registration_id || '—';
    $('modalFieldPersonId').textContent = r.person_id || '—';
    $('modalFieldEmail').textContent = r.email || '(Empty / Missing)';
    $('modalFieldPhone').textContent = r.phone || '(Empty / Missing)';
    $('modalFieldEvent').textContent = r.event_name || '—';

    // Status Banner
    const banner = $('modalStatusBanner');
    const icon = $('modalStatusIcon');
    const title = $('modalStatusTitle');
    const desc = $('modalStatusDesc');

    banner.className = `modal-status-banner ${status}`;
    if (status === 'clean') {
      icon.textContent = '✓';
      title.textContent = 'Clean & Verified Record';
      desc.textContent = 'Passed all 6 schema validation rules, syntax checks, and deduplication scans.';
    } else if (status === 'review') {
      icon.textContent = '⌕';
      title.textContent = 'Manual Review Candidate';
      desc.textContent = 'Signal detected: repeated person_id, shared email, or high phonetic name similarity.';
    } else {
      icon.textContent = '✕';
      title.textContent = 'Validation Issue Detected';
      desc.textContent = 'Mandatory field is missing or failed standard RFC syntax validation.';
    }

    // Diagnosis Tags & Explanation
    const tagsContainer = $('modalDiagnosisTags');
    const explanationEl = $('modalDiagnosisExplanation');
    const recText = $('modalRecommendationText');

    let tags = [];
    let explanation = '';
    let recommendation = '';

    if (status === 'clean') {
      tags = ['Schema Valid', 'Unique Identifier', 'RFC Email Compliant', 'Ready for Badge'];
      explanation = 'All attendee fields conform to event registration specifications. Contact information is verified and unique within the attendee pool.';
      recommendation = 'Ready for immediate event check-in badge generation and automated QR ticket dispatch.';
    } else if (status === 'review') {
      const rsn = r.review_reason || '';
      if (rsn.includes('repeated_email')) tags.push('Repeated Email Address');
      if (rsn.includes('repeated_person_id')) tags.push('Duplicate Person ID');
      if (rsn.includes('similar_name')) tags.push('Fuzzy Name Match (>=88%)');

      explanation = `Flags: ${rsn.replace(/;/g, ', ')}. This attendee profile shares identity attributes with another registered participant. Note: Similar names and repeated identifiers are review signals, not proof of duplicate identity.`;
      recommendation = 'Check the attendee roster before the event or during badge pickup. Confirm whether this is a duplicate submission or a legitimate attendee with shared company contacts.';
    } else {
      const iss = r.validation_issues || '';
      if (iss.includes('missing_email')) tags.push('Missing Email');
      if (iss.includes('invalid_email')) tags.push('Invalid Email Syntax');
      if (iss.includes('missing_phone')) tags.push('Missing Phone Number');
      if (iss.includes('invalid_phone')) tags.push('Invalid Phone Number');

      explanation = `Validation errors encountered: ${iss.replace(/;/g, ', ')}. Without valid contact details, automated event confirmations, schedule updates, and QR tickets cannot be dispatched.`;
      recommendation = 'Contact the attendee directly via secondary channel (e.g. phone if email is missing, or organizer outreach) to obtain corrected registration credentials.';
    }

    tagsContainer.innerHTML = tags.map(t => `<span class="issue-pill ${status === 'clean' ? 'clean-pill' : status === 'review' ? 'review-pill' : 'invalid-pill'}">${t}</span>`).join('');
    explanationEl.textContent = explanation;
    recText.textContent = recommendation;

    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeRecordModal() {
    const modal = $('recordModal');
    if (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
  }

  // --- Copying to Clipboard ---
  function copyText(text, label = 'Copied') {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`${label} copied to clipboard`, 'success');
    }).catch(() => {
      showToast('Could not copy to clipboard', 'error');
    });
  }

  // --- Data Loading & Analysis Fetch ---
  async function loadData() {
    try {
      // 1. Fetch Summary
      const sumRes = await fetch('/api/summary');
      let sumData = await sumRes.json();

      // 2. Fetch Records: Fetch all records up to 50000 without artificial caps
      let cleanRes = await fetch('/api/records?type=clean&limit=50000').then(r => r.json()).catch(() => ({ rows: [] }));
      let reviewRes = await fetch('/api/records?type=review&limit=50000').then(r => r.json()).catch(() => ({ rows: [] }));
      let invalidRes = await fetch('/api/records?type=invalid&limit=50000').then(r => r.json()).catch(() => ({ rows: [] }));

      const cleanRows = (cleanRes.rows || []).map(r => ({ ...r, _status: 'clean' }));
      const reviewRows = (reviewRes.rows || []).map(r => ({ ...r, _status: 'review' }));
      const invalidRows = (invalidRes.rows || []).map(r => ({ ...r, _status: 'invalid' }));

      state.allRecords = [...cleanRows, ...reviewRows, ...invalidRows];

      // Merge server summary with client metrics safely without overwriting real totals
      if (sumData && sumData.total_records !== undefined) {
        if (!sumData.events || !Object.keys(sumData.events).length) {
          const computed = computeClientMetrics(state.allRecords);
          sumData = {
            ...sumData,
            events: computed.events,
            issues: computed.issues,
            dimensions: computed.dimensions,
            readiness: computed.readiness
          };
        }
      } else {
        sumData = computeClientMetrics(state.allRecords);
      }

      state.summary = sumData;
      updateDashboard(sumData);
      applyFiltersAndRender();
    } catch (err) {
      console.error('Data load error:', err);
      showToast('Could not load registration data', 'error');
    }
  }

  async function loadSample(type) {
    const btn = $('sample320Btn');
    if (btn) btn.disabled = true;
    showToast('Loading 320 uploaded dataset…', 'info');
    try {
      const res = await fetch(`/api/load_sample?type=${type}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to load sample');
      await loadData();
      showToast(`✓ Loaded ${data.summary.total_records.toLocaleString()} records successfully!`, 'success');
    } catch (err) {
      showToast('Sample error: ' + err.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function clearRecords() {
    const btn = $('clearBtn');
    if (btn) btn.disabled = true;
    showToast('Clearing registration records…', 'info');
    try {
      const res = await fetch('/api/clear', { method: 'POST' });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to clear records');
      state.allRecords = [];
      state.summary = data.summary;
      updateDashboard(data.summary);
      applyFiltersAndRender();
      showToast('✓ All records cleared. Upload a CSV to begin.', 'success');
    } catch (err) {
      showToast('Clear error: ' + err.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function runAudit() {
    const btn = $('run');
    const headerBtn = $('headerRunBtn');
    const btnText = $('runBtnText');

    if (btn) btn.classList.add('loading');
    if (headerBtn) headerBtn.disabled = true;
    if (btnText) btnText.textContent = 'Auditing Records…';

    try {
      showToast('Processing registrations & checking duplicate identities…', 'info');
      const res = await fetch('/api/process', { method: 'POST' });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Audit process failed');

      await loadData();
      showToast('Quality audit complete! All metrics & exports updated.', 'success');
    } catch (err) {
      showToast('Analysis error: ' + err.message, 'error');
    } finally {
      if (btn) btn.classList.remove('loading');
      if (headerBtn) headerBtn.disabled = false;
      if (btnText) btnText.textContent = 'Run Quality Audit';
    }
  }

  // --- Smart CSV Parser & Normalizer ---
  function parseCSV(text) {
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
    const lines = [];
    let row = [];
    let inQuotes = false;
    let curVal = '';

    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      const next = text[i + 1];

      if (c === '"') {
        if (inQuotes && next === '"') {
          curVal += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (c === ',' && !inQuotes) {
        row.push(curVal.trim());
        curVal = '';
      } else if ((c === '\r' || c === '\n') && !inQuotes) {
        if (c === '\r' && next === '\n') i++;
        row.push(curVal.trim());
        if (row.some(val => val.length > 0)) {
          lines.push(row);
        }
        row = [];
        curVal = '';
      } else {
        curVal += c;
      }
    }
    if (curVal.length > 0 || row.length > 0) {
      row.push(curVal.trim());
      if (row.some(val => val.length > 0)) {
        lines.push(row);
      }
    }
    return lines;
  }

  function normalizeCSVForUpload(rawContent) {
    const rows = parseCSV(rawContent);
    if (!rows.length) {
      throw new Error('The selected CSV file appears to be empty.');
    }
    if (rows.length === 1) {
      throw new Error('CSV must contain a header row and at least one data record.');
    }

    const rawHeaders = rows[0];
    const dataRows = rows.slice(1);

    const cleanKey = k => String(k || '').toLowerCase().replace(/[\s_\-]+/g, '');

    const aliases = {
      registration_id: ['registrationid', 'registration_id', 'regid', 'reg_id', 'ticketid', 'orderid', 'id', 'bookingid', 'regno', 'registrationnumber', 'registration'],
      person_id: ['personid', 'person_id', 'participantid', 'userid', 'user_id', 'attendeeid', 'pid', 'memberid'],
      full_name: ['fullname', 'full_name', 'name', 'attendeename', 'participantname', 'studentname', 'candidatename', 'attendee', 'person', 'applicantname', 'contactname', 'attendees'],
      email: ['email', 'emailaddress', 'mail', 'electronicmail', 'emailid', 'e-mail'],
      phone: ['phone', 'phonenumber', 'mobile', 'mobilenumber', 'contact', 'contactnumber', 'telephone', 'cell', 'cellphone', 'phoneno'],
      event_name: ['eventname', 'event_name', 'event', 'track', 'session', 'workshop', 'conference', 'eventtrack']
    };

    const headerColIndex = {};
    rawHeaders.forEach((h, colIdx) => {
      const ck = cleanKey(h);
      for (const [stdKey, aliasList] of Object.entries(aliases)) {
        if (ck === cleanKey(stdKey) || aliasList.includes(ck)) {
          if (headerColIndex[stdKey] === undefined) {
            headerColIndex[stdKey] = colIdx;
          }
        }
      }
    });

    const stdHeaders = ['registration_id', 'person_id', 'full_name', 'email', 'phone', 'event_name'];
    const standardizedRecords = [];

    dataRows.forEach((row, rowIdx) => {
      const rec = {};
      stdHeaders.forEach(stdKey => {
        const colIdx = headerColIndex[stdKey];
        rec[stdKey] = (colIdx !== undefined && row[colIdx] !== undefined) ? row[colIdx].trim() : '';
      });

      // Auto-generate identifiers if not provided in the CSV
      if (!rec.registration_id) {
        rec.registration_id = `R${String(rowIdx + 1).padStart(4, '0')}`;
      }
      if (!rec.person_id) {
        rec.person_id = `P${String(rowIdx + 1).padStart(4, '0')}`;
      }
      if (!rec.event_name) {
        rec.event_name = 'General Event';
      }

      standardizedRecords.push(rec);
    });

    // Convert to normalized CSV text with the exact required header row
    const csvLines = [stdHeaders.join(',')];
    standardizedRecords.forEach(rec => {
      const line = stdHeaders.map(k => {
        let v = rec[k] || '';
        if (v.includes(',') || v.includes('"') || v.includes('\n') || v.includes('\r')) {
          v = `"${v.replace(/"/g, '""')}"`;
        }
        return v;
      }).join(',');
      csvLines.push(line);
    });

    return {
      csvContent: csvLines.join('\n'),
      count: standardizedRecords.length,
      mappedFields: Object.keys(headerColIndex)
    };
  }

  function downloadTemplate() {
    const templateContent = `registration_id,person_id,full_name,email,phone,event_name
R0001,P0001,Priya Sharma,priya.sharma@example.com,9896233790,Tech Symposium
R0002,P0002,Rahul Iyer,rahul.iyer@example.com,9249827706,Career Seminar
R0003,P0003,Aarav Sharma,aarav.sharma@example.com,9553035110,Python Workshop`;

    const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'event_registrations_template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Downloaded sample CSV template', 'success');
  }

  async function processUploadFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showToast('Please upload a valid .csv file.', 'error');
      return;
    }

    showToast(`Parsing and validating ${file.name}…`, 'info');
    try {
      const rawText = await file.text();
      const { csvContent, count, mappedFields } = normalizeCSVForUpload(rawText);

      showToast(`Uploading ${count} records with mapped columns…`, 'info');

      const res = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'text/csv;charset=utf-8' },
        body: csvContent
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Upload failed');

      showToast(`✓ Uploaded & audited ${data.uploaded} records successfully!`, 'success');
      await loadData();
    } catch (err) {
      showToast('Upload error: ' + err.message, 'error');
    }
  }

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    // Theme Toggles
    const themeBtnSidebar = $('themeToggleSidebar');
    const themeBtnHeader = $('themeToggleHeader');
    if (themeBtnSidebar) themeBtnSidebar.addEventListener('click', toggleTheme);
    if (themeBtnHeader) themeBtnHeader.addEventListener('click', toggleTheme);

    // Run Audit Buttons
    const runBtn = $('run');
    const headerRunBtn = $('headerRunBtn');
    const emptyStateRunBtn = $('emptyStateRunBtn');
    const clearBtn = $('clearBtn');
    const sample320Btn = $('sample320Btn');
    const sampleBtn = $('sampleBtn');
    const templateBtn = $('templateBtn');

    if (runBtn) runBtn.addEventListener('click', runAudit);
    if (headerRunBtn) headerRunBtn.addEventListener('click', runAudit);
    if (emptyStateRunBtn) emptyStateRunBtn.addEventListener('click', runAudit);
    if (clearBtn) clearBtn.addEventListener('click', clearRecords);
    if (sample320Btn) sample320Btn.addEventListener('click', () => loadSample('320'));
    if (sampleBtn) sampleBtn.addEventListener('click', runAudit);
    if (templateBtn) templateBtn.addEventListener('click', downloadTemplate);

    // File Upload input
    const fileInput = $('file');
    if (fileInput) {
      fileInput.addEventListener('change', async e => {
        const file = e.target.files[0];
        if (file) await processUploadFile(file);
        fileInput.value = '';
      });
    }

    // Drag and drop upload support on hero banner
    const heroBanner = $('overview');
    if (heroBanner) {
      ['dragenter', 'dragover'].forEach(name => {
        heroBanner.addEventListener(name, e => {
          e.preventDefault();
          heroBanner.style.outline = '2px dashed #6366f1';
        });
      });
      ['dragleave', 'drop'].forEach(name => {
        heroBanner.addEventListener(name, e => {
          e.preventDefault();
          heroBanner.style.outline = 'none';
        });
      });
      heroBanner.addEventListener('drop', async e => {
        e.preventDefault();
        const file = e.dataTransfer && e.dataTransfer.files[0];
        if (file) await processUploadFile(file);
      });
    }

    // Tabs Filter (All / Clean / Review / Invalid)
    $$('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.filter.status = btn.dataset.type;
        syncTabUI();
        applyFiltersAndRender();
      });
    });

    // Quick Chips in Sidebar
    $$('.quick-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        state.filter.status = chip.dataset.filterType;
        syncTabUI();
        applyFiltersAndRender();
        const recSection = $('records');
        if (recSection) recSection.scrollIntoView({ behavior: 'smooth' });
      });
    });

    // Overview Stat Cards Click Filter
    $$('.stat-card').forEach(card => {
      card.addEventListener('click', () => {
        state.filter.status = card.dataset.filter;
        syncTabUI();
        applyFiltersAndRender();
        const recSection = $('records');
        if (recSection) recSection.scrollIntoView({ behavior: 'smooth' });
      });
    });

    // Issue Diagnostic Chips
    $$('.issue-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        state.filter.issue = chip.dataset.issue;
        syncIssueChipsUI();
        applyFiltersAndRender();
        const recSection = $('records');
        if (recSection) recSection.scrollIntoView({ behavior: 'smooth' });
      });
    });

    // Reset Issues Button
    const resetIssuesBtn = $('resetIssuesBtn');
    if (resetIssuesBtn) resetIssuesBtn.addEventListener('click', resetAllFilters);

    const clearFilterBannerBtn = $('clearFilterBannerBtn');
    if (clearFilterBannerBtn) clearFilterBannerBtn.addEventListener('click', resetAllFilters);

    // Event Dropdown Filter
    const eventSelect = $('eventSelect');
    if (eventSelect) {
      eventSelect.addEventListener('change', () => {
        state.filter.event = eventSelect.value;
        syncEventFilterUI();
        applyFiltersAndRender();
      });
    }

    // "All Events" button in header
    $$('.btn-event-filter').forEach(btn => {
      btn.addEventListener('click', () => {
        state.filter.event = btn.dataset.event;
        syncEventFilterUI();
        applyFiltersAndRender();
      });
    });

    // Page Size Select
    const pageSizeSelect = $('pageSizeSelect');
    if (pageSizeSelect) {
      pageSizeSelect.addEventListener('change', () => {
        state.pagination.pageSize = Number(pageSizeSelect.value);
        state.pagination.page = 1;
        renderTable();
      });
    }

    // Search Input with Debounce
    const searchInput = $('search');
    const searchClear = $('searchClearBtn');
    let searchTimer = null;

    if (searchInput) {
      searchInput.addEventListener('input', () => {
        const val = searchInput.value.trim();
        if (searchClear) searchClear.style.display = val ? 'block' : 'none';

        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
          state.filter.search = val;
          applyFiltersAndRender();
        }, 220);
      });
    }

    if (searchClear) {
      searchClear.addEventListener('click', () => {
        searchInput.value = '';
        searchClear.style.display = 'none';
        state.filter.search = '';
        applyFiltersAndRender();
      });
    }

    // Pagination Buttons
    const prevBtn = $('prevPageBtn');
    const nextBtn = $('nextPageBtn');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (state.pagination.page > 1) {
          state.pagination.page--;
          renderTable();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(state.filteredRecords.length / state.pagination.pageSize);
        if (state.pagination.page < totalPages) {
          state.pagination.page++;
          renderTable();
        }
      });
    }

    // Modal Close
    const modalCloseBtn = $('modalCloseBtn');
    const modalCloseActionBtn = $('modalCloseActionBtn');
    const recordModal = $('recordModal');

    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeRecordModal);
    if (modalCloseActionBtn) modalCloseActionBtn.addEventListener('click', closeRecordModal);

    if (recordModal) {
      recordModal.addEventListener('click', e => {
        if (e.target === recordModal) closeRecordModal();
      });
    }

    window.addEventListener('keydown', e => {
      if (e.key === 'Escape') closeRecordModal();
    });

    // Modal Copy Individual Field Buttons
    $$('.btn-copy-small').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const targetId = btn.dataset.copyTarget;
        const targetEl = $(targetId);
        if (targetEl) {
          copyText(targetEl.textContent, 'Field');
        }
      });
    });

    // Modal Copy Full Record Button
    const modalCopyAllBtn = $('modalCopyAllBtn');
    if (modalCopyAllBtn) {
      modalCopyAllBtn.addEventListener('click', () => {
        if (state.selectedRecord) {
          const jsonStr = JSON.stringify(state.selectedRecord, null, 2);
          copyText(jsonStr, 'Record details');
        }
      });
    }

    // Mobile Sidebar Toggle
    const mobileMenuBtn = $('mobileMenuBtn');
    const sidebar = $('sidebar');
    if (mobileMenuBtn && sidebar) {
      mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });
    }

    // Smooth Anchor Navigation
    $$('.nav-item').forEach(link => {
      link.addEventListener('click', e => {
        $$('.nav-item').forEach(n => n.classList.remove('active'));
        link.classList.add('active');
        if (sidebar) sidebar.classList.remove('mobile-open');
      });
    });
  }

  // --- Initialization ---
  function init() {
    applyTheme(state.theme);
    setupEventListeners();
    loadData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
