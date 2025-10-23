/**
 * Vector Database Management JavaScript
 * Handles client-side functionality for the vector database management UI
 */

// Global state
const state = {
    collections: [],
    currentCollection: null,
    currentRecords: [],
    recordsPerPage: 20,
    currentPage: 1,
    totalRecords: 0,
    currentFilter: "",
    deleteType: null, // 'collection' or 'record'
    deleteId: null,
};

// DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize
    loadCollections();
    
    // Setup event listeners
    setupEventListeners();
});

/**
 * Setup all event listeners for the page
 */
function setupEventListeners() {
    // Collection creation
    document.getElementById('btn-create-collection').addEventListener('click', showCreateCollectionModal);
    document.getElementById('btn-submit-collection').addEventListener('click', createCollection);
    
    // Collection refresh
    document.getElementById('btn-refresh-data').addEventListener('click', () => loadCollectionData(state.currentCollection));
    
    // Collection deletion
    document.getElementById('btn-delete-collection').addEventListener('click', () => confirmDelete('collection', state.currentCollection));
    
    // Pagination
    document.getElementById('prev-page').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page').addEventListener('click', () => changePage(1));
    
    // Filtering
    document.getElementById('btn-apply-filter').addEventListener('click', applyFilter);
    
    // Search
    document.getElementById('search-form').addEventListener('submit', function(e) {
        e.preventDefault();
        performSearch();
    });
    
    // Upload data
    document.getElementById('upload-data-form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        uploadData();
    });
    
    // Delete confirmation
    document.getElementById('btn-confirm-delete').addEventListener('click', executeDelete);
}

/**
 * Load all collections from the server
 */
function loadCollections() {
    fetch('/admin/api/vector-db/collections')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.collections = data.collections;
                displayCollections();
            } else {
                //showAlert('danger', `Error: ${data.error}`);
            }
        })
        .catch(error => {
            //showAlert('danger', `Failed to load collections: ${error}`);
            console.error('Error:', error);
        });
}

/**
 * Display collections in the table
 */
