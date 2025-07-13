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
    
    // Document viewer elements
    const documentViewerModal = document.getElementById('documentViewerModal');
    const documentTitle = document.getElementById('documentTitle');
    const documentMeta = document.getElementById('documentMeta');
    const viewOriginalBtn = document.getElementById('viewOriginalBtn');
    const viewMarkdownBtn = document.getElementById('viewMarkdownBtn');
    const documentLoading = document.getElementById('documentLoading');
    const originalDocumentContainer = document.getElementById('originalDocumentContainer');
    const markdownDocumentContainer = document.getElementById('markdownDocumentContainer');
    const documentError = document.getElementById('documentError');
    const documentErrorMessage = document.getElementById('documentErrorMessage');
    const originalDocumentContent = document.getElementById('originalDocumentContent');
    const markdownDocumentContent = document.getElementById('markdownDocumentContent');
    
    let currentDocumentId = null;
    let currentDocumentInfo = null;
    
    // Handle document view button clicks
    $('#documentsTable').on('click', '.view-document', function() {
        currentDocumentId = $(this).data('document-id');
        const filename = $(this).data('filename');
        
        // Show the modal
        const modal = new bootstrap.Modal(documentViewerModal);
        modal.show();
        
        // Reset UI state
        showLoading();
        documentTitle.textContent = filename;
        documentMeta.textContent = 'Loading document information...';
        
        // Load document information
        loadDocumentInfo(currentDocumentId);
    });
    
    // View Original button click
    viewOriginalBtn.addEventListener('click', function() {
        if (currentDocumentId && currentDocumentInfo) {
            showOriginalDocument();
        }
    });
    
    // View Markdown button click
    viewMarkdownBtn.addEventListener('click', function() {
        if (currentDocumentId && currentDocumentInfo) {
            showMarkdownDocument();
        }
    });
    
    function showLoading() {
        documentLoading.classList.remove('d-none');
        originalDocumentContainer.classList.add('d-none');
        markdownDocumentContainer.classList.add('d-none');
        documentError.classList.add('d-none');
    }
    
    function showError(message) {
        documentLoading.classList.add('d-none');
        originalDocumentContainer.classList.add('d-none');
        markdownDocumentContainer.classList.add('d-none');
        documentError.classList.remove('d-none');
        documentErrorMessage.textContent = message;
    }
    
    function loadDocumentInfo(documentId) {
        fetch(`/api/knowledge/info/${documentId}`, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load document information');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                currentDocumentInfo = data.document;
                updateDocumentInfo(currentDocumentInfo);
                // Default to showing markdown view
                showMarkdownDocument();
            } else {
                throw new Error(data.error || 'Failed to load document information');
            }
        })
        .catch(error => {
            console.error('Error loading document info:', error);
            showError('Failed to load document information: ' + error.message);
        });
    }
    
    function updateDocumentInfo(docInfo) {
        documentTitle.textContent = docInfo.original_filename;
        
        const statusBadge = getStatusBadge(docInfo.status);
        const metaInfo = `
            ${statusBadge} • ${docInfo.content_type?.toUpperCase() || 'UNKNOWN'} • 
            ${docInfo.chunk_count || 0} chunks • 
            Uploaded: ${new Date(docInfo.created_at).toLocaleDateString()}
        `;
        documentMeta.innerHTML = metaInfo;
        
        // Enable/disable buttons based on status
        viewOriginalBtn.disabled = docInfo.status !== 'completed';
        viewMarkdownBtn.disabled = docInfo.status !== 'completed';
        
        if (docInfo.status !== 'completed') {
            const reason = docInfo.status === 'error' ? 'processing failed' : 'still processing';
            viewOriginalBtn.title = `Document ${reason}`;
            viewMarkdownBtn.title = `Document ${reason}`;
        } else {
            viewOriginalBtn.title = 'View original document';
            viewMarkdownBtn.title = 'View processed markdown';
        }
    }
    
    function getStatusBadge(status) {
        switch (status) {
            case 'completed':
                return '<span class="badge bg-success">Completed</span>';
            case 'processing':
                return '<span class="badge bg-warning">Processing</span>';
            case 'error':
                return '<span class="badge bg-danger">Error</span>';
            default:
                return '<span class="badge bg-secondary">' + status + '</span>';
        }
    }
    
    function showOriginalDocument() {
        showLoading();
        
        // Update button states
        viewOriginalBtn.classList.add('active');
        viewMarkdownBtn.classList.remove('active');
        
        // For most file types, we'll open in a new tab
        const contentType = currentDocumentInfo.content_type?.toLowerCase();
        
        if (contentType === 'txt') {
            // For text files, load content directly
            fetch(`/api/knowledge/view/original/${currentDocumentId}`, {
                method: 'GET',
                credentials: 'same-origin'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load original document');
                }
                return response.text();
            })
            .then(content => {
                originalDocumentContent.innerHTML = `<pre class="markdown-content">${escapeHtml(content)}</pre>`;
                documentLoading.classList.add('d-none');
                originalDocumentContainer.classList.remove('d-none');
                markdownDocumentContainer.classList.add('d-none');
                documentError.classList.add('d-none');
            })
            .catch(error => {
                console.error('Error loading original document:', error);
                showError('Failed to load original document: ' + error.message);
            });
        } else {
            // For other file types (PDF, DOCX, etc.), embed or provide download link
            const downloadUrl = `/api/knowledge/view/original/${currentDocumentId}`;
            
            if (contentType === 'pdf') {
                // Embed PDF
                originalDocumentContent.innerHTML = `
                    <iframe src="${downloadUrl}" class="original-document-iframe" type="application/pdf">
                        <p>Your browser does not support PDF viewing. 
                        <a href="${downloadUrl}" target="_blank" class="btn btn-primary btn-sm">
                            <i class="fas fa-download me-1"></i>Download PDF
                        </a></p>
                    </iframe>
                `;
            } else {
                // For other file types, provide download link
                originalDocumentContent.innerHTML = `
                    <div class="text-center py-5">
                        <i class="fas fa-file fa-3x mb-3 text-muted"></i>
                        <h5>Preview not available for this file type</h5>
                        <p class="text-muted mb-3">File type: ${contentType?.toUpperCase() || 'Unknown'}</p>
                        <a href="${downloadUrl}" target="_blank" class="btn btn-primary">
                            <i class="fas fa-download me-1"></i>Download Original File
                        </a>
                    </div>
                `;
            }
            
            documentLoading.classList.add('d-none');
            originalDocumentContainer.classList.remove('d-none');
            markdownDocumentContainer.classList.add('d-none');
            documentError.classList.add('d-none');
        }
    }
    
    function showMarkdownDocument() {
        showLoading();
        
        // Update button states
        viewOriginalBtn.classList.remove('active');
        viewMarkdownBtn.classList.add('active');
        
        fetch(`/api/knowledge/view/markdown/${currentDocumentId}`, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load markdown content');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Convert markdown to HTML for better display
                markdownDocumentContent.innerHTML = `<div class="markdown-content">${convertMarkdownToHtml(data.markdown_content)}</div>`;
                
                documentLoading.classList.add('d-none');
                originalDocumentContainer.classList.add('d-none');
                markdownDocumentContainer.classList.remove('d-none');
                documentError.classList.add('d-none');
            } else {
                throw new Error(data.error || 'Failed to load markdown content');
            }
        })
        .catch(error => {
            console.error('Error loading markdown document:', error);
            showError('Failed to load processed content: ' + error.message);
        });
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function convertMarkdownToHtml(markdown) {
        // Simple markdown to HTML conversion for basic formatting
        let html = escapeHtml(markdown);
        
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
        
        // Line breaks
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        
        // Wrap in paragraphs
        html = '<p>' + html + '</p>';
        
        // Clean up empty paragraphs
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/<p><br><\/p>/g, '');
        
        return html;
    }
    
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
    
    // Reset document viewer modal when closed
    $('#documentViewerModal').on('hidden.bs.modal', function() {
        currentDocumentId = null;
        currentDocumentInfo = null;
        showLoading();
        viewOriginalBtn.classList.remove('active');
        viewMarkdownBtn.classList.remove('active');
        documentTitle.textContent = 'Loading...';
        documentMeta.textContent = 'Document information';
    });
});
