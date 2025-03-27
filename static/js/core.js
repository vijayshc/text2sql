/**
 * core.js - Core initialization and shared variables for Text2SQL application
 */

// Global variables accessible to all modules
const text2sql = {
    dataTable: null,
    progressInterval: null,
    selectedTables: [],
    workspaceSelect: null,
    queryInput: null,
    submitButton: null,
    viewSchemaBtn: null,
    schemaModal: null,
    loadingSpinner: null
};

// Initialize core functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize references to important DOM elements
    text2sql.workspaceSelect = document.getElementById('workspaceSelect');
    text2sql.queryInput = document.getElementById('queryInput');
    text2sql.submitButton = document.getElementById('submitQuery');
    text2sql.viewSchemaBtn = document.getElementById('viewSchemaBtn');
    
    const schemaModalElement = document.getElementById('schemaModal');
    if (schemaModalElement) {
        text2sql.schemaModal = new bootstrap.Modal(schemaModalElement);
    }
    
    text2sql.loadingSpinner = document.getElementById('loadingSpinner');
    
    // Initialize the workspace description if element exists
    if (text2sql.workspaceSelect) {
        updateWorkspaceDescription();
    }
    
    // Set up primary event listeners, with null checks
    if (text2sql.workspaceSelect) {
        text2sql.workspaceSelect.addEventListener('change', function() {
            updateWorkspaceDescription();
            // Reload table names when workspace changes
            if (typeof tableMentions !== 'undefined') {
                tableMentions.fetchTableNames();
                // Reset selected tables when workspace changes
                text2sql.selectedTables = [];
                tableMentions.updateSelectedTablesDisplay();
            }
        });
    }
    
    if (text2sql.submitButton) {
        text2sql.submitButton.addEventListener('click', queryHandler.submitQuery);
    }
    
    if (text2sql.viewSchemaBtn) {
        text2sql.viewSchemaBtn.addEventListener('click', function() {
            if (typeof schemaManager !== 'undefined' && schemaManager.loadSchema) {
                schemaManager.loadSchema.call(schemaManager);
            }
        });
    }
    
    // Setup input field event listeners
    if (text2sql.queryInput) {
        text2sql.queryInput.addEventListener('keydown', tableMentions.handleQueryKeydown);
        text2sql.queryInput.addEventListener('input', tableMentions.handleQueryInput);
        text2sql.queryInput.addEventListener('blur', function(e) {
            // Don't hide dropdown if clicking inside it
            if (tableMentions.tableMentionDropdown && !tableMentions.tableMentionDropdown.contains(e.relatedTarget)) {
                tableMentions.hideTableMentionDropdown();
            }
        });
    }
    
    // Initialize empty table and fetch table names for autocomplete if these functions exist
    if (typeof resultsDisplay !== 'undefined' && resultsDisplay.initializeEmptyTable) {
        resultsDisplay.initializeEmptyTable();
    }
    
    if (typeof tableMentions !== 'undefined' && tableMentions.fetchTableNames) {
        tableMentions.fetchTableNames();
    }
});

// Update the workspace description in the UI
function updateWorkspaceDescription() {
    const workspaceSelect = document.getElementById('workspaceSelect');
    const descriptionElement = document.querySelector('.workspace-description');
    
    if (workspaceSelect && descriptionElement) {
        const selectedWorkspace = workspaceSelect.value;
        
        // Find the workspace description from the server
        fetch(`/api/workspaces`)
            .then(response => response.json())
            .then(data => {
                const workspace = data.workspaces.find(w => w.name === selectedWorkspace);
                if (workspace) {
                    descriptionElement.textContent = workspace.description;
                } else {
                    descriptionElement.textContent = '';
                }
            })
            .catch(error => {
                console.error('Error fetching workspace description:', error);
                descriptionElement.textContent = '';
            });
    }
}

// Global event listener to close dropdowns when clicking elsewhere
document.addEventListener('click', function(e) {
    // Hide dropdown when clicking outside
    if (tableMentions.tableMentionDropdown && 
        !tableMentions.tableMentionDropdown.contains(e.target) && 
        e.target !== text2sql.queryInput) {
        tableMentions.hideTableMentionDropdown();
    }
});