function displayCollections() {
    const tableBody = document.getElementById('collections-list');
    
    if (state.collections.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center">No collections found</td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    
    state.collections.forEach(collection => {
        html += `
            <tr>
                <td>${collection}</td>
                <td>Loading...</td>
                <td>Loading...</td>
                <td>Loading...</td>
                <td>
                    <button class="btn btn-sm btn-primary btn-view-collection" data-collection="${collection}">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
    
    // Initialize DataTable for collections list - with safe destruction first
    const collectionsSelector = '#collections-table';
    const collectionsTable = $(collectionsSelector);
    
    // Safely destroy existing DataTable if it exists
    if ($.fn.DataTable.isDataTable(collectionsSelector)) {
        try {
            collectionsTable.DataTable().clear();
            collectionsTable.DataTable().destroy();
            // Remove any DataTable classes that might interfere
            collectionsTable.removeClass('dataTable');
        } catch (e) {
            console.warn('Error destroying collections DataTable:', e);
        }
    }
    
    // Ensure proper table classes for styling
    collectionsTable.addClass('table table-hover table-bordered');
    
    // Initialize fresh DataTable
    try {
        collectionsTable.DataTable({
            responsive: true,
            autoWidth: false,
            pageLength: 10,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            language: {
                search: 'Filter collections:',
                lengthMenu: 'Show _MENU_ collections per page',
                emptyTable: 'No collections found'
            },
            columnDefs: [
                { targets: -1, orderable: false, searchable: false } // Actions column
            ]
        });
    } catch (e) {
        console.warn('Error initializing collections DataTable:', e);
    }

    // Fetch collection details after displaying the basic list
    state.collections.forEach(collection => {
        fetchCollectionDetails(collection);
    });
    
    // Add event listeners to view buttons
    document.querySelectorAll('.btn-view-collection').forEach(button => {
        button.addEventListener('click', function() {
            const collection = this.getAttribute('data-collection');
            loadCollectionData(collection);
        });
    });
}

/**
 * Fetch details for a specific collection
 */
function fetchCollectionDetails(collectionName) {
    fetch(`/admin/api/vector-db/collections/${collectionName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCollectionRow(collectionName, data.collection_info, data.collection_stats);
            }
        })
        .catch(error => {
            console.error(`Error fetching details for ${collectionName}:`, error);
        });
}

/**
 * Update the table row with collection details
 */
function updateCollectionRow(collectionName, info, stats) {
    const rows = document.querySelectorAll('#collections-list tr');
    
    for (const row of rows) {
        const nameCell = row.querySelector('td:first-child');
        if (nameCell && nameCell.textContent === collectionName) {
            // Find dimension from collection info
            let dimension = 'N/A';
            
            // Try to get dimension from different possible locations in the API response
            if (info) {
                // Option 1: Direct dimension property
                if (info.dimension) {
                    dimension = info.dimension;
                }
                // Option 2: From schema fields
                else if (info.schema) {
                    // Look for vector field
                    const vectorField = info.schema.find(field => field.type === 'VECTOR' || field.data_type === 'VECTOR');
                    if (vectorField) {
                        // Try different property names for dimension
                        dimension = vectorField.dimension || vectorField.params?.dimension || vectorField.dim || 'N/A';
                    }
                    
                    // If still not found, look for embedding_size or vector_dimension
                    if (dimension === 'N/A') {
                        for (const field of info.schema) {
                            if (field.params && (field.params.dimension || field.params.embedding_size || field.params.vector_dimension)) {
                                dimension = field.params.dimension || field.params.embedding_size || field.params.vector_dimension;
                                break;
                            }
                        }
                    }
                }
                // Option 3: Check collection_params
                else if (info.collection_params && info.collection_params.dimension) {
                    dimension = info.collection_params.dimension;
                }
            }
            
            // Get record count
            const recordCount = stats?.row_count || 0;
            
            // Get description
            const description = info?.description || '';
            
            // Update cells
            row.querySelector('td:nth-child(2)').textContent = dimension;
            row.querySelector('td:nth-child(3)').textContent = recordCount;
            row.querySelector('td:nth-child(4)').textContent = description;
            
            break;
        }
    }
}

/**
 * Show the create collection modal
 */
function showCreateCollectionModal() {
    // Reset form
    document.getElementById('create-collection-form').reset();
    
    // Show modal
    $('#createCollectionModal').modal('show');
}

/**
 * Create a new collection
 */
function createCollection() {
    const collectionName = document.getElementById('collection-name').value.trim();
    const vectorDimension = parseInt(document.getElementById('vector-dimension').value, 10);
    const description = document.getElementById('collection-description').value.trim();
    
    if (!collectionName) {
        //showAlert('danger', 'Collection name is required');
        return;
    }
    
    if (isNaN(vectorDimension) || vectorDimension < 1) {
        //showAlert('danger', 'Vector dimension must be a positive number');
        return;
    }
    
    // Disable button during submission
    const submitBtn = document.getElementById('btn-submit-collection');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    
    fetch('/admin/api/vector-db/collections', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            collection_name: collectionName,
            dimension: vectorDimension,
            description: description
        })
    })
    .then(response => response.json())
    .then(data => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Create';
        
        if (data.success) {
            $('#createCollectionModal').modal('hide');
            //showAlert('success', data.message || 'Collection created successfully');
            loadCollections();  // Reload the collections list
        } else {
            //showAlert('danger', data.error || 'Failed to create collection');
        }
    })
    .catch(error => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Create';
        //showAlert('danger', `Error creating collection: ${error}`);
        console.error('Error:', error);
    });
}

/**
 * Load data for a specific collection
 */
