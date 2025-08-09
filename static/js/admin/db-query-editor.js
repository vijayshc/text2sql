/**
 * Database Query Editor
 * Handles SQL editor initialization and query execution
 */

class DatabaseQueryEditor {
    constructor() {
        this.editor = null;
        this.executeButton = document.getElementById('executeBtn');
        this.clearButton = document.getElementById('clearBtn');
        this.resultsContainer = document.getElementById('resultsContainer');
        this.resultStats = document.getElementById('resultStats');
        this.editorStatus = document.getElementById('editorStatus');
        this.formatSqlBtn = document.getElementById('formatSqlBtn');
        this.copyToClipboardBtn = document.getElementById('copyToClipboardBtn');
        this.refreshSchemaBtn = document.getElementById('refreshSchemaBtn');
        this.expandAllBtn = document.getElementById('expandAllBtn');
        this.collapseAllBtn = document.getElementById('collapseAllBtn');
        
        this.dataTable = null;
        this.initializeEventListeners();
    }
    
    initializeMonacoEditor() {
        // Configure RequireJS for Monaco
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.40.0/min/vs' }});
        
        // Load Monaco
        require(['vs/editor/editor.main'], () => {
            // Define SQL language
            monaco.languages.register({ id: 'sql' });
            
            // Create editor
            this.editor = monaco.editor.create(document.getElementById('sqlEditor'), {
                value: '',
                language: 'sql',
                theme: 'vs',
                automaticLayout: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                glyphMargin: false,
                folding: true,
                fontSize: 14,
                fontFamily: 'Consolas, "Courier New", monospace',
                scrollbar: {
                    vertical: 'visible',
                    horizontal: 'visible',
                    useShadows: false,
                    verticalHasArrows: true,
                    horizontalHasArrows: true
                }
            });
            
            // Make editor accessible globally for schema browser to use
            window.sqlEditor = this.editor;
            
            // Add keyboard shortcut for executing query (Ctrl+Enter)
            this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
                this.executeQuery();
            });
            
            // Update editor status with cursor position
            this.editor.onDidChangeCursorPosition((e) => {
                if (this.editorStatus) {
                    this.editorStatus.textContent = `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
                }
            });
        });
    }
    
    initializeEventListeners() {
        // Set up execute button
        if (this.executeButton) {
            this.executeButton.addEventListener('click', () => this.executeQuery());
        }
        
        // Set up clear button
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => {
                if (this.editor) {
                    this.editor.setValue('-- Write your SQL query here\n');
                }
            });
        }
        
        // Format SQL button
        if (this.formatSqlBtn) {
            this.formatSqlBtn.addEventListener('click', () => {
                try {
                    // Simple SQL formatting (can be enhanced)
                    if (this.editor) {
                        const value = this.editor.getValue();
                        // A very basic SQL formatter - in production, consider using a library like sql-formatter
                        const formatted = value
                            .replace(/\s+/g, ' ')
                            .replace(/ (SELECT|FROM|WHERE|GROUP BY|ORDER BY|HAVING|LEFT JOIN|RIGHT JOIN|INNER JOIN|OUTER JOIN|UNION|INSERT INTO|UPDATE|DELETE FROM)/gi, '\n$1')
                            .replace(/(,)/gi, '$1\n    ');
                            
                        this.editor.setValue(formatted);
                    }
                } catch (e) {
                    console.error('Error formatting SQL:', e);
                }
            });
        }
        
        // Copy to clipboard button
        if (this.copyToClipboardBtn) {
            this.copyToClipboardBtn.addEventListener('click', () => {
                if (this.editor) {
                    const sql = this.editor.getValue();
                    navigator.clipboard.writeText(sql).then(() => {
                        this.showToast('SQL copied to clipboard');
                    });
                }
            });
        }
        
        // Refresh schema button
        if (this.refreshSchemaBtn && window.schemaTreeBuilder) {
            this.refreshSchemaBtn.addEventListener('click', () => {
                window.schemaTreeBuilder.loadSchema();
            });
        }
        
        // Expand all schema items
        if (this.expandAllBtn && window.schemaTreeBuilder) {
            this.expandAllBtn.addEventListener('click', () => {
                window.schemaTreeBuilder.expandAll();
            });
        }
        
        // Collapse all schema items
        if (this.collapseAllBtn && window.schemaTreeBuilder) {
            this.collapseAllBtn.addEventListener('click', () => {
                window.schemaTreeBuilder.collapseAll();
            });
        }
    }
    
    // Show a simple toast message
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast-message';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 2000);
    }
    
    async executeQuery() {
        if (!this.editor) return;
        
        const sql = this.editor.getValue().trim();
        if (!sql || sql.startsWith('--')) {
            this.showMessage('Please enter a valid SQL query.', 'warning');
            return;
        }
        
        // Show loading state
        this.showLoading();
        
        try {
            const response = await fetch('/admin/database/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sql })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Failed to execute query');
            }
            
            if (result.success) {
                if (result.isSelect) {
                    // Display results in table
                    this.displayResultsTable(result);
                } else {
                    // Display success message for non-SELECT queries
                    this.showMessage(
                        `Query executed successfully. ${result.message || ''}`,
                        'success'
                    );
                }
            } else {
                throw new Error(result.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Error executing query:', error);
            this.showMessage(error.message, 'error');
        }
    }
    
    displayResultsTable(result) {
        if (!result.columns || !result.data) {
            this.showMessage('Query returned no data.', 'info');
            return;
        }
        
        // Clean up any existing DataTable
        if (this.dataTable) {
            this.dataTable.destroy();
            this.dataTable = null;
        }
        
        // Clear previous results
        this.resultsContainer.innerHTML = '';
        
        // Create table wrapper with proper DataTables structure
        const tableResponsive = document.createElement('div');
        tableResponsive.className = 'table-responsive';
        
        // Create table with DataTables expected structure
        const table = document.createElement('table');
        table.className = 'table table-bordered';
        table.id = 'sqlResultsTable';
        table.setAttribute('width', '100%');
        table.setAttribute('cellspacing', '0');
        
        // Create header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // Add data columns directly - no extra column
        result.columns.forEach(column => {
            const th = document.createElement('th');
            th.textContent = column;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create tbody
        const tbody = document.createElement('tbody');
        table.appendChild(tbody);
        
        // Add table to container
        tableResponsive.appendChild(table);
        this.resultsContainer.appendChild(tableResponsive);
        
        // Format the data for DataTables - no extra column
        const dataSet = result.data.map(row => {
            const rowData = [];
            
            // Add actual data columns
            result.columns.forEach(column => {
                const value = row[column];
                
                // Format null values
                if (value === null) {
                    rowData.push('<span class="text-muted"><i>NULL</i></span>');
                } else {
                    rowData.push(value);
                }
            });
            
            return rowData;
        });
        
        // Initialize DataTable
        this.dataTable = $('#sqlResultsTable').DataTable({
            data: dataSet,
            autoWidth: false,
            ordering: true,
            order: [[0, 'asc']], // Default sort on first column
            responsive: false, // Disable responsive mode to show horizontal scrollbar
            scrollX: true,
            scrollCollapse: false,
            pageLength: 10,
            lengthMenu: [[5, 10, 25, 50, -1], [5, 10, 25, 50, "All"]],
            //scrollX: true, // Enable horizontal scrolling
            //scrollCollapse: true,
            dom: 'Bfrtilp', // Include length menu (l) and full pagination (p)
            buttons: [
                'copy', 'csv', 'excel', 'pdf', 'print'
            ]
        });
        
        // Add event listener for expand/collapse
        $('#sqlResultsTable tbody').on('click', 'td.details-control', (e) => {
            const tr = $(e.target).closest('tr');
            const row = this.dataTable.row(tr);
            
            if (row.child.isShown()) {
                // This row is already open - close it
                row.child.hide();
                tr.removeClass('shown');
                tr.find('td.details-control i').removeClass('fa-minus-circle').addClass('fa-plus-circle');
            } else {
                // Open this row
                row.child(formatRowDetails(row.data())).show();
                tr.addClass('shown');
                tr.find('td.details-control i').removeClass('fa-plus-circle').addClass('fa-minus-circle');
            }
        });
        
        // Update stats
        if (this.resultStats) {
            this.resultStats.innerHTML = `<span class="badge bg-primary">${result.rowCount} row(s) returned</span>`;
        }
    }
    
    showMessage(message, type = 'info') {
        this.resultsContainer.innerHTML = `
            <div class="result-message ${type}">
                <div class="d-flex align-items-center">
                    <i class="bi ${this.getIconForMessageType(type)} me-2"></i>
                    <span>${message}</span>
                </div>
            </div>
        `;
        
        // Clear stats
        if (this.resultStats) {
            this.resultStats.textContent = '';
        }
    }
    
    showLoading() {
        this.resultsContainer.innerHTML = `
            <div class="p-4 text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Executing query...</p>
            </div>
        `;
        
        // Clear stats
        if (this.resultStats) {
            this.resultStats.textContent = '';
        }
    }
    
    getIconForMessageType(type) {
        switch (type) {
            case 'success': return 'bi-check-circle';
            case 'error': return 'bi-exclamation-circle';
            case 'warning': return 'bi-exclamation-triangle';
            case 'info': 
            default: return 'bi-info-circle';
        }
    }
}

// Initialize when DOM content is loaded
document.addEventListener('DOMContentLoaded', () => {
    const editor = new DatabaseQueryEditor();
    editor.initializeMonacoEditor();
});
