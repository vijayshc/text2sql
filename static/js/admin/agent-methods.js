document.addEventListener('DOMContentLoaded', () => {
  const methodsList = document.getElementById('methodsList');
  const btnNewMethod = document.getElementById('btnNewMethod');
  let editingId = null; // null => create, number => edit existing

  if (!methodsList || !btnNewMethod) return; // Only on that page

  const methodModal = new bootstrap.Modal(document.getElementById('methodModal'));

  function loadTeamsIntoSelect(selectEl) {
    return fetch('/api/agent/teams').then(r=>r.json()).then(d=>{
      selectEl.innerHTML = '';
      (d.teams||[]).forEach(t=>{
        const opt = document.createElement('option');
        opt.value = t.id; opt.textContent = t.name; selectEl.appendChild(opt);
      });
    });
  }

  function refreshMethods(){
    fetch('/api/agent/methods').then(r=>r.json()).then(d=>{
      methodsList.innerHTML = '';
      (d.methods||[]).forEach(m => {
        const li = document.createElement('li');
        li.className='list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `<div><strong>${m.name}</strong> <span class="badge bg-secondary text-uppercase ms-1">${m.type}</span><div class="text-muted small">Team #${m.team_id}${m.description? ' · '+m.description:''}</div></div>
        <div>
          <button class="btn btn-sm btn-outline-primary me-1" data-action="edit" data-id="${m.id}"><i class="fas fa-edit"></i></button>
          <button class="btn btn-sm btn-outline-success me-1" data-action="run" data-id="${m.id}"><i class="fas fa-play"></i></button>
          <button class="btn btn-sm btn-outline-danger" data-action="del" data-id="${m.id}"><i class="fas fa-trash"></i></button>
        </div>`;
        methodsList.appendChild(li);
      })
    })
  }

  btnNewMethod.addEventListener('click', ()=>{
    document.getElementById('methodName').value = '';
    document.getElementById('methodDesc').value = '';
    document.getElementById('methodType').value = 'reflection';
    document.getElementById('methodConfig').value = JSON.stringify({max_rounds:4}, null, 2);
    editingId = null;
    loadTeamsIntoSelect(document.getElementById('methodTeam')).then(()=>{
      methodModal.show();
    })
  })

  document.getElementById('saveMethodBtn').addEventListener('click', ()=>{
    const name = document.getElementById('methodName').value.trim();
    const description = document.getElementById('methodDesc').value.trim();
    const type = document.getElementById('methodType').value;
    const team_id = parseInt(document.getElementById('methodTeam').value, 10);
    let config = {};
    try { config = JSON.parse(document.getElementById('methodConfig').value); } catch(e){ alert('Invalid config JSON'); return; }
    const payload = {name, description, type, team_id, config};
    if(editingId === null){
      fetch('/api/agent/methods', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
        .then(r=>r.json()).then(res=>{
          if(res.error){ alert(res.error); return; }
          methodModal.hide(); refreshMethods();
        })
    } else {
      fetch(`/api/agent/methods/${editingId}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
        .then(r=>r.json()).then(res=>{
          if(res.error){ alert(res.error); return; }
          methodModal.hide(); editingId = null; refreshMethods();
        })
    }
  })

  methodsList.addEventListener('click', (e)=>{
    const btn = e.target.closest('button[data-action]'); if(!btn) return;
    const id = parseInt(btn.getAttribute('data-id'),10);
    const action = btn.getAttribute('data-action');
    if(action==='del'){
      if(confirm('Delete method?')) fetch(`/api/agent/methods/${id}`, {method:'DELETE'}).then(()=>refreshMethods());
    }
    if(action==='edit'){
      fetch(`/api/agent/methods/${id}`).then(r=>r.json()).then(m=>{
        document.getElementById('methodName').value = m.name;
        document.getElementById('methodDesc').value = m.description||'';
        document.getElementById('methodType').value = m.type;
        document.getElementById('methodConfig').value = JSON.stringify(m.config||{}, null, 2);
        loadTeamsIntoSelect(document.getElementById('methodTeam')).then(()=>{
          const sel = document.getElementById('methodTeam');
          Array.from(sel.options).forEach(o=>{ o.selected = String(o.value)===String(m.team_id); });
          methodModal.show();
        })
        editingId = id;
      })
    }
    if(action==='run'){
      const task = prompt('Enter input to run:'); if(!task) return;
      fetch(`/api/agent/run/method/${id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task})})
        .then(r=>r.json()).then(res=>{
          if(res.success){ alert(res.reply || 'Done'); }
          else{ alert('Error: ' + (res.error||'unknown')); }
        })
    }
  })

  refreshMethods();
});
