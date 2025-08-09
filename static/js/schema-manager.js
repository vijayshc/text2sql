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
            
            // Initialize DataTables for schema tables
            this.initializeDataTables();

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
            
            // Initialize DataTables for schema tables
            this.initializeDataTables();
            
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
        return schemaData.map((table, index) => {
            return `
                <div class="schema-table-container mb-4" data-table="${table.name}">
                    <h4>${table.name}</h4>
                    ${table.description ? `<p class="text-muted mb-3">${table.description}</p>` : ''}
                    <div class="table-responsive">
                        <table class="table table-sm table-striped table-bordered schema-table schema-datatable w-100" id="schemaTable_${index}" data-table-init="false">
                            <thead class="table-light">
                                <tr>
                                    <th>Column</th>
                                    <th>Type</th>
                                    <th>Description</th>
                                    <th>Primary Key</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${table.columns.map(col => `
                                    <tr>
                                        <td>${col.name}</td>
                                        <td>${col.datatype}</td>
                                        <td>${col.description || ''}</td>
                                        <td class="text-center">${col.is_primary_key ? '<i class="fas fa-key text-warning"></i>' : ''}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
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
        
        // Reinitialize DataTables for visible tables
        this.initializeDataTables();
    },
    
    // Initialize DataTables for schema tables
    initializeDataTables: function() {
        // Wait a bit for DOM to be fully updated
        setTimeout(() => {
            // Destroy existing DataTables if any
            $('.schema-datatable').each(function() {
                if ($.fn.DataTable.isDataTable(this)) {
                    $(this).DataTable().destroy();
                }
            });
            
            // Initialize DataTables for all schema tables
            $('.schema-datatable').each(function() {
                $(this).DataTable({
                    responsive: false, // Disable responsive for better alignment
                    pageLength: 10,
                    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
                    autoWidth: false, // Disable auto width calculation
                    scrollX: false,   // Disable horizontal scroll for alignment
                    language: {
                        search: "Filter results:",
                        lengthMenu: "Show _MENU_ entries per page",
                        emptyTable: "No columns found",
                        info: "Showing _START_ to _END_ of _TOTAL_ columns",
                        infoEmpty: "Showing 0 to 0 of 0 columns",
                        infoFiltered: "(filtered from _MAX_ total columns)"
                    },
                    columnDefs: [
                        {
                            targets: 0, // Column name
                            className: 'dt-left'
                        },
                        {
                            targets: 1, // Type
                            className: 'dt-left'
                        },
                        {
                            targets: 2, // Description
                            className: 'dt-left'
                        },
                        {
                            targets: 3, // Primary Key column
                            orderable: false,
                            searchable: false,
                            className: 'dt-center'
                        }
                    ],
                    drawCallback: function(settings) {
                        // Force column width recalculation for alignment
                        this.api().columns.adjust();
                    },
                    initComplete: function(settings, json) {
                        // Ensure columns are properly aligned after initialization
                        this.api().columns.adjust();
                    },
                    order: [[0, 'asc']], // Sort by column name by default
                dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                    '<"row"<"col-sm-12"tr>>' +
                    '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
                    drawCallback: function() {
                        // Ensure proper table layout after draw
                        $(this).css('width', '100%');
                        $(this).find('th, td').css('text-align', function(i) {
                            return i === 3 ? 'center' : 'left';
                        });
                    }
                });
            });
        }, 100);
    }
};