/**
 * Query Editor JS
 * 
 * JavaScript for the Query Editor functionality.
 */

// Initialize Monaco editor
let editor;

// Load Monaco editor
require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs' }});
require(['vs/editor/editor.main'], function() {
    editor = monaco.editor.create(document.getElementById('monaco-editor-container'), {
        value: '',
        language: 'sql',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: {
            enabled: true
        },
        scrollBeyondLastLine: false,
        fontSize: 14,
        tabSize: 2
    });
    
    // Add resize handler
    window.addEventListener('resize', function() {
        if(editor) {
            editor.layout();
        }
    });
});

// Document ready
$(document).ready(function() {
    // Execute query button click handler
    $('#executeQueryBtn').click(function() {
        const query = editor.getValue();
        if (!query.trim()) {
            showAlert('error', 'Query cannot be empty');
            return;
        }
        
        executeQuery(query);
    });
    
    // Format query button click handler
    $('#formatQueryBtn').click(function() {
        const query = editor.getValue();
        if (!query.trim()) {
            showAlert('error', 'Query cannot be empty');
            return;
        }
        
        showStatus('Formatting query...');
        
        $.ajax({
            url: '/api/format-query',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ 
                query: query 
            }),
            success: function(response) {
                hideStatus();
                if (response.status === 'success') {
                    editor.setValue(response.formatted_query);
                    showAlert('success', 'Query formatted successfully');
                } else {
                    showAlert('error', response.error || 'Error formatting query');
                }
            },
            error: function(xhr) {
                hideStatus();
                showAlert('error', xhr.responseJSON?.error || 'Error formatting query');
            }
        });
    });
    
    // Complete query button click handler
    $('#completeQueryBtn').click(function() {
        const query = editor.getValue();
        if (!query.trim()) {
            showQueryError('Query cannot be empty');
            return;
        }
        
        const workspace = $('#workspaceSelect').val(); // Using the workspace from main sidebar
        showStatus('Completing query...');
        hideQueryError(); // Hide any previous error
        
        $.ajax({
            url: '/api/complete-query',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ 
                query: query,
                workspace: workspace
            }),
            success: function(response) {
                hideStatus();
                if (response.status === 'success') {
                    editor.setValue(response.completed_query);
                    // Show a brief success message that auto-hides
                    $('#queryStatusText').text('Query completed successfully');
                    $('#querySpinner').hide();
                    $('#queryStatusArea').show();
                    setTimeout(() => {
                        $('#queryStatusArea').hide();
                    }, 2000);
                } else {
                    showQueryError(response.error || 'Error completing query');
                }
            },
            error: function(xhr) {
                hideStatus();
                showQueryError(xhr.responseJSON?.error || 'Error completing query');
            }
        });
    });
    
    // Save query button click handler
    $('#saveQueryBtn').click(function() {
        const query = editor.getValue();
        if (!query.trim()) {
            showQueryError('Query cannot be empty');
            return;
        }
        
        hideQueryError(); // Hide any previous error
        // Show save query modal
        $('#saveQueryModal').modal('show');
    });
    
    // Save query confirm button click handler
    $('#saveQueryConfirmBtn').click(function() {
        const queryName = $('#queryName').val();
        const queryDescription = $('#queryDescription').val();
        const query = editor.getValue();
        
        if (!queryName.trim()) {
            // Show error in modal
            const modalError = $('<div class="alert alert-danger alert-dismissible fade show mt-2" role="alert">' +
                'Query name is required' +
                '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                '</div>');
            $('#saveQueryForm').before(modalError);
            return;
        }
        
        $.ajax({
            url: '/api/save-query',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                query: query,
                name: queryName,
                description: queryDescription
            }),
            success: function(response) {
                $('#saveQueryModal').modal('hide');
                if (response.status === 'success') {
                    // Show a brief success message that auto-hides
                    $('#queryStatusText').text('Query saved successfully');
                    $('#querySpinner').hide();
                    $('#queryStatusArea').show();
                    setTimeout(() => {
                        $('#queryStatusArea').hide();
                    }, 2000);
                } else {
                    showQueryError(response.error || 'Error saving query');
                }
            },
            error: function(xhr) {
                $('#saveQueryModal').modal('hide');
                showQueryError(xhr.responseJSON?.error || 'Error saving query');
            }
        });
    });
    
    // View schema button click handler
    $('#viewSchemaEditorBtn').click(function() {
        // Trigger the schema modal from the existing schema view button
        $('#viewSchemaBtn').click();
    });
});

