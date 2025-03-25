document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let dataTable = null;
    let progressInterval = null;
    const workspaceSelect = document.getElementById('workspaceSelect');
    const queryInput = document.getElementById('queryInput');
    const submitButton = document.getElementById('submitQuery');
    const viewSchemaBtn = document.getElementById('viewSchemaBtn');
    const schemaModal = new bootstrap.Modal(document.getElementById('schemaModal'));

    // Event Listeners
    workspaceSelect.addEventListener('change', updateWorkspaceDescription);
    queryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            submitQuery();
        }
    });
    submitButton.addEventListener('click', submitQuery);
    viewSchemaBtn.addEventListener('click', loadSchema);

    // Initialize workspace description and empty table state
    updateWorkspaceDescription();
    initializeEmptyTable();

    function initializeEmptyTable() {
        if (dataTable) {
            dataTable.destroy();
        }
        
        $('#resultsTable').html('<thead><tr><th>No Results</th></tr></thead><tbody><tr><td>Run a query to see results</td></tr></tbody>');
        
        dataTable = $('#resultsTable').DataTable({
            responsive: true,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            language: {
                search: "Filter results:",
                lengthMenu: "Show _MENU_ entries per page",
                emptyTable: "No results available"
            }
        });
    }

    function initializeDataTable(columns, data) {
        // Destroy existing DataTable if it exists
        if (dataTable) {
            dataTable.destroy();
        }

        // Clear and rebuild table structure
        const table = $('#resultsTable');
        table.empty();
        
        // Create thead with columns
        const thead = $('<thead>').appendTo(table);
        const headerRow = $('<tr>').appendTo(thead);
        columns.forEach(col => {
            $('<th>').text(col).appendTo(headerRow);
        });
        
        // Create tbody
        $('<tbody>').appendTo(table);

        // Initialize DataTable with data
        dataTable = table.DataTable({
            data: data,
            columns: columns.map(col => ({ 
                title: col,
                data: null,
                render: function(data, type, row, meta) {
                    return row[meta.col] ?? '';
                }
            })),
            responsive: true,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            language: {
                search: "Filter results:",
                lengthMenu: "Show _MENU_ entries per page",
                emptyTable: "No results available"
            }
        });
    }

    function showLoading() {
        loadingSpinner.classList.remove('d-none');
    }

    function hideLoading() {
        loadingSpinner.classList.add('d-none');
    }

    function updateWorkspaceDescription() {
        const selectedOption = workspaceSelect.selectedOptions[0];
        const description = selectedOption.getAttribute('data-description') || '';
        document.querySelector('.workspace-description').textContent = description;
    }

    function updateProgress(step, totalSteps = 4) {
        const progressBar = document.querySelector('#queryProgress');
        const progressStatus = progressBar.querySelector('.progress-status');
        const progressPercentage = progressBar.querySelector('.progress-percentage');
        const progressBarInner = progressBar.querySelector('.progress-bar');
        
        const currentStep = step + 1;
        const percentage = Math.round((currentStep / totalSteps) * 100);
        
        progressBar.classList.remove('d-none');
        progressBarInner.style.width = `${percentage}%`;
        progressBarInner.setAttribute('aria-valuenow', percentage);
        progressPercentage.textContent = `${percentage}%`;
        
        const stepMessages = {
            0: "Analyzing query intent...",
            1: "Identifying relevant tables...",
            2: "Selecting relevant columns...",
            3: "Generating SQL query..."
        };
        
        progressStatus.textContent = stepMessages[step] || "Processing...";
    }

    async function pollQueryProgress(queryId) {
        try {
            const response = await fetch(`/api/query/progress/${queryId}`);
            const progress = await response.json();
            
            if (progress.error) {
                clearInterval(progressInterval);
                showError(progress.error);
                return;
            }
            
            // Update progress bar and steps
            if (progress.steps && progress.steps.length > 0) {
                updateProgress(progress.current_step - 1);
                displaySteps(progress.steps, progress.current_step - 1);
            }
            
            // If query is complete, display results and stop polling
            if (progress.status === 'completed' && progress.result) {
                clearInterval(progressInterval);
                displayResults(progress.result);
                document.querySelector('#queryProgress').classList.add('d-none');
            } else if (progress.status === 'error') {
                clearInterval(progressInterval);
                showError(progress.error || 'An error occurred while processing your query');
                document.querySelector('#queryProgress').classList.add('d-none');
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }

    function clearAllResults() {
        try {
            // Clear SQL tab
            const sqlCodeElement = document.getElementById('sqlCode');
            if (sqlCodeElement) {
                sqlCodeElement.textContent = '';
                sqlCodeElement.innerHTML = '';
            }
            
            // Clear explanation tab
            const explanationElement = document.getElementById('explanationText');
            if (explanationElement) {
                explanationElement.innerHTML = '';
            }
            
            // Clear steps tab content
            const stepsContainer = document.getElementById('steps-container');
            if (stepsContainer) {
                stepsContainer.innerHTML = '';
            }
            
            // Also clear the steps tab itself
            const stepsTab = document.getElementById('steps');
            if (stepsTab) {
                stepsTab.innerHTML = '';
            }
            
            // Reset DataTable with empty state
            initializeEmptyTable();
        } catch (error) {
            console.error('Error clearing results:', error);
        }
    }

    async function submitQuery() {
        const query = queryInput.value.trim();
        if (!query) {
            showError('Please enter a query');
            return;
        }

        // Clear previous results
        clearAllResults();

        // Reset UI state and show progress bar
        document.querySelector('#queryProgress').classList.remove('d-none');
        updateProgress(0);
        
        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    workspace: workspaceSelect.value
                })
            });
            
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Failed to process query');
            }
            
            const result = await response.json();
            
            // Start polling for progress
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            progressInterval = setInterval(() => pollQueryProgress(result.query_id), 500);
            
        } catch (error) {
            showError(error.message);
            document.querySelector('#queryProgress').classList.add('d-none');
        }
    }

    function displayResults(result) {
        // Format and display SQL with syntax highlighting
        const sqlCode = document.getElementById('sqlCode');
        sqlCode.className = 'sql';
        sqlCode.textContent = result.sql || '';
        
        // Format SQL keywords
        const formattedSQL = result.sql.replace(
            /\b(SELECT|FROM|WHERE|JOIN|ON|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|AND|OR|AS|DISTINCT|INNER|LEFT|RIGHT|OUTER|UNION|ALL|LIMIT|OFFSET|DESC|ASC)\b/gi,
            match => `<span class="sql-keyword">${match}</span>`
        );
        sqlCode.innerHTML = formattedSQL;
        
        // Display explanation
        document.getElementById('explanationText').innerHTML = result.explanation || '';
        
        // Handle data table results
        if (result.chart_data && result.chart_data.data) {
            const columns = result.chart_data.columns;
            const data = result.chart_data.data;
            
            if (dataTable) {
                dataTable.destroy();
            }
            
            const table = $('#resultsTable');
            table.empty();
            
            const thead = $('<thead>').appendTo(table);
            const headerRow = $('<tr>').appendTo(thead);
            columns.forEach(col => {
                $('<th>').text(col).appendTo(headerRow);
            });
            
            $('<tbody>').appendTo(table);
            
            // Initialize DataTable with improved configuration
            dataTable = table.DataTable({
                data: data,
                columns: columns.map(col => ({
                    data: col,
                    title: col,
                    render: function(data, type, row) {
                        if (type === 'display') {
                            // Handle long text content
                            if (data && data.length > 50) {
                                return `<span title="${data}">${data.substr(0, 50)}...</span>`;
                            }
                        }
                        return data;
                    }
                })),
                responsive: true,
                autoWidth: false,
                dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                     '<"row"<"col-sm-12"tr>>' +
                     '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
                pageLength: 10,
                lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
                columnDefs: [{
                    targets: '_all',
                    className: 'text-wrap'
                }]
            });
        } else {
            initializeEmptyTable();
        }

        // Display steps
        const stepsContainer = document.createElement('div');
        stepsContainer.className = 'steps-timeline';
        
        if (result.steps && result.steps.length > 0) {
            result.steps.forEach((step, index) => {
                const stepElement = document.createElement('div');
                stepElement.className = 'step-item mb-4';
                stepElement.innerHTML = `
                    <div class="d-flex align-items-start">
                        <div class="step-number bg-primary text-white rounded-circle p-2 me-3">
                            ${index + 1}
                        </div>
                        <div class="step-content">
                            <h6 class="mb-1">${step.step}</h6>
                            <p class="text-muted mb-2">${step.description}</p>
                            ${step.result ? `
                                <div class="step-result bg-light p-3 rounded">
                                    <pre class="mb-0"><code>${typeof step.result === 'object' ? 
                                        JSON.stringify(step.result, null, 2) : step.result}</code></pre>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
                stepsContainer.appendChild(stepElement);
            });
        } else {
            stepsContainer.innerHTML = '<p class="text-muted">No processing steps available</p>';
        }
        
        // Clear and update steps tab content
        const stepsTab = document.getElementById('steps');
        stepsTab.innerHTML = '';
        stepsTab.appendChild(stepsContainer);
    }

    async function loadSchema() {
        showLoading();
        try {
            const response = await fetch(`/api/schema?workspace=${workspaceSelect.value}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load schema');
            }

            // Format schema data into HTML
            const schemaHtml = formatSchemaData(result.schema);
            document.getElementById('schemaContent').innerHTML = schemaHtml;

            // Update table filter dropdown and set up filtering
            initializeSchemaFiltering(result.schema);

            schemaModal.show();
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    }

    function formatSchemaData(schemaData) {
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
    }

    function initializeSchemaFiltering(schemaData) {
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
        tableFilter.removeEventListener('change', filterSchemaTables);
        tableFilter.addEventListener('change', filterSchemaTables);
    }

    function filterSchemaTables(event) {
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

    function showError(message) {
        // Create toast notification for error
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function showSuccess(message) {
        // Create toast notification for success
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function displaySteps(steps, currentStep = -1) {
        const stepsContainer = document.getElementById('steps');
        if (!stepsContainer) return;

        // Create steps container if it doesn't exist
        let stepsTimeline = stepsContainer.querySelector('.steps-timeline');
        if (!stepsTimeline) {
            stepsTimeline = document.createElement('div');
            stepsTimeline.className = 'steps-timeline';
            stepsContainer.appendChild(stepsTimeline);
        }

        // Update or create each step
        steps.forEach((step, index) => {
            let stepElement = stepsContainer.querySelector(`.step-item[data-step="${index}"]`);
            const isCurrentStep = index === currentStep;
            const isPastStep = index < currentStep;
            
            if (!stepElement) {
                stepElement = document.createElement('div');
                stepElement.className = 'step-item mb-4';
                stepElement.setAttribute('data-step', index);
                stepsTimeline.appendChild(stepElement);
            }

            stepElement.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="step-number ${isPastStep ? 'bg-success' : isCurrentStep ? 'bg-primary' : 'bg-secondary'} text-white rounded-circle p-2 me-3">
                        ${isPastStep ? '<i class="fas fa-check"></i>' : (index + 1)}
                    </div>
                    <div class="step-content">
                        <h6 class="mb-1">${step.step || step.name}</h6>
                        <p class="text-muted mb-2">${step.description}</p>
                        ${step.result ? `
                            <div class="step-result bg-light p-3 rounded">
                                <pre class="mb-0"><code>${typeof step.result === 'object' ? 
                                    JSON.stringify(step.result, null, 2) : step.result}</code></pre>
                            </div>
                        ` : ''}
                    </div>
                </div>
                ${isCurrentStep ? '<div class="current-step-indicator pulsing"></div>' : ''}
            `;

            // Add visual state classes
            stepElement.classList.remove('completed', 'current', 'pending');
            if (isPastStep) {
                stepElement.classList.add('completed');
            } else if (isCurrentStep) {
                stepElement.classList.add('current');
            } else {
                stepElement.classList.add('pending');
            }
        });

        // Show the steps tab if it was hidden
        const stepsTab = document.querySelector('[href="#steps"]');
        if (stepsTab) {
            const tab = new bootstrap.Tab(stepsTab);
            tab.show();
        }
    }

    // Remove all other displaySteps function definitions and update handleResponse accordingly
    function handleResponse(response) {
        if (response.steps) {
            displaySteps(response.steps);
            $('#steps-tab').show();
        } else {
            $('#steps-tab').hide();
        }
        
        $('.results-container').show();
        $('#loading').hide();
    }

    // Initialize UI elements
    const resultsContainer = document.querySelector('.results-container');
    const loadingIndicator = document.getElementById('loading');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const sqlCode = document.getElementById('sql-code');
    const stepsContainer = document.getElementById('steps-container');
    const explanationContainer = document.getElementById('explanation-container');
    
    // Handle form submission
    submitButton.addEventListener('click', function() {
        const query = queryInput.value.trim();
        if (!query) {
            showError('Please enter a query');
            return;
        }

        // Show loading state
        loadingIndicator.style.display = 'block';
        resultsContainer.style.display = 'block';
        errorContainer.style.display = 'none';
        
        // Make API request
        fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.style.display = 'none';
            
            if (data.error) {
                showError(data.error);
                return;
            }

            // Display SQL
            sqlCode.textContent = data.sql || 'No SQL generated';
            Prism.highlightElement(sqlCode);

            // Display explanation
            if (data.explanation) {
                explanationContainer.innerHTML = `<p class="mb-3">${data.explanation}</p>`;
                explanationContainer.style.display = 'block';
            } else {
                explanationContainer.style.display = 'none';
            }

            // Display steps
            displaySteps(data.steps);
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            showError('An error occurred while processing your request');
            console.error('Error:', error);
        });
    });

    // Show error message
    function showError(message) {
        errorContainer.style.display = 'block';
        errorMessage.textContent = message;
        resultsContainer.style.display = 'none';
    }

    // Handle example queries
    document.querySelectorAll('.example-query').forEach(example => {
        example.addEventListener('click', function() {
            queryInput.value = this.textContent;
            submitButton.click();
        });
    });

    // Copy SQL button

});