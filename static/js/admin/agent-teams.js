document.addEventListener('DOMContentLoaded', () => {
  const teamsTableEl = document.getElementById('teamsTable');
  const workflowsTableEl = document.getElementById('workflowsTable');
  const btnNewTeam = document.getElementById('btnNewTeam');
  const btnNewWorkflow = document.getElementById('btnNewWorkflow');
  const agentsBuilder = document.getElementById('agentsBuilder');
  const agentsList = document.getElementById('agentsList');
  const addAgentBtn = document.getElementById('addAgentBtn');

  const teamModal = new bootstrap.Modal(document.getElementById('teamModal'));
  const workflowModal = new bootstrap.Modal(document.getElementById('workflowModal'));

  let teamsDataTable = null;
  let workflowsDataTable = null;
  let teamsCache = [];
  let workflowsCache = [];
  let teamNameLookup = new Map();

  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function initDataTables() {
    if (!(window.jQuery && $.fn.DataTable)) {
      return;
    }

    if (teamsTableEl) {
      teamsDataTable = $(teamsTableEl).DataTable({
        columns: [
          { title: 'Team' },
          { title: 'Agents' },
          { title: 'Mode' },
          { title: 'Max Rounds' },
          { title: 'Actions', orderable: false, searchable: false }
        ],
        order: [[0, 'asc']],
        drawCallback: function() { this.api().columns.adjust(); },
        initComplete: function() { this.api().columns.adjust(); }
      });
    }

    if (workflowsTableEl) {
      workflowsDataTable = $(workflowsTableEl).DataTable({
        columns: [
          { title: 'Workflow' },
          { title: 'Team' },
          { title: 'Nodes' },
          { title: 'Entry' },
          { title: 'Actions', orderable: false, searchable: false }
        ],
        order: [[0, 'asc']],
        drawCallback: function() { this.api().columns.adjust(); },
        initComplete: function() { this.api().columns.adjust(); }
      });
    }
  }

  function formatExecutionMode(team) {
    const mode = team?.config?.settings?.execution_mode || 'roundrobin';
    switch (mode) {
      case 'selector':
        return '<span class="badge bg-info text-dark">Selector</span>';
      case 'swarm':
        return '<span class="badge bg-warning text-dark">Swarm</span>';
      default:
        return '<span class="badge bg-secondary">Round Robin</span>';
    }
  }

  function renderAgents(team) {
    const agents = team?.config?.agents || [];
    if (agents.length === 0) {
      return '<span class="text-muted">No agents</span>';
    }

    const badges = agents.slice(0, 3).map(agent =>
      `<span class="badge bg-secondary me-1">${escapeHtml(agent.name || agent.role || 'Agent')}</span>`
    ).join('');
    const remaining = agents.length - 3;
    return remaining > 0
      ? `${badges}<span class="badge bg-light text-muted">+${remaining} more</span>`
      : badges;
  }

  function buildTeamRow(team) {
    const description = team.description ? `<div class="text-muted small">${escapeHtml(team.description)}</div>` : '';
    const maxRounds = team?.config?.settings?.max_rounds ?? '-';
    const actions = `
      <div class="btn-group btn-group-sm" role="group">
        <button class="btn btn-outline-primary" data-action="edit" data-id="${team.id}" title="Edit team"><i class="fas fa-edit"></i></button>
        <button class="btn btn-outline-danger" data-action="del" data-id="${team.id}" title="Delete team"><i class="fas fa-trash"></i></button>
      </div>`;

    return [
      `<div><strong>${escapeHtml(team.name)}</strong>${description}</div>`,
      renderAgents(team),
      formatExecutionMode(team),
      maxRounds,
      actions
    ];
  }

  function parseWorkflowGraph(graph) {
    if (!graph) return { nodes: [], config: {} };
    if (typeof graph === 'string') {
      try { return JSON.parse(graph); }
      catch { return { nodes: [], config: {} }; }
    }
    return graph;
  }

  function buildWorkflowRow(workflow) {
    const graph = parseWorkflowGraph(workflow.graph);
    const nodes = Array.isArray(graph.nodes) ? graph.nodes.length : 0;
    const entry = graph?.config?.entry_point || 'Auto';
    const description = workflow.description ? `<div class="text-muted small">${escapeHtml(workflow.description)}</div>` : '';
    const teamLabel = teamNameLookup.get(workflow.team_id) || `Team #${workflow.team_id}`;
    const actions = `
      <div class="btn-group btn-group-sm" role="group">
        <button class="btn btn-outline-primary" data-action="editwf" data-id="${workflow.id}" title="Edit workflow"><i class="fas fa-edit"></i></button>
        <button class="btn btn-outline-success" data-action="runwf" data-id="${workflow.id}" title="Run workflow"><i class="fas fa-play"></i></button>
        <button class="btn btn-outline-danger" data-action="delwf" data-id="${workflow.id}" title="Delete workflow"><i class="fas fa-trash"></i></button>
      </div>`;

    return [
      `<div><strong>${escapeHtml(workflow.name)}</strong>${description}</div>`,
      escapeHtml(teamLabel),
      nodes,
      escapeHtml(entry || ''),
      actions
    ];
  }

  function renderTeamsTable(teams) {
    if (teamsDataTable) {
      const rows = teams.map(buildTeamRow);
      teamsDataTable.clear();
      if (rows.length) {
        teamsDataTable.rows.add(rows);
      }
      teamsDataTable.draw();
    } else if (teamsTableEl) {
      const tbody = teamsTableEl.querySelector('tbody');
      if (!tbody) return;
      tbody.innerHTML = teams.map(team => {
        const row = buildTeamRow(team);
        return `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`;
      }).join('');
    }
  }

  function renderWorkflowsTable(workflows) {
    if (workflowsDataTable) {
      const rows = workflows.map(buildWorkflowRow);
      workflowsDataTable.clear();
      if (rows.length) {
        workflowsDataTable.rows.add(rows);
      }
      workflowsDataTable.draw();
    } else if (workflowsTableEl) {
      const tbody = workflowsTableEl.querySelector('tbody');
      if (!tbody) return;
      tbody.innerHTML = workflows.map(workflow => {
        const row = buildWorkflowRow(workflow);
        return `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`;
      }).join('');
    }
  }

  function handleTeamAction(action, id) {
    if (!id) return;

    if (action === 'del') {
      if (confirm('Delete team?')) {
        fetch(`/api/agent/teams/${id}`, { method: 'DELETE' })
          .then(() => refresh())
          .catch(err => alert('Failed to delete team: ' + err.message));
      }
      return;
    }

    if (action === 'edit') {
      fetch(`/api/agent/teams/${id}`)
        .then(r => r.json())
        .then(t => {
          document.getElementById('teamName').value = t.name;
          document.getElementById('teamDesc').value = t.description || '';
          document.getElementById('teamConfig').value = JSON.stringify(t.config || {}, null, 2);

          const settings = (t.config && t.config.settings) || {};
          document.getElementById('executionMode').value = settings.execution_mode || 'roundrobin';
          document.getElementById('maxRounds').value = settings.max_rounds || 6;
          document.getElementById('selectorPrompt').value = settings.selector_prompt || `AGENT SELECTOR

Available agents:
{roles}

Current conversation:
{history}

INSTRUCTIONS:
- Read the conversation above
- Select EXACTLY ONE agent name from {participants}
- Respond with ONLY the agent name, nothing else
- Do not explain, do not use tools, do not add commentary
- Just return the agent name

Select agent:`;
          document.getElementById('allowRepeatedSpeaker').checked = settings.allow_repeated_speaker !== false;
          toggleSelectorSettings();

          loadServersAndTools().then(() => {
            bootstrapAgentsBuilder((t.config && t.config.agents) || []);
          });

          teamModal.show();
          document.getElementById('saveTeamBtn').onclick = () => {
            const name = document.getElementById('teamName').value.trim();
            const description = document.getElementById('teamDesc').value.trim();

            syncBuilderToJson();
            syncSettingsToJson();

            let config = {};
            try {
              config = JSON.parse(document.getElementById('teamConfig').value);
            } catch (e) {
              alert('Invalid JSON config. Please fix the JSON or use the visual builder.');
              return;
            }

            fetch(`/api/agent/teams/${id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name, description, config })
            })
              .then(r => r.json())
              .then(result => {
                if (result.error) {
                  alert('Error saving team: ' + result.error);
                } else {
                  teamModal.hide();
                  refresh();
                }
              })
              .catch(err => {
                alert('Network error: ' + err.message);
              });
          };
        });
    }
  }

  function handleWorkflowAction(action, id) {
    if (!id) return;

    if (action === 'delwf') {
      if (confirm('Delete workflow?')) {
        fetch(`/api/agent/workflows/${id}`, { method: 'DELETE' })
          .then(() => refresh())
          .catch(err => alert('Failed to delete workflow: ' + err.message));
      }
      return;
    }

    if (action === 'editwf') {
      fetch(`/api/agent/workflows/${id}`)
        .then(r => r.json())
        .then(w => {
          currentWorkflowId = parseInt(id, 10);
          document.getElementById('wfName').value = w.name;
          document.getElementById('wfDesc').value = w.description || '';
          document.getElementById('wfGraph').value = JSON.stringify(w.graph || {}, null, 2);

          loadGraphFlowConfig(w.graph || {});

          fetch('/api/agent/teams').then(r => r.json()).then(d => {
            const sel = document.getElementById('wfTeam'); sel.innerHTML='';
            (d.teams || []).forEach(t => {
              const opt = document.createElement('option'); opt.value = t.id; opt.textContent = t.name; if (t.id === w.team_id) opt.selected = true; sel.appendChild(opt);
            });

            const selectedTeam = d.teams.find(t => t.id === w.team_id);
            if (selectedTeam) {
              populateAgentLists(selectedTeam.config);
            }

            loadWorkflowIntoBuilder(w.graph || {});
            refreshWorkflowVisualization();
            workflowModal.show();
          });
        });
      return;
    }

    if (action === 'runwf') {
      const task = prompt('Enter task/input to run:');
      if (!task) return;
      fetch(`/api/agent/run/workflow/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task })
      })
        .then(r => r.json()).then(res => {
          if (res.success) {
            alert(res.reply || 'Done');
          } else {
            try {
              const modal = new bootstrap.Modal(document.getElementById('agentErrorModal'));
              document.getElementById('agentErrorMessage').textContent = res.error || 'Unknown error';
              document.getElementById('agentErrorTrace').textContent = res.trace || '';
              modal.show();
              document.getElementById('copyAgentErrorTrace').onclick = () => {
                const txt = document.getElementById('agentErrorTrace').textContent || '';
                navigator.clipboard?.writeText(txt);
              };
            } catch (e) {
              alert((res.error || 'Error') + (res.trace ? `\n\n${res.trace}` : ''));
            }
          }
        });
    }
  }

  function refresh() {
    const teamsPromise = fetch('/api/agent/teams').then(r => r.json()).catch(error => ({ error }));
    const workflowsPromise = fetch('/api/agent/workflows').then(r => r.json()).catch(error => ({ error }));

    Promise.all([teamsPromise, workflowsPromise]).then(([teamsResponse, workflowsResponse]) => {
      if (teamsResponse?.error) {
        console.error('Failed to load agent teams:', teamsResponse.error);
        teamsCache = [];
      } else {
        teamsCache = teamsResponse?.teams || [];
      }

      teamNameLookup = new Map(teamsCache.map(team => [team.id, team.name]));
      renderTeamsTable(teamsCache);

      if (workflowsResponse?.error) {
        console.error('Failed to load workflows:', workflowsResponse.error);
        workflowsCache = [];
      } else {
        workflowsCache = workflowsResponse?.workflows || [];
      }

      renderWorkflowsTable(workflowsCache);
    }).catch(error => {
      console.error('Failed to refresh agent data:', error);
      teamsCache = [];
      workflowsCache = [];
      renderTeamsTable([]);
      renderWorkflowsTable([]);
    });
  }

  initDataTables();

  btnNewTeam.addEventListener('click', ()=>{
    document.getElementById('teamName').value = '';
    document.getElementById('teamDesc').value = '';
    document.getElementById('executionMode').value = 'roundrobin';
    document.getElementById('maxRounds').value = '6';
    document.getElementById('selectorPrompt').value = `AGENT SELECTOR

Available agents:
{roles}

Task history:
{history}

INSTRUCTIONS:
1. Read the task history above
2. Select EXACTLY ONE agent from: {participants}
3. Respond with ONLY the agent name - no explanation, no tools, no extra text
4. Valid responses are only the agent names listed in the participants

Selected agent:`;
    document.getElementById('allowRepeatedSpeaker').checked = true;
    toggleSelectorSettings();
    document.getElementById('teamConfig').value = JSON.stringify({
      agents: [],
      settings: {
        max_rounds: 6,
        execution_mode: "roundrobin",
        selector_prompt: "AGENT SELECTOR\n\nAvailable agents:\n{roles}\n\nCurrent conversation:\n{history}\n\nINSTRUCTIONS:\n- Read the conversation above\n- Select EXACTLY ONE agent name from {participants}\n- Respond with ONLY the agent name, nothing else\n- Do not explain, do not use tools, do not add commentary\n- Just return the agent name\n\nSelect agent:",
        allow_repeated_speaker: true
      }
    }, null, 2);
    bootstrapAgentsBuilder([]);
    
    // Reset save button to create mode
    document.getElementById('saveTeamBtn').onclick = ()=>{
      const name = document.getElementById('teamName').value.trim();
      const description = document.getElementById('teamDesc').value.trim();
      
      // Sync both agents and settings to JSON
      syncBuilderToJson();
      syncSettingsToJson();
      
      const configText = document.getElementById('teamConfig').value;
      let config = {};
      try { 
        config = JSON.parse(configText); 
      } catch(e) { 
        alert('Invalid JSON config. Please fix the JSON or use the visual builder.'); 
        return; 
      }
      fetch('/api/agent/teams', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, config})})
        .then(r=>r.json())
        .then(result => {
          if (result.error) {
            alert('Error creating team: ' + result.error);
          } else {
            teamModal.hide(); 
            refresh();
          }
        })
        .catch(err => {
          alert('Network error: ' + err.message);
        });
    };
    
    teamModal.show();
  });

  // Toggle selector settings based on execution mode
  function toggleSelectorSettings() {
    const mode = document.getElementById('executionMode').value;
    const selectorSettings = document.getElementById('selectorSettings');
    selectorSettings.style.display = mode === 'selector' ? 'block' : 'none';
  }

  // Add event listener for execution mode change
  document.getElementById('executionMode').addEventListener('change', ()=>{
    toggleSelectorSettings();
    syncSettingsToJson();
    
    // Refresh agent rows to show/hide agent type selector
    const currentAgents = [];
    Array.from(agentsList.children).forEach((row)=>{
      const agent = {
        name: row.querySelector('.agent-name').value.trim(),
        role: row.querySelector('.agent-role').value.trim(),
        system_prompt: row.querySelector('.agent-prompt').value.trim(),
        description: row.querySelector('.agent-desc')?.value.trim() || '',
        agent_type: row.querySelector('.agent-type')?.value || 'worker',
        tools: row.agentData?.tools || []
      };
      currentAgents.push(agent);
    });
    
    // Rebuild the agent rows with the new layout
    bootstrapAgentsBuilder(currentAgents);
  });

  // Add event listeners for all setting inputs
  document.getElementById('maxRounds').addEventListener('change', syncSettingsToJson);
  document.getElementById('selectorPrompt').addEventListener('change', syncSettingsToJson);
  document.getElementById('allowRepeatedSpeaker').addEventListener('change', syncSettingsToJson);

  function syncSettingsToJson() {
    const currentConfig = safeParseJson();
    const settings = {
      max_rounds: parseInt(document.getElementById('maxRounds').value) || 6,
      execution_mode: document.getElementById('executionMode').value,
      selector_prompt: document.getElementById('selectorPrompt').value,
      allow_repeated_speaker: document.getElementById('allowRepeatedSpeaker').checked
    };
    
    currentConfig.settings = settings;
    document.getElementById('teamConfig').value = JSON.stringify(currentConfig, null, 2);
  }

  // Set up save button for creating new teams (this will be overridden when editing)
  document.getElementById('saveTeamBtn').onclick = ()=>{
    const name = document.getElementById('teamName').value.trim();
    const description = document.getElementById('teamDesc').value.trim();
    
    // Sync both agents and settings to JSON
    syncBuilderToJson();
    syncSettingsToJson();
    
    const configText = document.getElementById('teamConfig').value;
    let config = {};
    try { 
      config = JSON.parse(configText); 
    } catch(e) { 
      alert('Invalid JSON config. Please fix the JSON or use the visual builder.'); 
      return; 
    }
    fetch('/api/agent/teams', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, config})})
      .then(r=>r.json())
      .then(result => {
        if (result.error) {
          alert('Error creating team: ' + result.error);
        } else {
          teamModal.hide(); 
          refresh();
        }
      })
      .catch(err => {
        alert('Network error: ' + err.message);
      });
  };

  btnNewWorkflow.addEventListener('click', ()=>{
    currentWorkflowId = null; // Reset to create mode
    document.getElementById('wfName').value = '';
    document.getElementById('wfDesc').value = '';
    document.getElementById('wfGraph').value = JSON.stringify({
      "nodes": [],
      "edges": [],
      "config": {
        "entry_point": "",
        "termination": {
          "type": "max_message",
          "max_messages": 20
        }
      }
    }, null, 2);
    
    // Reset GraphFlow config UI
    document.getElementById('entryPointAgent').value = '';
    document.getElementById('terminationType').value = 'max_message';
    document.getElementById('maxMessages').value = '20';
    document.getElementById('terminationText').value = 'TERMINATE';
    toggleTerminationConfig();
    
    // populate team list
    fetch('/api/agent/teams').then(r=>r.json()).then(d=>{
      const sel = document.getElementById('wfTeam');
      sel.innerHTML = '';
      (d.teams||[]).forEach(t=>{
        const opt = document.createElement('option');
        opt.value = t.id; opt.textContent = `${t.name}`; sel.appendChild(opt);
      });
      workflowModal.show();
      
      // Populate agent lists when team is selected
      if (d.teams && d.teams.length > 0) {
        populateAgentLists(d.teams[0].config);
      }
    })
  });

  // Global variable to track workflow editing state
  let currentWorkflowId = null;

  document.getElementById('saveWorkflowBtn').addEventListener('click', ()=>{
    const name = document.getElementById('wfName').value.trim();
    const description = document.getElementById('wfDesc').value.trim();
    if(!name) {alert('Name required'); return;}
    const team_id = parseInt(document.getElementById('wfTeam').value, 10);
    
    // Always sync GraphFlow configuration before saving in case user made UI changes
    syncGraphFlowConfig();
    
    const graphText = document.getElementById('wfGraph').value;
    let graph = {};
    try { 
      graph = JSON.parse(graphText); 
      console.log('Saving workflow with graph:', graph);
    } catch(e) { 
      alert('Invalid Graph JSON: ' + e.message + '\n\nPlease fix the JSON syntax or use the visual builder.'); 
      return; 
    }
    
    if (currentWorkflowId) {
      // Update existing workflow
      fetch(`/api/agent/workflows/${currentWorkflowId}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, team_id, graph})})
        .then(r=>r.json()).then((result) => { 
          if (result.error) {
            alert('Error updating workflow: ' + result.error);
          } else {
            workflowModal.hide(); 
            refresh(); 
            currentWorkflowId = null; 
          }
        })
        .catch(err => {
          alert('Network error: ' + err.message);
        });
    } else {
      // Create new workflow
      fetch('/api/agent/workflows', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, team_id, graph})})
        .then(r=>r.json()).then((result) => { 
          if (result.error) {
            alert('Error creating workflow: ' + result.error);
          } else {
            workflowModal.hide(); 
            refresh(); 
          }
        })
        .catch(err => {
          alert('Network error: ' + err.message);
        });
    }
  });

  // GraphFlow event listeners
  document.getElementById('terminationType')?.addEventListener('change', toggleTerminationConfig);
  document.getElementById('maxMessages')?.addEventListener('change', syncGraphFlowConfig);
  document.getElementById('terminationText')?.addEventListener('change', syncGraphFlowConfig);
  document.getElementById('entryPointAgent')?.addEventListener('change', syncGraphFlowConfig);
  document.getElementById('enableMessageFilter')?.addEventListener('change', toggleMessageFilter);
  document.getElementById('addFilterBtn')?.addEventListener('click', addMessageFilter);
  document.getElementById('addEdgeBtn')?.addEventListener('click', addGraphEdge);
  
  // Add change listener for direct JSON editing
  document.getElementById('wfGraph')?.addEventListener('input', function() {
    // Add visual indicator that JSON has been modified
    const btn = document.getElementById('syncFromGraphJsonBtn');
    if (btn) {
      btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> JSON Modified';
      btn.className = 'btn btn-sm btn-warning';
    }
  });
  
  document.getElementById('wfTeam')?.addEventListener('change', (e) => {
    const teamId = e.target.value;
    if (teamId) {
      fetch(`/api/agent/teams/${teamId}`)
        .then(r => r.json())
        .then(team => {
          populateAgentLists(team.config);
        })
        .catch(err => console.error('Failed to load team:', err));
    }
  });

  document.addEventListener('click', (event) => {
    const btn = event.target.closest('button[data-action]');
    if (!btn) return;

    if (btn.closest('#teamsTable')) {
      handleTeamAction(btn.getAttribute('data-action'), btn.getAttribute('data-id'));
    } else if (btn.closest('#workflowsTable')) {
      handleWorkflowAction(btn.getAttribute('data-action'), btn.getAttribute('data-id'));
    }
  });

  refresh();

  // --- Workflow Builder ---
  const nodesList = document.getElementById('nodesList');
  const addNodeBtn = document.getElementById('addNodeBtn');
  const nodeName = document.getElementById('nodeName');
  const nodeAgent = document.getElementById('nodeAgent');
  const saveNodeBtn = document.getElementById('saveNodeBtn');
  const removeNodeBtn = document.getElementById('removeNodeBtn');

  function parseGraph(){ try{ return JSON.parse(document.getElementById('wfGraph').value||'{}'); }catch{ return {nodes:[], edges:[]}; } }
  function writeGraph(g){ 
    document.getElementById('wfGraph').value = JSON.stringify(g, null, 2); 
    console.log('Updated workflow JSON:', g);
    // Auto-refresh visualization when graph changes
    refreshWorkflowVisualization();
  }
  function refreshNodeSelectors(g){
    // Use the populateNodeSelectors function for consistency
    populateNodeSelectors(g);
    
    // populate agent list from selected team
    const nodeAgentDropdown = document.getElementById('nodeAgent');
    if (nodeAgentDropdown) {
      nodeAgentDropdown.innerHTML='<option value="">Select Agent</option>';
      try{
        const teamId = parseInt(document.getElementById('wfTeam').value,10);
        if (teamId) {
          fetch(`/api/agent/teams/${teamId}`).then(r=>r.json()).then(t=>{
            populateAgentLists(t.config);
            console.log('Refreshed agent list for team:', teamId);
          }).catch(err => console.error('Failed to load team agents:', err));
        }
      }catch(error){
        console.error('Error refreshing node selectors:', error);
      }
    }
  }
  function refreshNodesList(g){
    nodesList.innerHTML='';
    (g.nodes||[]).forEach(n=>{
      const opt=document.createElement('option'); 
      opt.value=n.id; 
      opt.textContent=`${n.name || 'Unnamed'} (Agent: ${n.agent || 'None'})`; 
      nodesList.appendChild(opt);
    })
  }
  function selectNode(g, id){
    const n=(g.nodes||[]).find(x=>String(x.id)===String(id)); 
    if(!n){ 
      nodeName.value=''; 
      nodeAgent.value=''; 
      document.getElementById('enableMessageFilter').checked = false;
      toggleMessageFilter();
      return; 
    }
    
    console.log('Selecting node:', n);
    
    nodeName.value = n.name || ''; 
    
    // Ensure agent dropdown is populated before setting value
    const nodeAgentDropdown = document.getElementById('nodeAgent');
    if (nodeAgentDropdown) {
      // If the dropdown is empty, try to populate it first
      if (nodeAgentDropdown.options.length <= 1) {
        console.log('Agent dropdown empty, trying to populate...');
        try {
          const teamId = parseInt(document.getElementById('wfTeam').value, 10);
          if (teamId) {
            fetch(`/api/agent/teams/${teamId}`)
              .then(r => r.json())
              .then(team => {
                populateAgentLists(team.config);
                // Set the agent value after population
                nodeAgentDropdown.value = n.agent || '';
                console.log('Set agent after population:', n.agent);
              })
              .catch(err => {
                console.error('Failed to load team for agent population:', err);
                nodeAgentDropdown.value = n.agent || '';
              });
          } else {
            nodeAgentDropdown.value = n.agent || '';
          }
        } catch (error) {
          console.error('Error populating agents:', error);
          nodeAgentDropdown.value = n.agent || '';
        }
      } else {
        // Dropdown is already populated, set value directly
        nodeAgentDropdown.value = n.agent || '';
        console.log('Set agent value directly:', n.agent);
      }
    }
    
    // Handle message filtering
    const hasMessageFilter = n.message_filter && n.message_filter.enabled;
    document.getElementById('enableMessageFilter').checked = hasMessageFilter;
    toggleMessageFilter();
    
    if (hasMessageFilter) {
      console.log('Loading message filters for node:', n.message_filter);
      updateFiltersDisplay(n);
    }
  }
  
  function toggleMessageFilter() {
    const enabled = document.getElementById('enableMessageFilter').checked;
    document.getElementById('messageFilterConfig').style.display = enabled ? 'block' : 'none';
    
    if (!enabled) {
      const nodeId = document.getElementById('nodesList').value;
      if (nodeId) {
        const graph = parseGraph();
        const node = graph.nodes.find(n => String(n.id) === String(nodeId));
        if (node && node.message_filter) {
          node.message_filter.enabled = false;
          writeGraph(graph);
        }
      }
    }
  }
  nodesList?.addEventListener('change', ()=>{
    const g=parseGraph(); refreshNodeSelectors(g); selectNode(g, nodesList.value);
  })
  addNodeBtn?.addEventListener('click', ()=>{
    const g=parseGraph(); const id = Date.now();
    g.nodes = g.nodes||[]; g.nodes.push({id, name:`Node ${g.nodes.length+1}`, agent:''});
    writeGraph(g); refreshNodesList(g); refreshNodeSelectors(g); nodesList.value=String(id); selectNode(g, id);
  })
  saveNodeBtn?.addEventListener('click', ()=>{
    const g=parseGraph(); 
    const id = nodesList?.value; 
    if(!id) {
      alert('Please select a node to save');
      return;
    }
    
    const n=(g.nodes||[]).find(x=>String(x.id)===String(id)); 
    if(!n) {
      alert('Selected node not found in graph');
      return;
    }
    
    // Update node properties
    const newName = nodeName.value.trim() || `Node ${n.id}`;
    const newAgent = nodeAgent.value;
    
    console.log('Updating node:', {
      id: n.id, 
      oldName: n.name, 
      newName: newName, 
      oldAgent: n.agent, 
      newAgent: newAgent
    });
    
    n.name = newName;
    n.agent = newAgent;
    
    // Note: Edges are managed separately in Edge Configuration section
    // No automatic edge creation based on predecessor/successor
    
    writeGraph(g); 
    refreshNodesList(g); 
    refreshNodeSelectors(g); 
    selectNode(g, id);
    
    // Show success message
    console.log('Node saved successfully. New graph:', g);
    alert(`Node "${newName}" saved successfully!`);
  })
  removeNodeBtn?.addEventListener('click', ()=>{
    const g=parseGraph(); const id=nodesList?.value; if(!id) return;
    g.nodes=(g.nodes||[]).filter(x=>String(x.id)!==String(id));
    g.edges=(g.edges||[]).filter(e=>String(e.from)!==String(id) && String(e.to)!==String(id));
    writeGraph(g); refreshNodesList(g); refreshNodeSelectors(g);
    nodeName.value=''; nodeAgent.value='';
  })

  // --- GraphFlow Configuration Functions ---
  
  function toggleTerminationConfig() {
    const type = document.getElementById('terminationType').value;
    document.getElementById('maxMessagesConfig').style.display = type === 'max_message' ? 'block' : 'none';
    document.getElementById('textMentionConfig').style.display = type === 'text_mention' ? 'block' : 'none';
  }
  
  function populateAgentLists(teamConfig) {
    const agents = (teamConfig && teamConfig.agents) || [];
    const agentSelects = [
      document.getElementById('nodeAgent'),
      document.getElementById('entryPointAgent'),
      document.getElementById('filterSource')
    ];
    
    agentSelects.forEach(select => {
      if (select) {
        const currentValue = select.value;
        select.innerHTML = select.id === 'entryPointAgent' ? '<option value="">Auto-detect (source nodes)</option>' : '<option value="">Select Agent</option>';
        agents.forEach(agent => {
          const opt = document.createElement('option');
          opt.value = agent.name;
          opt.textContent = agent.name;
          if (agent.name === currentValue) opt.selected = true;
          select.appendChild(opt);
        });
      }
    });
  }
  
  function populateNodeSelectors(graph) {
    const nodes = graph.nodes || [];
    const selectors = [
      document.getElementById('edgeFrom'),
      document.getElementById('edgeTo')
    ];
    
    selectors.forEach(select => {
      if (select) {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Select Node</option>';
        nodes.forEach(node => {
          const opt = document.createElement('option');
          opt.value = node.id;
          opt.textContent = `${node.name || 'Node'} (${node.id})`;
          if (String(node.id) === String(currentValue)) opt.selected = true;
          select.appendChild(opt);
        });
      }
    });
  }
  
  function syncGraphFlowConfig() {
    try {
      const graph = parseGraph();
      
      // Update termination config
      const terminationType = document.getElementById('terminationType').value;
      const config = graph.config || {};
      config.termination = config.termination || {};
      config.termination.type = terminationType;
      
      if (terminationType === 'max_message') {
        config.termination.max_messages = parseInt(document.getElementById('maxMessages').value) || 20;
      } else if (terminationType === 'text_mention') {
        config.termination.text = document.getElementById('terminationText').value || 'TERMINATE';
      }
      
      // Update entry point
      const entryPoint = document.getElementById('entryPointAgent').value;
      config.entry_point = entryPoint || '';
      
      graph.config = config;
      writeGraph(graph);
      
      // Auto-refresh visualization when config changes
      refreshWorkflowVisualization();
    } catch (e) {
      console.error('Error syncing GraphFlow config:', e);
    }
  }
  
  function loadGraphFlowConfig(graph) {
    try {
      const config = graph.config || {};
      const termination = config.termination || {};
      
      document.getElementById('entryPointAgent').value = config.entry_point || '';
      document.getElementById('terminationType').value = termination.type || 'max_message';
      document.getElementById('maxMessages').value = termination.max_messages || 20;
      document.getElementById('terminationText').value = termination.text || 'TERMINATE';
      
      toggleTerminationConfig();
    } catch (e) {
      console.error('Error loading GraphFlow config:', e);
    }
  }

  function loadWorkflowIntoBuilder(graph) {
    try {
      const nodes = graph.nodes || [];
      const edges = graph.edges || [];
      
      console.log('Loading workflow into builder:', { nodes, edges });
      
      // Populate node lists and selectors first
      refreshNodesList(graph);
      refreshNodeSelectors(graph);
      
      // If there are nodes, select the first one to show its properties
      if (nodes.length > 0) {
        const firstNode = nodes[0];
        const nodesList = document.getElementById('nodesList');
        if (nodesList) {
          nodesList.value = String(firstNode.id);
          
          // Ensure agents are loaded before selecting node
          setTimeout(() => {
            selectNode(graph, firstNode.id);
            console.log('Selected first node after delay:', firstNode);
          }, 100);
        }
      }
      
      // Load edges information (shown in JSON, could add edge list UI later)
      console.log('Loaded edges:', edges);
      
      // Update the visualization
      refreshWorkflowVisualization();
      
    } catch (e) {
      console.error('Error loading workflow into builder:', e);
    }
  }
  
  function addMessageFilter() {
    const source = document.getElementById('filterSource').value;
    const position = document.getElementById('filterPosition').value;
    const count = parseInt(document.getElementById('filterCount').value) || 1;
    
    if (!source) {
      alert('Please select a source agent');
      return;
    }
    
    const nodeId = document.getElementById('nodesList').value;
    if (!nodeId) {
      alert('Please select a node first');
      return;
    }
    
    const graph = parseGraph();
    const node = graph.nodes.find(n => String(n.id) === String(nodeId));
    if (!node) return;
    
    // Initialize message filter
    if (!node.message_filter) {
      node.message_filter = { enabled: true, filters: [] };
    }
    
    // Add filter rule
    node.message_filter.filters.push({
      source: source,
      position: position,
      count: count
    });
    
    writeGraph(graph);
    updateFiltersDisplay(node);
    
    // Clear inputs
    document.getElementById('filterSource').value = '';
    document.getElementById('filterPosition').value = 'last';
    document.getElementById('filterCount').value = '1';
  }
  
  function updateFiltersDisplay(node) {
    const filtersList = document.getElementById('filtersList');
    const filters = (node.message_filter && node.message_filter.filters) || [];
    
    filtersList.innerHTML = '';
    filters.forEach((filter, index) => {
      const div = document.createElement('div');
      div.className = 'small bg-light p-1 rounded mb-1 d-flex justify-content-between align-items-center';
      div.innerHTML = `
        <span>${filter.source} (${filter.position}, ${filter.count})</span>
        <button class="btn btn-sm btn-outline-danger" onclick="removeMessageFilter(${index})">×</button>
      `;
      filtersList.appendChild(div);
    });
  }
  
  function removeMessageFilter(index) {
    const nodeId = document.getElementById('nodesList').value;
    if (!nodeId) return;
    
    const graph = parseGraph();
    const node = graph.nodes.find(n => String(n.id) === String(nodeId));
    if (!node || !node.message_filter) return;
    
    node.message_filter.filters.splice(index, 1);
    if (node.message_filter.filters.length === 0) {
      node.message_filter.enabled = false;
    }
    
    writeGraph(graph);
    updateFiltersDisplay(node);
  }
  
  function addGraphEdge() {
    const fromId = document.getElementById('edgeFrom').value;
    const toId = document.getElementById('edgeTo').value;
    
    if (!fromId || !toId) {
      alert('Please select both from and to nodes');
      return;
    }
    
    if (fromId === toId) {
      alert('From and to nodes cannot be the same');
      return;
    }
    
    const graph = parseGraph();
    
    // Check if edge already exists
    const existingEdge = graph.edges.find(e => 
      String(e.from) === String(fromId) && String(e.to) === String(toId)
    );
    
    if (existingEdge) {
      alert('Edge already exists');
      return;
    }
    
    const edge = {
      from: parseInt(fromId),
      to: parseInt(toId)
    };
    
    // Add optional configurations
    const conditionType = document.getElementById('conditionType').value;
    const conditionText = document.getElementById('conditionText').value;
    const activationGroup = document.getElementById('activationGroup').value;
    const activationCondition = document.getElementById('activationCondition').value;
    
    if (conditionType && conditionText) {
      edge.condition = {
        type: conditionType,
        text: conditionText
      };
    }
    
    if (activationGroup) {
      edge.activation_group = activationGroup;
      if (activationCondition !== 'all') {
        edge.activation_condition = activationCondition;
      }
    }
    
    graph.edges.push(edge);
    writeGraph(graph);
    
    // Clear inputs
    document.getElementById('edgeFrom').value = '';
    document.getElementById('edgeTo').value = '';
    document.getElementById('conditionType').value = '';
    document.getElementById('conditionText').value = '';
    document.getElementById('activationGroup').value = '';
    document.getElementById('activationCondition').value = 'all';
    
    alert('Edge added successfully');
  }

  // --- Workflow Builder ---

  // Add event listener for "Sync from JSON" button in workflow editor
  document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'syncFromGraphJsonBtn') {
      try {
        const graphJson = document.getElementById('wfGraph').value;
        const graph = JSON.parse(graphJson);
        
        console.log('Syncing workflow from JSON:', graph);
        
        // Update the GraphFlow configuration UI
        loadGraphFlowConfig(graph);
        
        // Load the graph into the builder
        loadWorkflowIntoBuilder(graph);
        
        // Refresh visualization
        refreshWorkflowVisualization();
        
        // Show success message
        const btn = e.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Synced!';
        btn.className = 'btn btn-sm btn-success';
        
        setTimeout(() => {
          btn.innerHTML = originalText;
          btn.className = 'btn btn-sm btn-outline-secondary';
        }, 2000);
        
      } catch (error) {
        alert('Invalid JSON format. Please fix the JSON syntax and try again.');
        console.error('JSON sync error:', error);
      }
    }
  });

  // Global function for removing message filters (called from HTML)
  window.removeMessageFilter = removeMessageFilter;

  let serversCache = [];
  function loadServersAndTools(){
    return fetch('/api/agent/mcp/servers-with-tools').then(r=>r.json()).then(d=>{
      serversCache = d.servers||[]; return serversCache;
    }).catch(()=>{ serversCache=[]; return []; });
  }
  function bootstrapAgentsBuilder(agents){
    console.log('Bootstrapping agents builder with:', agents);
    agentsList.innerHTML='';
    
    // Ensure servers are loaded first
    if (!serversCache || serversCache.length === 0) {
      console.log('Loading servers first...');
      loadServersAndTools().then(()=>{
        console.log('Servers loaded, now adding agent rows...');
        (agents||[]).forEach((a, index) => {
          console.log(`Adding agent row ${index}:`, a);
          addAgentRow(a);
        });
      });
    } else {
      console.log('Servers already loaded, adding agent rows directly...');
      (agents||[]).forEach((a, index) => {
        console.log(`Adding agent row ${index}:`, a);
        addAgentRow(a);
      });
    }
  }
  function addAgentRow(agent){
    console.log('Adding agent row for:', agent);
    const idx = agentsList.children.length;
    const row = document.createElement('div'); row.className='border rounded p-2 mb-2 agent-row';
    
    // Check execution mode to show/hide agent type selector
    const executionMode = document.getElementById('executionMode').value;
    const showAgentType = executionMode === 'selector';
    
    row.innerHTML = `
      <div class="row g-2 align-items-end">
        <div class="col-md-2">
          <label class="form-label small">Name</label>
          <input class="form-control form-control-sm agent-name" value="${(agent?.name||'').replace(/"/g, '&quot;')}">
        </div>
        <div class="col-md-2">
          <label class="form-label small">Role</label>
          <input class="form-control form-control-sm agent-role" value="${(agent?.role||'').replace(/"/g, '&quot;')}">
        </div>
        ${showAgentType ? `
        <div class="col-md-2">
          <label class="form-label small">Agent Type</label>
          <select class="form-select form-select-sm agent-type">
            <option value="worker" ${(agent?.agent_type||'worker')==='worker'?'selected':''}>Worker</option>
            <option value="selector" ${(agent?.agent_type)==='selector'?'selected':''}>Selector</option>
          </select>
        </div>` : ''}
        <div class="col-md-3">
          <label class="form-label small">Description</label>
          <textarea class="form-control form-control-sm agent-desc" rows="2" placeholder="Brief description of agent role">${(agent?.description||'').replace(/</g, '&lt;')}</textarea>
        </div>
        <div class="col-md-${showAgentType ? '2' : '3'}">
          <label class="form-label small">System Prompt</label>
          <textarea class="form-control form-control-sm agent-prompt" rows="3">${(agent?.system_prompt||'').replace(/</g, '&lt;')}</textarea>
        </div>
        <div class="col-md-1 text-end">
          <button class="btn btn-sm btn-outline-danger remove-agent">Remove</button>
        </div>
      </div>
      <div class="row g-2 mt-2">
        <div class="col-md-5">
          <label class="form-label small">MCP Server</label>
          <select class="form-select form-select-sm server-select"><option value="">Select server</option></select>
        </div>
        <div class="col-md-5">
          <label class="form-label small">Tools</label>
          <select multiple class="form-select form-select-sm tools-select"></select>
        </div>
        <div class="col-md-2 d-grid">
          <button class="btn btn-sm btn-outline-primary add-tools">Add Tools</button>
        </div>
      </div>
      <div class="mt-2 small text-muted">Assigned tools: <span class="assigned-tools"></span></div>
    `;
    agentsList.appendChild(row);
    
    // Store the original agent data for reference
    row.agentData = agent;
    
    // populate server list
    const serverSelect = row.querySelector('.server-select');
    serversCache.forEach(s=>{
      const opt=document.createElement('option'); opt.value=s.id; opt.textContent=s.name; serverSelect.appendChild(opt);
    });
    
    const toolsSelect = row.querySelector('.tools-select');
    serverSelect.addEventListener('change', ()=>{
      // populate tools for server
      const sid = parseInt(serverSelect.value,10);
      toolsSelect.innerHTML='';
      const server = serversCache.find(x=>x.id===sid);
      (server?.tools||[]).forEach(t=>{
        const opt=document.createElement('option'); opt.value=t.name; opt.textContent=t.title||t.name; toolsSelect.appendChild(opt);
      })
    });
    
    // load existing tools and display them
    const assignedSpan = row.querySelector('.assigned-tools');
    const assigned = (agent?.tools||[]);
    console.log('Assigned tools for agent:', assigned);
    
    // Store tools in row data
    if (!row.agentData) row.agentData = {tools: []};
    row.agentData.tools = [...assigned];
    
    // Function to update the assigned tools display with remove buttons
    function updateAssignedToolsDisplay() {
      if (row.agentData.tools.length === 0) {
        assignedSpan.innerHTML = '<em>No tools assigned</em>';
        return;
      }
      
      const toolElements = row.agentData.tools.map((tool, index) => {
        return `<span class="badge bg-secondary me-1">
          #${tool.server_id}:${tool.tool_name}
          <button type="button" class="btn-close btn-close-white ms-1" 
                  onclick="removeAssignedTool(this, ${index})" 
                  style="font-size: 0.6em;" aria-label="Remove tool"></button>
        </span>`;
      });
      
      assignedSpan.innerHTML = toolElements.join('');
    }
    
    // Function to remove a tool (will be attached to window for onclick)
    window.removeAssignedTool = function(button, toolIndex) {
      // Find the row containing this button
      const row = button.closest('.agent-row');
      if (!row || !row.agentData || !row.agentData.tools) return;
      
      // Remove the tool at the specified index
      row.agentData.tools.splice(toolIndex, 1);
      
      // Find the updateAssignedToolsDisplay function for this row
      const assignedSpan = row.querySelector('.assigned-tools');
      
      // Update display by recreating the tool badges
      if (row.agentData.tools.length === 0) {
        assignedSpan.innerHTML = '<em>No tools assigned</em>';
      } else {
        const toolElements = row.agentData.tools.map((tool, index) => {
          return `<span class="badge bg-secondary me-1">
            #${tool.server_id}:${tool.tool_name}
            <button type="button" class="btn-close btn-close-white ms-1" 
                    onclick="removeAssignedTool(this, ${index})" 
                    style="font-size: 0.6em;" aria-label="Remove tool"></button>
          </span>`;
        });
        assignedSpan.innerHTML = toolElements.join('');
      }
      
      // Sync to JSON
      syncBuilderToJson();
    };
    
    // Initial display update
    updateAssignedToolsDisplay();
    
    row.querySelector('.add-tools').addEventListener('click', ()=>{
      const sid = parseInt(serverSelect.value,10); if(!sid) return;
      const selected = Array.from(toolsSelect.selectedOptions).map(o=>({server_id:sid, tool_name:o.value}));
      
      // Update the row's agent data
      if (!row.agentData) row.agentData = {tools: []};
      if (!row.agentData.tools) row.agentData.tools = [];
      
      // Add new tools, avoiding duplicates
      selected.forEach(newTool => {
        const exists = row.agentData.tools.some(existing => 
          existing.server_id === newTool.server_id && existing.tool_name === newTool.tool_name
        );
        if (!exists) {
          row.agentData.tools.push(newTool);
        }
      });
      
      // Update display using the new function
      updateAssignedToolsDisplay();
      
      // Sync to JSON
      syncBuilderToJson();
    });
    
    row.querySelector('.remove-agent').addEventListener('click', ()=>{
      row.remove();
      syncBuilderToJson();
    });
    
    // Add event listeners for name, role, description, agent type, and prompt changes
    const inputClasses = ['agent-name', 'agent-role', 'agent-desc', 'agent-prompt'];
    if (showAgentType) {
      inputClasses.push('agent-type');
    }
    
    inputClasses.forEach(className => {
      const input = row.querySelector(`.${className}`);
      if (input) {
        input.addEventListener('change', syncBuilderToJson);
        input.addEventListener('blur', syncBuilderToJson);
        input.addEventListener('input', () => {
          syncBuilderToJson();
        });
      }
    });
  }
  function safeParseJson(){
    try{ return JSON.parse(document.getElementById('teamConfig').value||'{}'); }catch{ return {}; }
  }
  function writeConfig(partial){
    const current = safeParseJson();
    const merged = {...current, ...partial};
    document.getElementById('teamConfig').value = JSON.stringify(merged, null, 2);
  }
  function syncBuilderToJson(){
    console.log('Syncing builder to JSON...');
    const agents=[];
    Array.from(agentsList.children).forEach((row, index)=>{
      const name = row.querySelector('.agent-name').value.trim();
      const role = row.querySelector('.agent-role').value.trim();
      const system_prompt = row.querySelector('.agent-prompt').value.trim();
      const description = row.querySelector('.agent-desc')?.value.trim() || '';
      const agent_type = row.querySelector('.agent-type')?.value || 'worker';
      
      // Use stored agent data for tools, fallback to parsing if needed
      let tools = [];
      if (row.agentData && row.agentData.tools) {
        tools = row.agentData.tools;
      } else {
        // Fallback: parse from assigned tools text
        const assignedText = row.querySelector('.assigned-tools').textContent||'';
        tools = assignedText.split(',').map(s=>s.trim()).filter(Boolean).map(tok=>{
          const m = tok.match(/^#([^:]+):(.+)$/); if(!m) return null;
          return {server_id: parseInt(m[1],10), tool_name: m[2]}
        }).filter(Boolean);
      }
      
      const agent = {name, role, system_prompt, description, agent_type, tools};
      console.log(`Agent ${index}:`, agent);
      agents.push(agent);
    });
    
    console.log('All agents:', agents);
    const currentConfig = safeParseJson();
    currentConfig.agents = agents;
    document.getElementById('teamConfig').value = JSON.stringify(currentConfig, null, 2);
  }
  if (addAgentBtn){
    addAgentBtn.addEventListener('click', ()=> addAgentRow({
      name:'Agent', 
      role:'', 
      system_prompt:'', 
      description: 'An agent responsible for specific tasks.',
      agent_type: 'worker',
      tools:[]
    }));
  }
  
  // Add event listener for "Sync from JSON" button
  const syncFromJsonBtn = document.getElementById('syncFromJsonBtn');
  if (syncFromJsonBtn) {
    syncFromJsonBtn.addEventListener('click', () => {
      try {
        const config = JSON.parse(document.getElementById('teamConfig').value || '{}');
        const agents = config.agents || [];
        const settings = config.settings || {};
        
        // Update settings fields
        document.getElementById('executionMode').value = settings.execution_mode || 'roundrobin';
        document.getElementById('maxRounds').value = settings.max_rounds || 6;
        document.getElementById('selectorPrompt').value = settings.selector_prompt || `AGENT SELECTOR

