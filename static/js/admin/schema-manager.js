/**
 * schema-manager.js - Admin schema management functionality
 */

const schemaAdmin = {
    // Store current state
    currentWorkspace: null,
    currentTable: null,
    allTables: [],
    editingWorkspace: undefined,
    
    // Initialize schema management functionality
    init: function() {
        // Initialize modals
        this.workspaceModal = new bootstrap.Modal(document.getElementById('workspaceModal'));
        this.tableModal = new bootstrap.Modal(document.getElementById('tableModal'));
        this.columnModal = new bootstrap.Modal(document.getElementById('columnModal'));
        this.joinModal = new bootstrap.Modal(document.getElementById('joinModal'));
        this.importExportModal = new bootstrap.Modal(document.getElementById('importExportModal'));
        this.confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load initial data
        this.loadWorkspaces();
        this.loadJoinConditions();
    },
    
    // Setup event listeners for buttons and forms
    setupEventListeners: function() {
        // Workspace actions
        document.getElementById('addWorkspaceBtn').addEventListener('click', () => this.showWorkspaceModal());
        document.getElementById('saveWorkspaceBtn').addEventListener('click', () => this.saveWorkspace());
        
        // Table actions
        document.getElementById('addTableBtn').addEventListener('click', () => this.showTableModal());
        document.getElementById('saveTableBtn').addEventListener('click', () => this.saveTable());
        
        // Column actions
        document.getElementById('saveColumnBtn').addEventListener('click', () => this.saveColumn());
        
        // Join actions
        document.getElementById('addJoinBtn').addEventListener('click', () => this.showJoinModal());
        document.getElementById('saveJoinBtn').addEventListener('click', () => this.saveJoinCondition());
        
        // Import/Export actions
        document.getElementById('importSchemaBtn').addEventListener('click', () => this.showImportModal('schema'));
        document.getElementById('exportSchemaBtn').addEventListener('click', () => this.showExportModal('schema'));
        document.getElementById('importJoinsBtn').addEventListener('click', () => this.showImportModal('joins'));
        document.getElementById('exportJoinsBtn').addEventListener('click', () => this.showExportModal('joins'));
        document.getElementById('importExportSaveBtn').addEventListener('click', () => this.handleImportExportSave());
        
        // Reload action
        document.getElementById('reloadSchemaBtn').addEventListener('click', () => this.reloadSchemaFromFiles());
        
        // Delete confirmation
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => {
            if (this.deleteCallback) {
                this.deleteCallback();
                this.confirmDeleteModal.hide();
            }
        });
    },
    
    // Load workspaces from API
    loadWorkspaces: function() {
        fetch('/admin/api/schema/workspaces')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.renderWorkspacesList(data.workspaces);
                } else {
                    uiUtils.showError(data.error || 'Failed to load workspaces');
                }
            })
            .catch(error => {
                console.error('Error loading workspaces:', error);
                uiUtils.showError('Error loading workspaces. See console for details.');
            });
    },
    
    // Render workspaces list in sidebar
    renderWorkspacesList: function(workspaces) {
        const workspacesList = document.getElementById('workspacesList');
        workspacesList.innerHTML = '';
        
        if (workspaces.length === 0) {
            workspacesList.innerHTML = `
                <div class="list-group-item text-center text-muted">
                    No workspaces defined
                </div>
            `;
            return;
        }
        
        workspaces.forEach(workspace => {
            const item = document.createElement('a');
            item.href = '#';
            item.classList.add('list-group-item', 'list-group-item-action', 'd-flex', 'justify-content-between', 'align-items-center');
            
            if (this.currentWorkspace && this.currentWorkspace.name === workspace.name) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div>
                    <div><strong>${workspace.name}</strong></div>
                    <div class="small text-muted">${workspace.description || 'No description'}</div>
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary edit-workspace-btn" title="Edit Workspace">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger delete-workspace-btn" title="Delete Workspace">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            // Add event listener for selecting workspace
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.btn')) {
                    this.selectWorkspace(workspace.name);
                }
            });
            
            // Add event listeners for edit and delete buttons
            const editBtn = item.querySelector('.edit-workspace-btn');
            const deleteBtn = item.querySelector('.delete-workspace-btn');
            
            editBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.showWorkspaceModal(workspace.name);
            });
            
            deleteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.confirmDelete(
                    `Are you sure you want to delete workspace "${workspace.name}"? This will delete all tables within the workspace.`,
                    () => this.deleteWorkspace(workspace.name)
                );
            });
            
            workspacesList.appendChild(item);
        });
    },
    
    // Select a workspace and load its details
    selectWorkspace: function(workspaceName) {
        fetch(`/admin/api/schema/workspaces/${encodeURIComponent(workspaceName)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.currentWorkspace = data.workspace;
                    this.currentTable = null;
                    
                    // Update UI to indicate selected workspace
                    const workspaceItems = document.querySelectorAll('#workspacesList .list-group-item');
                    workspaceItems.forEach(item => {
                        item.classList.remove('active');
                        if (item.querySelector('strong').textContent === workspaceName) {
                            item.classList.add('active');
                        }
                    });
                    
                    // Enable Add Table button
                    document.getElementById('addTableBtn').disabled = false;
                    
                    // Render the workspace details and tables
                    this.renderWorkspaceDetails(data.workspace);
                    this.renderTablesList(data.workspace.tables || []);
                } else {
                    uiUtils.showError(data.error || `Failed to load workspace "${workspaceName}"`);
                }
            })
            .catch(error => {
                console.error('Error selecting workspace:', error);
                uiUtils.showError('Error selecting workspace. See console for details.');
            });
    },
    
    // Render workspace details in the detail panel
    renderWorkspaceDetails: function(workspace) {
        const detailHeader = document.getElementById('detailHeader');
        const detailContent = document.getElementById('detailContent');
        
        detailHeader.textContent = `Workspace: ${workspace.name}`;
        
        detailContent.innerHTML = `
            <div class="mb-3">
                <h5>Description</h5>
                <p>${workspace.description || 'No description'}</p>
            </div>
            <div>
                <h5>Statistics</h5>
                <p>${workspace.tables ? workspace.tables.length : 0} tables defined</p>
            </div>
            <div class="mt-3">
                <button class="btn btn-outline-primary me-2 edit-workspace-btn">
                    <i class="fas fa-edit"></i> Edit Workspace
                </button>
                <button class="btn btn-outline-danger delete-workspace-btn">
                    <i class="fas fa-trash"></i> Delete Workspace
                </button>
            </div>
        `;
        
        // Add event listeners to the buttons
        detailContent.querySelector('.edit-workspace-btn').addEventListener('click', () => {
            this.showWorkspaceModal(workspace.name);
        });
        
        detailContent.querySelector('.delete-workspace-btn').addEventListener('click', () => {
            this.confirmDelete(
                `Are you sure you want to delete workspace "${workspace.name}"? This will delete all tables within the workspace.`,
                () => this.deleteWorkspace(workspace.name)
            );
        });
    },
    
    // Render tables list for the selected workspace
    renderTablesList: function(tables) {
        const tablesList = document.getElementById('tablesList');
        tablesList.innerHTML = '';
        
        if (!tables || tables.length === 0) {
            tablesList.innerHTML = `
                <div class="list-group-item text-center text-muted">
                    No tables defined in this workspace
                </div>
            `;
            return;
        }
        
        tables.forEach(table => {
            const item = document.createElement('a');
            item.href = '#';
            item.classList.add('list-group-item', 'list-group-item-action', 'd-flex', 'justify-content-between', 'align-items-center');
            
            if (this.currentTable && this.currentTable.name === table.name) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div>
                    <div><strong>${table.name}</strong></div>
                    <div class="small text-muted">${table.columns ? table.columns.length : 0} columns</div>
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary edit-table-btn" title="Edit Table">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger delete-table-btn" title="Delete Table">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            // Add event listener for selecting table
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.btn')) {
                    this.selectTable(table);
                }
            });
            
            // Add event listeners for edit and delete buttons
            const editBtn = item.querySelector('.edit-table-btn');
            const deleteBtn = item.querySelector('.delete-table-btn');
            
            editBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.showTableModal(table);
            });
            
            deleteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.confirmDelete(
                    `Are you sure you want to delete table "${table.name}"?`,
                    () => this.deleteTable(table.name)
                );
            });
            
            tablesList.appendChild(item);
        });
    },
    
    // Select a table and show its details
    selectTable: function(table) {
        this.currentTable = table;
        
        // Update UI to indicate selected table
        const tableItems = document.querySelectorAll('#tablesList .list-group-item');
        tableItems.forEach(item => {
            item.classList.remove('active');
            if (item.querySelector('strong').textContent === table.name) {
                item.classList.add('active');
            }
        });
        
        // Render the table details
        this.renderTableDetails(table);
    },
    
    // Render table details in the detail panel
    renderTableDetails: function(table) {
        const detailHeader = document.getElementById('detailHeader');
        const detailContent = document.getElementById('detailContent');
        
        detailHeader.textContent = `Table: ${table.name}`;
        
        // Extract primary key columns for easier reference
        const primaryKeys = (table.columns || [])
            .filter(col => col.is_primary_key)
            .map(col => col.name);
            
        let columnsHtml = '';
        if (!table.columns || table.columns.length === 0) {
            columnsHtml = `<p class="text-center text-muted">No columns defined for this table</p>`;
        } else {
            columnsHtml = `
                <table class="table table-striped table-hover">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Description</th>
                            <th>PK</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${table.columns.map((column, index) => `
                            <tr>
                                <td>${column.name}</td>
                                <td>${column.datatype}</td>
                                <td>${column.description || ''}</td>
                                <td>${column.is_primary_key ? '<i class="fas fa-key"></i>' : ''}</td>
                                <td class="text-end">
                                    <div class="btn-group btn-group-sm">
                                        <button class="btn btn-outline-secondary edit-column-btn" data-index="${index}" title="Edit Column">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                        <button class="btn btn-outline-danger delete-column-btn" data-index="${index}" title="Delete Column">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        detailContent.innerHTML = `
            <div class="mb-3">
                <h5>Description</h5>
                <p>${table.description || 'No description'}</p>
            </div>
            <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h5>Columns</h5>
                    <button class="btn btn-outline-primary btn-sm add-column-btn">
                        <i class="fas fa-plus"></i> Add Column
                    </button>
                </div>
                ${columnsHtml}
            </div>
            <div class="mt-3">
                <button class="btn btn-outline-primary me-2 edit-table-btn">
                    <i class="fas fa-edit"></i> Edit Table
                </button>
                <button class="btn btn-outline-danger delete-table-btn">
                    <i class="fas fa-trash"></i> Delete Table
                </button>
            </div>
        `;
        
        // Add event listeners
        detailContent.querySelector('.add-column-btn').addEventListener('click', () => {
            this.showColumnModal();
        });
        
        detailContent.querySelector('.edit-table-btn').addEventListener('click', () => {
            this.showTableModal(table);
        });
        
        detailContent.querySelector('.delete-table-btn').addEventListener('click', () => {
            this.confirmDelete(
                `Are you sure you want to delete table "${table.name}"?`,
                () => this.deleteTable(table.name)
            );
        });
        
        // Add column edit/delete event listeners
        const editColumnBtns = detailContent.querySelectorAll('.edit-column-btn');
        const deleteColumnBtns = detailContent.querySelectorAll('.delete-column-btn');
        
        editColumnBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const columnIndex = parseInt(btn.dataset.index);
                this.showColumnModal(table.columns[columnIndex], columnIndex);
            });
        });
        
        deleteColumnBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const columnIndex = parseInt(btn.dataset.index);
                const column = table.columns[columnIndex];
                this.confirmDelete(
                    `Are you sure you want to delete column "${column.name}" from table "${table.name}"?`,
                    () => this.deleteColumn(columnIndex)
                );
            });
        });
    },
    
    // Show modal for creating/editing a workspace
    showWorkspaceModal: function(workspaceName = null) {
        const isEdit = !!workspaceName;
        const modalTitle = document.getElementById('workspaceModalTitle');
        const nameInput = document.getElementById('workspaceName');
        const descInput = document.getElementById('workspaceDescription');
        
        // Set modal title
        modalTitle.textContent = isEdit ? 'Edit Workspace' : 'Add Workspace';
        
        if (isEdit) {
            // Load workspace details
            fetch(`/admin/api/schema/workspaces/${encodeURIComponent(workspaceName)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        nameInput.value = data.workspace.name;
                        descInput.value = data.workspace.description || '';
                        this.editingWorkspace = workspaceName;
                        this.workspaceModal.show();
                    } else {
                        uiUtils.showError(data.error || `Failed to load workspace "${workspaceName}"`);
                    }
                })
                .catch(error => {
                    console.error('Error loading workspace details:', error);
                    uiUtils.showError('Error loading workspace details. See console for details.');
                });
        } else {
            // Clear form for new workspace
            nameInput.value = '';
            descInput.value = '';
            this.editingWorkspace = undefined;
            this.workspaceModal.show();
        }
    },
    
    // Save workspace (create or update)
    saveWorkspace: function() {
        const nameInput = document.getElementById('workspaceName');
        const descInput = document.getElementById('workspaceDescription');
        
        const name = nameInput.value.trim();
        const description = descInput.value.trim();
        
        if (!name) {
            uiUtils.showError('Workspace name is required');
            return;
        }
        
        // Use a separate flag stored when opening the modal to determine if this is an edit operation
        // instead of relying on currentWorkspace which might be set from normal navigation
        const isEdit = this.editingWorkspace !== undefined;
        
        const url = isEdit 
            ? `/admin/api/schema/workspaces/${encodeURIComponent(this.editingWorkspace)}`
            : '/admin/api/schema/workspaces';
        
        const method = isEdit ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.workspaceModal.hide();
                
                // Clear the editing flag
                this.editingWorkspace = undefined;
                
                // Refresh workspace list
                this.loadWorkspaces();
                
                // If editing current workspace, reload it
                if (isEdit && this.currentWorkspace && this.currentWorkspace.name === this.editingWorkspace) {
                    this.selectWorkspace(name);
                }
                
                uiUtils.showSuccess(`Workspace "${name}" ${isEdit ? 'updated' : 'created'} successfully`);
            } else {
                uiUtils.showError(data.error || `Failed to ${isEdit ? 'update' : 'create'} workspace`);
            }
        })
        .catch(error => {
            console.error(`Error ${isEdit ? 'updating' : 'creating'} workspace:`, error);
            uiUtils.showError(`Error ${isEdit ? 'updating' : 'creating'} workspace. See console for details.`);
        });
    },
    
    // Delete workspace
    deleteWorkspace: function(workspaceName) {
        fetch(`/admin/api/schema/workspaces/${encodeURIComponent(workspaceName)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                uiUtils.showSuccess(`Workspace "${workspaceName}" deleted successfully`);
                
                // Clear current workspace if it was deleted
                if (this.currentWorkspace && this.currentWorkspace.name === workspaceName) {
                    this.currentWorkspace = null;
                    this.currentTable = null;
                    
                    // Reset detail panel
                    document.getElementById('detailHeader').textContent = 'Details';
                    document.getElementById('detailContent').innerHTML = `
                        <div class="text-center text-muted py-5">
                            <i class="fas fa-arrow-left fa-2x mb-3"></i>
                            <p>Select a workspace or table to view details</p>
                        </div>
                    `;
                    
                    // Reset tables list
                    document.getElementById('tablesList').innerHTML = `
                        <div class="list-group-item text-center text-muted">
                            Select a workspace to view tables
                        </div>
                    `;
                    
                    // Disable Add Table button
                    document.getElementById('addTableBtn').disabled = true;
                }
                
                // Refresh workspace list
                this.loadWorkspaces();
                
                // Reload join conditions
                this.loadJoinConditions();
            } else {
                uiUtils.showError(data.error || `Failed to delete workspace "${workspaceName}"`);
            }
        })
        .catch(error => {
            console.error(`Error deleting workspace:`, error);
            uiUtils.showError(`Error deleting workspace. See console for details.`);
        });
    },
    
    // Show modal for creating/editing a table
    showTableModal: function(table = null) {
        const isEdit = !!table;
        const modalTitle = document.getElementById('tableModalTitle');
        const nameInput = document.getElementById('tableName');
        const descInput = document.getElementById('tableDescription');
        const workspaceInput = document.getElementById('tableWorkspace');
        
        // Set modal title
        modalTitle.textContent = isEdit ? 'Edit Table' : 'Add Table';
        
        // Set workspace
        workspaceInput.value = this.currentWorkspace.name;
        
        if (isEdit) {
            // Populate form with table details
            nameInput.value = table.name;
            descInput.value = table.description || '';
        } else {
            // Clear form for new table
            nameInput.value = '';
            descInput.value = '';
        }
        
        this.tableModal.show();
    },
    
    // Save table (create or update)
    saveTable: function() {
        const nameInput = document.getElementById('tableName');
        const descInput = document.getElementById('tableDescription');
        const workspaceInput = document.getElementById('tableWorkspace');
        
        const name = nameInput.value.trim();
        const description = descInput.value.trim();
        const workspace = workspaceInput.value;
        
        if (!name) {
            uiUtils.showError('Table name is required');
            return;
        }
        
        if (!workspace) {
            uiUtils.showError('Workspace is required');
            return;
        }
        
        const isEdit = !!this.currentTable;
        const url = isEdit 
            ? `/admin/api/schema/tables/${encodeURIComponent(this.currentTable.name)}?workspace=${encodeURIComponent(workspace)}`
            : '/admin/api/schema/tables';
        
        const method = isEdit ? 'PUT' : 'POST';
        const body = {
            name: name,
            description: description,
            workspace: workspace
        };
        
        if (isEdit && this.currentTable.columns) {
            body.columns = this.currentTable.columns;
        }
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.tableModal.hide();
                
                // If editing current table, reload workspace to refresh table list
                this.selectWorkspace(workspace);
                
                // If we have a new table from the response, select it
                if (!isEdit && data.table) {
                    this.selectTable(data.table);
                }
                
                uiUtils.showSuccess(`Table "${name}" ${isEdit ? 'updated' : 'created'} successfully`);
                
                // Reload join conditions
                this.loadJoinConditions();
                
                // Load all tables for join dropdowns
                this.loadAllTables();
            } else {
                uiUtils.showError(data.error || `Failed to ${isEdit ? 'update' : 'create'} table`);
            }
        })
        .catch(error => {
            console.error(`Error ${isEdit ? 'updating' : 'creating'} table:`, error);
            uiUtils.showError(`Error ${isEdit ? 'updating' : 'creating'} table. See console for details.`);
        });
    },
    
    // Delete table
    deleteTable: function(tableName) {
        if (!this.currentWorkspace) {
            uiUtils.showError('No workspace selected');
            return;
        }
        
        fetch(`/admin/api/schema/tables/${encodeURIComponent(tableName)}?workspace=${encodeURIComponent(this.currentWorkspace.name)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                uiUtils.showSuccess(`Table "${tableName}" deleted successfully`);
                
                // Clear current table if it was deleted
                if (this.currentTable && this.currentTable.name === tableName) {
                    this.currentTable = null;
                    
                    // Reset detail panel
                    document.getElementById('detailHeader').textContent = 'Details';
                    document.getElementById('detailContent').innerHTML = `
                        <div class="text-center text-muted py-5">
                            <i class="fas fa-arrow-left fa-2x mb-3"></i>
                            <p>Select a workspace or table to view details</p>
                        </div>
                    `;
                }
                
                // Reload workspace to refresh table list
                this.selectWorkspace(this.currentWorkspace.name);
                
                // Reload join conditions
                this.loadJoinConditions();
                
                // Load all tables for join dropdowns
                this.loadAllTables();
            } else {
                uiUtils.showError(data.error || `Failed to delete table "${tableName}"`);
            }
        })
        .catch(error => {
            console.error(`Error deleting table:`, error);
            uiUtils.showError(`Error deleting table. See console for details.`);
        });
    },
    
    // Show modal for creating/editing a column
    showColumnModal: function(column = null, columnIndex = null) {
        if (!this.currentTable) {
            uiUtils.showError('No table selected');
            return;
        }
        
        const isEdit = column !== null;
        const modalTitle = document.getElementById('columnModalTitle');
        const nameInput = document.getElementById('columnName');
        const datatypeInput = document.getElementById('columnDatatype');
        const descInput = document.getElementById('columnDescription');
        const pkCheckbox = document.getElementById('isPrimaryKey');
        const tableNameInput = document.getElementById('columnTableName');
        const workspaceInput = document.getElementById('columnWorkspace');
        const columnIndexInput = document.getElementById('columnIndex');
        
        // Set modal title
        modalTitle.textContent = isEdit ? 'Edit Column' : 'Add Column';
        
        // Set hidden fields
        tableNameInput.value = this.currentTable.name;
        workspaceInput.value = this.currentWorkspace.name;
        columnIndexInput.value = columnIndex !== null ? columnIndex : '';
        
        if (isEdit) {
            // Populate form with column details
            nameInput.value = column.name;
            datatypeInput.value = column.datatype;
            descInput.value = column.description || '';
            pkCheckbox.checked = column.is_primary_key || false;
        } else {
            // Clear form for new column
            nameInput.value = '';
            datatypeInput.value = '';
            descInput.value = '';
            pkCheckbox.checked = false;
        }
        
        this.columnModal.show();
    },
    
    // Save column (create or update)
    saveColumn: function() {
        const nameInput = document.getElementById('columnName');
        const datatypeInput = document.getElementById('columnDatatype');
        const descInput = document.getElementById('columnDescription');
        const pkCheckbox = document.getElementById('isPrimaryKey');
        const tableNameInput = document.getElementById('columnTableName');
        const workspaceInput = document.getElementById('columnWorkspace');
        const columnIndexInput = document.getElementById('columnIndex');
        
        const name = nameInput.value.trim();
        const datatype = datatypeInput.value.trim();
        const description = descInput.value.trim();
        const isPrimaryKey = pkCheckbox.checked;
        const tableName = tableNameInput.value;
        const workspace = workspaceInput.value;
        const columnIndex = columnIndexInput.value !== '' ? parseInt(columnIndexInput.value) : null;
        
        if (!name) {
            uiUtils.showError('Column name is required');
            return;
        }
        
        if (!datatype) {
            uiUtils.showError('Data type is required');
            return;
        }
        
        if (!tableName || !workspace) {
            uiUtils.showError('Table and workspace information is missing');
            return;
        }
        
        // Clone current table to modify
        const updatedTable = JSON.parse(JSON.stringify(this.currentTable));
        
        // Create new column object
        const column = {
            name: name,
            datatype: datatype,
            description: description,
            is_primary_key: isPrimaryKey
        };
        
        // Add or update column in the table
        if (columnIndex !== null) {
            // Update existing column
            updatedTable.columns[columnIndex] = column;
        } else {
            // Add new column
            if (!updatedTable.columns) {
                updatedTable.columns = [];
            }
            updatedTable.columns.push(column);
        }
        
        // Save updated table
        fetch(`/admin/api/schema/tables/${encodeURIComponent(tableName)}?workspace=${encodeURIComponent(workspace)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedTable)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.columnModal.hide();
                
                // If updating current table, refresh it
                fetch(`/admin/api/schema/tables/${encodeURIComponent(tableName)}?workspace=${encodeURIComponent(workspace)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.currentTable = data.table;
                            this.renderTableDetails(data.table);
                            
                            // Reload join conditions
                            this.loadJoinConditions();
                            
                            uiUtils.showSuccess(`Column "${name}" ${columnIndex !== null ? 'updated' : 'added'} successfully`);
                        } else {
                            uiUtils.showError(data.error || `Failed to refresh table "${tableName}"`);
                        }
                    });
            } else {
                uiUtils.showError(data.error || `Failed to ${columnIndex !== null ? 'update' : 'add'} column`);
            }
        })
        .catch(error => {
            console.error(`Error ${columnIndex !== null ? 'updating' : 'adding'} column:`, error);
            uiUtils.showError(`Error ${columnIndex !== null ? 'updating' : 'adding'} column. See console for details.`);
        });
    },
    
    // Delete column
    deleteColumn: function(columnIndex) {
        if (!this.currentTable || !this.currentWorkspace) {
            uiUtils.showError('No table selected');
            return;
        }
        
        // Clone current table to modify
        const updatedTable = JSON.parse(JSON.stringify(this.currentTable));
        
        // Get column name for success message
        const columnName = updatedTable.columns[columnIndex].name;
        
        // Remove column
        updatedTable.columns.splice(columnIndex, 1);
        
        // Save updated table
        fetch(`/admin/api/schema/tables/${encodeURIComponent(this.currentTable.name)}?workspace=${encodeURIComponent(this.currentWorkspace.name)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedTable)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // If updating current table, refresh it
                fetch(`/admin/api/schema/tables/${encodeURIComponent(this.currentTable.name)}?workspace=${encodeURIComponent(this.currentWorkspace.name)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.currentTable = data.table;
                            this.renderTableDetails(data.table);
                            uiUtils.showSuccess(`Column "${columnName}" deleted successfully`);
                        } else {
                            uiUtils.showError(data.error || `Failed to refresh table "${this.currentTable.name}"`);
                        }
                    });
            } else {
                uiUtils.showError(data.error || `Failed to delete column`);
            }
        })
        .catch(error => {
            console.error(`Error deleting column:`, error);
            uiUtils.showError(`Error deleting column. See console for details.`);
        });
    },
    
    // Load all tables for join dropdowns
    loadAllTables: function() {
        fetch('/admin/api/schema/tables')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.allTables = data.tables;
                    
                    // Update tables in join modal dropdowns
                    const leftTableSelect = document.getElementById('leftTable');
                    const rightTableSelect = document.getElementById('rightTable');
                    
                    // Clear current options except first
                    leftTableSelect.innerHTML = '<option value="">Select a table</option>';
                    rightTableSelect.innerHTML = '<option value="">Select a table</option>';
                    
                    // Add table options
                    this.allTables.forEach(table => {
                        const leftOption = document.createElement('option');
                        leftOption.value = table.name;
                        leftOption.textContent = table.name;
                        leftTableSelect.appendChild(leftOption);
                        
                        const rightOption = document.createElement('option');
                        rightOption.value = table.name;
                        rightOption.textContent = table.name;
                        rightTableSelect.appendChild(rightOption);
                    });
                } else {
                    console.error('Failed to load tables:', data.error);
                }
            })
            .catch(error => {
                console.error('Error loading tables:', error);
            });
    },
    
    // Load all join conditions
    loadJoinConditions: function() {
        // Load all tables first to ensure dropdowns have latest data
        this.loadAllTables();
        
        fetch('/admin/api/schema/joins')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.renderJoinConditions(data.joins);
                } else {
                    uiUtils.showError(data.error || 'Failed to load join conditions');
                }
            })
            .catch(error => {
                console.error('Error loading join conditions:', error);
                uiUtils.showError('Error loading join conditions. See console for details.');
            });
    },
    
    // Render join conditions table
    renderJoinConditions: function(joins) {
        const joinsTable = document.getElementById('joinsTable');
        const noJoinsMessage = document.getElementById('noJoinsMessage');
        const joinsTableBody = document.getElementById('joinsTableBody');
        
        if (!joins || joins.length === 0) {
            joinsTable.style.display = 'none';
            noJoinsMessage.style.display = 'block';
            return;
        }
        
        joinsTable.style.display = 'table';
        noJoinsMessage.style.display = 'none';
        
        joinsTableBody.innerHTML = '';
        
        joins.forEach((join, index) => {
            const row = document.createElement('tr');
            
            row.innerHTML = `
                <td>${join.left_table}</td>
                <td>${join.right_table}</td>
                <td>${join.join_type || 'INNER'}</td>
                <td><code>${join.condition}</code>${join.description ? `<br><small class="text-muted">${join.description}</small>` : ''}</td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-secondary edit-join-btn" data-index="${index}" title="Edit Join">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger delete-join-btn" data-index="${index}" title="Delete Join">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            
            // Add event listeners for edit and delete buttons
            const editBtn = row.querySelector('.edit-join-btn');
            const deleteBtn = row.querySelector('.delete-join-btn');
            
            editBtn.addEventListener('click', () => {
                this.showJoinModal(join, index);
            });
            
            deleteBtn.addEventListener('click', () => {
                this.confirmDelete(
                    `Are you sure you want to delete the join condition between "${join.left_table}" and "${join.right_table}"?`,
                    () => this.deleteJoinCondition(index)
                );
            });
            
            joinsTableBody.appendChild(row);
        });
    },
    
    // Show modal for creating/editing a join condition
    showJoinModal: function(join = null, joinIndex = null) {
        const isEdit = join !== null;
        const modalTitle = document.getElementById('joinModalTitle');
        const leftTableSelect = document.getElementById('leftTable');
        const rightTableSelect = document.getElementById('rightTable');
        const joinTypeSelect = document.getElementById('joinType');
        const conditionInput = document.getElementById('joinCondition');
        const descriptionInput = document.getElementById('joinDescription');
        const joinIdInput = document.getElementById('joinId');
        
        // Set modal title
        modalTitle.textContent = isEdit ? 'Edit Join Condition' : 'Add Join Condition';
        
        // Set join ID
        joinIdInput.value = joinIndex !== null ? joinIndex : '';
        
        if (isEdit) {
            // Populate form with join details
            leftTableSelect.value = join.left_table;
            rightTableSelect.value = join.right_table;
            joinTypeSelect.value = join.join_type || 'INNER'; // Default to INNER if not specified
            conditionInput.value = join.condition;
            descriptionInput.value = join.description || '';
        } else {
            // Clear form for new join
            leftTableSelect.value = '';
            rightTableSelect.value = '';
            joinTypeSelect.value = 'INNER'; // Default to INNER JOIN
            conditionInput.value = '';
            descriptionInput.value = '';
        }
        
        this.joinModal.show();
    },
    
    // Save join condition (create or update)
    saveJoinCondition: function() {
        const leftTableSelect = document.getElementById('leftTable');
        const rightTableSelect = document.getElementById('rightTable');
        const joinTypeSelect = document.getElementById('joinType');
        const conditionInput = document.getElementById('joinCondition');
        const descriptionInput = document.getElementById('joinDescription');
        const joinIdInput = document.getElementById('joinId');
        
        const leftTable = leftTableSelect.value;
        const rightTable = rightTableSelect.value;
        const joinType = joinTypeSelect.value;
        const condition = conditionInput.value.trim();
        const description = descriptionInput.value.trim();
        const joinId = joinIdInput.value !== '' ? parseInt(joinIdInput.value) : null;
        
        if (!leftTable) {
            uiUtils.showError('Left table is required');
            return;
        }
        
        if (!rightTable) {
            uiUtils.showError('Right table is required');
            return;
        }
        
        if (!condition) {
            uiUtils.showError('Join condition is required');
            return;
        }
        
        const isEdit = joinId !== null;
        const url = isEdit 
            ? `/admin/api/schema/joins/${joinId}`
            : '/admin/api/schema/joins';
        
        const method = isEdit ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                left_table: leftTable,
                right_table: rightTable,
                join_type: joinType,
                condition: condition,
                description: description
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.joinModal.hide();
                
                // Refresh join conditions
                this.loadJoinConditions();
                
                uiUtils.showSuccess(`Join condition ${isEdit ? 'updated' : 'created'} successfully`);
            } else {
                uiUtils.showError(data.error || `Failed to ${isEdit ? 'update' : 'create'} join condition`);
            }
        })
        .catch(error => {
            console.error(`Error ${isEdit ? 'updating' : 'creating'} join condition:`, error);
            uiUtils.showError(`Error ${isEdit ? 'updating' : 'creating'} join condition. See console for details.`);
        });
    },
    
    // Delete join condition
    deleteJoinCondition: function(joinIndex) {
        fetch(`/admin/api/schema/joins/${joinIndex}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                uiUtils.showSuccess(`Join condition deleted successfully`);
                
                // Refresh join conditions
                this.loadJoinConditions();
            } else {
                uiUtils.showError(data.error || `Failed to delete join condition`);
            }
        })
        .catch(error => {
            console.error(`Error deleting join condition:`, error);
            uiUtils.showError(`Error deleting join condition. See console for details.`);
        });
    },
    
    // Show import modal
    showImportModal: function(type) {
        const modalTitle = document.getElementById('importExportModalTitle');
        const contentArea = document.getElementById('importExportContent');
        const saveBtn = document.getElementById('importExportSaveBtn');
        const saveBtnText = document.getElementById('importExportSaveBtnText');
        
        modalTitle.textContent = type === 'schema' ? 'Import Schema' : 'Import Join Conditions';
        contentArea.value = '';
        contentArea.placeholder = `Paste ${type === 'schema' ? 'schema' : 'join conditions'} JSON here...`;
        
        saveBtnText.textContent = 'Import';
        saveBtn.classList.remove('btn-success');
        saveBtn.classList.add('btn-primary');
        
        // Set current operation for save button handler
        this.importExportOperation = {
            type: type,
            mode: 'import'
        };
        
        this.importExportModal.show();
    },
    
    // Show export modal
    showExportModal: function(type) {
        const modalTitle = document.getElementById('importExportModalTitle');
        const contentArea = document.getElementById('importExportContent');
        const saveBtn = document.getElementById('importExportSaveBtn');
        const saveBtnText = document.getElementById('importExportSaveBtnText');
        
        modalTitle.textContent = type === 'schema' ? 'Export Schema' : 'Export Join Conditions';
        contentArea.value = 'Loading...';
        
        // Set current operation for save button handler
        this.importExportOperation = {
            type: type,
            mode: 'export'
        };
        
        // Load data to export
        const url = type === 'schema' ? '/admin/api/schema/export' : '/admin/api/schema/joins/export';
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const exportData = type === 'schema' ? data.schema : data.joins;
                    contentArea.value = JSON.stringify(exportData, null, 2);
                } else {
                    contentArea.value = `Error: ${data.error || 'Failed to export data'}`;
                }
            })
            .catch(error => {
                console.error(`Error exporting ${type}:`, error);
                contentArea.value = `Error: Could not export data. See console for details.`;
            });
        
        saveBtnText.textContent = 'Copy to Clipboard';
        saveBtn.classList.remove('btn-primary');
        saveBtn.classList.add('btn-success');
        
        this.importExportModal.show();
    },
    
    // Handle import/export save button click
    handleImportExportSave: function() {
        const contentArea = document.getElementById('importExportContent');
        
        if (!this.importExportOperation) {
            uiUtils.showError('No import/export operation specified');
            return;
        }
        
        const { type, mode } = this.importExportOperation;
        
        if (mode === 'export') {
            // Copy to clipboard
            contentArea.select();
            document.execCommand('copy');
            uiUtils.showSuccess('Copied to clipboard!');
            return;
        } else if (mode === 'import') {
            // Import data
            try {
                const jsonData = JSON.parse(contentArea.value);
                
                const url = type === 'schema' ? '/admin/api/schema/import' : '/admin/api/schema/joins/import';
                
                fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(jsonData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.importExportModal.hide();
                        uiUtils.showSuccess(`${type === 'schema' ? 'Schema' : 'Join conditions'} imported successfully`);
                        
                        // Refresh data
                        this.loadWorkspaces();
                        this.loadJoinConditions();
                        
                        // Reset detail panels
                        if (this.currentWorkspace) {
                            this.selectWorkspace(this.currentWorkspace.name);
                        }
                    } else {
                        uiUtils.showError(data.error || `Failed to import ${type === 'schema' ? 'schema' : 'join conditions'}`);
                    }
                })
                .catch(error => {
                    console.error(`Error importing ${type}:`, error);
                    uiUtils.showError(`Error importing ${type}. See console for details.`);
                });
            } catch (error) {
                uiUtils.showError(`Invalid JSON: ${error.message}`);
            }
        }
    },
    
    // Reload schema and join conditions from files
    reloadSchemaFromFiles: function() {
        fetch('/admin/api/schema/reload', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                uiUtils.showSuccess(data.message || 'Schema and join conditions reloaded successfully');
                
                // Refresh data
                this.loadWorkspaces();
                this.loadJoinConditions();
                
                // Reset detail panels
                if (this.currentWorkspace) {
                    this.selectWorkspace(this.currentWorkspace.name);
                }
            } else {
                uiUtils.showError(data.error || 'Failed to reload schema from files');
            }
        })
        .catch(error => {
            console.error('Error reloading schema from files:', error);
            uiUtils.showError('Error reloading schema from files. See console for details.');
        });
    },
    
    // Show confirmation modal for delete operations
    confirmDelete: function(message, callback) {
        document.getElementById('confirmDeleteMessage').textContent = message;
        this.deleteCallback = callback;
        this.confirmDeleteModal.show();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    schemaAdmin.init();
});