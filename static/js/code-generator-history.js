/**
 * Code Generator History JavaScript
 * Handles history viewing with Monaco Editor
 */

let monacoEditor = null;
let currentFilePath = null;
let originalCode = null;

document.addEventListener('DOMContentLoaded', function() {
    initMonacoEditor();
    initDetailModal();
});

/**
 * Initialize Monaco Editor
 */
function initMonacoEditor() {
    require.config({ 
        paths: { 
            'vs': '/static/vendor/monaco-editor/0.36.1/min/vs' 
        }
    });
    
    require(['vs/editor/editor.main'], function() {
        console.log('Monaco Editor loaded successfully');
    });
}

/**
 * Create Monaco Editor instance
 */
function createMonacoEditor(code) {
    if (monacoEditor) {
        monacoEditor.dispose();
    }
    
    require(['vs/editor/editor.main'], function() {
        monacoEditor = monaco.editor.create(document.getElementById('monacoEditorContainer'), {
            value: code,
            language: 'sql',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            readOnly: false
        });
        
        // Track changes
        monacoEditor.onDidChangeModelContent(function() {
            const currentCode = monacoEditor.getValue();
            const hasChanges = currentCode !== originalCode;
            
            const saveBtn = document.getElementById('saveCodeBtn');
            if (hasChanges) {
                saveBtn.style.display = 'inline-block';
            } else {
                saveBtn.style.display = 'none';
            }
        });
    });
}

/**
 * Setup the detail modal
 */
function initDetailModal() {
    const detailModal = document.getElementById('detailModal');
    
    if (detailModal) {
        detailModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const recordId = button.getAttribute('data-record-id');
            
            // Show loading, hide content
            document.getElementById('modalLoading').style.display = 'block';
            document.getElementById('modalContent').style.display = 'none';
            
            // Reset save button
            document.getElementById('saveCodeBtn').style.display = 'none';
            
            // Fetch details
            fetch(`/code-generator/api/history/${recordId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        displayDetails(data.history);
                        document.getElementById('modalLoading').style.display = 'none';
                        document.getElementById('modalContent').style.display = 'block';
                    } else {
                        alert('Error loading details: ' + (data.error || 'Unknown error'));
                        bootstrap.Modal.getInstance(detailModal).hide();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error loading details');
                    bootstrap.Modal.getInstance(detailModal).hide();
                });
        });
        
        // Cleanup on modal close
        detailModal.addEventListener('hidden.bs.modal', function() {
            if (monacoEditor) {
                monacoEditor.dispose();
                monacoEditor = null;
            }
            currentFilePath = null;
            originalCode = null;
        });
    }
    
    // Setup copy button
    document.getElementById('copyCodeBtn').addEventListener('click', function() {
        if (!monacoEditor) {
            alert('Editor not initialized');
            return;
        }
        
        const code = monacoEditor.getValue();
        navigator.clipboard.writeText(code).then(() => {
            const btn = this;
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            btn.classList.remove('btn-outline-primary');
            btn.classList.add('btn-success');
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-primary');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
            alert('Failed to copy code to clipboard');
        });
    });
    
    // Setup save button
    document.getElementById('saveCodeBtn').addEventListener('click', function() {
        if (!monacoEditor || !currentFilePath) {
            alert('Cannot save: Editor or file path not available');
            return;
        }
        
        const code = monacoEditor.getValue();
        
        // Confirm save
        if (!confirm('Save changes to the SQL file?')) {
            return;
        }
        
        const btn = this;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        // Save code
        fetch('/code-generator/api/save-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file: currentFilePath,
                code: code
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                originalCode = code;
                btn.style.display = 'none';
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
                
                // Show success message
                alert('Code saved successfully!');
            } else {
                alert('Error saving code: ' + (data.error || 'Unknown error'));
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving code');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
        });
    });
}

/**
 * Display details in modal
 */
function displayDetails(record) {
    document.getElementById('detailUser').textContent = record.username || 'Unknown';
    document.getElementById('detailProject').textContent = record.project_name || '-';
    document.getElementById('detailMapping').textContent = record.mapping_name || '-';
    
    const statusBadge = record.status === 'success' 
        ? '<span class="badge bg-success">Success</span>'
        : '<span class="badge bg-danger">Error</span>';
    document.getElementById('detailStatus').innerHTML = statusBadge;
    
    const createdAt = record.started_at ? new Date(record.started_at).toLocaleString() : '-';
    document.getElementById('detailCreatedAt').textContent = createdAt;
    
    const duration = record.duration_seconds ? record.duration_seconds.toFixed(1) + 's' : '-';
    document.getElementById('detailDuration').textContent = duration;
    
    document.getElementById('detailCodeLines').textContent = record.code_lines || '-';
    document.getElementById('detailOutputFile').textContent = record.output_file || '-';
    
    // Tables used - already an array from API
    const tables = record.table_names || [];
    document.getElementById('detailTables').innerHTML = tables.length > 0 
        ? tables.map(t => `<span class="badge bg-secondary">${t}</span>`).join(' ')
        : '-';
    
    document.getElementById('detailHadExisting').textContent = record.had_existing_code ? 'Yes' : 'No';
    
    // Error section
    const errorSection = document.getElementById('detailErrorSection');
    if (record.error_message) {
        document.getElementById('detailError').textContent = record.error_message;
        errorSection.style.display = 'block';
    } else {
        errorSection.style.display = 'none';
    }
    
    // Load generated code
    currentFilePath = record.output_file;
    loadGeneratedCode(currentFilePath);
}

/**
 * Load generated code from file
 */
function loadGeneratedCode(filePath) {
    if (!filePath) {
        createMonacoEditor('-- No code file available --');
        return;
    }
    
    createMonacoEditor('-- Loading code... --');
    
    // Read file via API
    fetch(`/code-generator/api/read-code?file=${encodeURIComponent(filePath)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                originalCode = data.code;
                createMonacoEditor(data.code);
            } else {
                createMonacoEditor(`-- Error loading code: ${data.error || 'Unknown error'} --`);
            }
        })
        .catch(error => {
            console.error('Error loading code:', error);
            createMonacoEditor('-- Error loading code --');
        });
}
