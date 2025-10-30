/**
 * File Browser - Admin Panel
 * OneDrive-style file browser with upload, download, edit, and delete capabilities
 */

(function() {
    'use strict';

    // State management
    let currentPath = '';
    let selectedItem = null;
    let allItems = [];
    let monacoEditor = null;
    let currentEditingFile = null;

    // DOM Elements
    const fileListBody = document.getElementById('fileListBody');
    const fileBreadcrumbs = document.getElementById('fileBreadcrumbs');
    const searchBox = document.getElementById('searchBox');
    const itemCount = document.getElementById('itemCount');
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    const uploadFolderBtn = document.getElementById('uploadFolderBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const deleteBtn = document.getElementById('deleteBtn');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    const fileEditorContainer = document.getElementById('fileEditorContainer');
    const monacoEditorContainer = document.getElementById('monacoEditorContainer');
    const editorFileName = document.getElementById('editorFileName');
    const saveFileBtn = document.getElementById('saveFileBtn');
    const closeEditorBtn = document.getElementById('closeEditorBtn');

    /**
     * Initialize the file browser
     */
    function init() {
        setupEventListeners();
        loadMonacoEditor();
        loadDirectory('');
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Upload buttons
        uploadFileBtn.addEventListener('click', () => fileInput.click());
        uploadFolderBtn.addEventListener('click', () => folderInput.click());
        
        // File inputs
        fileInput.addEventListener('change', handleFileUpload);
        folderInput.addEventListener('change', handleFolderUpload);
        
        // Action buttons
        downloadBtn.addEventListener('click', handleDownload);
        deleteBtn.addEventListener('click', handleDelete);
        
        // Search
        searchBox.addEventListener('input', handleSearch);
        
        // Editor buttons
        saveFileBtn.addEventListener('click', handleSaveFile);
        closeEditorBtn.addEventListener('click', closeEditor);

        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }

    /**
     * Load Monaco Editor
     */
    function loadMonacoEditor() {
        if (typeof require === 'undefined') {
            console.error('Monaco loader not found');
            return;
        }

        require.config({ 
            paths: { 
                'vs': '/static/vendor/monaco-editor/0.45.0/min/vs' 
            } 
        });

        require(['vs/editor/editor.main'], function() {
            console.log('Monaco Editor loaded successfully');
        });
    }

    /**
     * Load directory contents
     */
    function loadDirectory(path) {
        currentPath = path;
        showLoading();

        fetch(`/admin/file-browser/api/list?path=${encodeURIComponent(path)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load directory');
                }
                return response.json();
            })
            .then(data => {
                allItems = data.items || [];
                renderBreadcrumbs(data.breadcrumbs || []);
                renderFileList(allItems);
                updateItemCount(allItems.length);
                clearSelection();
            })
            .catch(error => {
                console.error('Error loading directory:', error);
                showToast('Error', 'Failed to load directory: ' + error.message, 'danger');
                renderFileList([]);
            });
    }

    /**
     * Render breadcrumbs
     */
    function renderBreadcrumbs(breadcrumbs) {
        fileBreadcrumbs.innerHTML = '';
        
        breadcrumbs.forEach((crumb, index) => {
            const li = document.createElement('li');
            li.className = 'breadcrumb-item';
            
            if (index === breadcrumbs.length - 1) {
                li.classList.add('active');
                li.textContent = crumb.label;
            } else {
                const a = document.createElement('a');
                a.href = '#';
                a.textContent = crumb.label;
                a.dataset.path = crumb.path;
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    loadDirectory(crumb.path);
                });
                li.appendChild(a);
            }
            
            fileBreadcrumbs.appendChild(li);
        });
    }

    /**
     * Render file list
     */
    function renderFileList(items) {
        fileListBody.innerHTML = '';

        if (items.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="5" class="text-center">No files or folders</td>';
            fileListBody.appendChild(tr);
            return;
        }

        // Add parent directory link if not at root
        if (currentPath) {
            const tr = createParentRow();
            fileListBody.appendChild(tr);
        }

        // Add files and folders
        items.forEach(item => {
            const tr = createFileRow(item);
            fileListBody.appendChild(tr);
        });
    }

    /**
     * Create parent directory row
     */
    function createParentRow() {
        const tr = document.createElement('tr');
        tr.className = 'file-browser-parent';
        tr.innerHTML = `
            <td></td>
            <td>
                <div class="file-name">
                    <i class="fas fa-level-up-alt"></i>
                    <div>
                        <div class="file-main-name">..</div>
                    </div>
                </div>
            </td>
            <td></td>
            <td></td>
            <td></td>
        `;
        
        tr.addEventListener('click', () => {
            const pathParts = currentPath.split('/').filter(p => p);
            pathParts.pop();
            loadDirectory(pathParts.join('/'));
        });
        
        return tr;
    }

    /**
     * Create file/folder row
     */
    function createFileRow(item) {
        const tr = document.createElement('tr');
        tr.dataset.item = JSON.stringify(item);
        
        const icon = getFileIcon(item);
        const modifiedDate = formatDate(item.modified);
        const size = item.isDirectory ? '' : formatFileSize(item.size);
        const uploadedBy = item.uploadedByName || '';
        
        tr.innerHTML = `
            <td>
                <input type="checkbox" class="form-check-input" data-path="${item.relativePath}">
            </td>
            <td>
                <div class="file-name">
                    <i class="fas ${icon}"></i>
                    <div>
                        <div class="file-main-name">${escapeHtml(item.name)}</div>
                    </div>
                </div>
            </td>
            <td>${modifiedDate}</td>
            <td>${size}</td>
            <td>${escapeHtml(uploadedBy)}</td>
        `;
        
        // Handle row selection
        const checkbox = tr.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            handleItemSelection(item, checkbox.checked);
        });
        
        // Handle row click
        tr.addEventListener('click', (e) => {
            if (e.target.tagName !== 'INPUT') {
                if (item.isDirectory) {
                    loadDirectory(item.relativePath);
                } else {
                    handleItemSelection(item, !checkbox.checked);
                    checkbox.checked = !checkbox.checked;
                }
            }
        });
        
        // Handle double-click for files
        tr.addEventListener('dblclick', (e) => {
            if (!item.isDirectory) {
                openFileEditor(item);
            }
        });
        
        return tr;
    }

    /**
     * Get icon for file type
     */
    function getFileIcon(item) {
        if (item.isDirectory) {
            return 'fa-folder';
        }
        
        const ext = item.name.split('.').pop().toLowerCase();
        const iconMap = {
            'pdf': 'fa-file-pdf',
            'doc': 'fa-file-word',
            'docx': 'fa-file-word',
            'xls': 'fa-file-excel',
            'xlsx': 'fa-file-excel',
            'ppt': 'fa-file-powerpoint',
            'pptx': 'fa-file-powerpoint',
            'jpg': 'fa-file-image',
            'jpeg': 'fa-file-image',
            'png': 'fa-file-image',
            'gif': 'fa-file-image',
            'svg': 'fa-file-image',
            'py': 'fa-file-code',
            'js': 'fa-file-code',
            'html': 'fa-file-code',
            'css': 'fa-file-code',
            'json': 'fa-file-code',
            'xml': 'fa-file-code',
            'sql': 'fa-file-code',
            'zip': 'fa-file-archive',
            'rar': 'fa-file-archive',
            'tar': 'fa-file-archive',
            'gz': 'fa-file-archive',
            'mp4': 'fa-file-video',
            'avi': 'fa-file-video',
            'mov': 'fa-file-video',
            'mp3': 'fa-file-audio',
            'wav': 'fa-file-audio',
            'txt': 'fa-file-alt',
            'md': 'fa-file-alt',
            'csv': 'fa-file-alt'
        };
        
        return iconMap[ext] || 'fa-file-alt';
    }

    /**
     * Handle item selection
     */
    function handleItemSelection(item, selected) {
        // Clear other selections
        document.querySelectorAll('.file-browser-table tbody tr').forEach(row => {
            row.classList.remove('selected');
        });
        document.querySelectorAll('.file-browser-table input[type="checkbox"]').forEach(cb => {
            if (cb.dataset.path !== item.relativePath) {
                cb.checked = false;
            }
        });
        
        if (selected) {
            selectedItem = item;
            const row = document.querySelector(`tr[data-item*='"${item.relativePath}"']`);
            if (row) {
                row.classList.add('selected');
            }
            downloadBtn.disabled = false;
            deleteBtn.disabled = false;
        } else {
            selectedItem = null;
            downloadBtn.disabled = true;
            deleteBtn.disabled = true;
        }
    }

    /**
     * Clear selection
     */
    function clearSelection() {
        selectedItem = null;
        downloadBtn.disabled = true;
        deleteBtn.disabled = true;
        document.querySelectorAll('.file-browser-table tbody tr').forEach(row => {
            row.classList.remove('selected');
        });
        document.querySelectorAll('.file-browser-table input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
    }

    /**
     * Handle file upload
     */
    function handleFileUpload(e) {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('path', currentPath);

        fetch('/admin/file-browser/api/upload-file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', 'File uploaded successfully', 'success');
                loadDirectory(currentPath);
            } else {
                showToast('Error', data.error || 'Failed to upload file', 'danger');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            showToast('Error', 'Failed to upload file', 'danger');
        })
        .finally(() => {
            fileInput.value = '';
        });
    }

    /**
     * Handle folder upload
     */
    function handleFolderUpload(e) {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
            formData.append('relative_paths', file.webkitRelativePath || file.name);
        });
        formData.append('path', currentPath);

        fetch('/admin/file-browser/api/upload-folder', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', `Uploaded ${data.files.length} files successfully`, 'success');
                loadDirectory(currentPath);
            } else {
                showToast('Error', data.error || 'Failed to upload folder', 'danger');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            showToast('Error', 'Failed to upload folder', 'danger');
        })
        .finally(() => {
            folderInput.value = '';
        });
    }

    /**
     * Handle download
     */
    function handleDownload() {
        if (!selectedItem) return;

        const path = selectedItem.relativePath;
        const url = selectedItem.isDirectory 
            ? `/admin/file-browser/api/download-folder?path=${encodeURIComponent(path)}`
            : `/admin/file-browser/api/download-file?path=${encodeURIComponent(path)}`;

        // Show download toast with auto-hide
        showToast('Download', 'Download started', 'success');
        
        // Create temporary link and trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = selectedItem.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    /**
     * Handle delete
     */
    function handleDelete() {
        if (!selectedItem) return;

        const itemType = selectedItem.isDirectory ? 'folder' : 'file';
        if (!confirm(`Are you sure you want to delete this ${itemType}?\n\n${selectedItem.name}`)) {
            return;
        }

        fetch('/admin/file-browser/api/item', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                path: selectedItem.relativePath
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', `${itemType} deleted successfully`, 'success');
                loadDirectory(currentPath);
            } else {
                showToast('Error', data.error || `Failed to delete ${itemType}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            showToast('Error', `Failed to delete ${itemType}`, 'danger');
        });
    }

    /**
     * Handle search
     */
    function handleSearch(e) {
        const searchTerm = e.target.value.toLowerCase();
        
        if (!searchTerm) {
            renderFileList(allItems);
            updateItemCount(allItems.length);
            return;
        }

        const filtered = allItems.filter(item => 
            item.name.toLowerCase().includes(searchTerm)
        );
        
        renderFileList(filtered);
        updateItemCount(filtered.length);
    }

    /**
     * Open file in Monaco editor
     */
    function openFileEditor(item) {
        const loadingToast = showToast('Loading', 'Loading file...', 'info');

        fetch(`/admin/file-browser/api/file-content?path=${encodeURIComponent(item.relativePath)}`)
            .then(response => response.json())
            .then(data => {
                // Hide loading toast
                hideToast(loadingToast);
                
                if (data.content !== undefined) {
                    currentEditingFile = item;
                    editorFileName.textContent = `Edit: ${item.name}`;
                    fileEditorContainer.style.display = 'flex';
                    
                    if (!monacoEditor) {
                        require(['vs/editor/editor.main'], function() {
                            createMonacoEditor(data.content, item.name);
                        });
                    } else {
                        monacoEditor.setValue(data.content);
                        setEditorLanguage(item.name);
                    }
                } else {
                    showToast('Error', data.error || 'Failed to load file', 'danger');
                }
            })
            .catch(error => {
                // Hide loading toast
                hideToast(loadingToast);
                console.error('Load file error:', error);
                showToast('Error', 'Failed to load file', 'danger');
            });
    }

    /**
     * Create Monaco editor instance
     */
    function createMonacoEditor(content, filename) {
        const theme = document.body.classList.contains('theme-light') || 
                     document.body.classList.contains('theme-lightColored') 
                     ? 'vs' : 'vs-dark';

        monacoEditor = monaco.editor.create(monacoEditorContainer, {
            value: content,
            language: getLanguageFromFilename(filename),
            theme: theme,
            automaticLayout: true,
            minimap: { enabled: true },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on'
        });
    }

    /**
     * Set editor language based on filename
     */
    function setEditorLanguage(filename) {
        if (monacoEditor) {
            const language = getLanguageFromFilename(filename);
            monaco.editor.setModelLanguage(monacoEditor.getModel(), language);
        }
    }

    /**
     * Get Monaco language from filename
     */
    function getLanguageFromFilename(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const languageMap = {
            'js': 'javascript',
            'py': 'python',
            'json': 'json',
            'html': 'html',
            'css': 'css',
            'sql': 'sql',
            'xml': 'xml',
            'md': 'markdown',
            'txt': 'plaintext',
            'csv': 'plaintext',
            'yaml': 'yaml',
            'yml': 'yaml'
        };
        return languageMap[ext] || 'plaintext';
    }

    /**
     * Handle file save
     */
    function handleSaveFile() {
        if (!monacoEditor || !currentEditingFile) return;

        const content = monacoEditor.getValue();

        fetch('/admin/file-browser/api/file-content', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                path: currentEditingFile.relativePath,
                content: content
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Success', 'File saved successfully', 'success');
                closeEditor();
                loadDirectory(currentPath);
            } else {
                showToast('Error', data.error || 'Failed to save file', 'danger');
            }
        })
        .catch(error => {
            console.error('Save error:', error);
            showToast('Error', 'Failed to save file', 'danger');
        });
    }

    /**
     * Close editor
     */
    function closeEditor() {
        fileEditorContainer.style.display = 'none';
        currentEditingFile = null;
        if (monacoEditor) {
            monacoEditor.setValue('');
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    function handleKeyboardShortcuts(e) {
        // Ctrl+S or Cmd+S to save in editor
        if ((e.ctrlKey || e.metaKey) && e.key === 's' && fileEditorContainer.style.display === 'flex') {
            e.preventDefault();
            handleSaveFile();
        }
        
        // Escape to close editor
        if (e.key === 'Escape' && fileEditorContainer.style.display === 'flex') {
            e.preventDefault();
            closeEditor();
        }
        
        // Delete key to delete selected item
        if (e.key === 'Delete' && selectedItem && fileEditorContainer.style.display === 'none') {
            e.preventDefault();
            handleDelete();
        }
    }

    /**
     * Show loading state
     */
    function showLoading() {
        fileListBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center">
                    <div class="file-browser-loading">
                        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Loading files...
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * Update item count
     */
    function updateItemCount(count) {
        itemCount.textContent = count;
    }

    /**
     * Show toast notification
     */
    function showToast(title, message, type = 'info') {
        const toastEl = document.getElementById('notificationToast');
        const toastTitle = document.getElementById('toastTitle');
        const toastBody = document.getElementById('toastBody');
        
        toastTitle.textContent = title;
        toastBody.textContent = message;
        
        // Remove existing background classes
        toastEl.classList.remove('bg-success', 'bg-danger', 'bg-info', 'bg-warning');
        
        // Add appropriate class based on type
        if (type === 'success') {
            toastEl.classList.add('bg-success');
        } else if (type === 'danger') {
            toastEl.classList.add('bg-danger');
        } else if (type === 'warning') {
            toastEl.classList.add('bg-warning');
        } else {
            toastEl.classList.add('bg-info');
        }
        
        // Always autohide, but with different delays based on type
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: type === 'success' ? 2000 : (type === 'danger' || type === 'warning') ? 5000 : 3000
        });
        toast.show();
        
        return toast; // Return toast instance for manual control if needed
    }

    /**
     * Hide toast notification
     */
    function hideToast(toast) {
        if (toast && typeof toast.hide === 'function') {
            toast.hide();
        } else {
            // Fallback: hide the toast element directly
            const toastEl = document.getElementById('notificationToast');
            if (toastEl) {
                const bsToast = bootstrap.Toast.getInstance(toastEl);
                if (bsToast) {
                    bsToast.hide();
                }
            }
        }
    }

    /**
     * Format date
     */
    function formatDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (days === 0) {
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        } else if (days === 1) {
            return 'Yesterday';
        } else if (days < 7) {
            return `${days} days ago`;
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
    }

    /**
     * Format file size
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Escape HTML
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
