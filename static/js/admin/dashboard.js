/**
 * Admin Dashboard JavaScript
 * Handles dashboard data loading and display
 */
document.addEventListener('DOMContentLoaded', function() {
    // Load dashboard statistics
    loadDashboardStats();
    
    // Load recent activities
    loadRecentActivities();
});

/**
 * Fetch dashboard statistics from API
 */
function loadDashboardStats() {
    fetch('/admin/api/dashboard/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Update statistics counters
            document.getElementById('userCount').textContent = data.userCount || '0';
            document.getElementById('roleCount').textContent = data.roleCount || '0';
            document.getElementById('queryCount').textContent = data.queryCount || '0';
            document.getElementById('activityCount').textContent = data.activityCount || '0';
        })
        .catch(error => {
            console.error('Error loading dashboard stats:', error);
            // Show error message or set default values
            document.getElementById('userCount').textContent = 'Error';
            document.getElementById('roleCount').textContent = 'Error';
            document.getElementById('queryCount').textContent = 'Error';
            document.getElementById('activityCount').textContent = 'Error';
        });
}

/**
 * Fetch recent activities from API
 */
function loadRecentActivities() {
    fetch('/admin/api/audit-logs?limit=5')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const tableBody = document.getElementById('recentActivitiesList');
            tableBody.innerHTML = ''; // Clear loading message
            
            if (data.logs && data.logs.length > 0) {
                // Add each activity to the table
                data.logs.forEach(log => {
                    const row = document.createElement('tr');
                    
                    // Format date
                    const date = new Date(log.timestamp);
                    const formattedDate = date.toLocaleString();
                    
                    // Create badge based on action type
                    let badgeClass = 'bg-secondary';
                    if (log.action.includes('login')) badgeClass = 'bg-info';
                    else if (log.action.includes('query')) badgeClass = 'bg-primary';
                    else if (log.action.includes('error')) badgeClass = 'bg-danger';
                    else if (log.action.includes('create') || log.action.includes('update') || log.action.includes('delete')) badgeClass = 'bg-warning';
                    
                    // Create table row
                    row.innerHTML = `
                        <td>${formattedDate}</td>
                        <td>${log.username || 'System'}</td>
                        <td><span class="badge ${badgeClass}">${log.action}</span></td>
                        <td>${log.details}</td>
                    `;
                    
                    tableBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="4" class="text-center">No recent activities found</td>';
                tableBody.appendChild(row);
            }
        })
        .catch(error => {
            console.error('Error loading recent activities:', error);
            const tableBody = document.getElementById('recentActivitiesList');
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load recent activities</td></tr>';
        });
}