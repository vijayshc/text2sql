/**
 * feedback.js - Feedback submission functionality
 */

const feedback = {
    // Setup feedback event listeners only once
    setupFeedbackEventListeners: function(result) {
        // Remove any existing event listeners to prevent duplicates
        const thumbsUpBtn = document.getElementById('thumbsUpBtn');
        const thumbsDownBtn = document.getElementById('thumbsDownBtn');
        
        // Clone and replace buttons to remove existing event listeners
        const thumbsUpClone = thumbsUpBtn.cloneNode(true);
        const thumbsDownClone = thumbsDownBtn.cloneNode(true);
        thumbsUpBtn.parentNode.replaceChild(thumbsUpClone, thumbsUpBtn);
        thumbsDownBtn.parentNode.replaceChild(thumbsDownClone, thumbsDownBtn);
        
        // Add event handlers to the fresh buttons
        document.getElementById('thumbsUpBtn').addEventListener('click', function() {
            if (!feedback.validateFeedbackSubmission()) return;
            
            feedback.submitFeedback(1, result);
            this.classList.add('active');
            document.getElementById('thumbsDownBtn').classList.remove('active');
        });
        
        document.getElementById('thumbsDownBtn').addEventListener('click', function() {
            if (!feedback.validateFeedbackSubmission()) return;
            
            feedback.submitFeedback(0, result);
            this.classList.add('active');
            document.getElementById('thumbsUpBtn').classList.remove('active');
        });
    },
    
    // Validate that we have SQL before submitting feedback
    validateFeedbackSubmission: function() {
        const sqlCode = document.getElementById('sqlCode');
        if (!sqlCode || !sqlCode.textContent.trim()) {
            uiUtils.showError('Cannot submit feedback: No SQL query available');
            return false;
        }
        return true;
    },
    
    // Submit feedback to the server
    submitFeedback: async function(rating, result) {
        try {
            if (!this.validateFeedbackSubmission()) return;
            
            const feedbackData = {
                query_text: text2sql.queryInput.value,
                sql_query: result.sql,
                feedback_rating: rating,
                results_summary: result.chart_data ? 
                    `Returned ${result.chart_data.data.length} rows with ${result.chart_data.columns.length} columns` : 
                    'No data returned',
                workspace: text2sql.workspaceSelect.value,
                tables_used: text2sql.selectedTables
            };
            
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(feedbackData)
            });
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to submit feedback');
            }
            
            // Show success message
            uiUtils.showSuccess('Thank you for your feedback!');
        } catch (error) {
            console.error('Error submitting feedback:', error);
            uiUtils.showError('Failed to submit feedback: ' + error.message);
        }
    }
};