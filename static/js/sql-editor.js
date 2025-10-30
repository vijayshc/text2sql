// filepath: /home/vijay/text2sql_react/static/js/sql-editor.js

/**
 * sql-editor.js - Integrates Monaco Editor in SQL Tab for manual editing and execution
 */

// Initialize Monaco editor for SQL tab
let sqlEditor;
require.config({ paths: { 'vs': '/static/vendor/monaco-editor/0.45.0/min/vs' }});

// Wait for DOM to be fully loaded before initializing the editor
document.addEventListener('DOMContentLoaded', function() {
    require(['vs/editor/editor.main'], function() {
        // Make sure the container exists before creating the editor
        const editorContainer = document.getElementById('sqlEditorContainer');
        if (editorContainer) {
            sqlEditor = monaco.editor.create(editorContainer, {
                value: '',
                language: 'sql',
            theme: (window.themeManager && window.themeManager.getCurrentTheme && window.themeManager.getCurrentTheme() !== 'dark') ? 'vs' : 'vs-dark',
                automaticLayout: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                tabSize: 2
            });
            
            // Make editor accessible globally for schema browser to use
            window.sqlEditor = sqlEditor;
            
            // Resize handler
            window.addEventListener('resize', () => sqlEditor.layout());
        } else {
            console.error('SQL Editor container not found in the DOM');
        }
    });
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
        if (!sqlEditor) {
            uiUtils.showError('SQL Editor not initialized');
            return;
        }
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