function loadCollectionData(collectionName) {
    state.currentCollection = collectionName;
    state.currentPage = 1;
    state.currentFilter = "";
    
    // Update UI
    document.getElementById('current-collection-name').textContent = collectionName;
    document.getElementById('collection-detail-section').style.display = 'block';
    document.getElementById('filter-expr').value = '';
    
    // Load collection details and records
    loadCollectionDetails(collectionName);
    loadCollectionRecords(collectionName);
}

/**
 * Load details for a specific collection
 */
function loadCollectionDetails(collectionName) {
    fetch(`/admin/api/vector-db/collections/${collectionName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCollectionDetails(data.collection_info, data.collection_stats);
            } else {
                document.getElementById('collection-info').innerHTML = `
                    <div class="alert alert-danger">
                        Failed to load collection details: ${data.error}
                    </div>
                `;
            }
        })
        .catch(error => {
            document.getElementById('collection-info').innerHTML = `
                <div class="alert alert-danger">
                    Error loading collection details: ${error}
                </div>
            `;
            console.error('Error:', error);
        });
}

/**
 * Display collection details
 */
function displayCollectionDetails(info, stats) {
    const infoDiv = document.getElementById('collection-info');
    
    let html = '<dl class="row">';
    
    // Basic info
    html += `<dt class="col-sm-4">Name</dt><dd class="col-sm-8">${info.collection_name || 'N/A'}</dd>`;
    html += `<dt class="col-sm-4">Description</dt><dd class="col-sm-8">${info.description || 'N/A'}</dd>`;
    html += `<dt class="col-sm-4">Record Count</dt><dd class="col-sm-8">${stats.row_count || 0}</dd>`;
    
    // Schema info
    if (info.schema && info.schema.length > 0) {
        html += '<dt class="col-sm-4">Schema</dt><dd class="col-sm-8">';
        html += '<table class="table table-sm table-bordered">';
        html += '<thead><tr><th>Field</th><th>Type</th><th>Properties</th></tr></thead>';
        html += '<tbody>';
        
        info.schema.forEach(field => {
            let properties = '';
            if (field.type === 'VECTOR') {
                properties = `Dimension: ${field.dimension || 'N/A'}`;
            } else if (field.params) {
                properties = Object.entries(field.params)
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(', ');
            }
            
            html += `<tr>
                <td>${field.name}</td>
                <td>${field.type}</td>
                <td>${properties}</td>
            </tr>`;
        });
        
        html += '</tbody></table></dd>';
    }
    
    html += '</dl>';
    infoDiv.innerHTML = html;
}

/**
 * Load records for a specific collection
 */
function loadCollectionRecords(collectionName, page = 1, filter = "", forceRefresh = false) {
    const limit = state.recordsPerPage;
    const offset = (page - 1) * limit;
    
    // Show loading indicator
    document.getElementById('records-list').innerHTML = `
        <tr>
            <td colspan="3" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
                <div class="mt-2">Loading records...</div>
            </td>
        </tr>
    `;
    
    // Add cache-busting parameter for force refresh
    const timestamp = forceRefresh ? `&_t=${Date.now()}` : '';
    
    let url = `/admin/api/vector-db/collections/${collectionName}/data?limit=${limit}&offset=${offset}${timestamp}`;
    if (filter) {
        url += `&filter=${encodeURIComponent(filter)}`;
    }
    
    // Use no-cache headers for force refresh
    const fetchOptions = forceRefresh ? {
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    } : {};
    
    fetch(url, fetchOptions)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`Loaded ${data.data ? data.data.length : 0} records out of ${data.total} total`);
                state.currentRecords = data.data;
                state.totalRecords = data.total;
                state.currentPage = page;
                
                displayCollectionRecords(data.data);
                updatePagination(data.total, limit, page);
            } else {
                document.getElementById('records-list').innerHTML = `
                    <tr>
                        <td colspan="3" class="text-center">
                            <div class="alert alert-danger">
                                Failed to load records: ${data.error}
                            </div>
                        </td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            document.getElementById('records-list').innerHTML = `
                <tr>
                    <td colspan="3" class="text-center">
                        <div class="alert alert-danger">
                            Error loading records: ${error}
                        </div>
                    </td>
                </tr>
            `;
            console.error('Error:', error);
        });
}