// Execute query function
function executeQuery(query) {
    showStatus('Executing query...');
    $('#resultsCard').hide();
    hideQueryError(); // Hide any previous error
    
    $.ajax({
        url: '/api/execute-query',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ query: query }),
        success: function(response) {
            hideStatus();
            if (response.status === 'success') {
                displayResults(response);
            } else {
                showQueryError(response.error || 'Error executing query');
            }
        },
        error: function(xhr) {
            hideStatus();
            showQueryError(xhr.responseJSON?.error || 'Error executing query');
        }
    });
}

// Display query results
function displayResults(response) {
    console.log("Displaying results:", response); // Debug log
    if (response.status === 'success') {
        // Always clean up existing DataTable first, regardless of whether we have results or not
        try {
            if ($.fn.DataTable.isDataTable('#queryEditorResultsTable')) {
                $('#queryEditorResultsTable').DataTable().destroy();
                console.log("Destroyed existing DataTable"); // Debug log
            }
            
            // Remove all content and event handlers to ensure clean slate
            $('#queryEditorResultsTable').empty();
        } catch (e) {
            console.error("Error destroying DataTable:", e);
        }
        
        // Create a completely fresh table structure
        $('#queryEditorResultsTable').html('<thead></thead><tbody></tbody>');
        
        // First make sure the results card is visible
        $('#resultsCard').show();
        
        if (response.results && response.results.length > 0) {
            console.log("Results found:", response.results.length, "rows"); // Debug log
            
            const tableHead = $('#queryEditorResultsTable thead');
            const tableBody = $('#queryEditorResultsTable tbody');
            
            // Hide no results message
            $('#noResultsMessage').hide();
            
            // Add table headers
            let headerRow = $('<tr>');
            response.columns.forEach(column => {
                headerRow.append($('<th>').text(column));
            });
            tableHead.append(headerRow);
            
            // Add table rows
            response.results.forEach(row => {
                let tableRow = $('<tr>');
                response.columns.forEach(column => {
                    tableRow.append($('<td>').text(row[column] !== null ? row[column] : 'NULL'));
                });
                tableBody.append(tableRow);
            });
            
            // Initialize DataTable with options - give DOM time to update
            setTimeout(() => {
                try {
                    $('#queryEditorResultsTable').DataTable({
                        responsive: false, // Disable responsive features
                        scrollX: true,      // Enable horizontal scrolling
                        scrollY: '350px',   // Enable vertical scrolling with fixed height
                        scrollCollapse: true,
                        pageLength: 10,
                        ordering: true,
                        searching: true,
                        destroy: true,      // Enable clean destruction
                        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'All']]
                    });
                    console.log("DataTable initialized"); // Debug log
                } catch (e) {
                    console.error("Error initializing DataTable:", e);
                    // Fallback to show data without DataTable functionality
                    $('#resultsCard').show();
                }
            }, 200);
        } else {
            // Show no results message
            $('#resultsCard').show();
            $('#resultsTableHead').empty();
            $('#resultsTableBody').empty();
            $('#noResultsMessage').show();
        }
    } else {
        showAlert('error', response.error || 'Error executing query');
    }
}

// Show status message
function showStatus(message) {
    $('#queryStatusText').text(message);
    $('#queryStatusArea').show();
    $('#querySpinner').show();
}

// Hide status message
function hideStatus() {
    $('#queryStatusArea').hide();
}

// Show query error in the dedicated error area
function showQueryError(errorMessage) {
    // Set error message text
    $('#queryErrorText').text(errorMessage);
    // Show error area
    $('#queryErrorArea').show();
    
    // Add click handler for close button if not already added
    $('#queryErrorCloseBtn').off('click').on('click', function() {
        hideQueryError();
    });
}

// Hide query error message
function hideQueryError() {
    $('#queryErrorArea').hide();
}

// Show alert message (still used for non-query-execution errors)
function showAlert(type, message, container = 'body') {
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const alertIcon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    
    // const alert = $(`
    //     <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
    //         <i class="fas ${alertIcon} me-2"></i> ${message}
    //         <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    //     </div>
    // `);
    
    // // Append alert to container
    // $(container).prepend(alert);
    
    // // Auto-dismiss after 5 seconds
    // setTimeout(() => {
    //     alert.alert('close');
    // }, 5000);
}
