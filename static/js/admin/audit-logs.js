/**
 * Audit Logs JavaScript
 * Handles filtering and displaying log details
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize filter functionality
    initFilters();
    
    // Initialize log detail modal
    initLogDetailModal();
    
    // Initialize export functionality
    initExport();
});

/**
 * Setup filter functionality for logs
 */
function initFilters() {
    const filterOptions = document.querySelectorAll('.filter-option');
    
    filterOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get selected filter
            const filter = this.getAttribute('data-filter');
            
            // Get all log rows
            const rows = document.querySelectorAll('.log-row');
            
            // Apply filter
            rows.forEach(row => {
                const action = row.getAttribute('data-action');
                
                if (filter === 'all') {
                    // Show all rows
                    row.style.display = '';
                } else {
                    // Show only matching rows
                    if (action && action.includes(filter)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                }
            });
            
            // Update filter button text
            const filterText = this.textContent.trim();
            document.getElementById('filterDropdown').innerHTML = `<i class="fas fa-filter fa-sm"></i> ${filterText}`;
        });
    });
}

/**
 * Setup log detail modal with data loading
 */
function initLogDetailModal() {
    const logDetailModal = document.getElementById('logDetailModal');
    
    if (logDetailModal) {
        // When the modal is shown, load log details
        logDetailModal.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            
            // Extract log ID
            const logId = button.getAttribute('data-log-id');
            
            // Load log details
            loadLogDetails(logId);
        });
    }
}

/**
 * Fetch log details from API
 */
function loadLogDetails(logId) {
    // Show loading state
    document.getElementById('queryText').textContent = 'Loading...';
    document.getElementById('sqlQuery').textContent = 'Loading...';
    document.getElementById('response').textContent = 'Loading...';
    
    // Hide all containers initially
    document.getElementById('queryTextContainer').style.display = 'none';
    document.getElementById('sqlQueryContainer').style.display = 'none';
    document.getElementById('responseContainer').style.display = 'none';
    
    // Fetch log details - corrected URL path
    fetch(`/admin/api/audit-logs/${logId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Display query text if available
            if (data.query_text) {
                document.getElementById('queryTextContainer').style.display = 'block';
                document.getElementById('queryText').textContent = data.query_text;
            }
            
            // Display SQL query if available
            if (data.sql_query) {
                document.getElementById('sqlQueryContainer').style.display = 'block';
                document.getElementById('sqlQuery').textContent = data.sql_query;
            }
            
            // Display response if available
            if (data.response) {
                document.getElementById('responseContainer').style.display = 'block';
                document.getElementById('response').textContent = data.response;
            }
            
            // If no data available for a section, display a message
            if (!data.query_text && !data.sql_query && !data.response) {
                document.getElementById('responseContainer').style.display = 'block';
                document.getElementById('response').textContent = 'No detailed information available for this log entry.';
            }
        })
        .catch(error => {
            console.error('Error loading log details:', error);
            document.getElementById('responseContainer').style.display = 'block';
            document.getElementById('response').textContent = 'An error occurred while loading the log details.';
        });
}

/**
 * Setup export functionality
 */
function initExport() {
    const exportBtn = document.getElementById('exportLogsBtn');
    
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            // Get current filter if any
            let filter = 'all';
            const filterDropdown = document.getElementById('filterDropdown');
            if (filterDropdown.textContent.includes('Login Events')) {
                filter = 'login';
            } else if (filterDropdown.textContent.includes('User Management')) {
                filter = 'user';
            } else if (filterDropdown.textContent.includes('SQL Queries')) {
                filter = 'query';
            }
            
            // Redirect to export URL - corrected URL path
            window.location.href = `/admin/api/audit-logs/export?filter=${filter}`;
        });
    }
}