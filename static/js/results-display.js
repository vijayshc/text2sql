/**
 * results-display.js - Results rendering and data table management
 */

const resultsDisplay = {
    // Initialize empty table for initial state
    initializeEmptyTable: function() {
        if (text2sql.dataTable) {
            text2sql.dataTable.destroy();
        }
        
        $('#resultsTable').html('<thead><tr><th>No Results</th></tr></thead><tbody><tr><td>Run a query to see results</td></tr></tbody>');
        
        text2sql.dataTable = $('#resultsTable').DataTable({
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
    },
    
    // Initialize DataTable with query result data
    initializeDataTable: function(columns, data) {
        // Destroy existing DataTable if it exists
        if (text2sql.dataTable) {
            text2sql.dataTable.destroy();
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

        // Initialize DataTable with improved configuration
        text2sql.dataTable = table.DataTable({
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
            }],
            language: {
                search: "Filter results:",
                lengthMenu: "Show _MENU_ entries per page",
                emptyTable: "No results available"
            }
        });
    },
    
    // Clear all results from all tabs
    clearAllResults: function() {
        try {
            // Clear SQL tab
            const sqlCodeElement = document.getElementById('sqlCode');
            if (sqlCodeElement) {
                sqlCodeElement.textContent = '';
                sqlCodeElement.innerHTML = '';
            }
            
            // Hide feedback controls
            const feedbackControls = document.getElementById('feedbackControls');
            if (feedbackControls) {
                feedbackControls.style.display = 'none';
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
            this.initializeEmptyTable();
        } catch (error) {
            console.error('Error clearing results:', error);
        }
    },

    // Display results in all tabs
    displayResults: function(result) {
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
        
        // Show the feedback controls if we have SQL
        const feedbackControls = document.getElementById('feedbackControls');
        if (result.sql) {
            // Show feedback controls
            feedbackControls.style.display = 'block';
            
            // Reset the active state of feedback buttons
            document.getElementById('thumbsUpBtn').classList.remove('active');
            document.getElementById('thumbsDownBtn').classList.remove('active');
            
            // Make sure event listeners are properly set up
            feedback.setupFeedbackEventListeners(result);
        } else {
            // Hide feedback controls if no SQL
            feedbackControls.style.display = 'none';
        }
        
        // Display explanation
        document.getElementById('explanationText').innerHTML = result.explanation || '';
        
        // Handle data table results
        if (result.chart_data && result.chart_data.data) {
            const columns = result.chart_data.columns;
            const data = result.chart_data.data;
            this.initializeDataTable(columns, data);
        } else {
            this.initializeEmptyTable();
        }
        
        // Display steps
        this.displaySteps(result.steps);
    },

    // Display processing steps in the Steps tab
    displaySteps: function(steps, currentStep = -1) {
        const stepsContainer = document.getElementById('steps');
        if (!stepsContainer) return;
        
        // Clear the steps container before adding new steps
        stepsContainer.innerHTML = '';
        
        // Create steps container
        const stepsTimeline = document.createElement('div');
        stepsTimeline.className = 'steps-timeline';
        stepsContainer.appendChild(stepsTimeline);
        
        // Log the received steps for debugging
        console.log("Steps received:", steps);
        
        // If no steps provided, show a message
        if (!steps || steps.length === 0) {
            const emptyMessage = document.createElement('p');
            emptyMessage.className = 'text-muted';
            emptyMessage.textContent = 'No processing steps available';
            stepsTimeline.appendChild(emptyMessage);
            return;
        }
        
        // Ensure intent step is displayed (it should be provided by the API)
        // Create each step
        steps.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = 'step-item mb-4';
            stepElement.setAttribute('data-step', index);
            
            const isCurrentStep = index === currentStep;
            const isPastStep = index < currentStep;
            
            // Make sure we have either step or name to display
            const stepName = step.step || step.name || `Step ${index + 1}`;
            
            stepElement.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="step-number ${isPastStep ? 'bg-success' : isCurrentStep ? 'bg-primary' : 'bg-secondary'} text-white rounded-circle p-2 me-3">
                        ${isPastStep ? '<i class="fas fa-check"></i>' : (index + 1)}
                    </div>
                    <div class="step-content">
                        <h6 class="mb-1">${stepName}</h6>
                        <p class="text-muted mb-2">${step.description || ''}</p>
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
            if (isPastStep) {
                stepElement.classList.add('completed');
            } else if (isCurrentStep) {
                stepElement.classList.add('current');
            } else {
                stepElement.classList.add('pending');
            }
            
            stepsTimeline.appendChild(stepElement);
        });
        
        // Show the steps tab if it was hidden
        const stepsTab = document.querySelector('[href="#steps"]');
        if (stepsTab) {
            const tab = new bootstrap.Tab(stepsTab);
            tab.show();
        }
    },

    // Handle response from API
    handleResponse: function(response) {
        if (response.steps) {
            this.displaySteps(response.steps);
            $('#steps-tab').show();
        } else {
            $('#steps-tab').hide();
        }
        
        $('.results-container').show();
        $('#loading').hide();
    }
};