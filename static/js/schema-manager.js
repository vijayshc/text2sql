/**
 * schema-manager.js - Schema loading and display functionality
 */

const schemaManager = {
    // Load schema data from API
    loadSchema: async function() {
        uiUtils.showLoading();
        try {
            const workspaceValue = text2sql.workspaceSelect ? text2sql.workspaceSelect.value : 'Default';
            const response = await fetch(`/api/schema?workspace=${workspaceValue}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load schema');
            }

            // Format schema data into HTML
            const schemaContent = document.getElementById('schemaContent');
            if (!schemaContent) {
                throw new Error('Schema content element not found');
            }
            
            const schemaHtml = this.formatSchemaData(result.schema);
            schemaContent.innerHTML = schemaHtml;

            // Update table filter dropdown and set up filtering
            this.initializeSchemaFiltering(result.schema);

            // Display the modal
            if (text2sql.schemaModal) {
                text2sql.schemaModal.show();
            } else {
                // Fallback if Bootstrap modal object isn't available
                const modalElement = document.getElementById('schemaModal');
                if (modalElement) {
                    const modal = new bootstrap.Modal(modalElement);
                    modal.show();
                } else {
                    throw new Error('Schema modal element not found');
                }
            }
        } catch (error) {
            uiUtils.showError(error.message);
            console.error('Schema loading error:', error);
        } finally {
            uiUtils.hideLoading();
        }
    },
    
    // Show detailed information about a specific table
    showTableInfo: async function(tableName) {
        try {
            uiUtils.showLoading();
            
            // First load the schema
            const response = await fetch(`/api/schema?workspace=${text2sql.workspaceSelect.value}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load schema');
            }

            // Format schema data into HTML
            const schemaHtml = this.formatSchemaData(result.schema);
            document.getElementById('schemaContent').innerHTML = schemaHtml;

            // Initialize filtering and set selected table
            this.initializeSchemaFiltering(result.schema);
            
            // Set the table filter dropdown to this specific table
            const tableFilter = document.getElementById('tableFilter');
            if (tableFilter) {
                tableFilter.value = tableName;
                // Trigger change event to update display
                const event = new Event('change');
                tableFilter.dispatchEvent(event);
            }
            
            // Show the schema modal
            text2sql.schemaModal.show();
        } catch (error) {
            uiUtils.showError(error.message);
        } finally {
            uiUtils.hideLoading();
        }
    },
    
    // Format schema data from API into HTML
    formatSchemaData: function(schemaData) {
        return schemaData.map(table => {
            const primaryKeys = table.columns
                .filter(col => col.is_primary_key)
                .map(col => col.name);
                
            return `
                <div class="schema-table-container" data-table="${table.name}">
                    <h4>${table.name}</h4>
                    ${table.description ? `<p class="text-muted mb-3">${table.description}</p>` : ''}
                    <table class="table table-sm table-striped schema-table">
                        <thead>
                            <tr>
                                <th>Column</th>
                                <th>Type</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${table.columns.map(col => `
                                <tr ${col.is_primary_key ? 'class="table-primary"' : ''}>
                                    <td>${col.name}</td>
                                    <td>${col.datatype}</td>
                                    <td>${col.description || ''}</td>
                                </tr>
                            `).join('')}
                            ${primaryKeys.length > 0 ? `
                                <tr class="table-primary">
                                    <td colspan="3">
                                        <strong>Primary Key(s):</strong> ${primaryKeys.join(', ')}
                                    </td>
                                </tr>
                            ` : ''}
                        </tbody>
                    </table>
                </div>
            `;
        }).join('\n');
    },
    
    // Initialize the schema filtering functionality
    initializeSchemaFiltering: function(schemaData) {
        const tableFilter = document.getElementById('tableFilter');
        tableFilter.innerHTML = '<option value="all">All Tables</option>';
        
        // Add table options
        schemaData
            .map(table => table.name)
            .sort()
            .forEach(tableName => {
                const option = document.createElement('option');
                option.value = tableName;
                option.textContent = tableName;
                tableFilter.appendChild(option);
            });

        // Remove any existing event listener and add a new one
        // Use an arrow function to maintain the correct 'this' context
        tableFilter.removeEventListener('change', this._handleFilterChange);
        this._handleFilterChange = (event) => this.filterSchemaTables(event);
        tableFilter.addEventListener('change', this._handleFilterChange);
    },
    
    // Filter tables in the schema view based on selection
    filterSchemaTables: function(event) {
        const selectedTable = event.target.value;
        const tables = document.querySelectorAll('.schema-table-container');
        
        tables.forEach(table => {
            if (selectedTable === 'all' || table.dataset.table === selectedTable) {
                table.style.display = '';
            } else {
                table.style.display = 'none';
            }
        });
    }
};