document.addEventListener('DOMContentLoaded', () => {
  const teamsList = document.getElementById('teamsList');
  const workflowsList = document.getElementById('workflowsList');
  const btnNewTeam = document.getElementById('btnNewTeam');
  const btnNewWorkflow = document.getElementById('btnNewWorkflow');
  const agentsBuilder = document.getElementById('agentsBuilder');
  const agentsList = document.getElementById('agentsList');
  const addAgentBtn = document.getElementById('addAgentBtn');

  const teamModal = new bootstrap.Modal(document.getElementById('teamModal'));
  const workflowModal = new bootstrap.Modal(document.getElementById('workflowModal'));

  function refresh() {
    fetch('/api/agent/teams').then(r=>r.json()).then(d=>{
      teamsList.innerHTML = '';
      (d.teams||[]).forEach(t=>{
        const li = document.createElement('li');
        li.className='list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `<div><strong>${t.name}</strong><div class="text-muted small">${t.description||''}</div></div>
        <div>
          <button class="btn btn-sm btn-outline-primary me-1" data-action="edit" data-id="${t.id}"><i class="fas fa-edit"></i></button>
          <button class="btn btn-sm btn-outline-danger" data-action="del" data-id="${t.id}"><i class="fas fa-trash"></i></button>
        </div>`;
        teamsList.appendChild(li);
      })
    });
    fetch('/api/agent/workflows').then(r=>r.json()).then(d=>{
      workflowsList.innerHTML = '';
      (d.workflows||[]).forEach(w=>{
        const li = document.createElement('li');
        li.className='list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `<div><strong>${w.name}</strong><div class="text-muted small">Team #${w.team_id}</div></div>
        <div>
          <button class="btn btn-sm btn-outline-primary me-1" data-action="editwf" data-id="${w.id}"><i class="fas fa-edit"></i></button>
          <button class="btn btn-sm btn-outline-success me-1" data-action="runwf" data-id="${w.id}"><i class="fas fa-play"></i></button>
          <button class="btn btn-sm btn-outline-danger" data-action="delwf" data-id="${w.id}"><i class="fas fa-trash"></i></button>
        </div>`;
        workflowsList.appendChild(li);
      })
    });
  }

  btnNewTeam.addEventListener('click', ()=>{
    document.getElementById('teamName').value = '';
    document.getElementById('teamDesc').value = '';
    document.getElementById('executionMode').value = 'roundrobin';
    document.getElementById('maxRounds').value = '6';
    document.getElementById('selectorPrompt').value = `Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
When the task is complete, let the user approve or disapprove the task.`;
    document.getElementById('allowRepeatedSpeaker').checked = true;
    toggleSelectorSettings();
    document.getElementById('teamConfig').value = JSON.stringify({
      agents: [],
      settings: {
        max_rounds: 6,
        execution_mode: "roundrobin",
        selector_prompt: "Select an agent to perform task.\n\n{roles}\n\nCurrent conversation context:\n{history}\n\nRead the above conversation, then select an agent from {participants} to perform the next task.\nWhen the task is complete, let the user approve or disapprove the task.",
        allow_repeated_speaker: true
      }
    }, null, 2);
    bootstrapAgentsBuilder([]);
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

  document.getElementById('saveTeamBtn').addEventListener('click', ()=>{
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
  });

  btnNewWorkflow.addEventListener('click', ()=>{
    currentWorkflowId = null; // Reset to create mode
    document.getElementById('wfName').value = '';
    document.getElementById('wfDesc').value = '';
    document.getElementById('wfGraph').value = '{"nodes":[],"edges":[]}';
    // populate team list
    fetch('/api/agent/teams').then(r=>r.json()).then(d=>{
      const sel = document.getElementById('wfTeam');
      sel.innerHTML = '';
      (d.teams||[]).forEach(t=>{
        const opt = document.createElement('option');
        opt.value = t.id; opt.textContent = `${t.name}`; sel.appendChild(opt);
      });
      workflowModal.show();
    })
  });

  // Global variable to track workflow editing state
  let currentWorkflowId = null;

  document.getElementById('saveWorkflowBtn').addEventListener('click', ()=>{
    const name = document.getElementById('wfName').value.trim();
    const description = document.getElementById('wfDesc').value.trim();
    const team_id = parseInt(document.getElementById('wfTeam').value, 10);
    const graphText = document.getElementById('wfGraph').value;
    let graph = {};
    try { graph = JSON.parse(graphText); } catch(e) { alert('Invalid Graph JSON'); return; }
    
    if (currentWorkflowId) {
      // Update existing workflow
      fetch(`/api/agent/workflows/${currentWorkflowId}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, team_id, graph})})
        .then(r=>r.json()).then(()=>{ workflowModal.hide(); refresh(); currentWorkflowId = null; });
    } else {
      // Create new workflow
      fetch('/api/agent/workflows', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, team_id, graph})})
        .then(r=>r.json()).then(()=>{ workflowModal.hide(); refresh(); });
    }
  });

  teamsList.addEventListener('click', (e)=>{
    const btn = e.target.closest('button[data-action]'); if(!btn) return;
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-action');
    if(action==='del'){
      if(confirm('Delete team?')) fetch(`/api/agent/teams/${id}`, {method:'DELETE'}).then(()=>refresh());
    }
    if(action==='edit'){
      fetch(`/api/agent/teams/${id}`).then(r=>r.json()).then(t=>{
        document.getElementById('teamName').value = t.name;
        document.getElementById('teamDesc').value = t.description||'';
        document.getElementById('teamConfig').value = JSON.stringify(t.config||{}, null, 2);
        
        // Load settings from config
        const settings = (t.config && t.config.settings) || {};
        document.getElementById('executionMode').value = settings.execution_mode || 'roundrobin';
        document.getElementById('maxRounds').value = settings.max_rounds || 6;
        document.getElementById('selectorPrompt').value = settings.selector_prompt || `Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
When the task is complete, let the user approve or disapprove the task.`;
        document.getElementById('allowRepeatedSpeaker').checked = settings.allow_repeated_speaker !== false;
        toggleSelectorSettings();
        
        // Load agents after servers are loaded
        loadServersAndTools().then(() => {
          bootstrapAgentsBuilder((t.config&&t.config.agents)||[]);
        });
        
        teamModal.show();
        document.getElementById('saveTeamBtn').onclick = ()=>{
          const name = document.getElementById('teamName').value.trim();
          const description = document.getElementById('teamDesc').value.trim();
          
          // Always sync builder and settings to JSON before parsing
          syncBuilderToJson();
          syncSettingsToJson();
          
          let config={}; 
          try {
            config=JSON.parse(document.getElementById('teamConfig').value);
          } catch(e) {
            alert('Invalid JSON config. Please fix the JSON or use the visual builder.');
            return;
          }
          
          fetch(`/api/agent/teams/${id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description, config})})
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
        }
      })
    }
  })

  workflowsList.addEventListener('click', (e)=>{
    const btn = e.target.closest('button[data-action]'); if(!btn) return;
    const id = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-action');
    if(action==='delwf'){
      if(confirm('Delete workflow?')) fetch(`/api/agent/workflows/${id}`, {method:'DELETE'}).then(()=>refresh());
    }
    if(action==='editwf'){
      fetch(`/api/agent/workflows/${id}`).then(r=>r.json()).then(w=>{
        currentWorkflowId = parseInt(id); // Set to edit mode
        document.getElementById('wfName').value = w.name;
        document.getElementById('wfDesc').value = w.description||'';
        document.getElementById('wfGraph').value = JSON.stringify(w.graph||{}, null, 2);
        fetch('/api/agent/teams').then(r=>r.json()).then(d=>{
          const sel = document.getElementById('wfTeam'); sel.innerHTML='';
          (d.teams||[]).forEach(t=>{
            const opt = document.createElement('option'); opt.value=t.id; opt.textContent=t.name; if(t.id===w.team_id) opt.selected=true; sel.appendChild(opt);
          });
          workflowModal.show();
          // No need for onclick handler anymore - the main event listener handles it
        })
      })
    }
    if(action==='runwf'){
      const task = prompt('Enter task/input to run:');
      if(!task) return;
      fetch(`/api/agent/run/workflow/${id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task})})
        .then(r=>r.json()).then(res=>{
          if(res.success){
            alert(res.reply || 'Done');
          } else {
            try {
              const modal = new bootstrap.Modal(document.getElementById('agentErrorModal'));
              document.getElementById('agentErrorMessage').textContent = res.error || 'Unknown error';
              document.getElementById('agentErrorTrace').textContent = res.trace || '';
              modal.show();
              document.getElementById('copyAgentErrorTrace').onclick = ()=>{
                const txt = document.getElementById('agentErrorTrace').textContent || '';
                navigator.clipboard?.writeText(txt);
              }
            } catch (e) {
              alert((res.error||'Error') + (res.trace? `\n\n${res.trace}`:''));
            }
          }
        })
    }
  })

  refresh();

  // --- Workflow Builder ---
  const nodesList = document.getElementById('nodesList');
  const addNodeBtn = document.getElementById('addNodeBtn');
  const nodeName = document.getElementById('nodeName');
  const nodeAgent = document.getElementById('nodeAgent');
  const nodePrev = document.getElementById('nodePrev');
  const nodeNext = document.getElementById('nodeNext');
  const saveNodeBtn = document.getElementById('saveNodeBtn');
  const removeNodeBtn = document.getElementById('removeNodeBtn');

  function parseGraph(){ try{ return JSON.parse(document.getElementById('wfGraph').value||'{}'); }catch{ return {nodes:[], edges:[]}; } }
  function writeGraph(g){ document.getElementById('wfGraph').value = JSON.stringify(g, null, 2); }
  function refreshNodeSelectors(g){
    // populate agent list from selected team
    nodeAgent.innerHTML='';
    try{
      const teamId = parseInt(document.getElementById('wfTeam').value,10);
      fetch(`/api/agent/teams/${teamId}`).then(r=>r.json()).then(t=>{
        (t.config?.agents||[]).forEach(a=>{
          const opt=document.createElement('option'); opt.value=a.name; opt.textContent=a.name; nodeAgent.appendChild(opt);
        })
      })
    }catch{}
    // nodes
    nodePrev.innerHTML=''; nodeNext.innerHTML='';
    const none=document.createElement('option'); none.value=''; none.textContent='None'; nodePrev.appendChild(none.cloneNode(true)); nodeNext.appendChild(none.cloneNode(true));
    (g.nodes||[]).forEach(n=>{
      const opt1=document.createElement('option'); opt1.value=n.id; opt1.textContent=n.name; nodePrev.appendChild(opt1);
      const opt2=document.createElement('option'); opt2.value=n.id; opt2.textContent=n.name; nodeNext.appendChild(opt2);
    })
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
      nodePrev.value=''; 
      nodeNext.value=''; 
      return; 
    }
    
    nodeName.value = n.name || ''; 
    nodeAgent.value = n.agent || '';
    
    // find predecessors/successors via edges
    const preds=(g.edges||[]).filter(e=>String(e.to)===String(id)).map(e=>String(e.from));
    const succs=(g.edges||[]).filter(e=>String(e.from)===String(id)).map(e=>String(e.to));
    nodePrev.value=preds[0]||''; 
    nodeNext.value=succs[0]||'';
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
    const id = nodesList.value; 
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
    
    // rebuild edges to reflect prev/next single selections
    g.edges=(g.edges||[]).filter(e=>String(e.from)!==String(id) && String(e.to)!==String(id));
    if(nodePrev.value) g.edges.push({from: Number(nodePrev.value), to: Number(id)});
    if(nodeNext.value) g.edges.push({from: Number(id), to: Number(nodeNext.value)});
    
    writeGraph(g); 
    refreshNodesList(g); 
    refreshNodeSelectors(g); 
    selectNode(g, id);
    
    // Show success message
    console.log('Node saved successfully. New graph:', g);
    alert(`Node "${newName}" saved successfully!`);
  })
  removeNodeBtn?.addEventListener('click', ()=>{
    const g=parseGraph(); const id=nodesList.value; if(!id) return;
    g.nodes=(g.nodes||[]).filter(x=>String(x.id)!==String(id));
    g.edges=(g.edges||[]).filter(e=>String(e.from)!==String(id) && String(e.to)!==String(id));
    writeGraph(g); refreshNodesList(g); refreshNodeSelectors(g);
    nodeName.value=''; nodeAgent.value=''; nodePrev.value=''; nodeNext.value='';
  })

  // --- Agents Builder ---
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
    const row = document.createElement('div'); row.className='border rounded p-2 mb-2';
    
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
          <input class="form-control form-control-sm agent-desc" value="${(agent?.description||'').replace(/"/g, '&quot;')}" placeholder="Brief description of agent role">
        </div>
        <div class="col-md-${showAgentType ? '2' : '3'}">
          <label class="form-label small">System Prompt</label>
          <input class="form-control form-control-sm agent-prompt" value="${(agent?.system_prompt||'').replace(/"/g, '&quot;')}">
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
    assignedSpan.textContent = assigned.map(x=>`#${x.server_id}:${x.tool_name}`).join(', ');
    
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
      
      // Update display
      assignedSpan.textContent = row.agentData.tools.map(x=>`#${x.server_id}:${x.tool_name}`).join(', ');
      
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
        document.getElementById('selectorPrompt').value = settings.selector_prompt || `Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
When the task is complete, let the user approve or disapprove the task.`;
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
