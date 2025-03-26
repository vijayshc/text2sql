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
    text2sql.schemaModal = new bootstrap.Modal(document.getElementById('schemaModal'));
    text2sql.loadingSpinner = document.getElementById('loadingSpinner');
    
    // Initialize the workspace description
    updateWorkspaceDescription();

    // Set up primary event listeners
    text2sql.workspaceSelect.addEventListener('change', function() {
        updateWorkspaceDescription();
        // Reload table names when workspace changes
        tableMentions.fetchTableNames();
        // Reset selected tables when workspace changes
        text2sql.selectedTables = [];
        tableMentions.updateSelectedTablesDisplay();
    });

    text2sql.submitButton.addEventListener('click', queryHandler.submitQuery);
    text2sql.viewSchemaBtn.addEventListener('click', schemaManager.loadSchema);
    
    // Setup input field event listeners
    text2sql.queryInput.addEventListener('keydown', tableMentions.handleQueryKeydown);
    text2sql.queryInput.addEventListener('input', tableMentions.handleQueryInput);
    text2sql.queryInput.addEventListener('blur', function(e) {
        // Don't hide dropdown if clicking inside it
        if (tableMentions.tableMentionDropdown && !tableMentions.tableMentionDropdown.contains(e.relatedTarget)) {
            tableMentions.hideTableMentionDropdown();
        }
    });

    // Initialize empty table and fetch table names for autocomplete
    resultsDisplay.initializeEmptyTable();
    tableMentions.fetchTableNames();
});

// Update the workspace description in the UI
function updateWorkspaceDescription() {
    const selectedOption = text2sql.workspaceSelect.selectedOptions[0];
    const description = selectedOption.getAttribute('data-description') || '';
    document.querySelector('.workspace-description').textContent = description;
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