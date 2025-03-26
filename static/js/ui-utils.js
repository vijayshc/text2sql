/**
 * ui-utils.js - UI utility functions for notifications, loading indicators, etc.
 */

const uiUtils = {
    // Show loading spinner
    showLoading: function() {
        const loadingSpinner = document.getElementById('loadingSpinner');
        if (loadingSpinner) {
            loadingSpinner.classList.remove('d-none');
        }
    },
    
    // Hide loading spinner
    hideLoading: function() {
        const loadingSpinner = document.getElementById('loadingSpinner');
        if (loadingSpinner) {
            loadingSpinner.classList.add('d-none');
        }
    },
    
    // Show error toast notification
    showError: function(message) {
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
    },
    
    // Show success toast notification
    showSuccess: function(message) {
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
    },
    
    // Show timeout warning toast
    showTimeoutWarning: function(message) {
        // Create toast notification for timeout warnings - using a different style than regular errors
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-warning border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('data-bs-autohide', 'false'); // Don't auto-hide timeout warnings
        
        // Add an icon and more detailed message for timeouts
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-clock me-2"></i><strong>Query Timeout:</strong> ${message}
                    <div class="mt-2 small">Try simplifying your query or filtering to fewer tables.</div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, {
            autohide: false // Ensure timeout warnings stay visible until dismissed
        });
        bsToast.show();
        
        // Also display a message in the results area
        const resultsTab = document.getElementById('results');
        if (resultsTab) {
            const timeoutMessage = document.createElement('div');
            timeoutMessage.className = 'alert alert-warning mt-3';
            timeoutMessage.innerHTML = `
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Query Processing Timeout</h5>
                <p>${message}</p>
                <hr>
                <p class="mb-0">Suggestions:</p>
                <ul>
                    <li>Try a simpler query with fewer conditions</li>
                    <li>Specify tables using the @ mention feature to focus the query</li>
                    <li>Break down your question into smaller parts</li>
                </ul>
            `;
            resultsTab.innerHTML = '';
            resultsTab.appendChild(timeoutMessage);
            
            // Show the results tab
            const resultsTabLink = document.querySelector('[href="#results"]');
            if (resultsTabLink) {
                const tab = new bootstrap.Tab(resultsTabLink);
                tab.show();
            }
        }
        
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
};