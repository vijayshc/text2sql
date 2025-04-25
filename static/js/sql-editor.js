// filepath: /home/vijay/text2sql_react/static/js/sql-editor.js

/**
 * sql-editor.js - Integrates Monaco Editor in SQL Tab for manual editing and execution
 */

// Initialize Monaco editor for SQL tab
let sqlEditor;
require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs' }});
require(['vs/editor/editor.main'], function() {
    sqlEditor = monaco.editor.create(document.getElementById('sqlEditorContainer'), {
        value: '',
        language: 'sql',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        tabSize: 2
    });
    // Resize handler
    window.addEventListener('resize', () => sqlEditor.layout());
});

// Set generated SQL into editor when results are displayed
(function() {
    const originalDisplayResults = resultsDisplay.displayResults;
    resultsDisplay.displayResults = function(result) {
        originalDisplayResults.call(this, result);
        if (sqlEditor && result.sql) {
            sqlEditor.setValue(result.sql);
        }
    };
})();

// Run SQL button handler
$(document).ready(function() {
    $('#runSqlBtn').click(function() {
        const query = sqlEditor.getValue().trim();
        if (!query) {
            uiUtils.showError('Query cannot be empty');
            return;
        }
        uiUtils.showLoading();
        $.ajax({
            url: '/api/execute-query',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ query: query }),
            success: function(response) {
                uiUtils.hideLoading();
                if (response.status === 'success') {
                    // Switch to Results tab
                    const resultsLink = document.querySelector('[href="#results"]');
                    if (resultsLink) new bootstrap.Tab(resultsLink).show();
                    // Render table
                    resultsDisplay.initializeDataTable(response.columns, response.results);
                    // Save chart data for dashboard tab
                    text2sql.currentResult = text2sql.currentResult || {};
                    text2sql.currentResult.chart_data = {
                        columns: response.columns,
                        data: response.results
                    };
                } else {
                    uiUtils.showError(response.error || 'Error executing SQL query');
                }
            },
            error: function(xhr) {
                uiUtils.hideLoading();
                uiUtils.showError(xhr.responseJSON?.error || 'Error executing SQL query');
            }
        });
    });
});