/**
 * Display records in the table
 */
function displayCollectionRecords(records) {
    const tableBody = document.getElementById('records-list');
    const headerRow = document.getElementById('records-header').querySelector('tr');
    
    if (!records || records.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center">No records found</td>
            </tr>
        `;
        return;
    }
    
    // Get all keys from records for table headers
    const allKeys = new Set();
    
    // First pass: collect all unique keys across all records
    records.forEach(record => {
        if (record && typeof record === 'object') {
            Object.keys(record).forEach(key => {
                // Skip vector data field as it's too large for display
                if (key !== 'vector' && key !== 'vector_field') {
                    allKeys.add(key);
                }
            });
        }
    });
    
    // If no keys were found, show an error
    if (allKeys.size === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center">
                    <div class="alert alert-warning">
                        Records appear to be empty or in an invalid format
                    </div>
                </td>
            </tr>
        `;
        console.error("No fields found in records:", records);
        return;
    }
    
    // Check if this is a search result with similarity scores
    const hasSearchResults = records.some(record => 'similarity' in record);
    
    // Reorder keys to prioritize important fields and put similarity first when present
    const sortedKeys = prioritizeKeys(Array.from(allKeys), hasSearchResults);
    
    // Create header row
    let headerHtml = '';
    sortedKeys.forEach(key => {
        // Add special styling for similarity header
        if (key === 'similarity' && hasSearchResults) {
            headerHtml += `<th class="text-center">Similarity Score</th>`;
        } else {
            headerHtml += `<th>${key}</th>`;
        }
    });
    headerHtml += '<th>Actions</th>';
    headerRow.innerHTML = headerHtml;
    
    // Create rows
    let html = '';
    records.forEach(record => {
        // Add special class for search results 
        const rowClass = hasSearchResults ? 'search-result-row' : '';
        html += `<tr class="${rowClass}">`;
        
        sortedKeys.forEach(key => {
            let value = record[key];
            let cellClass = '';
            
            // Special handling for similarity scores
            if (key === 'similarity' && hasSearchResults) {
                // Format similarity score for display
                const score = parseFloat(value);
                const displayValue = isNaN(score) ? value : score.toFixed(4);
                
                // Determine color class based on score
                if (!isNaN(score)) {
                    if (score >= 0.9) cellClass = 'similarity-high';
                    else if (score >= 0.7) cellClass = 'similarity-medium';
                    else cellClass = 'similarity-low';
                }
                
                // Display as formatted badge
                value = `<span class="similarity-score">${displayValue}</span>`;
                
                html += `<td class="text-center ${cellClass}">${value}</td>`;
                
            } else {
                // Format other values for display
                if (value === null || value === undefined) {
                    value = '';
                } else if (typeof value === 'object') {
                    try {
                        value = JSON.stringify(value);
                    } catch (e) {
                        value = '[Object]';
                    }
                } else if (typeof value === 'string' && value.length > 100) {
                    value = value.substring(0, 100) + '...';
                }
                
                html += `<td>${value}</td>`;
            }
        });
        
        // Actions column with dropdown
        const recordId = record.id || record.ID || record._id || '';
        html += `
            <td class="text-center">
                <div class="dropdown">
                    <button class="btn btn-sm btn-primary dropdown-toggle" type="button" id="dropdownMenuButton-${recordId}" 
                        data-bs-toggle="dropdown" aria-expanded="false">
                        Actions
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="dropdownMenuButton-${recordId}">
                        <li><a class="dropdown-item btn-view-record" href="#" data-record='${JSON.stringify({ id: recordId })}'>
                            <i class="fas fa-eye"></i> View
                        </a></li>
                        <li><a class="dropdown-item btn-delete-record text-danger" href="#" data-record-id="${recordId}">
                            <i class="fas fa-trash"></i> Delete
                        </a></li>
                    </ul>
                </div>
            </td>
        </tr>`;
    });
    
    tableBody.innerHTML = html;

    // Initialize DataTable on records table (destroy/reinit to pick new columns)
    const recordsSelector = '#records-table';
    const recordsTable = $(recordsSelector);
    
    // Safely destroy existing DataTable if it exists
    if ($.fn.DataTable.isDataTable(recordsSelector)) {
        try {
            recordsTable.DataTable().clear();
            recordsTable.DataTable().destroy();
            // Remove any DataTable classes that might interfere
            recordsTable.removeClass('dataTable');
        } catch (e) {
            console.warn('Error destroying records DataTable:', e);
        }
    }
    
    // Ensure proper table classes for styling
    recordsTable.addClass('table table-hover table-bordered');
    
    // Initialize fresh DataTable
    try {
        recordsTable.DataTable({
            responsive: true,
            autoWidth: false,
            pageLength: 10,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            language: {
                search: 'Filter records:',
                lengthMenu: 'Show _MENU_ records per page',
                emptyTable: 'No records found'
            },
            columnDefs: [
                { targets: -1, orderable: false, searchable: false } // Actions column
            ],
            order: hasSearchResults ? [[0, 'desc']] : [] // Sort by similarity if available
        });
    } catch (e) {
        console.warn('Error initializing records DataTable:', e);
    }

    // Hide custom pagination in favor of DataTables controls
    const customPager = document.getElementById('custom-pagination');
    if (customPager) customPager.style.display = 'none';
    
    // Add event listeners to dropdown items
    document.querySelectorAll('.dropdown-item.btn-view-record').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            try {
                const recordData = JSON.parse(this.getAttribute('data-record'));
                showRecordDetails(recordData);
            } catch (e) {
                console.error("Error parsing record data:", e);
                //showAlert('danger', 'Error viewing record details');
            }
        });
    });
    
    document.querySelectorAll('.dropdown-item.btn-delete-record').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const recordId = this.getAttribute('data-record-id');
            if (recordId) {
                confirmDelete('record', recordId);
            } else {
                //showAlert('danger', 'Record ID not found');
            }
        });
    });
}

