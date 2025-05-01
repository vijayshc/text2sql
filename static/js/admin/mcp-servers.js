document.addEventListener('DOMContentLoaded', function() {
    // Load servers on page load
    loadServers();
    
    // Setup event listeners
    document.getElementById('addServerBtn').addEventListener('click', showAddServerModal);
    document.getElementById('saveServerBtn').addEventListener('click', saveServer);
    document.getElementById('confirmDeleteBtn').addEventListener('click', deleteServer);
    document.getElementById('serverType').addEventListener('change', toggleServerConfig);
});

// Server operations
function loadServers() {
    fetch('/api/admin/mcp-servers', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayServers(data.servers);
        } else {
            showAlert('danger', 'Failed to load servers: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error loading servers:', error);
        showAlert('danger', 'Error loading servers. Please try again.');
    });
}

function displayServers(servers) {
    const tableBody = document.querySelector('#serversTable tbody');
    const noServersMsg = document.getElementById('noServers');
    
    // Destroy existing DataTable if it exists
    if ($.fn.DataTable.isDataTable('#serversTable')) {
        $('#serversTable').DataTable().destroy();
    }
    
    tableBody.innerHTML = '';
    
    if (servers.length === 0) {
        noServersMsg.classList.remove('d-none');
        // Initialize empty DataTable
        $('#serversTable').DataTable({
            responsive: true,
            language: {
                emptyTable: "No MCP servers have been configured"
            }
        });
        return;
    }
    
    noServersMsg.classList.add('d-none');
    
    // Add rows to the table
    servers.forEach(server => {
        const row = document.createElement('tr');
        row.dataset.serverId = server.id;
        
        const statusClass = getStatusClass(server.status);
        const statusText = capitalizeFirstLetter(server.status);
        
        row.innerHTML = `
            <td>${server.name}</td>
            <td>${capitalizeFirstLetter(server.server_type)}</td>
            <td>${server.description || '—'}</td>
            <td>
                <span class="server-status ${statusClass}"></span>
                ${statusText}
            </td>
            <td>
                <div class="server-actions">
                    ${server.status === 'stopped' ? 
                        `<button class="btn btn-sm btn-success start-server" title="Start Server">
                            <i class="fas fa-play"></i>
                        </button>` : 
                        server.status === 'running' ? 
                        `<button class="btn btn-sm btn-secondary stop-server" title="Stop Server">
                            <i class="fas fa-stop"></i>
                        </button>` :
                        `<button class="btn btn-sm btn-warning restart-server" title="Restart Server">
                            <i class="fas fa-sync"></i>
                        </button>`
                    }
                    <button class="btn btn-sm btn-info view-tools" title="View Tools">
                        <i class="fas fa-tools"></i>
                    </button>
                    <button class="btn btn-sm btn-primary edit-server" title="Edit Server">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger delete-server" title="Delete Server">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Initialize DataTable
    const dataTable = $('#serversTable').DataTable({
        responsive: true,
        order: [[0, 'asc']], // Sort by name by default
        language: {
            emptyTable: "No MCP servers have been configured"
        }
    });
    
    // Add event listeners after DataTable initialization
    servers.forEach(server => {
        const row = tableBody.querySelector(`tr[data-server-id="${server.id}"]`);
        
        // Add event listeners to buttons
        const startBtn = row.querySelector('.start-server');
        if (startBtn) {
            startBtn.addEventListener('click', () => startServer(server.id));
        }
        
        const stopBtn = row.querySelector('.stop-server');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => stopServer(server.id));
        }
        
        const restartBtn = row.querySelector('.restart-server');
        if (restartBtn) {
            restartBtn.addEventListener('click', () => restartServer(server.id));
        }
        
        const toolsBtn = row.querySelector('.view-tools');
        toolsBtn.addEventListener('click', () => viewServerTools(server.id, server.name));
        
        const editBtn = row.querySelector('.edit-server');
        editBtn.addEventListener('click', () => showEditServerModal(server));
        
        const deleteBtn = row.querySelector('.delete-server');
        deleteBtn.addEventListener('click', () => showDeleteServerModal(server.id, server.name));
    });
}

function showAddServerModal() {
    // Reset form
    document.getElementById('serverForm').reset();
    document.getElementById('serverId').value = '';
    document.getElementById('serverModalTitle').textContent = 'Add MCP Server';
    
    // Show stdio config by default
    document.getElementById('stdioConfig').classList.remove('d-none');
    document.getElementById('httpConfig').classList.add('d-none');
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('serverModal'));
    modal.show();
}

function showEditServerModal(server) {
    // Fill form with server data
    document.getElementById('serverId').value = server.id;
    document.getElementById('serverName').value = server.name;
    document.getElementById('serverDescription').value = server.description || '';
    document.getElementById('serverType').value = server.server_type;
    
    // Update title
    document.getElementById('serverModalTitle').textContent = 'Edit MCP Server';
    
    // Handle configuration based on server type
    if (server.server_type === 'stdio') {
        document.getElementById('stdioConfig').classList.remove('d-none');
        document.getElementById('httpConfig').classList.add('d-none');
        
        // Fill stdio config
        document.getElementById('stdioCommand').value = server.config.command || '';
        document.getElementById('stdioArgs').value = server.config.args ? server.config.args.join(' ') : '';
        
        // Handle env vars
        if (server.config.env) {
            const envLines = [];
            for (const [key, value] of Object.entries(server.config.env)) {
                envLines.push(`${key}=${value}`);
            }
            document.getElementById('stdioEnv').value = envLines.join('\n');
        } else {
            document.getElementById('stdioEnv').value = '';
        }
    } else {
        document.getElementById('stdioConfig').classList.add('d-none');
        document.getElementById('httpConfig').classList.remove('d-none');
        
        // Fill HTTP config
        document.getElementById('httpBaseUrl').value = server.config.base_url || '';
        
        // Handle headers
        if (server.config.headers) {
            const headerLines = [];
            for (const [key, value] of Object.entries(server.config.headers)) {
                headerLines.push(`${key}: ${value}`);
            }
            document.getElementById('httpHeaders').value = headerLines.join('\n');
        } else {
            document.getElementById('httpHeaders').value = '';
        }
    }
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('serverModal'));
    modal.show();
}

function toggleServerConfig() {
    const serverType = document.getElementById('serverType').value;
    
    if (serverType === 'stdio') {
        document.getElementById('stdioConfig').classList.remove('d-none');
        document.getElementById('httpConfig').classList.add('d-none');
    } else {
        document.getElementById('stdioConfig').classList.add('d-none');
        document.getElementById('httpConfig').classList.remove('d-none');
    }
}

function saveServer() {
    // Basic validation
    const serverName = document.getElementById('serverName').value.trim();
    const serverType = document.getElementById('serverType').value;
    
    if (!serverName) {
        showAlert('danger', 'Server name is required');
        return;
    }
    
    const serverId = document.getElementById('serverId').value;
    const isNew = !serverId;
    
    // Prepare data object
    const serverData = {
        name: serverName,
        description: document.getElementById('serverDescription').value.trim(),
        server_type: serverType,
        config: {}
    };
    
    // Add type-specific configuration
    if (serverType === 'stdio') {
        const command = document.getElementById('stdioCommand').value.trim();
        if (!command) {
            showAlert('danger', 'Command is required for STDIO servers');
            return;
        }
        
        serverData.config.command = command;
        
        // Parse arguments
        const argsStr = document.getElementById('stdioArgs').value.trim();
        if (argsStr) {
            serverData.config.args = argsStr.split(' ').filter(arg => arg.trim() !== '');
        }
        
        // Parse environment variables
        const envStr = document.getElementById('stdioEnv').value.trim();
        if (envStr) {
            const env = {};
            envStr.split('\n').forEach(line => {
                const match = line.match(/^([^=]+)=(.*)$/);
                if (match) {
                    env[match[1].trim()] = match[2].trim();
                }
            });
            serverData.config.env = env;
        }
    } else {
        const baseUrl = document.getElementById('httpBaseUrl').value.trim();
        if (!baseUrl) {
            showAlert('danger', 'Base URL is required for HTTP servers');
            return;
        }
        
        serverData.config.base_url = baseUrl;
        
        // Parse headers
        const headersStr = document.getElementById('httpHeaders').value.trim();
        if (headersStr) {
            const headers = {};
            headersStr.split('\n').forEach(line => {
                const match = line.match(/^([^:]+):\s*(.*)$/);
                if (match) {
                    headers[match[1].trim()] = match[2].trim();
                }
            });
            serverData.config.headers = headers;
        }
    }
    
    // Send request to server
    const url = isNew 
        ? '/api/admin/mcp-servers' 
        : `/api/admin/mcp-servers/${serverId}`;
    
    fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify(serverData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('serverModal')).hide();
            
            // Show success message
            showAlert('success', isNew 
                ? 'Server added successfully' 
                : 'Server updated successfully');
            
            // Reload servers
            loadServers();
        } else {
            showAlert('danger', 'Failed to save server: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error saving server:', error);
        showAlert('danger', 'Error saving server. Please try again.');
    });
}

function showDeleteServerModal(serverId, serverName) {
    // Update modal content
    document.getElementById('deleteServerName').textContent = serverName;
    
    // Store server ID for delete confirmation
    document.getElementById('confirmDeleteBtn').dataset.serverId = serverId;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('deleteServerModal'));
    modal.show();
}

function deleteServer() {
    const serverId = document.getElementById('confirmDeleteBtn').dataset.serverId;
    
    fetch(`/api/admin/mcp-servers/${serverId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        // Hide modal
        bootstrap.Modal.getInstance(document.getElementById('deleteServerModal')).hide();
        
        if (data.success) {
            // Show success message
            showAlert('success', data.message);
            
            // Reload servers to update DataTable
            loadServers();
        } else {
            showAlert('danger', 'Failed to delete server: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error deleting server:', error);
        showAlert('danger', 'Error deleting server. Please try again.');
    });
}

function startServer(serverId) {
    changeServerStatus(serverId, 'start');
}

function stopServer(serverId) {
    changeServerStatus(serverId, 'stop');
}

function restartServer(serverId) {
    changeServerStatus(serverId, 'restart');
}

function changeServerStatus(serverId, action) {
    // Show loading state for this specific row
    const dataTable = $('#serversTable').DataTable();
    const row = document.querySelector(`tr[data-server-id="${serverId}"]`);
    const actionCell = row.querySelector('td:last-child');
    const originalContent = actionCell.innerHTML;
    actionCell.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    fetch(`/api/admin/mcp-servers/${serverId}/${action}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showAlert('success', data.message);
            
            // Reload servers
            loadServers();
        } else {
            // Restore original action buttons
            actionCell.innerHTML = originalContent;
            
            // Show error
            showAlert('danger', 'Failed to ' + action + ' server: ' + data.error);
        }
    })
    .catch(error => {
        // Restore original action buttons
        actionCell.innerHTML = originalContent;
        
        console.error(`Error ${action}ing server:`, error);
        showAlert('danger', `Error ${action}ing server. Please try again.`);
    });
}

function viewServerTools(serverId, serverName) {
    // Update modal title
    document.getElementById('toolsModalTitle').textContent = `Tools for ${serverName}`;
    
    // Reset modal content
    document.getElementById('toolsList').innerHTML = '';
    document.getElementById('noTools').classList.add('d-none');
    document.getElementById('toolsError').classList.add('d-none');
    
    // Show loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'text-center p-4';
    loadingIndicator.innerHTML = `
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2">Loading tools...</p>
    `;
    document.getElementById('toolsList').appendChild(loadingIndicator);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('toolsModal'));
    modal.show();
    
    // Fetch tools
    fetch(`/api/admin/mcp-servers/${serverId}/tools`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        // Remove loading indicator
        document.getElementById('toolsList').innerHTML = '';
        
        if (data.success && data.tools && data.tools.length > 0) {
            // Display tools
            data.tools.forEach(tool => {
                const toolItem = document.createElement('div');
                toolItem.className = 'tool-item p-3 mb-3';
                
                // Format tool function
                const func = tool.function;
                
                let parametersHtml = '';
                if (func.parameters && Object.keys(func.parameters).length > 0) {
                    parametersHtml = `
                        <div class="parameter-title">Parameters:</div>
                        <pre class="parameter-schema">${JSON.stringify(func.parameters, null, 2)}</pre>
                    `;
                }
                
                toolItem.innerHTML = `
                    <div class="tool-name">${func.name}</div>
                    <div class="tool-description">${func.description || 'No description'}</div>
                    ${parametersHtml}
                `;
                
                document.getElementById('toolsList').appendChild(toolItem);
            });
        } else if (data.success) {
            // No tools found
            document.getElementById('noTools').classList.remove('d-none');
        } else {
            // Error
            document.getElementById('toolsError').textContent = 'Error: ' + data.error;
            document.getElementById('toolsError').classList.remove('d-none');
        }
    })
    .catch(error => {
        // Remove loading indicator
        document.getElementById('toolsList').innerHTML = '';
        
        console.error('Error fetching tools:', error);
        document.getElementById('toolsError').textContent = 'Error fetching tools. Please try again.';
        document.getElementById('toolsError').classList.remove('d-none');
    });
}

// Utility functions
function initMcpServerAdmin() {
    loadServers();
    document.getElementById('addServerBtn').addEventListener('click', showAddServerModal);
    document.getElementById('saveServerBtn').addEventListener('click', saveServer);
    document.getElementById('confirmDeleteBtn').addEventListener('click', deleteServer);
    document.getElementById('serverType').addEventListener('change', toggleServerConfig);
    
    // Initialize empty DataTable until data is loaded
    $('#serversTable').DataTable({
        responsive: true,
        language: {
            emptyTable: "Loading MCP servers..."
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMcpServerAdmin);
} else {
    initMcpServerAdmin();
}

// Utility functions
function showAlert(type, message) {
    const container = document.querySelector('.main-content') || document.querySelector('.container') || document.body;
    const alertEl = document.createElement('div');
    alertEl.className = `alert alert-${type} alert-dismissible fade show`;
    alertEl.setAttribute('role', 'alert');
    alertEl.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    container.insertBefore(alertEl, container.firstChild);
    setTimeout(() => {
        bootstrap.Alert.getOrCreateInstance(alertEl).close();
    }, 5000);
}

function getStatusClass(status) {
    switch (status) {
        case 'running':
            return 'status-running';
        case 'stopped':
            return 'status-stopped';
        case 'error':
            return 'status-error';
        default:
            return 'status-stopped';
    }
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}
