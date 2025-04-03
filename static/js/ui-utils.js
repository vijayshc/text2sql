/**
 * ui-utils.js - UI utility functions for notifications, loading indicators, etc.
 */

const uiUtils = {
    // Show loading spinner
    showLoading: function() {
        const loadingSpinner = document.getElementById('loadingSpinner');
        if (loadingSpinner) {
            // Add fade-in animation
            loadingSpinner.style.display = 'flex';
            loadingSpinner.style.opacity = '0';
            
            // Trigger reflow to ensure animation works
            void loadingSpinner.offsetWidth;
            
            // Start animation
            loadingSpinner.style.transition = 'opacity 0.3s ease';
            loadingSpinner.style.opacity = '1';
        }
    },
    
    // Hide loading spinner
    hideLoading: function() {
        const loadingSpinner = document.getElementById('loadingSpinner');
        if (loadingSpinner) {
            // Add fade-out animation
            loadingSpinner.style.transition = 'opacity 0.3s ease';
            loadingSpinner.style.opacity = '0';
            
            // Remove from DOM after animation completes
            setTimeout(() => {
                loadingSpinner.style.display = 'none';
            }, 300);
        }
    },
    
    // Show error toast notification
    showError: function(message) {
        // Create toast notification for error with enhanced styling
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Add icon and improved layout
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-exclamation-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Initialize Bootstrap toast with autohide
        const bsToast = new bootstrap.Toast(toast, {
            delay: 5000,
            animation: true
        });
        bsToast.show();
        
        // Clean up DOM after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            // Add slide-out animation
            toast.style.transform = 'translateX(30px)';
            toast.style.opacity = '0';
            toast.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
            
            // Remove from DOM after animation
            setTimeout(() => toast.remove(), 300);
        });
    },
    
    // Show success toast notification
    showSuccess: function(message) {
        // Create toast notification for success
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        toast.setAttribute('aria-atomic', 'true');
        
        // Add success icon and improved layout
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check-circle me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Initialize Bootstrap toast with autohide
        const bsToast = new bootstrap.Toast(toast, {
            delay: 3000,
            animation: true
        });
        bsToast.show();
        
        // Clean up DOM after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            // Add slide-out animation
            toast.style.transform = 'translateX(30px)';
            toast.style.opacity = '0';
            toast.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
            
            // Remove from DOM after animation
            setTimeout(() => toast.remove(), 300);
        });
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
        
        // Clean up DOM after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            // Add slide-out animation
            toast.style.transform = 'translateX(30px)';
            toast.style.opacity = '0';
            toast.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
            
            // Remove from DOM after animation
            setTimeout(() => toast.remove(), 300);
        });
        
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
            
            // Add fade-in animation to the alert
            timeoutMessage.style.opacity = '0';
            timeoutMessage.style.transform = 'translateY(10px)';
            
            resultsTab.innerHTML = '';
            resultsTab.appendChild(timeoutMessage);
            
            // Trigger animation after adding to DOM
            setTimeout(() => {
                timeoutMessage.style.transition = 'all 0.5s ease';
                timeoutMessage.style.opacity = '1';
                timeoutMessage.style.transform = 'translateY(0)';
            }, 10);
            
            // Show the results tab
            const resultsTabLink = document.querySelector('[href="#results"]');
            if (resultsTabLink) {
                const tab = new bootstrap.Tab(resultsTabLink);
                tab.show();
            }
        }
    }
};