/**
 * Prioritize and order keys for display in the records table
 */
function prioritizeKeys(keys, isSearchResult) {
    // Define priority order for keys
    const priorityOrder = ['id', 'similarity', 'query_text', 'feedback_rating', 'sql_query', 'created_at'];
    
    if (isSearchResult) {
        // For search results, ensure similarity is first if present
        if (keys.includes('similarity')) {
            keys = keys.filter(key => key !== 'similarity');
            keys.unshift('similarity');
        }
    }
    
    // Sort the remaining keys based on priority
    return keys.sort((a, b) => {
        const indexA = priorityOrder.indexOf(a);
        const indexB = priorityOrder.indexOf(b);
        
        if (indexA === -1 && indexB === -1) {
            // Both keys not in priority list, sort alphabetically
            return a.localeCompare(b);
        }
        
        // If only one key is in priority list, it comes first
        if (indexA === -1) return 1;
        if (indexB === -1) return -1;
        
        // Both keys in priority list, use their relative order
        return indexA - indexB;
    });
}

/**
 * Show record details in a modal
 */
function showRecordDetails(recordData) {
    // Find the full record details based on any possible ID field
    let record = null;
    const possibleIdFields = ['id', 'ID', '_id', 'Id'];
    
    // Try to find the record using different possible ID field names
    for (const idField of possibleIdFields) {
        if (recordData.id !== undefined) {
            record = state.currentRecords.find(r => {
                // Handle different ID field names in records as well
                for (const field of possibleIdFields) {
                    if (r[field] !== undefined && r[field].toString() === recordData.id.toString()) {
                        return true;
                    }
                }
                return false;
            });
            if (record) break;
        }
    }
    
    if (!record) {
        //showAlert('danger', 'Record details not found');
        return;
    }
    
    const contentDiv = document.getElementById('record-detail-content');
    
    // Create formatted HTML for all record fields
    let html = '<dl class="row">';
    
    // Prepare keys in a meaningful order
    const keys = Object.keys(record);
    const hasSimiliarity = keys.includes('similarity');
    const orderedKeys = [];
    
    // First add similarity if it exists
    if (hasSimiliarity) {
        orderedKeys.push('similarity');
    }
    
    // Then add standard ID field
    if (keys.includes('id')) {
        orderedKeys.push('id');
    }
    
    // Add the rest of the fields alphabetically
    orderedKeys.push(...keys.filter(key => 
        key !== 'similarity' && 
        key !== 'id' && 
        key !== 'vector' && // Skip vector field as it's too large
        key !== 'vector_field' 
    ).sort());
    
    // Generate the detail view
    orderedKeys.forEach(key => {
        const value = record[key];
        let displayValue;
        
        // Format value for display
        if (value === null || value === undefined) {
            displayValue = '<em>null</em>';
        } else if (key === 'similarity') {
            // Format similarity score with more precision and highlight
            const score = parseFloat(value);
            if (!isNaN(score)) {
                const scoreClass = score >= 0.9 ? 'success' : (score >= 0.7 ? 'warning' : 'danger');
                displayValue = `<span class="badge badge-${scoreClass}">${score.toFixed(6)}</span>`;
            } else {
                displayValue = value;
            }
        } else if (typeof value === 'object') {
            try {
                displayValue = `<pre class="pre-scrollable" style="max-height: 200px">${JSON.stringify(value, null, 2)}</pre>`;
            } catch (e) {
                displayValue = String(value);
            }
        } else if (typeof value === 'boolean') {
            displayValue = value ? '<span class="badge badge-success">True</span>' : '<span class="badge badge-secondary">False</span>';
        } else {
            displayValue = String(value);
        }
        
        html += `
            <dt class="col-sm-3">${key}</dt>
            <dd class="col-sm-9">${displayValue}</dd>
        `;
    });
    
    html += '</dl>';
    contentDiv.innerHTML = html;
    
    // Update modal title with record identifier
    const idField = record.id || record.ID || record._id || '';
    const modalTitle = `Record Details - ID: ${idField}`;
    document.getElementById('recordDetailModalLabel').textContent = modalTitle;
    
    // Show modal
    $('#recordDetailModal').modal('show');
}

