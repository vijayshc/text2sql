(function(){
  // Initialize Markdown-it
  const md = window.markdownit({
    html: false, // Disable HTML tags in source
    xhtmlOut: false, // Use '/' to close single tags (<br />)
    breaks: true, // Convert '\n' in paragraphs into <br>
    linkify: true, // Autoconvert URL-like text to links
    typographer: true, // Enable some language-neutral replacement + quotes beautification
    highlight: function (str, lang) {
      if (lang && window.hljs && hljs.getLanguage(lang)) {
        try {
          return '<pre class="hljs"><code>' +
                 hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                 '</code></pre>';
        } catch (__) {}
      }
      // Use external default escaping
      return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
    }
  });

  const runsTableBody = () => document.querySelector('#runsTable tbody');
  const eventsTableBody = () => document.querySelector('#eventsTable tbody');
  const runMeta = () => document.querySelector('#runMeta');
  const runsLimitEl = () => document.querySelector('#runsLimit');
  const refreshBtn = () => document.querySelector('#refreshRunsBtn');
  const selectedRunLabel = () => document.querySelector('#selectedRunLabel');

  async function fetchJSON(url){
    const res = await fetch(url, { credentials: 'same-origin' });
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  function fmt(ts){
    if(!ts) return '-';
    try { 
      // Handle different timestamp formats
      let date;
      if (typeof ts === 'string') {
        // If the timestamp doesn't have timezone info, treat it as local time
        if (!ts.includes('T') && !ts.includes('Z') && !ts.includes('+') && !ts.includes('-')) {
          // SQLite CURRENT_TIMESTAMP format: "YYYY-MM-DD HH:MM:SS"
          // Convert to ISO format but treat as local time
          date = new Date(ts + ' UTC'); // SQLite CURRENT_TIMESTAMP is actually UTC
        } else if (ts.includes(' ') && !ts.includes('T')) {
          // Python isoformat with space: "YYYY-MM-DD HH:MM:SS" (local time)
          date = new Date(ts.replace(' ', 'T'));
        } else {
          // Standard ISO format
          date = new Date(ts);
        }
      } else {
        date = new Date(ts);
      }
      
      // Format in local timezone
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch (e) { 
      console.warn('Date parsing error:', e, 'for timestamp:', ts);
      return ts; 
    }
  }

  function badge(status){
    const s = (status||'').toLowerCase();
    const map = { running: 'bg-info', success: 'bg-success', error: 'bg-danger' };
    const cls = map[s] || 'bg-secondary';
    return `<span class="badge ${cls}">${status}</span>`;
  }

  async function loadRuns(){
    const limit = encodeURIComponent(runsLimitEl().value || '50');
    const data = await fetchJSON(`/api/agent/runs?limit=${limit}`);
    const rows = (data.runs||[]).map(r => `
      <tr data-run-id="${r.id}">
        <td>${r.id}</td>
        <td>${r.entity_type}</td>
        <td>${r.entity_id}</td>
        <td class="text-monospace small" title="${(r.task||'').replace(/"/g, '&quot;')}">${previewTask(r.task)}</td>
        <td>${badge(r.status)}</td>
        <td>${fmt(r.started_at)}</td>
        <td>${fmt(r.finished_at)}</td>
        <td>
          <button class="btn btn-sm btn-outline-primary view-run" data-run-id="${r.id}"><i class="fas fa-eye"></i></button>
        </td>
      </tr>`).join('');
    runsTableBody().innerHTML = rows || '<tr><td colspan="8" class="text-muted">No runs</td></tr>';
  }

  function previewTask(task) {
    if (!task) return '-';
    const str = String(task);
    if (str.length > 100) return str.slice(0, 100) + '…';
    return str;
  }

  function previewDetail(detail){
    try{
      const str = typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2);
      if(str.length > 180) return str.slice(0, 180) + '…';
      return str;
    }catch(_){ return String(detail); }
  }

  async function loadRun(runId){
    const data = await fetchJSON(`/api/agent/runs/${runId}`);
    const run = data.run;
    const events = data.events || [];
    selectedRunLabel().textContent = `Run #${run.id} - ${run.status}`;
    
    // Build the final reply section with expand button if content exists
    const finalReplySection = run.final_reply ? `
      <div class="alert alert-success py-2 px-3 small d-flex justify-content-between align-items-start">
        <div class="flex-grow-1 me-2">
          <div class="fw-bold mb-1">Final Reply:</div>
          <div class="text-truncate" style="max-width: 80ch;">${(run.final_reply||'').slice(0,200)}${(run.final_reply||'').length > 200 ? '...' : ''}</div>
        </div>
        <button class="btn btn-link btn-sm p-0 view-result" data-result='${JSON.stringify(run.final_reply||'').replace(/'/g, "&#39;")}' title="View full result">
          <i class="fas fa-expand"></i>
        </button>
      </div>
    ` : '';

    runMeta().innerHTML = `
      <div class="small text-muted">Task:</div>
      <div class="mb-2"><code>${(run.task||'').replace(/</g,'&lt;')}</code></div>
      ${run.error ? `<div class="alert alert-danger py-1 px-2 small">${run.error}</div>` : ''}
      ${finalReplySection}
    `;

    const rows = events.map((e, idx) => `
      <tr>
        <td>${idx+1}</td>
        <td>${fmt(e.ts)}</td>
        <td><span class="badge bg-secondary">${e.event_type}</span></td>
        <td>${e.source||''}</td>
        <td>${e.agent_name||''}</td>
        <td>${e.server_id||''}</td>
        <td>${e.tool_name||''}</td>
        <td>
          <span class="text-monospace small">${previewDetail(e.detail)}</span>
          <button class="btn btn-link btn-sm ms-1 p-0 view-payload" data-payload='${JSON.stringify(e.detail||{}).replace(/'/g, "&#39;")}' title="View full"><i class="fas fa-expand"></i></button>
        </td>
      </tr>
    `).join('');
    eventsTableBody().innerHTML = rows || '<tr><td colspan="8" class="text-muted">No events</td></tr>';
    // Switch to details tab if tabs exist
    const tabTriggerEl = document.querySelector('#tab-details-tab');
    if (tabTriggerEl && window.bootstrap && bootstrap.Tab) {
      try {
        const tab = new bootstrap.Tab(tabTriggerEl);
        tab.show();
      } catch {}
    }
  }

  function attachHandlers(){
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.view-run');
      if(btn){
        const runId = btn.getAttribute('data-run-id');
        loadRun(runId).catch(console.error);
      }
      
      const pl = e.target.closest('.view-payload');
      if(pl){
        const json = pl.getAttribute('data-payload');
        const pretty = (()=>{ try { return JSON.stringify(JSON.parse(json), null, 2); } catch { return json; } })();
        document.getElementById('payloadPre').textContent = pretty;
        const modal = new bootstrap.Modal(document.getElementById('payloadModal'));
        modal.show();
      }
      
      const res = e.target.closest('.view-result');
      if(res){
        const resultText = JSON.parse(res.getAttribute('data-result'));
        showResultModal(resultText);
      }
    });

    // Handle result modal view mode toggle
    document.addEventListener('change', (e) => {
      if (e.target.name === 'resultViewMode') {
        const formatted = document.getElementById('resultFormatted');
        const raw = document.getElementById('resultRaw');
        if (e.target.id === 'resultViewFormatted') {
          formatted.style.display = 'block';
          raw.style.display = 'none';
        } else {
          formatted.style.display = 'none';
          raw.style.display = 'block';
        }
      }
    });

    refreshBtn().addEventListener('click', () => loadRuns().catch(console.error));
    runsLimitEl().addEventListener('change', () => loadRuns().catch(console.error));
  }

  function showResultModal(resultText) {
    // Set up the formatted view with markdown
    const formattedDiv = document.getElementById('resultFormatted');
    const rawPre = document.getElementById('resultRaw');
    
    // Render markdown
    formattedDiv.innerHTML = md.render(resultText);
    
    // Highlight code blocks
    formattedDiv.querySelectorAll('pre code').forEach((block) => {
      if (window.hljs) {
        hljs.highlightElement(block);
      }
    });
    
    // Set raw text
    rawPre.textContent = resultText;
    
    // Show formatted view by default
    document.getElementById('resultViewFormatted').checked = true;
    formattedDiv.style.display = 'block';
    rawPre.style.display = 'none';
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('resultModal'));
    modal.show();
  }

  // init
  document.addEventListener('DOMContentLoaded', () => {
    attachHandlers();
    loadRuns().catch(console.error);
  });
})();