Available agents:
{roles}

Current conversation:
{history}

INSTRUCTIONS:
- Read the conversation above
- Select EXACTLY ONE agent name from {participants}
- Respond with ONLY the agent name, nothing else
- Do not explain, do not use tools, do not add commentary
- Just return the agent name

Select agent:`;
        document.getElementById('allowRepeatedSpeaker').checked = settings.allow_repeated_speaker !== false;
        toggleSelectorSettings();
        
        console.log('Syncing from JSON:', agents);
        bootstrapAgentsBuilder(agents);
      } catch (e) {
        alert('Invalid JSON format. Please fix the JSON syntax.');
        console.error('JSON parse error:', e);
      }
    });
  }
});

// Workflow Visualization with Mermaid.js
function refreshWorkflowVisualization() {
  const vizContainer = document.getElementById('workflowVisualization');
  const mermaidContainer = document.getElementById('mermaidContainer');
  const placeholder = document.getElementById('vizPlaceholder');
  
  if (!vizContainer || !mermaidContainer || !placeholder) return;
  
  // Check if Mermaid is available
  if (typeof mermaid === 'undefined') {
    showVisualizationError(mermaidContainer, 'Mermaid.js library not loaded. Please refresh the page.');
    return;
  }
  
  try {
    const graph = JSON.parse(document.getElementById('wfGraph').value || '{}');
    const nodes = graph.nodes || [];
    const edges = graph.edges || [];
    const config = graph.config || {};
    
    if (nodes.length === 0) {
      placeholder.style.display = 'block';
      mermaidContainer.style.display = 'none';
      placeholder.innerHTML = `
        <div class="text-center text-muted">
          <i class="fas fa-project-diagram fa-3x mb-2"></i>
          <p>No nodes defined. Add nodes to see workflow visualization.</p>
        </div>
      `;
      return;
    }
    
    // Generate Mermaid diagram syntax
    const mermaidSyntax = generateMermaidSyntax(nodes, edges, config);
    console.log('Generated Mermaid syntax:', mermaidSyntax);
    
    // Clear and prepare container
    mermaidContainer.innerHTML = '';
    placeholder.style.display = 'none';
    mermaidContainer.style.display = 'block';
    
    // Create unique ID for this diagram
    const diagramId = 'workflow-diagram-' + Date.now();
    mermaidContainer.innerHTML = `<div id="${diagramId}" class="mermaid">${mermaidSyntax}</div>`;
    
    // Initialize Mermaid with custom config if not already done
    try {
      mermaid.initialize({
        startOnLoad: true,
        theme: 'default',
        flowchart: {
          curve: 'basis',
          nodeSpacing: 50,
          rankSpacing: 50,
          padding: 20,
          useMaxWidth: true,
          htmlLabels: true
        },
        themeVariables: {
          primaryColor: '#e3f2fd',
          primaryTextColor: '#1976d2',
          primaryBorderColor: '#1976d2',
          lineColor: '#666',
          secondaryColor: '#fff3e0',
          tertiaryColor: '#f3e5f5'
        }
      });
    } catch (initError) {
      console.log('Mermaid already initialized, continuing...');
    }
    
    // Render the diagram
    const diagramElement = document.getElementById(diagramId);
    mermaid.run({
      nodes: [diagramElement]
    }).then(() => {
      console.log('Mermaid diagram rendered successfully');
      
      // Add configuration legend
      addMermaidLegend(vizContainer, config, nodes.length, edges.length);
      
      // Add click handlers for interactivity
      addDiagramInteractivity(diagramId);
      
    }).catch((error) => {
      console.error('Mermaid rendering error:', error);
      showVisualizationError(mermaidContainer, 'Diagram rendering failed: ' + error.message);
    });
    
  } catch (error) {
    console.error('Visualization error:', error);
    showVisualizationError(mermaidContainer, error.message);
  }
}

function generateMermaidSyntax(nodes, edges, config) {
  let syntax = 'graph TD\n';
  
  // Add nodes with styling
  nodes.forEach(node => {
    const nodeId = `N${node.id}`;
    const nodeName = (node.name || node.agent || 'Node').replace(/["\n]/g, '');
    const isEntryPoint = config.entry_point === node.agent;
    const hasMessageFilter = node.message_filter && node.message_filter.enabled;
    
    // Choose node shape and styling based on type
    let nodeDefinition;
    if (isEntryPoint) {
      nodeDefinition = `${nodeId}["🚀 ${nodeName}"]:::entryPoint`;
    } else if (hasMessageFilter) {
      nodeDefinition = `${nodeId}["🔍 ${nodeName}"]:::messageFilter`;
    } else {
      nodeDefinition = `${nodeId}["🤖 ${nodeName}"]:::regularNode`;
    }
    
    syntax += `    ${nodeDefinition}\n`;
  });
  
  syntax += '\n';
  
  // Add edges with conditions and styling
  edges.forEach((edge, index) => {
    const fromId = `N${edge.from}`;
    const toId = `N${edge.to}`;
    
    let edgeDefinition = `    ${fromId}`;
    let linkText = '';
    let edgeClass = 'normalFlow';
    
    // Add condition text if present
    if (edge.condition) {
      if (typeof edge.condition === 'string') {
        linkText = edge.condition.substring(0, 15) + (edge.condition.length > 15 ? '...' : '');
      } else if (edge.condition.text) {
        linkText = edge.condition.text.substring(0, 15) + (edge.condition.text.length > 15 ? '...' : '');
      }
      edgeClass = 'conditionalFlow';
    }
    
    // Add activation group info
    if (edge.activation_group && !linkText) {
      linkText = `Group: ${edge.activation_group}`;
      edgeClass = 'activationGroup';
    } else if (edge.activation_group && linkText) {
      linkText += ` (${edge.activation_group})`;
    }
    
    // Choose arrow style and add link text
    if (linkText) {
      edgeDefinition += ` -->|"${linkText}"| ${toId}`;
    } else {
      edgeDefinition += ` --> ${toId}`;
    }
    
    syntax += `${edgeDefinition}\n`;
    
    // Add edge styling
    syntax += `    linkStyle ${index} stroke:${edgeClass === 'conditionalFlow' ? '#dc3545' : edgeClass === 'activationGroup' ? '#fd7e14' : '#6c757d'},stroke-width:2px${edgeClass === 'conditionalFlow' ? ',stroke-dasharray: 5 5' : ''}\n`;
  });
  
  syntax += '\n';
  
  // Add CSS styling
  syntax += `    classDef entryPoint fill:#d4edda,stroke:#155724,stroke-width:3px,color:#155724
    classDef messageFilter fill:#fff3cd,stroke:#856404,stroke-width:2px,color:#856404
    classDef regularNode fill:#e9ecef,stroke:#6c757d,stroke-width:2px,color:#495057
    classDef conditionalFlow stroke:#dc3545,stroke-width:2px,stroke-dasharray: 5 5
    classDef activationGroup stroke:#fd7e14,stroke-width:2px`;
  
  return syntax;
}

