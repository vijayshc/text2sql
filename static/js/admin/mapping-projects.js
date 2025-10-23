/**
 * Mapping Projects Management
 * Handles project selection and document upload/management with DataTables
 */

let currentProject = null;
let projectsTable = null;
let documentsTable = null;
let projectsModal = null;
let projectFormModal = null;
let uploadMappingModal = null;
let deleteModal = null;
let deleteCallback = null;

// Initialize on page load
$(document).ready(function() {
    initializeModals();
    initializeUploadArea();
    setupEventListeners();
});

function initializeModals() {
    projectsModal = new bootstrap.Modal(document.getElementById('projectsModal'));
    projectFormModal = new bootstrap.Modal(document.getElementById('projectFormModal'));
    uploadMappingModal = new bootstrap.Modal(document.getElementById('uploadMappingModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
}

function initializeUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    
    // Click to browse
    uploadArea.addEventListener('click', () => fileInput.click());
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    
    // File selection
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect();
        }
    });
}

function setupEventListeners() {
    // Select Project button
    $('#selectProjectBtn').on('click', showProjectsModal);
    
    // Upload Mapping button
    $('#uploadMappingBtn').on('click', showUploadModal);
    
    // Create Project button
    $('#createProjectBtn').on('click', showCreateProjectForm);
    
    // Save Project button
    $('#saveProjectBtn').on('click', saveProject);
    
    // Confirm Delete button
    $('#confirmDeleteBtn').on('click', () => {
        if (deleteCallback) {
            deleteCallback();
        }
    });
}

function showProjectsModal() {
    loadProjects();
    projectsModal.show();
}

function loadProjects() {
    $.ajax({
        url: '/api/mapping-projects',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderProjectsTable(response.projects);
            } else {
                showAlert('danger', 'Failed to load projects');
            }
        },
        error: function(xhr) {
            showAlert('danger', 'Error loading projects: ' + (xhr.responseJSON?.error || xhr.statusText));
        }
    });
}

function renderProjectsTable(projects) {
    // Destroy existing DataTable if it exists
    if (projectsTable && $.fn.DataTable.isDataTable('#projectsTable')) {
        projectsTable.destroy();
        projectsTable = null;
    }
    
    const tbody = $('#projectsTable tbody');
    tbody.empty();
    
    projects.forEach(project => {
        const row = $('<tr>');
        row.append($('<td>').text(project.name));
        row.append($('<td>').text(project.description || ''));
        row.append($('<td>').text(new Date(project.created_at).toLocaleString()));
        
        const actions = $('<td>');
        actions.append(
            $('<button>').addClass('btn btn-sm btn-success me-1')
                .html('<i class="fas fa-check"></i> Select')
                .on('click', () => selectProject(project))
        );
        actions.append(
            $('<button>').addClass('btn btn-sm btn-outline-primary me-1')
                .html('<i class="fas fa-edit"></i>')
                .on('click', () => showEditProjectForm(project))
        );
        actions.append(
            $('<button>').addClass('btn btn-sm btn-outline-danger')
                .html('<i class="fas fa-trash"></i>')
                .on('click', () => confirmDeleteProject(project))
        );
        row.append(actions);
        
        tbody.append(row);
    });
    
    // Initialize DataTable
    projectsTable = $('#projectsTable').DataTable({
        order: [[2, 'desc']], // Sort by created_at descending
        pageLength: 10,
        language: {
            emptyTable: "No projects found. Click 'Create New Project' to get started."
        }
    });
}

function selectProject(project) {
    currentProject = project;
    projectsModal.hide();
    
    // Update UI
    $('#noProjectSelected').hide();
    $('#projectDetails').show();
    $('#uploadMappingBtn').show(); // Show upload button when project is selected
    $('#projectName').text(project.name);
    $('#projectDescription').text(project.description || 'No description');
    
    // Load documents for this project
    loadDocuments(project.id);
}

function showUploadModal() {
    if (!currentProject) {
        showAlert('warning', 'Please select a project first');
        return;
    }
    uploadMappingModal.show();
}

function loadDocuments(projectId) {
    $.ajax({
        url: `/api/mapping-projects/${projectId}/documents`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderDocumentsTable(response.documents);
            } else {
                showAlert('danger', 'Failed to load documents');
            }
        },
        error: function(xhr) {
            showAlert('danger', 'Error loading documents: ' + (xhr.responseJSON?.error || xhr.statusText));
        }
    });
}

function renderDocumentsTable(documents) {
    // Destroy existing DataTable if it exists
    if (documentsTable && $.fn.DataTable.isDataTable('#documentsTable')) {
        documentsTable.destroy();
        documentsTable = null;
    }
    
    const tbody = $('#documentsTable tbody');
    tbody.empty();
    
    documents.forEach(doc => {
        const row = $('<tr>');
        row.append($('<td>').text(doc.filename));
        row.append($('<td>').text(doc.uploaded_by_name || 'Unknown'));
        row.append($('<td>').text(new Date(doc.uploaded_at).toLocaleString()));
        
        const actions = $('<td>');
        actions.append(
            $('<button>').addClass('btn btn-sm btn-outline-primary me-1')
                .html('<i class="fas fa-download"></i>')
                .attr('title', 'Download')
                .on('click', () => downloadDocument(doc))
        );
        actions.append(
            $('<button>').addClass('btn btn-sm btn-outline-danger')
                .html('<i class="fas fa-trash"></i>')
                .attr('title', 'Delete')
                .on('click', () => confirmDeleteDocument(doc))
        );
        row.append(actions);
        
        tbody.append(row);
    });
    
    // Initialize DataTable
    documentsTable = $('#documentsTable').DataTable({
        order: [[2, 'desc']], // Sort by uploaded_at descending
        pageLength: 10,
        language: {
            emptyTable: "No documents uploaded yet. Drag and drop or click to upload."
        }
    });
}

