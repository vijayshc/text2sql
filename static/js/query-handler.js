/**
 * query-handler.js - Query submission and progress tracking
 */

const queryHandler = {
    // Submit query to the backend
    submitQuery: function() {
        const query = text2sql.queryInput.value.trim();
        if (!query) {
            uiUtils.showError('Please enter a query');
            return;
        }

        // Clear previous results
        resultsDisplay.clearAllResults();

        // Reset UI state and show progress bar
        document.querySelector('#queryProgress').classList.remove('d-none');
        queryHandler.updateProgress(0);
        
        // Submit the query to the API
        fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                workspace: text2sql.workspaceSelect.value,
                tables: text2sql.selectedTables
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(result => {
                    throw new Error(result.error || 'Failed to process query');
                });
            }
            return response.json();
        })
        .then(result => {
            // Start polling for progress
            if (text2sql.progressInterval) {
                clearInterval(text2sql.progressInterval);
            }
            text2sql.progressInterval = setInterval(() => queryHandler.pollQueryProgress(result.query_id), 500);
        })
        .catch(error => {
            uiUtils.showError(error.message);
            document.querySelector('#queryProgress').classList.add('d-none');
        });
    },
    
    // Update progress bar and status message
    updateProgress: function(step, totalSteps = 6) {
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
    },

    // Poll the server for query progress
    pollQueryProgress: function(queryId) {
        fetch(`/api/query/progress/${queryId}`)
            .then(response => {
                // Check if we got a 408 status code (timeout)
                if (response.status === 408) {
                    clearInterval(text2sql.progressInterval);
                    return response.json().then(result => {
                        uiUtils.showTimeoutWarning(result.error || "Query processing timed out after 2 minutes");
                        document.querySelector('#queryProgress').classList.add('d-none');
                    });
                }
                
                if (!response.ok) {
                    clearInterval(text2sql.progressInterval);
                    return response.json().then(result => {
                        uiUtils.showError(result.error || "An error occurred while processing your query");
                        document.querySelector('#queryProgress').classList.add('d-none');
                    });
                }
                
                return response.json();
            })
            .then(progress => {
                if (!progress) return;
                
                if (progress.error) {
                    clearInterval(text2sql.progressInterval);
                    // Check if it's a timeout error based on message content
                    if (progress.error.includes('timed out')) {
                        uiUtils.showTimeoutWarning(progress.error);
                    } else {
                        uiUtils.showError(progress.error);
                    }
                    document.querySelector('#queryProgress').classList.add('d-none');
                    return;
                }
                
                // Update progress bar and steps
                if (progress.steps && progress.steps.length > 0) {
                    queryHandler.updateProgress(progress.current_step - 1);
                    resultsDisplay.displaySteps(progress.steps, progress.current_step - 1);
                }
                
                // If query is complete, display results and stop polling
                if (progress.status === 'completed' && progress.result) {
                    clearInterval(text2sql.progressInterval);
                    resultsDisplay.displayResults(progress.result);
                    document.querySelector('#queryProgress').classList.add('d-none');
                } else if (progress.status === 'error') {
                    clearInterval(text2sql.progressInterval);
                    // Check if it's a timeout error based on message content
                    if (progress.error && progress.error.includes('timed out')) {
                        uiUtils.showTimeoutWarning(progress.error || 'The query processing timed out');
                    } else {
                        uiUtils.showError(progress.error || 'An error occurred while processing your query');
                    }
                    document.querySelector('#queryProgress').classList.add('d-none');
                }
            })
            .catch(error => {
                console.error('Error polling progress:', error);
            });
    }
};