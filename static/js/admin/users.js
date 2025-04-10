/**
 * User Management JavaScript
 * Handles user list and delete functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize delete modal functionality
    initDeleteModal();
});

/**
 * Setup the delete user modal with proper data
 */
function initDeleteModal() {
    // Get the delete modal element
    const deleteModal = document.getElementById('deleteModal');
    
    if (deleteModal) {
        // When the modal is shown, update its content with the user data
        deleteModal.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            
            // Extract user data from button attributes
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            
            // Update the modal content
            document.getElementById('deleteUserName').textContent = username;
            
            // Set up the form action for the delete operation
            const form = document.getElementById('deleteForm');
            form.action = `/api/admin/users/${userId}/delete`;
        });
    }
}