function addMermaidLegend(container, config, nodeCount, edgeCount) {
  // Remove existing legend
  const existingLegend = container.querySelector('.mermaid-legend');
  if (existingLegend) {
    existingLegend.remove();
  }
  
  const legend = document.createElement('div');
  legend.className = 'mermaid-legend mt-3 p-3 border rounded bg-light';
  legend.innerHTML = `
    <div class="row g-3 small">
      <div class="col-md-3">
        <strong><i class="fas fa-info-circle"></i> Elements:</strong>
        <div class="mt-1">
          <div><span class="badge bg-success me-1">🚀</span> Entry Point</div>
          <div><span class="badge bg-warning me-1">🔍</span> Message Filter</div>
          <div><span class="badge bg-secondary me-1">🤖</span> Regular Node</div>
        </div>
      </div>
      <div class="col-md-3">
        <strong><i class="fas fa-share-alt"></i> Flows:</strong>
        <div class="mt-1">
          <div><span style="color: #6c757d;">━━</span> Direct Flow</div>
          <div><span style="color: #dc3545;">┅┅</span> Conditional</div>
          <div><span style="color: #fd7e14;">━━</span> Activation Group</div>
        </div>
      </div>
      <div class="col-md-3">
        <strong><i class="fas fa-cog"></i> Configuration:</strong>
        <div class="mt-1">
          <div><strong>Entry:</strong> ${config.entry_point || 'Auto-detect'}</div>
          <div><strong>Termination:</strong> ${config.termination?.type || 'max_message'}</div>
          <div><strong>Max Messages:</strong> ${config.termination?.max_messages || 20}</div>
        </div>
      </div>
      <div class="col-md-3">
        <strong><i class="fas fa-chart-bar"></i> Statistics:</strong>
        <div class="mt-1">
          <div><strong>Nodes:</strong> ${nodeCount}</div>
          <div><strong>Edges:</strong> ${edgeCount}</div>
          <div><strong>Complexity:</strong> ${getComplexityLevel(nodeCount, edgeCount)}</div>
        </div>
      </div>
    </div>
  `;
  
  container.appendChild(legend);
}