/**
 * Update pagination controls
 */
function updatePagination(total, limit, currentPage) {
    const totalPages = Math.ceil(total / limit);
    document.getElementById('showing-records').textContent = state.currentRecords.length;
    document.getElementById('total-records').textContent = total;
    document.getElementById('current-page').textContent = currentPage;
    
    // Enable/disable pagination buttons
    document.getElementById('prev-page').disabled = currentPage <= 1;
    document.getElementById('next-page').disabled = currentPage >= totalPages;
}

/**
 * Change page in pagination
 */
function changePage(direction) {
    const newPage = state.currentPage + direction;
    if (newPage < 1) return;
    
    loadCollectionRecords(state.currentCollection, newPage, state.currentFilter);
}

/**
 * Apply filter to records
 */
function applyFilter() {
    const filter = document.getElementById('filter-expr').value.trim();
    state.currentFilter = filter;
    loadCollectionRecords(state.currentCollection, 1, filter);
}

/**
 * Perform a vector search
 */
function performSearch() {
    const searchText = document.getElementById('search-text').value.trim();
    const limit = document.getElementById('search-limit').value;
    
    if (!searchText) {
        //showAlert('danger', 'Please enter search text');
        return;
    }
    
    // Show loading indicator
    document.getElementById('records-list').innerHTML = `
        <tr>
            <td colspan="3" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">Searching...</span>
                </div>
                <div class="mt-2">Searching for similar records...</div>
            </td>
        </tr>
    `;
    
    // Perform the search request
    fetch(`/admin/api/vector-db/collections/${state.currentCollection}/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            search_text: searchText,
            limit: parseInt(limit, 10),
            filter: state.currentFilter || null
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && Array.isArray(data.results)) {
            // Log retrieval stats
            console.log(`Retrieved ${data.results.length} search results`);
            if (data.results.length > 0) {
                console.log(`Fields in first result: ${Object.keys(data.results[0]).join(', ')}`);
            }
            
            // Sort results by similarity score (higher scores first)
            const sortedResults = data.results.sort((a, b) => {
                // Handle potential missing similarity scores
                const scoreA = typeof a.similarity !== 'undefined' ? a.similarity : 0;
                const scoreB = typeof b.similarity !== 'undefined' ? b.similarity : 0;
                return scoreB - scoreA;
            });
            
            // Update state with search results
            state.currentRecords = sortedResults;
            state.totalRecords = sortedResults.length;
            state.currentPage = 1;
            
            // Display search results in the Collection Records table
            displayCollectionRecords(sortedResults);
            updatePagination(sortedResults.length, state.recordsPerPage, 1);
            
            // Show search indicator
            //showAlert('success', `Found ${sortedResults.length} records similar to "${searchText}" (sorted by similarity)`);
            
            // Update the current filter with search information
            document.getElementById('filter-expr').value = `Search: "${searchText}" (sorted by similarity)`;
        } else {
            // Handle empty or error results
            //showAlert('danger', data.error || 'Search returned no results');
            // Reload the original records if search fails
            loadCollectionRecords(state.currentCollection, state.currentPage, state.currentFilter);
        }
    })
    .catch(error => {
        //showAlert('danger', `Error performing search: ${error}`);
        console.error('Error:', error);
        // Reload the original records if search fails
        loadCollectionRecords(state.currentCollection, state.currentPage, state.currentFilter);
    });
}

/**
 * Confirm deletion of collection or record
 */
function confirmDelete(type, id) {
    state.deleteType = type;
    state.deleteId = id;
    
    let message = '';
    if (type === 'collection') {
        message = `Are you sure you want to delete the collection "${id}"?<br>This operation cannot be undone!`;
    } else if (type === 'record') {
        message = `Are you sure you want to delete the record with ID ${id}?<br>This operation cannot be undone!`;
    }
    
    document.getElementById('delete-confirm-message').innerHTML = message;
    $('#deleteConfirmModal').modal('show');
}

/**
 * Execute deletion after confirmation
 */
function executeDelete() {
    const type = state.deleteType;
    const id = state.deleteId;
    
    if (type === 'collection') {
        deleteCollection(id);
    } else if (type === 'record') {
        deleteRecord(id);
    }
    
    // Hide modal
    $('#deleteConfirmModal').modal('hide');
}

/**
 * Delete a collection
 */
function deleteCollection(collectionName) {
    fetch(`/admin/api/vector-db/collections/${collectionName}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            //showAlert('success', data.message || 'Collection deleted successfully');
            
            // Hide collection details
            document.getElementById('collection-detail-section').style.display = 'none';
            
            // Reload collections
            loadCollections();
        } else {
            //showAlert('danger', data.error || 'Failed to delete collection');
        }
    })
    .catch(error => {
        //showAlert('danger', `Error deleting collection: ${error}`);
        console.error('Error:', error);
    });
}

