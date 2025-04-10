/**
 * Role Management JavaScript
 * Handles client-side functionality for role management including:
 * - Creating/editing roles
 * - Managing role permissions
 * - Deleting roles
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTables
    $('#rolesTable').DataTable({
        order: [[0, 'asc']],
        columnDefs: [
            { orderable: false, targets: 4 } // Disable sorting on the actions column
        ]
    });

    $('#permissionsTable').DataTable({
        order: [[0, 'asc']],
        paging: false,
        searching: false
    });

    // Add new role button handler
    document.getElementById('btnAddRole').addEventListener('click', function() {
        // Clear form
        document.getElementById('roleId').value = '';
        document.getElementById('roleName').value = '';
        document.getElementById('roleDescription').value = '';
        
        // Update modal title
        document.getElementById('roleModalLabel').textContent = 'Add New Role';
        
        // Show modal
        new bootstrap.Modal(document.getElementById('roleModal')).show();
    });

    // Save role button handler
    document.getElementById('btnSaveRole').addEventListener('click', function() {
        const roleId = document.getElementById('roleId').value;
        const roleName = document.getElementById('roleName').value;
        const roleDescription = document.getElementById('roleDescription').value;
        
        if (!roleName) {
            showAlert('Role name is required', 'danger');
            return;
        }
        
        // Determine if this is an add or edit operation
        const isEdit = roleId ? true : false;
        const url = isEdit ? `/admin/api/roles/${roleId}` : '/admin/api/roles';
        const method = isEdit ? 'PUT' : 'POST';
        
        // Send API request
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: roleName,
                description: roleDescription
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('roleModal')).hide();
            
            // Show success message
            showAlert(data.message, 'success');
            
            // Reload page to show updated data
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('An error occurred while saving the role', 'danger');
        });
    });

    // Edit role button handlers
    document.querySelectorAll('.btn-edit-role').forEach(button => {
        button.addEventListener('click', function() {
            const roleId = this.getAttribute('data-role-id');
            const roleName = this.getAttribute('data-role-name');
            const roleDescription = this.getAttribute('data-role-description');
            
            // Fill form with role data
            document.getElementById('roleId').value = roleId;
            document.getElementById('roleName').value = roleName;
            document.getElementById('roleDescription').value = roleDescription;
            
            // Update modal title
            document.getElementById('roleModalLabel').textContent = 'Edit Role';
            
            // Show modal
            new bootstrap.Modal(document.getElementById('roleModal')).show();
        });
    });

    // Manage permissions button handlers
    document.querySelectorAll('.btn-manage-permissions').forEach(button => {
        button.addEventListener('click', function() {
            const roleId = this.getAttribute('data-role-id');
            const roleName = this.getAttribute('data-role-name');
            
            // Update modal title
            document.getElementById('permissionsModalLabel').textContent = `Manage Permissions for ${roleName}`;
            document.getElementById('permissionsRoleId').value = roleId;
            
            // Reset all checkboxes
            document.querySelectorAll('.permission-checkbox').forEach(cb => {
                cb.checked = false;
            });
            
            // Get current permissions for this role
            fetch(`/admin/api/roles/${roleId}/permissions`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Check the checkboxes for assigned permissions
                data.permissions.forEach(permissionName => {
                    // Find checkbox by name attribute instead of ID
                    document.querySelectorAll('.permission-checkbox').forEach(checkbox => {
                        if (checkbox.getAttribute('data-permission-name') === permissionName) {
                            checkbox.checked = true;
                        }
                    });
                });
                
                // Show modal
                new bootstrap.Modal(document.getElementById('permissionsModal')).show();
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while loading permissions', 'danger');
            });
        });
    });

    // Save permissions button handler
    document.getElementById('btnSavePermissions').addEventListener('click', function() {
        const roleId = document.getElementById('permissionsRoleId').value;
        
        // Get all checked permissions
        const permissions = [];
        document.querySelectorAll('.permission-checkbox:checked').forEach(cb => {
            permissions.push(cb.getAttribute('data-permission-name'));
        });
        
        // Send API request
        fetch(`/admin/api/roles/${roleId}/permissions`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                permissions: permissions
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('permissionsModal')).hide();
            
            // Show success message
            showAlert(data.message, 'success');
            
            // Reload page to show updated data
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('An error occurred while saving permissions', 'danger');
        });
    });

    // Delete role button handlers
    document.querySelectorAll('.btn-delete-role').forEach(button => {
        button.addEventListener('click', function() {
            const roleId = this.getAttribute('data-role-id');
            const roleName = this.getAttribute('data-role-name');
            
            // Set role name in confirmation dialog
            document.getElementById('deleteRoleName').textContent = roleName;
            
            // Store role ID to use when confirmed
            document.getElementById('btnConfirmDeleteRole').setAttribute('data-role-id', roleId);
            
            // Show modal
            new bootstrap.Modal(document.getElementById('deleteRoleModal')).show();
        });
    });

    // Confirm delete role button handler
    document.getElementById('btnConfirmDeleteRole').addEventListener('click', function() {
        const roleId = this.getAttribute('data-role-id');
        
        // Send API request
        fetch(`/admin/api/roles/${roleId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('deleteRoleModal')).hide();
            
            // Show success message
            showAlert(data.message, 'success');
            
            // Reload page to show updated data
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('An error occurred while deleting the role', 'danger');
        });
    });
});

/**
 * Display an alert message on the page
 * @param {string} message - The message to display
 * @param {string} type - The type of alert (success, danger, warning, info)
 */
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insert at the top of the main content area
    const mainContent = document.querySelector('main');
    mainContent.insertBefore(alertDiv, mainContent.firstChild.nextSibling.nextSibling);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => {
            alertDiv.remove();
        }, 150);
    }, 5000);
}