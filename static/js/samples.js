/**
 * samples.js - Sample questions and SQL management functionality
 */

const samples = {
    // Current state
    currentPage: 1,
    pageSize: 10,
    totalPages: 1,
    selectedTables: [],
    editSelectedTables: [],
    
    // Initialize samples functionality
    init: function() {
        // Load workspaces for dropdown
        samples.loadWorkspaces();
        
        // Load tables for the search input
        samples.loadTables();
        
        // Load existing samples
        samples.loadSamples();
        
        // Setup event listeners
        samples.setupEventListeners();
    },
    
    // Setup all event listeners
    setupEventListeners: function() {
        // Form submission for new samples
        document.getElementById('sampleForm').addEventListener('submit', function(e) {
            e.preventDefault();
            samples.saveSample();
        });
        
        // Table search functionality
        document.getElementById('tableSearch').addEventListener('input', function() {
            samples.handleTableSearch(this.value);
        });
        
        // Sample search functionality
        document.getElementById('sampleSearch').addEventListener('input', function() {
            samples.filterSamples(this.value);
        });
        
        // Pagination controls
        document.getElementById('prevPage').addEventListener('click', function() {
            if (samples.currentPage > 1) {
                samples.currentPage--;
                samples.loadSamples();
            }
        });
        
        document.getElementById('nextPage').addEventListener('click', function() {
            if (samples.currentPage < samples.totalPages) {
                samples.currentPage++;
                samples.loadSamples();
            }
        });
        
        // Modal action buttons
        document.getElementById('updateSampleBtn').addEventListener('click', function() {
            samples.updateSample();
        });
        
        document.getElementById('deleteSampleBtn').addEventListener('click', function() {
            samples.deleteSample();
        });
        
        // Modal table search
        document.getElementById('editTableSearch').addEventListener('input', function() {
            samples.handleEditTableSearch(this.value);
        });
        
        // Update selected tables when workspace changes
        document.getElementById('workspaceSelect').addEventListener('change', function() {
            samples.loadTables();
        });
        
        document.getElementById('editWorkspace').addEventListener('change', function() {
            samples.loadEditTables();
        });
    },
    
    // Load workspaces for dropdown
    loadWorkspaces: function() {
        fetch('/api/workspaces')
            .then(response => response.json())
            .then(data => {
                const workspaceSelect = document.getElementById('workspaceSelect');
                const editWorkspaceSelect = document.getElementById('editWorkspace');
                
                // Clear existing options
                workspaceSelect.innerHTML = '';
                editWorkspaceSelect.innerHTML = '';
                
                // Add workspaces to both dropdowns
                data.workspaces.forEach(workspace => {
                    const option = document.createElement('option');
                    option.value = workspace.name;
                    option.textContent = workspace.name;
                    workspaceSelect.appendChild(option);
                    
                    const editOption = document.createElement('option');
                    editOption.value = workspace.name;
                    editOption.textContent = workspace.name;
                    editWorkspaceSelect.appendChild(editOption);
                });
                
                // Set default workspace if available
                if (data.workspaces.length > 0) {
                    workspaceSelect.value = data.workspaces[0].name;
                    editWorkspaceSelect.value = data.workspaces[0].name;
                }
            })
            .catch(error => {
                console.error('Error loading workspaces:', error);
                uiUtils.showError('Failed to load workspaces');
            });
    },
    
    // Load tables based on selected workspace
    loadTables: function() {
        const workspace = document.getElementById('workspaceSelect').value;
        
        fetch(`/api/tables?workspace=${encodeURIComponent(workspace)}`)
            .then(response => response.json())
            .then(data => {
                samples.availableTables = data.tables;
                samples.updateSelectedTablesDisplay();
            })
            .catch(error => {
                console.error('Error loading tables:', error);
            });
    },
    
    // Load tables for edit modal
    loadEditTables: function() {
        const workspace = document.getElementById('editWorkspace').value;
        
        fetch(`/api/tables?workspace=${encodeURIComponent(workspace)}`)
            .then(response => response.json())
            .then(data => {
                samples.editAvailableTables = data.tables;
                samples.updateEditSelectedTablesDisplay();
            })
            .catch(error => {
                console.error('Error loading tables:', error);
            });
    },
    
    // Handle table search input
    handleTableSearch: function(query) {
        const resultsContainer = document.getElementById('tableSearchResults');
        
        if (!query || query.trim() === '') {
            resultsContainer.style.display = 'none';
            return;
        }
        
        // Filter tables based on query
        const matchingTables = samples.availableTables.filter(table => 
            table.toLowerCase().includes(query.toLowerCase())
        );
        
        // Display matching tables
        if (matchingTables.length > 0) {
            resultsContainer.innerHTML = '';
            
            matchingTables.forEach(tableName => {
                const item = document.createElement('a');
                item.classList.add('dropdown-item');
                item.href = '#';
                item.textContent = tableName;
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (!samples.selectedTables.includes(tableName)) {
                        samples.selectedTables.push(tableName);
                        samples.updateSelectedTablesDisplay();
                    }
                    document.getElementById('tableSearch').value = '';
                    resultsContainer.style.display = 'none';
                });
                resultsContainer.appendChild(item);
            });
            
            resultsContainer.style.display = 'block';
        } else {
            resultsContainer.style.display = 'none';
        }
    },
    
    // Handle table search in edit modal
    handleEditTableSearch: function(query) {
        const resultsContainer = document.getElementById('editTableSearchResults');
        
        if (!query || query.trim() === '') {
            resultsContainer.style.display = 'none';
            return;
        }
        
        // Filter tables based on query
        const matchingTables = samples.editAvailableTables.filter(table => 
            table.toLowerCase().includes(query.toLowerCase())
        );
        
        // Display matching tables
        if (matchingTables.length > 0) {
            resultsContainer.innerHTML = '';
            
            matchingTables.forEach(tableName => {
                const item = document.createElement('a');
                item.classList.add('dropdown-item');
                item.href = '#';
                item.textContent = tableName;
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (!samples.editSelectedTables.includes(tableName)) {
                        samples.editSelectedTables.push(tableName);
                        samples.updateEditSelectedTablesDisplay();
                    }
                    document.getElementById('editTableSearch').value = '';
                    resultsContainer.style.display = 'none';
                });
                resultsContainer.appendChild(item);
            });
            
            resultsContainer.style.display = 'block';
        } else {
            resultsContainer.style.display = 'none';
        }
    },
    
    // Update the display of selected tables
    updateSelectedTablesDisplay: function() {
        const container = document.getElementById('selectedTables');
        container.innerHTML = '';
        
        samples.selectedTables.forEach(tableName => {
            const tag = document.createElement('span');
            tag.classList.add('badge', 'bg-primary', 'd-flex', 'align-items-center');
            tag.innerHTML = `
                ${tableName}
                <button type="button" class="btn-close btn-close-white ms-2" 
                    aria-label="Remove ${tableName}"></button>
            `;
            
            tag.querySelector('.btn-close').addEventListener('click', function() {
                samples.selectedTables = samples.selectedTables.filter(t => t !== tableName);
                samples.updateSelectedTablesDisplay();
            });
            
            container.appendChild(tag);
        });
    },
    
    // Update the display of selected tables in edit modal
    updateEditSelectedTablesDisplay: function() {
        const container = document.getElementById('editSelectedTables');
        container.innerHTML = '';
        
        samples.editSelectedTables.forEach(tableName => {
            const tag = document.createElement('span');
            tag.classList.add('badge', 'bg-primary', 'd-flex', 'align-items-center');
            tag.innerHTML = `
                ${tableName}
                <button type="button" class="btn-close btn-close-white ms-2" 
                    aria-label="Remove ${tableName}"></button>
            `;
            
            tag.querySelector('.btn-close').addEventListener('click', function() {
                samples.editSelectedTables = samples.editSelectedTables.filter(t => t !== tableName);
                samples.updateEditSelectedTablesDisplay();
            });
            
            container.appendChild(tag);
        });
    },
    
    // Save a new sample
    saveSample: function() {
        const queryText = document.getElementById('queryText').value.trim();
        const sqlQuery = document.getElementById('sqlQuery').value.trim();
        const resultsSummary = document.getElementById('resultsSummary').value.trim();
        const workspace = document.getElementById('workspaceSelect').value;
        
        if (!queryText || !sqlQuery) {
            uiUtils.showError('Please provide both a question and SQL query');
            return;
        }
        
        const sampleData = {
            query_text: queryText,
            sql_query: sqlQuery,
            results_summary: resultsSummary || `Manual sample entry`,
            workspace: workspace,
            feedback_rating: 1, // Manual samples are always considered "positive" feedback
            tables_used: samples.selectedTables,
            is_manual_sample: true // Flag to identify manually added samples
        };
        
        fetch('/api/samples', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(sampleData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to save sample');
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            uiUtils.showSuccess('Sample saved successfully');
            
            // Clear form
            document.getElementById('queryText').value = '';
            document.getElementById('sqlQuery').value = '';
            document.getElementById('resultsSummary').value = '';
            samples.selectedTables = [];
            samples.updateSelectedTablesDisplay();
            
            // Reload samples
            samples.loadSamples();
        })
        .catch(error => {
            console.error('Error saving sample:', error);
            uiUtils.showError('Failed to save sample: ' + error.message);
        });
    },
    
    // Load existing samples
    loadSamples: function(searchQuery = '') {
        const url = searchQuery 
            ? `/api/samples?page=${samples.currentPage}&limit=${samples.pageSize}&query=${encodeURIComponent(searchQuery)}`
            : `/api/samples?page=${samples.currentPage}&limit=${samples.pageSize}`;
            
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load samples');
                }
                return response.json();
            })
            .then(data => {
                samples.renderSamplesTable(data.samples);
                samples.totalPages = Math.max(1, Math.ceil(data.total / samples.pageSize));
                
                // Update pagination info
                document.getElementById('paginationInfo').textContent = `Page ${samples.currentPage} of ${samples.totalPages}`;
                
                // Enable/disable pagination buttons
                document.getElementById('prevPage').disabled = samples.currentPage <= 1;
                document.getElementById('nextPage').disabled = samples.currentPage >= samples.totalPages;
            })
            .catch(error => {
                console.error('Error loading samples:', error);
                uiUtils.showError('Failed to load samples: ' + error.message);
            });
    },
    
    // Filter samples based on search query
    filterSamples: function(query) {
        samples.currentPage = 1; // Reset to first page when searching
        samples.loadSamples(query);
    },
    
    // Render samples in the table
    renderSamplesTable: function(samplesData) {
        const tableBody = document.getElementById('samplesTableBody');
        tableBody.innerHTML = '';
        
        if (samplesData.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="5" class="text-center">No samples found</td>';
            tableBody.appendChild(row);
            return;
        }
        
        samplesData.forEach(sample => {
            const row = document.createElement('tr');
            
            // Truncate long text for display
            const truncatedQuestion = sample.query_text.length > 50 
                ? sample.query_text.substring(0, 50) + '...' 
                : sample.query_text;
                
            const truncatedSql = sample.sql_query.length > 50 
                ? sample.sql_query.substring(0, 50) + '...' 
                : sample.sql_query;
            
            // Determine source label and style
            const sourceLabel = sample.is_manual_sample ? 'Manual' : 'Feedback';
            const sourceBadgeClass = sample.is_manual_sample ? 'bg-primary' : 'bg-success';
            
            row.innerHTML = `
                <td>${truncatedQuestion}</td>
                <td><code>${truncatedSql}</code></td>
                <td>${sample.workspace}</td>
                <td><span class="badge ${sourceBadgeClass}">${sourceLabel}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary edit-sample" 
                        data-sample-id="${sample.feedback_id}">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                </td>
            `;
            
            // Add event listener to edit button
            row.querySelector('.edit-sample').addEventListener('click', function() {
                samples.openSampleModal(sample.feedback_id);
            });
            
            tableBody.appendChild(row);
        });
    },
    
    // Open modal to view/edit a sample
    openSampleModal: function(sampleId) {
        fetch(`/api/samples/${sampleId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load sample details');
                }
                return response.json();
            })
            .then(sample => {
                // Populate modal fields
                document.getElementById('editSampleId').value = sample.feedback_id;
                document.getElementById('editQueryText').value = sample.query_text;
                document.getElementById('editSqlQuery').value = sample.sql_query;
                document.getElementById('editResultsSummary').value = sample.results_summary || '';
                document.getElementById('editWorkspace').value = sample.workspace;
                
                // Set selected tables
                samples.editSelectedTables = Array.isArray(sample.tables_used) ? 
                    sample.tables_used : 
                    (sample.tables_used ? sample.tables_used.split(',') : []);
                    
                // Load tables for the selected workspace
                samples.loadEditTables();
                
                // Show the modal
                const modal = new bootstrap.Modal(document.getElementById('sampleModal'));
                modal.show();
            })
            .catch(error => {
                console.error('Error loading sample details:', error);
                uiUtils.showError('Failed to load sample details: ' + error.message);
            });
    },
    
    // Update an existing sample
    updateSample: function() {
        const sampleId = document.getElementById('editSampleId').value;
        const queryText = document.getElementById('editQueryText').value.trim();
        const sqlQuery = document.getElementById('editSqlQuery').value.trim();
        const resultsSummary = document.getElementById('editResultsSummary').value.trim();
        const workspace = document.getElementById('editWorkspace').value;
        
        if (!queryText || !sqlQuery) {
            uiUtils.showError('Please provide both a question and SQL query');
            return;
        }
        
        const sampleData = {
            query_text: queryText,
            sql_query: sqlQuery,
            results_summary: resultsSummary || 'Manual sample entry',
            workspace: workspace,
            feedback_rating: 1, // Manual samples are always considered "positive" feedback
            tables_used: samples.editSelectedTables,
            is_manual_sample: true
        };
        
        fetch(`/api/samples/${sampleId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(sampleData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to update sample');
            }
            return response.json();
        })
        .then(data => {
            // Hide the modal
            bootstrap.Modal.getInstance(document.getElementById('sampleModal')).hide();
            
            // Show success message
            uiUtils.showSuccess('Sample updated successfully');
            
            // Reload samples
            samples.loadSamples();
        })
        .catch(error => {
            console.error('Error updating sample:', error);
            uiUtils.showError('Failed to update sample: ' + error.message);
        });
    },
    
    // Delete a sample
    deleteSample: function() {
        const sampleId = document.getElementById('editSampleId').value;
        
        // Confirm deletion
        if (!confirm('Are you sure you want to delete this sample?')) {
            return;
        }
        
        fetch(`/api/samples/${sampleId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to delete sample');
            }
            return response.json();
        })
        .then(data => {
            // Hide the modal
            bootstrap.Modal.getInstance(document.getElementById('sampleModal')).hide();
            
            // Show success message
            uiUtils.showSuccess('Sample deleted successfully');
            
            // Reload samples
            samples.loadSamples();
        })
        .catch(error => {
            console.error('Error deleting sample:', error);
            uiUtils.showError('Failed to delete sample: ' + error.message);
        });
    }
};

// Initialize samples functionality when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the samples page
    if (document.getElementById('sampleForm')) {
        samples.init();
    }
});