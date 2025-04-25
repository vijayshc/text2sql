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
                        // Handle null/undefined values
                        if (data === null || data === undefined) {
                            return '<span class="text-muted">NULL</span>';
                        }
                        
                        // Handle long text content
                        if (data && data.length > 50) {
                            return `<span title="${data}">${data.substr(0, 50)}...</span>`;
                        }
                    }
                    return data;
                }
            })),
            
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
            },
            drawCallback: function() {
                // Add animation to rows when drawing/redrawing
                $(this).find('tbody tr').each(function(index) {
                    $(this).css('opacity', '0');
                    $(this).css('transform', 'translateY(10px)');
                    
                    // Animate each row with a delay based on index
                    setTimeout(() => {
                        $(this).css('transition', 'all 0.3s ease');
                        $(this).css('opacity', '1');
                        $(this).css('transform', 'translateY(0)');
                    }, 50 * index);
                });
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
        // Store the current result in the global object for dashboard to access
        text2sql.currentResult = result;
        
        // Format and display SQL with syntax highlighting if static SQL block exists
        const sqlCodeEl = document.getElementById('sqlCode');
        if (sqlCodeEl) {
            sqlCodeEl.className = 'sql';
            sqlCodeEl.textContent = result.sql || '';
            // Format SQL keywords
            if (result.sql) {
                const formattedSQL = result.sql
                    .replace(/\b(SELECT|FROM|WHERE|JOIN|ON|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|AND|OR|AS|DISTINCT|INNER|LEFT|RIGHT|OUTER|UNION|ALL|LIMIT|OFFSET|DESC|ASC)\b/gi, 
                        match => `<span class="sql-keyword">${match}</span>`)
                    .replace(/'([^']*)'/g, match => `<span class="sql-string">${match}</span>`)
                    .replace(/\b(\d+(\.\d+)?)\b/g, match => `<span class="sql-number">${match}</span>`)
                    .replace(/\b(SUM|COUNT|AVG|MIN|MAX|COALESCE|CONCAT|SUBSTR|CAST|ROUND|DATE|EXTRACT)\(/gi,
                        match => `<span class="sql-function">${match}</span>`);
                sqlCodeEl.innerHTML = formattedSQL;
                // Add a subtle fade-in animation
                sqlCodeEl.style.opacity = '0';
                sqlCodeEl.style.transform = 'translateY(10px)';
                setTimeout(() => {
                    sqlCodeEl.style.transition = 'all 0.5s ease';
                    sqlCodeEl.style.opacity = '1';
                    sqlCodeEl.style.transform = 'translateY(0)';
                }, 100);
            }
        }
        
        // Show the feedback controls if we have SQL
        const feedbackControls = document.getElementById('feedbackControls');
        if (result.sql) {
            // Show feedback controls with fade-in
            feedbackControls.style.display = 'block';
            feedbackControls.style.opacity = '0';
            
            setTimeout(() => {
                feedbackControls.style.transition = 'opacity 0.5s ease';
                feedbackControls.style.opacity = '1';
            }, 500);
            
            // Reset the active state of feedback buttons
            document.getElementById('thumbsUpBtn').classList.remove('active');
            document.getElementById('thumbsDownBtn').classList.remove('active');
            
            // Make sure event listeners are properly set up
            feedback.setupFeedbackEventListeners(result);
        } else {
            // Hide feedback controls if no SQL
            feedbackControls.style.display = 'none';
        }
        
        // Display explanation with animation
        const explanationText = document.getElementById('explanationText');
        explanationText.innerHTML = result.explanation || '';
        
        if (result.explanation) {
            explanationText.style.opacity = '0';
            explanationText.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                explanationText.style.transition = 'all 0.5s ease';
                explanationText.style.opacity = '1';
                explanationText.style.transform = 'translateY(0)';
            }, 200);
        }
        
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
        
        // Update dashboard with new data and handle notifications
        if (typeof dashboard !== 'undefined') {
            dashboard.handleQueryResults(result);
            
            // Add a notification badge to dashboard tab if there are dashboard recommendations
            if (result.chart_data && 
                result.chart_data.dashboard_recommendations && 
                result.chart_data.dashboard_recommendations.is_suitable === true) {
                
                const dashboardTab = document.querySelector('a[href="#dashboard"]');
                if (dashboardTab) {
                    // Remove any existing badges
                    const existingBadges = dashboardTab.querySelectorAll('.badge');
                    existingBadges.forEach(badge => badge.remove());
                    
                    // Check if dashboard tab is not already active
                    const activeTab = document.querySelector('.nav-link.active');
                    if (activeTab && !activeTab.isEqualNode(dashboardTab)) {
                        // Add notification badge
                        const indicator = document.createElement('span');
                        indicator.className = 'badge bg-success ms-1 pulse-animation';
                        indicator.textContent = 'Auto';
                        indicator.style.animation = 'pulse 1.5s infinite';
                        dashboardTab.appendChild(indicator);
                        
                        // Add pulse animation if not already in CSS
                        if (!document.getElementById('pulse-animation-style')) {
                            const style = document.createElement('style');
                            style.id = 'pulse-animation-style';
                            style.textContent = `
                                @keyframes pulse {
                                    0% { transform: scale(1); }
                                    50% { transform: scale(1.1); }
                                    100% { transform: scale(1); }
                                }
                                .pulse-animation {
                                    animation: pulse 1.5s infinite;
                                }
                            `;
                            document.head.appendChild(style);
                        }
                        
                        // Remove indicator when tab is clicked
                        dashboardTab.addEventListener('click', function() {
                            if (indicator.parentNode === dashboardTab) {
                                dashboardTab.removeChild(indicator);
                            }
                        }, { once: true });
                    }
                }
            }
        }
    },

    // Display processing steps in the Steps tab
    displaySteps: function(steps, currentStep = -1) {
        const stepsContainer = document.getElementById('steps');
        if (!stepsContainer) return;
        
        // Create steps container if it doesn't exist
        let stepsTimeline = document.getElementById('steps-timeline');
        if (!stepsTimeline) {
            stepsTimeline = document.createElement('div');
            stepsTimeline.className = 'steps-timeline';
            stepsTimeline.id = 'steps-timeline';
            stepsContainer.appendChild(stepsTimeline);
        }
        
        if (!steps || steps.length === 0) {
            stepsTimeline.innerHTML = '<div class="text-center p-4">No processing steps available</div>';
            return;
        }

        // Check if we're displaying the final result (all steps completed)
        // This is likely the case when either:
        // 1. currentStep is -1 and there's SQL in the result, OR
        // 2. currentStep is equal to or greater than the last step index (steps.length - 1)
        const sqlCode = document.getElementById('sqlCode');
        const sqlCompleted = sqlCode && sqlCode.textContent && sqlCode.textContent.trim() !== '';
        const isQueryCompleted = (currentStep === -1 && sqlCompleted) || 
                                 (currentStep >= steps.length - 1) ||
                                 (document.getElementById('resultsTable').querySelector('tbody tr td') && 
                                  document.getElementById('resultsTable').querySelector('tbody tr td').textContent !== 'Run a query to see results');
        
        // Get current number of step elements already rendered
        const existingStepCount = stepsTimeline.querySelectorAll('.step-item').length;
        
        // Add only new steps that don't exist yet
        for (let index = existingStepCount; index < steps.length; index++) {
            const step = steps[index];
            const stepElement = document.createElement('div');
            stepElement.className = 'step-item';
            stepElement.id = `step-item-${index}`;
            stepElement.style.setProperty('--step-index', index);
            
            // Initialize with appropriate class based on query state
            if (isQueryCompleted) {
                stepElement.classList.add('completed');
            } else {
                stepElement.classList.add('pending');
            }
            
            // Create step content with placeholders
            stepElement.innerHTML = `
                <div class="step-number">${index + 1}</div>
                <div class="step-content">
                    <h6>${step.title || `Step ${index + 1}`}</h6>
                    <div class="step-description">${step.description || ''}</div>
                    <div class="step-result-container"></div>
                </div>
            `;
            
            // Add with fade-in animation
            stepElement.style.opacity = '0';
            stepsTimeline.appendChild(stepElement);
            
            // Trigger animation after adding to DOM
            setTimeout(() => {
                stepElement.style.transition = 'opacity 0.3s ease';
                stepElement.style.opacity = '1';
            }, 10);
        }
        
        // Update all step states
        if (stepsTimeline && steps && steps.length > 0) {
            steps.forEach((step, index) => {
                const stepElement = document.getElementById(`step-item-${index}`);
                
                if (stepElement) {
                    // Update class based on current step
                    stepElement.classList.remove('completed', 'current', 'pending');
                    
                    if (isQueryCompleted) {
                        // If query is completed, mark ALL steps as completed (green)
                        stepElement.classList.add('completed');
                    } else {
                        const isPastStep = currentStep > index;
                        const isCurrentStep = currentStep === index;
                        
                        if (isPastStep) stepElement.classList.add('completed');
                        if (isCurrentStep) stepElement.classList.add('current');
                        if (!isPastStep && !isCurrentStep) stepElement.classList.add('pending');
                    }
                    
                    // Update content if needed
                    const titleElement = stepElement.querySelector('h6');
                    if (titleElement && titleElement.textContent !== (step.title || `Step ${index + 1}`)) {
                        titleElement.textContent = step.title || `Step ${index + 1}`;
                    }
                    
                    const descElement = stepElement.querySelector('.step-description');
                    if (descElement && descElement.textContent !== (step.description || '')) {
                        descElement.textContent = step.description || '';
                    }
                    
                    // Update result if available
                    const resultContainer = stepElement.querySelector('.step-result-container');
                    if (resultContainer) {
                        // Only update result if it has changed
                        const currentResult = resultContainer.innerHTML;
                        const newResult = step.result ? `<div class="step-result"><pre>${step.result}</pre></div>` : '';
                        
                        if (currentResult !== newResult && newResult) {
                            if (resultContainer.childElementCount === 0) {
                                // Fade in if this is a new result
                                resultContainer.innerHTML = newResult;
                                const resultElement = resultContainer.querySelector('.step-result');
                                if (resultElement) {
                                    resultElement.style.opacity = '0';
                                    setTimeout(() => {
                                        resultElement.style.transition = 'opacity 0.3s ease';
                                        resultElement.style.opacity = '1';
                                    }, 10);
                                }
                            } else {
                                resultContainer.innerHTML = newResult;
                            }
                        }
                    }
                    
                    // Add current step indicator if it's the current step and query is not completed
                    const currentIndicator = stepElement.querySelector('.current-step-indicator');
                    if (!isQueryCompleted && currentStep === index && !currentIndicator) {
                        const indicatorDiv = document.createElement('div');
                        indicatorDiv.className = 'current-step-indicator';
                        stepElement.appendChild(indicatorDiv);
                    } else if ((isQueryCompleted || currentStep !== index) && currentIndicator) {
                        stepElement.removeChild(currentIndicator);
                    }
                }
            });
        }
        
        // Show the steps tab if it was hidden
        const stepsTab = document.querySelector('[href="#steps"]');
        if (stepsTab) {
            // First, remove any existing notification badges from the tab
            const existingBadges = stepsTab.querySelectorAll('.badge');
            existingBadges.forEach(badge => {
                stepsTab.removeChild(badge);
            });
            
            // Add a subtle notification to the tab if not active
            const activeTab = document.querySelector('.nav-link.active');
            if (activeTab && !activeTab.isEqualNode(stepsTab)) {
                const indicator = document.createElement('span');
                indicator.className = 'badge bg-primary ms-1';
                indicator.textContent = 'New';
                stepsTab.appendChild(indicator);
                
                // Remove indicator when tab is clicked
                stepsTab.addEventListener('click', function() {
                    if (indicator.parentNode === stepsTab) {
                        stepsTab.removeChild(indicator);
                    }
                }, { once: true });
            }
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