/**
 * Delete a record
 */
function deleteRecord(recordId) {
    fetch(`/admin/api/vector-db/collections/${state.currentCollection}/data/${recordId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            //showAlert('success', data.message || 'Record deleted successfully');
            
            // Reload records
            loadCollectionRecords(state.currentCollection, state.currentPage, state.currentFilter);
        } else {
            //showAlert('danger', data.error || 'Failed to delete record');
        }
    })
    .catch(error => {
        //showAlert('danger', `Error deleting record: ${error}`);
        console.error('Error:', error);
    });
}

/**
 * Upload data to a collection and generate embeddings
 */
function uploadData() {
    const fileInput = document.getElementById('upload-file');
    const textFieldName = document.getElementById('text-field-name').value.trim();
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showAlert('danger', 'Please select a file to upload');
        return;
    }
    
    if (!textFieldName) {
        showAlert('danger', 'Please specify the text field name for generating embeddings');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('text_field_name', textFieldName);
    
    // Disable the upload button and show progress
    const uploadBtn = document.getElementById('btn-upload-data');
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading & Processing...';
    
    // Show upload status
    showAlert('info', `Uploading and processing ${file.name}. This may take a few moments...`);
    
    fetch(`/admin/api/vector-db/collections/${state.currentCollection}/upload`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            // Check for specific HTTP error codes
            if (response.status === 400) {
                return Promise.reject({
                    message: 'Bad request: The server could not understand the request. Please check your file format and field name.'
                });
            } else if (response.status === 413) {
                return Promise.reject({
                    message: 'File too large: The uploaded file exceeds the size limit.'
                });
            } else if (response.status === 415) {
                return Promise.reject({
                    message: 'Unsupported file type: Please upload a supported file format (CSV or JSON).'
                });
            } else if (response.status === 500) {
                return Promise.reject({
                    message: 'Server error: An internal server error occurred while processing your request.'
                });
            } else {
                return Promise.reject({
                    message: `HTTP error ${response.status}: ${response.statusText}`
                });
            }
        }
        return response.json();
    })
    .then(data => {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload & Generate Embeddings';
        
        if (data.success) {
            showAlert('success', `Successfully uploaded data: ${data.message}`);
            
            // Reset form
            document.getElementById('upload-data-form').reset();
            
            // Add a small delay before reloading to ensure server processing is complete
            setTimeout(() => {
                // Force reload collection data with cache bypass to show the new records
                loadCollectionDetails(state.currentCollection); // Refresh collection details for updated count
                loadCollectionRecords(state.currentCollection, 1, "", true); // Force refresh records with cache bypass
                showAlert('info', 'Refreshing data display to show new records...');
            }, 500);
        } else {
            showAlert('danger', data.error || 'Failed to upload data');
        }
    })
    .catch(error => {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload & Generate Embeddings';
        showAlert('danger', `Error uploading data: ${error.message || 'An unknown error occurred'}`);
        console.error('Error:', error);
    });
}

/**
 * Show alert message as toast notification
 */
function showAlert(type, message) {
    // Get title based on alert type
    let title = "Notification";
    switch (type) {
        case 'success': title = "Success"; break;
        case 'danger': title = "Error"; break;
        case 'warning': title = "Warning"; break;
        case 'info': title = "Information"; break;
    }
    
    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const toastDiv = document.createElement('div');
    toastDiv.id = toastId;
    toastDiv.className = `toast ${type} toast-enter`;
    toastDiv.setAttribute('role', 'alert');
    toastDiv.setAttribute('aria-live', 'assertive');
    toastDiv.setAttribute('aria-atomic', 'true');
    
    toastDiv.innerHTML = `
        <div class="toast-header">
            <span class="toast-title ${type}">${title}</span>
            <button type="button" class="close" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    // Add to toast container
    const container = document.getElementById('toast-container');
    container.appendChild(toastDiv);
    
    // Animation effect
    setTimeout(() => {
        toastDiv.classList.remove('toast-enter');
        toastDiv.classList.add('toast-enter-active');
    }, 10);
    
    // Setup close button
    const closeBtn = toastDiv.querySelector('.close');
    closeBtn.addEventListener('click', () => {
        removeToast(toastId);
    });
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        removeToast(toastId);
    }, 5000);
}

/**
 * Remove toast notification with animation
 */
function removeToast(toastId) {
    const toast = document.getElementById(toastId);
    if (!toast) return;
    
    toast.classList.remove('toast-enter-active');
    toast.classList.add('toast-exit', 'toast-exit-active');
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}