function addDiagramInteractivity(diagramId) {
  // Add click handlers for nodes (future enhancement)
  const diagramElement = document.getElementById(diagramId);
  if (diagramElement) {
    // Add zoom and pan capabilities
    diagramElement.style.cursor = 'move';
    diagramElement.title = 'Workflow Diagram - Drag to pan, scroll to zoom';
  }
}

function showVisualizationError(container, errorMessage) {
  const placeholder = document.getElementById('vizPlaceholder');
  if (placeholder) {
    placeholder.style.display = 'block';
    placeholder.innerHTML = `
      <div class="text-center text-danger">
        <i class="fas fa-exclamation-triangle fa-3x mb-2"></i>
        <p><strong>Visualization Error</strong></p>
        <p class="small">${errorMessage}</p>
        <p class="small text-muted">Please check your workflow configuration and try again.</p>
      </div>
    `;
  }
  container.style.display = 'none';
}

function getComplexityLevel(nodeCount, edgeCount) {
  const ratio = edgeCount / Math.max(nodeCount, 1);
  if (nodeCount <= 2) return 'Simple';
  if (nodeCount <= 5 && ratio <= 1.5) return 'Medium';
  if (nodeCount <= 10 && ratio <= 2) return 'Complex';
  return 'Advanced';
}

function exportWorkflowDiagram() {
  try {
    const mermaidContainer = document.getElementById('mermaidContainer');
    const svgElement = mermaidContainer.querySelector('svg');
    
    if (!svgElement) {
      alert('No diagram to export. Please refresh the visualization first.');
      return;
    }
    
    // Get SVG data
    const svgData = new XMLSerializer().serializeToString(svgElement);
    const svgBlob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
    
    // Create download link
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(svgBlob);
    downloadLink.download = `workflow-diagram-${new Date().toISOString().slice(0,10)}.svg`;
    downloadLink.click();
    
    // Cleanup
    URL.revokeObjectURL(downloadLink.href);
    
    console.log('Workflow diagram exported successfully');
  } catch (error) {
    console.error('Export error:', error);
    alert('Failed to export diagram. Please try again.');
  }
}