function showCreateProjectForm() {
    $('#projectFormModalTitle').text('Create Project');
    $('#projectId').val('');
    $('#projectNameInput').val('');
    $('#projectDescInput').val('');
    projectsModal.hide();
    projectFormModal.show();
}

function showEditProjectForm(project) {
    $('#projectFormModalTitle').text('Edit Project');
    $('#projectId').val(project.id);
    $('#projectNameInput').val(project.name);
    $('#projectDescInput').val(project.description || '');
    projectsModal.hide();
    projectFormModal.show();
}

function saveProject() {
    const projectId = $('#projectId').val();
    const name = $('#projectNameInput').val().trim();
    const description = $('#projectDescInput').val().trim();
    
    if (!name) {
        showAlert('warning', 'Project name is required');
        return;
    }
    
    const url = projectId ? `/api/mapping-projects/${projectId}` : '/api/mapping-projects';
    const method = projectId ? 'PUT' : 'POST';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify({ name, description }),
        success: function(response) {
            if (response.success) {
                showAlert('success', projectId ? 'Project updated successfully' : 'Project created successfully');
                projectFormModal.hide();
                loadProjects();
                projectsModal.show();
            } else {
                showAlert('danger', response.error || 'Failed to save project');
            }
        },
        error: function(xhr) {
            showAlert('danger', 'Error saving project: ' + (xhr.responseJSON?.error || xhr.statusText));
        }
    });
}

function confirmDeleteProject(project) {
    $('#deleteMessage').text(`Are you sure you want to delete the project "${project.name}"? This will also delete all documents in this project.`);
    deleteCallback = () => deleteProject(project.id);
    projectsModal.hide();
    deleteModal.show();
}

function deleteProject(projectId) {
    $.ajax({
        url: `/api/mapping-projects/${projectId}`,
        method: 'DELETE',
        success: function(response) {
            if (response.success) {
                showAlert('success', 'Project deleted successfully');
                deleteModal.hide();
                loadProjects();
                projectsModal.show();
                
                // If deleted project was selected, clear selection
                if (currentProject && currentProject.id === projectId) {
                    currentProject = null;
                    $('#projectDetails').hide();
                    $('#noProjectSelected').show();
                    $('#uploadMappingBtn').hide(); // Hide upload button when no project selected
                }
            } else {
                showAlert('danger', response.error || 'Failed to delete project');
            }
        },
        error: function(xhr) {
            showAlert('danger', 'Error deleting project: ' + (xhr.responseJSON?.error || xhr.statusText));
        }
    });
}

function handleFileSelect() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    if (!currentProject) {
        showAlert('warning', 'Please select a project first');
        fileInput.value = '';
        return;
    }
    
    const allowedExtensions = ['.xlsx', '.xls'];
    const fileName = file.name.toLowerCase();
    const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));
    
    if (!isValid) {
        showAlert('danger', 'Invalid file type. Only .xlsx and .xls files are allowed.');
        fileInput.value = '';
        return;
    }
    
    uploadDocument(file);
}

function uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showAlert('info', 'Uploading document...');
    
    $.ajax({
        url: `/api/mapping-projects/${currentProject.id}/documents/upload`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                showAlert('success', 'Document uploaded successfully');
                document.getElementById('fileInput').value = '';
                uploadMappingModal.hide(); // Hide the modal after successful upload
                loadDocuments(currentProject.id);
            } else {
                showAlert('danger', response.error || 'Failed to upload document');
            }
        },
        error: function(xhr) {
            showAlert('danger', 'Error uploading document: ' + (xhr.responseJSON?.error || xhr.statusText));
        }
    });
}

function downloadDocument(doc) {
    window.location.href = `/api/mapping-projects/${doc.project_id}/documents/${doc.id}/download`;
}

function confirmDeleteDocument(doc) {
    $('#deleteMessage').text(`Are you sure you want to delete "${doc.filename}"?`);
    deleteCallback = () => deleteDocument(doc);
    deleteModal.show();
}

function deleteDocument(doc) {
    $.ajax({
        url: `/api/mapping-projects/${doc.project_id}/documents/${doc.id}`,
        method: 'DELETE',
        success: function(response) {
            if (response.success) {
                showAlert('success', 'Document deleted successfully');
                deleteModal.hide();
                loadDocuments(currentProject.id);
            } else {
                showAlert('danger', response.error || 'Failed to delete document');
            }
        },
        error: function(xhr) {
            showAlert('danger', 'Error deleting document: ' + (xhr.responseJSON?.error || xhr.statusText));
        }
    });
}

function showAlert(type, message) {
    // Remove any existing alerts
    $('.alert-container').remove();
    
    const alertHtml = `
        <div class="alert-container position-fixed top-0 start-50 translate-middle-x mt-3" style="z-index: 9999;">
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        </div>
    `;
    
    $('body').append(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        $('.alert-container').fadeOut(() => $('.alert-container').remove());
    }, 5000);
}
