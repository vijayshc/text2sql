/**
 * knowledge-admin.js - Handles admin interface for knowledge base management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const documentsTable = $('#documentsTable').DataTable({
        responsive: true,
        order: [[4, 'desc']], // Sort by upload date by default
        language: {
            emptyTable: "No documents available in the knowledge base"
        }
    });
    
    // Upload document functionality
    const uploadForm = document.getElementById('uploadDocumentForm');
    const fileInput = document.getElementById('documentFile');
    const uploadBtn = document.getElementById('uploadDocumentBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = uploadProgress.querySelector('.progress-bar');
    const processingAlert = document.getElementById('processingAlert');
    const processingMessage = document.getElementById('processingMessage');
    
    uploadBtn.addEventListener('click', function() {
        // Validate form
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select a file to upload');
            return;
        }
        
        // Get form data
        const formData = new FormData(uploadForm);
        
        // Show progress bar
        uploadProgress.classList.remove('d-none');
        
        // Disable upload button during upload
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Uploading...';
        
        // Upload file
        fetch('/api/knowledge/upload', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
            headers: {
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update progress bar to 100%
                progressBar.style.width = '100%';
                progressBar.setAttribute('aria-valuenow', 100);
                
                // Hide progress bar and show processing alert
                setTimeout(() => {
                    uploadProgress.classList.add('d-none');
                    processingAlert.classList.remove('d-none');
                    
                    // Start polling for processing status
                    pollProcessingStatus(data.documentId);
                }, 500);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Error uploading document:', error);
            uploadProgress.classList.add('d-none');
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = 'Upload';
            alert('Error uploading document: ' + error.message);
        });
    });
    
    // Function to poll document processing status
    function pollProcessingStatus(documentId) {
        let pollInterval = setInterval(() => {
            fetch(`/api/knowledge/status/${documentId}`)
            .then(response => response.json())
            .then(data => {
                // Update processing message
                processingMessage.textContent = data.message;
                
                // Check if processing is complete or failed
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    
                    // Show success message
                    processingAlert.classList.remove('alert-info');
                    processingAlert.classList.add('alert-success');
                    processingMessage.innerHTML = '<i class="fas fa-check-circle me-1"></i> Document processed successfully!';
                    
                    // Reload page after a short delay to show the new document
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    
                    // Show error message
                    processingAlert.classList.remove('alert-info');
                    processingAlert.classList.add('alert-danger');
                    processingMessage.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i> Error: ${data.message}`;
                    
                    // Re-enable upload button
                    uploadBtn.disabled = false;
                    uploadBtn.innerHTML = 'Upload';
                }
            })
            .catch(error => {
                console.error('Error polling status:', error);
            });
        }, 2000); // Poll every 2 seconds
    }
    
    // Handle document deletion
    const deleteConfirmModal = document.getElementById('deleteConfirmModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    let documentToDelete = null;
    
    // Setup delete button click events (using event delegation)
    $('#documentsTable').on('click', '.delete-document', function() {
        documentToDelete = $(this).closest('tr').data('document-id');
        const modal = new bootstrap.Modal(deleteConfirmModal);
        modal.show();
    });
    
    // Handle confirm delete button
    confirmDeleteBtn.addEventListener('click', function() {
        if (!documentToDelete) return;
        
        // Send delete request
        fetch(`/api/knowledge/delete/${documentToDelete}`, {
            method: 'DELETE',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Close modal
                bootstrap.Modal.getInstance(deleteConfirmModal).hide();
                
                // Remove row from table
                documentsTable.row($(`tr[data-document-id="${documentToDelete}"]`)).remove().draw();
                
                // Show success toast
                alert('Document deleted successfully');
            } else {
                throw new Error(data.error || 'Failed to delete document');
            }
        })
        .catch(error => {
            console.error('Error deleting document:', error);
            alert('Error deleting document: ' + error.message);
        })
        .finally(() => {
            documentToDelete = null;
        });
    });
    
    // Paste Text functionality
    const textForm = document.getElementById('pasteTextForm');
    const contentNameInput = document.getElementById('contentName');
    const contentTypeSelect = document.getElementById('contentType');
    const contentTextArea = document.getElementById('contentText');
    const contentTagsInput = document.getElementById('contentTags');
    const submitTextBtn = document.getElementById('submitTextBtn');
    const textProcessProgress = document.getElementById('textProcessProgress');
    const progressBarText = textProcessProgress.querySelector('.progress-bar');
    const textProcessingAlert = document.getElementById('textProcessingAlert');
    const textProcessingMessage = document.getElementById('textProcessingMessage');
    
    submitTextBtn.addEventListener('click', function() {
        // Basic validation
        if (!contentNameInput.value.trim()) {
            alert('Please enter a content name');
            return;
        }
        
        if (!contentTypeSelect.value) {
            alert('Please select a content type');
            return;
        }
        
        if (!contentTextArea.value.trim()) {
            alert('Please enter some content text');
            return;
        }
        
        // Prepare data for submission
        const data = {
            name: contentNameInput.value.trim(),
            content_type: contentTypeSelect.value,
            content: contentTextArea.value.trim(),
            tags: contentTagsInput.value ? contentTagsInput.value.split(',').map(tag => tag.trim()) : []
        };
        
        // Show progress bar
        textProcessProgress.classList.remove('d-none');
        
        // Disable submit button during processing
        submitTextBtn.disabled = true;
        submitTextBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processing...';
        
        // Send text data to server
        fetch('/api/knowledge/text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Submission failed');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update progress bar to 100%
                progressBarText.style.width = '100%';
                progressBarText.setAttribute('aria-valuenow', 100);
                
                // Hide progress bar and show processing alert
                setTimeout(() => {
                    textProcessProgress.classList.add('d-none');
                    textProcessingAlert.classList.remove('d-none');
                    
                    // Start polling for processing status
                    pollProcessingStatus(data.documentId);
                }, 500);
            } else {
                throw new Error(data.error || 'Submission failed');
            }
        })
        .catch(error => {
            console.error('Error submitting text:', error);
            textProcessProgress.classList.add('d-none');
            submitTextBtn.disabled = false;
            submitTextBtn.innerHTML = 'Add Content';
            alert('Error submitting text content: ' + error.message);
        });
    });
    
    // Reset modal form when it's closed
    $('#pasteTextModal').on('hidden.bs.modal', function() {
        textForm.reset();
        textProcessProgress.classList.add('d-none');
        textProcessingAlert.classList.add('d-none');
        submitTextBtn.disabled = false;
        submitTextBtn.innerHTML = 'Add Content';
    });
});
