(function(){
  // Initialize Markdown-it exactly like resultModal
  const md = window.markdownit({
    html: false,
    xhtmlOut: false,
    breaks: true,
    linkify: true,
    typographer: true
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
    // Check if we want full logs or filtered (default filtered)
    const showFull = document.getElementById('showFullLogs')?.checked || false;
    const url = `/api/agent/runs/${runId}${showFull ? '?full=1' : ''}`;
    const data = await fetchJSON(url);
    const run = data.run;
    const events = data.events || [];
    const isFiltered = data.filtered !== false;
    
    selectedRunLabel().textContent = `Run #${run.id} - ${run.status} ${isFiltered ? '(Filtered View)' : '(Full Logs)'}`;
    
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

    // Add log filter controls
    const logControls = `
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" id="showFullLogs" ${showFull ? 'checked' : ''}>
          <label class="form-check-label small" for="showFullLogs">
            Show full logs (${isFiltered ? events.length + ' filtered' : 'all verbose logs'})
          </label>
        </div>
        <small class="text-muted">Essential: LLM I/O, Agent Selection, Tool Calls</small>
      </div>
    `;

    runMeta().innerHTML = `
      <div class="small text-muted">Task:</div>
      <div class="mb-2"><code>${(run.task||'').replace(/</g,'&lt;')}</code></div>
      ${run.error ? `<div class="alert alert-danger py-1 px-2 small">${run.error}</div>` : ''}
      ${finalReplySection}
      ${logControls}
    `;

    const rows = events.map((e, idx) => {
      // Color code different event types
      let typeClass = 'bg-secondary';
      switch(e.event_type) {
        case 'llm_input':
        case 'llm_first_input':
          typeClass = 'bg-primary';
          break;
        case 'llm_result':
          typeClass = 'bg-success';
          break;
        case 'agent_response':
          typeClass = 'bg-info';
          break;
        case 'tool_call':
          typeClass = 'bg-warning';
          break;
        case 'tool_result':
          typeClass = 'bg-light text-dark';
          break;
        case 'error':
          typeClass = 'bg-danger';
          break;
      }
      
      const eventButtons = e.event_type === 'llm_result'
        ? `<button class="btn btn-link btn-sm ms-1 p-0 view-result" data-result='${JSON.stringify(e.detail||{}).replace(/'/g, "&#39;")}' data-event-type="llm_result" title="View conversation steps"><i class="fas fa-eye"></i></button>
          <button class="btn btn-link btn-sm ms-1 p-0 view-payload" data-payload='${JSON.stringify(e.detail||{}).replace(/'/g, "&#39;")}' title="View raw JSON"><i class="fas fa-expand"></i></button>`
        : `<button class="btn btn-link btn-sm ms-1 p-0 view-payload" data-payload='${JSON.stringify(e.detail||{}).replace(/'/g, "&#39;")}' title="View full"><i class="fas fa-expand"></i></button>`;

      return `
      <tr>
        <td>${idx+1}</td>
        <td class="small">${fmt(e.ts)}</td>
        <td><span class="badge ${typeClass}">${e.event_type}</span></td>
        <td class="small">${e.source||''}</td>
        <td class="small">${e.agent_name||''}</td>
        <td class="small">${e.server_id||''}</td>
        <td class="small">${e.tool_name||''}</td>
        <td class="small">
          <span class="text-monospace">${previewDetail(e.detail)}</span>
          ${eventButtons}
        </td>
      </tr>
    `}).join('');
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
        const eventType = res.getAttribute('data-event-type') || null;
        showResultModal(resultText, eventType);
      }
    });

    // Handle full logs toggle
    document.addEventListener('change', (e) => {
      if (e.target.id === 'showFullLogs') {
        // Re-load current run with new filter setting
        const currentRunId = selectedRunLabel().textContent.match(/Run #(\d+)/)?.[1];
        if (currentRunId) {
          loadRun(currentRunId).catch(console.error);
        }
      }
      
      // Handle result modal view mode toggle
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

  function showResultModal(resultText, eventType = null) {
    // Special handling for llm_result events - show step-by-step conversation
    if (eventType === 'llm_result') {
      return showLLMResultSteps(resultText);
    }

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

  function showLLMResultSteps(jsonData) {
    try {
      // jsonData might already be a parsed object or a string
      let data;
      if (typeof jsonData === 'string') {
        data = JSON.parse(jsonData);
      } else {
        data = jsonData;
      }
      const replyText = data.reply || '';

      // Extract messages from the reply text
      let messages = [];
      if (replyText.startsWith('messages=[')) {
        const messagesStr = replyText.substring(9); // Remove 'messages=[ prefix'

        // Parse individual message objects from the string
        // This is a simplified parser for the message format
        messages = parseMessagesFromString(messagesStr);
      } else {
        // Fallback if not in expected format
        messages = [];
      }

      // Create the steps view
      createStepsView(messages);

      // Show the steps modal
      const modal = new bootstrap.Modal(document.getElementById('stepsModal'));
      modal.show();

    } catch (error) {
      console.error('Error parsing LLM result:', error);
      // Fallback to regular modal display - convert object to string if needed
      const resultText = typeof jsonData === 'string' ? jsonData : JSON.stringify(jsonData, null, 2);
      showResultModal(resultText, 'llm_result_fallback');
    }
  }

  function parseMessagesFromString(messagesStr) {
    const messages = [];
    let currentPos = 0;

    while (currentPos < messagesStr.length) {
      // Find next message start - look for class names like "TextMessage(", "ToolCallRequestEvent(" etc.
      const messageClassMatch = messagesStr.substring(currentPos).match(/(TextMessage|ToolCallRequestEvent|ToolCallExecutionEvent|ToolCallSummaryMessage)(\(id=)/);

      if (!messageClassMatch) break;

      const messageStart = currentPos + messageClassMatch.index;
      const messageType = messageClassMatch[1];

      // Find the end of this message by counting parentheses
      let parenBalance = 0;
      let messageEnd = messageStart;

      for (let i = messageStart; i < messagesStr.length; i++) {
        if (messagesStr[i] === '(') parenBalance++;
        else if (messagesStr[i] === ')') {
          parenBalance--;
          if (parenBalance === 0) {
            messageEnd = i + 1;
            break;
          }
        }
      }

      if (parenBalance !== 0) break; // Unmatched parentheses

      const messageStr = messagesStr.substring(messageStart, messageEnd).trim();
      if (messageStr.endsWith(',')) {
        // Remove trailing comma if present
        messageStr = messageStr.slice(0, -1);
      }

      try {
        // Parse the message string into a JavaScript object
        const messageObj = parseMessageObject(messageStr);
        if (messageObj) {
          messages.push(messageObj);
        }
      } catch (e) {
        console.warn('Failed to parse message:', messageStr, e);
      }

      currentPos = messageEnd;
      // Skip whitespace and commas
      while (currentPos < messagesStr.length && (messagesStr[currentPos] === ',' || messagesStr[currentPos] === ' ' || messagesStr[currentPos] === '\n')) {
        currentPos++;
      }
    }

    return messages;
  }

  function parseMessageObject(messageStr) {
    // Simple parser for Python object representation
    // Expected format: Type(id='...', source='...', models_usage=..., metadata=..., created_at=..., content=..., ...)
    const typeMatch = messageStr.match(/^(\w+)\(/);
    if (!typeMatch) return null;

    const messageType = typeMatch[1];

    // Extract source
    const sourceMatch = messageStr.match(/source='([^']*)'/);
    const createdAtMatch = messageStr.match(/created_at=datetime\.datetime\(([^)]+)\)/);

    // Extract content - this needs to handle multiple formats properly
    let content = '';

    // Find content parameter start
    const contentKeyIndex = messageStr.indexOf('content=');
    if (contentKeyIndex !== -1) {
      const contentStart = contentKeyIndex + 8; // Skip "content="
      let contentEnd = contentStart;
      let contentValue = messageStr.substring(contentStart);

      // Find the end of content based on what type it is
      if (contentValue.startsWith("'")) {
        // Single quoted string - find matching end quote
        contentEnd = contentStart + 1; // Skip opening quote
        while (contentEnd < messageStr.length && messageStr[contentEnd] !== "'") {
          contentEnd++;
        }
        if (contentEnd < messageStr.length) {
          contentEnd++; // Include closing quote
          content = messageStr.substring(contentStart, contentEnd);
          content = content.slice(1, -1); // Remove quotes
        }
      } else if (contentValue.startsWith('"')) {
        // Double quoted string - find matching end quote
        contentEnd = contentStart + 1; // Skip opening quote
        while (contentEnd < messageStr.length && messageStr[contentEnd] !== '"') {
          contentEnd++;
        }
        if (contentEnd < messageStr.length) {
          contentEnd++; // Include closing quote
          content = messageStr.substring(contentStart, contentEnd);
          content = content.slice(1, -1); // Remove quotes
        }
      } else if (contentValue.startsWith('[')) {
        // List format [content] - find matching end bracket
        let bracketCount = 0;
        contentEnd = contentStart;

        // Find where the content list ends (could be before a comma or closing parenthesis)
        for (let i = contentStart; i < messageStr.length; i++) {
          if (messageStr[i] === '[') bracketCount++;
          else if (messageStr[i] === ']') {
            bracketCount--;
            if (bracketCount === 0) {
              contentEnd = i + 1;
              break;
            }
          }
          // Stop at next parameter or end of object
          if (bracketCount === 0 && (messageStr[i] === ',' || messageStr[i] === ')')) {
            contentEnd = i;
            break;
          }
        }

        if (contentEnd > contentStart) {
          content = messageStr.substring(contentStart, contentEnd);
          content = content.slice(1, -1); // Remove [ ]

          // For ToolCallRequestEvent, extract function name only - display arguments in plain text
          if (messageType === 'ToolCallRequestEvent') {
            try {
              // Parse FunctionCall(id='...', arguments='...', name='...')
              const funcCallMatch = content.match(/FunctionCall\(id='([^']*)',\s*arguments='([^']*)',\s*name='([^']*)'\)/);
              if (funcCallMatch) {
                const funcName = funcCallMatch[3];
                const funcArgs = funcCallMatch[2];
                // Keep original format: Function(name) and plain text for args
                content = `Function: ${funcName}\n\nArguments: ${funcArgs}`;
              }
            } catch (e) {
              // Keep original content if parsing fails
            }
          }
          // For other message types with list format, keep as is
        }
      } else {
        // Try simple content extraction for other formats
        const simpleEnd = messageStr.substring(contentStart).indexOf(',');
        if (simpleEnd !== -1) {
          content = messageStr.substring(contentStart, contentStart + simpleEnd);
        } else {
          content = contentValue.split(')')[0]; // Simple fallback
        }
      }
    }

    return {
      type: messageType,
      source: sourceMatch ? sourceMatch[1] : '',
      content: content,
      created_at: createdAtMatch ? createdAtMatch[1] : ''
    };
  }

  function createStepsView(messages) {
    const stepsModalBody = document.getElementById('stepsModalBody');
    if (!stepsModalBody) return;

    if (messages.length === 0) {
      stepsModalBody.innerHTML = '<div class="text-center p-4 text-muted">No conversation steps available</div>';
      return;
    }

    // Create steps timeline similar to main index page
    let html = '<div class="steps-timeline">';

    messages.forEach((message, index) => {
      const stepNumber = index + 1;
      const source = message.source || 'Unknown';
      let stepTitle = `${source}`;

      // Customize title based on message type
      switch (message.type) {
        case 'TextMessage':
          stepTitle = `${source.includes('user') ? '👤 User Query' : `🤖 Assistant Response: ${source}`}`;
          break;
        case 'ToolCallRequestEvent':
          stepTitle = `🛠️ Tool Call: ${source}`;
          break;
        case 'ToolCallExecutionEvent':
          stepTitle = `✅ Tool Execution: ${source}`;
          break;
        case 'ToolCallSummaryMessage':
          stepTitle = `📋 Tool Result: ${source}`;
          break;
        default:
          stepTitle = `📝 ${message.type}: ${source}`;
      }

      const rawContent = message.content || '';

      html += `
        <div class="step-item completed">
          <div class="step-number">${stepNumber}</div>
          <div class="step-content">
            <h6>${stepTitle}</h6>
          </div>
        </div>
      `;
    });

    html += '</div>';
    stepsModalBody.innerHTML = html;

    // Apply content after DOM insertion using the exact approach as resultModal
    messages.forEach((message, index) => {
      const stepElement = stepsModalBody.querySelector(`.step-item:nth-child(${index + 1}) .step-content`);
      if (!stepElement) return;

      const rawContent = message.content || '';

      if (message.type === 'ToolCallRequestEvent' || message.type === 'ToolCallExecutionEvent' || message.type === 'ToolCallSummaryMessage') {
        // For all tool-related messages, display plain text without markdown formatting
        const contentDiv = document.createElement('div');
        contentDiv.className = 'step-result-container';
        contentDiv.innerHTML = `<div class="step-result">${rawContent.replace(/\n/g, '<br>')}</div>`;
        stepElement.appendChild(contentDiv);
      } else if (rawContent) {
        // For other message types, use exact same approach as showResultModal
        const contentContainer = document.createElement('div');
        contentContainer.className = 'step-result-container';

        // Create the formatted div like resultModal
        const formattedDiv = document.createElement('div');
        formattedDiv.className = 'step-result markdown-content';

        // Unescape the content if it contains JSON escapes
        let contentToRender = rawContent;
        try {
          // If the content contains escaped characters like \n, unescape them
          if (rawContent.includes('\\n') || rawContent.includes('\\u')) {
            contentToRender = JSON.parse('"' + rawContent.replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t') + '"');
          }
        } catch (e) {
          // If unescaping fails, use original content
          contentToRender = rawContent;
        }

        formattedDiv.innerHTML = md.render(contentToRender);

        // Apply syntax highlighting exactly like resultModal
        formattedDiv.querySelectorAll('pre code').forEach((block) => {
          if (window.hljs) {
            hljs.highlightElement(block);
          }
        });

        contentContainer.appendChild(formattedDiv);
        stepElement.appendChild(contentContainer);
      } else {
        const descDiv = document.createElement('div');
        descDiv.className = 'step-description text-muted';
        descDiv.textContent = 'No content';
        stepElement.appendChild(descDiv);
      }
    });
  }

  // init
  document.addEventListener('DOMContentLoaded', () => {
    attachHandlers();
    loadRuns().catch(console.error);
  });
})();
