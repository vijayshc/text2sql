/**
 * Configuration Manager
 * Handles the UI interactions for the configuration management page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const configTable = document.getElementById('configTable');
    const configModal = document.getElementById('configModal');
    const configModalTitle = document.getElementById('configModalLabel');
    const configForm = document.getElementById('configForm');
    const createConfigBtn = document.getElementById('createConfigBtn');
    const saveConfigBtn = document.getElementById('saveConfig');
    const categoryFilterDropdown = document.getElementById('categoryFilterDropdown');
    const confirmationModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    const configModalInstance = new bootstrap.Modal(configModal);
    
    let currentConfigId = null;
    let deleteConfigId = null;
    let configurations = [];
    let categories = [];
    let currentCategory = 'all';
    
    // Initialize the page
    initPage();
    
    /**
     * Initialize the page
     */
    function initPage() {
        // Load configurations
        loadConfigurations();
        
        // Event listeners
        createConfigBtn.addEventListener('click', showCreateConfigModal);
        saveConfigBtn.addEventListener('click', saveConfiguration);
        document.getElementById('confirmDelete').addEventListener('click', deleteConfiguration);
        
        // When the value type changes to text, switch the input to textarea
        document.getElementById('configType').addEventListener('change', function() {
            updateValueFieldType();
        });
    }
    
    /**
     * Updates the value input field based on the selected type
     */
    function updateValueFieldType() {
        const valueType = document.getElementById('configType').value;
        const valueField = document.getElementById('configValue');
        const valueFieldContainer = valueField.parentElement;
        
        // Remove existing field
        valueField.remove();
        
        // Create new input based on type
        let newField;
        
        switch(valueType) {
            case 'text':
                newField = document.createElement('textarea');
                newField.rows = 4;
                break;
            case 'boolean':
                newField = document.createElement('select');
                ['true', 'false'].forEach(option => {
                    const opt = document.createElement('option');
                    opt.value = option;
                    opt.textContent = option;
                    newField.appendChild(opt);
                });
                break;
            default:
                newField = document.createElement('input');
                newField.type = 'text';
                if (valueType === 'integer' || valueType === 'float') {
                    newField.inputMode = 'numeric';
                }
                break;
        }
        
        // Add common attributes
        newField.className = 'form-control';
        newField.id = 'configValue';
        newField.name = 'value';
        
        // Add to container
        valueFieldContainer.appendChild(newField);
    }
    
    /**
     * Load all configurations
     */
    function loadConfigurations() {
        fetch('/admin/config/api/list')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    configurations = data.data;
                    categories = data.categories;
                    
                    // Initialize category filters
                    updateCategoryFilters();
                    
                    // Display configurations
                    displayConfigurations();
                } else {
                    showAlert('error', data.message || 'Failed to load configurations');
                }
            })
            .catch(error => {
                console.error('Error loading configurations:', error);
                showAlert('error', 'Failed to load configurations: ' + error.message);
            });
    }
    
    /**
     * Update category filter dropdown
     */
    function updateCategoryFilters() {
        // Get dropdown menu
        const dropdownMenu = categoryFilterDropdown.querySelector('.dropdown-menu');
        
        // Clear existing category items (keep the "All Categories" item and divider)
        const itemsToKeep = 2;
        while (dropdownMenu.children.length > itemsToKeep) {
            dropdownMenu.removeChild(dropdownMenu.lastChild);
        }
        
        // Add category items to dropdown
        categories.forEach(category => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'dropdown-item filter-category';
            item.textContent = category;
            item.dataset.category = category;
            item.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Update dropdown button text to show selected category
                const filterButton = categoryFilterDropdown.querySelector('button');
                filterButton.innerHTML = `<i class="fas fa-filter fa-sm"></i> Category: ${category}`;
                
                // Filter by category
                currentCategory = category;
                displayConfigurations();
            });
            
            dropdownMenu.appendChild(item);
        });
        
        // Update category datalist for the form
        const datalist = document.getElementById('categoryOptions');
        datalist.innerHTML = '';
        
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            datalist.appendChild(option);
        });
    }
    
    /**
     * Display configurations in the table
     */
    function displayConfigurations() {
        const tbody = configTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        // Filter configurations by selected category
        const filtered = currentCategory === 'all' 
            ? configurations 
            : configurations.filter(config => config.category === currentCategory);
        
        // Display configurations
        filtered.forEach(config => {
            const row = document.createElement('tr');
            
            // Key
            const keyCell = document.createElement('td');
            keyCell.textContent = config.key;
            row.appendChild(keyCell);
            
            // Value
            const valueCell = document.createElement('td');
            valueCell.textContent = config.is_sensitive ? '********' : config.value;
            row.appendChild(valueCell);
            
            // Value Type
            const typeCell = document.createElement('td');
            typeCell.textContent = config.value_type;
            row.appendChild(typeCell);
            
            // Category
            const categoryCell = document.createElement('td');
            categoryCell.textContent = config.category;
            row.appendChild(categoryCell);
            
            // Description
            const descCell = document.createElement('td');
            descCell.textContent = config.description;
            row.appendChild(descCell);
            
            // Actions
            const actionsCell = document.createElement('td');
            actionsCell.className = 'text-center';
            
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm btn-outline-primary me-2';
            editBtn.innerHTML = '<i class="fas fa-edit"></i>';
            editBtn.title = 'Edit';
            editBtn.addEventListener('click', () => showEditConfigModal(config.id));
            actionsCell.appendChild(editBtn);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-sm btn-outline-danger';
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.title = 'Delete';
            deleteBtn.addEventListener('click', () => confirmDeleteConfig(config.id));
            actionsCell.appendChild(deleteBtn);
            
            row.appendChild(actionsCell);
            
            tbody.appendChild(row);
        });
        
        if (filtered.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 6;
            cell.className = 'text-center';
            cell.textContent = 'No configurations found';
            row.appendChild(cell);
            tbody.appendChild(row);
        }
    }
    
    /**
     * Show the modal for creating a new configuration
     */
    function showCreateConfigModal() {
        configModalTitle.textContent = 'Create New Configuration';
        configForm.reset();
        currentConfigId = null;
        
        // Set default values
        document.getElementById('configType').value = 'string';
        document.getElementById('configCategory').value = 'general';
        
        // Make key editable
        document.getElementById('configKey').readOnly = false;
        
        // Update value field
        updateValueFieldType();
        
        configModalInstance.show();
    }
    
    /**
     * Show the modal for editing a configuration
     */
    function showEditConfigModal(configId) {
        configModalTitle.textContent = 'Edit Configuration';
        currentConfigId = configId;
        
        // Fetch configuration details
        fetch(`/admin/config/api/get/${configId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    const config = data.data;
                    
                    // Fill form fields
                    document.getElementById('configKey').value = config.key;
                    document.getElementById('configKey').readOnly = true; // Don't allow key editing
                    document.getElementById('configType').value = config.value_type;
                    document.getElementById('configCategory').value = config.category;
                    document.getElementById('configDescription').value = config.description;
                    document.getElementById('configSensitive').checked = config.is_sensitive;
                    
                    // Update value field type and set value
                    updateValueFieldType();
                    document.getElementById('configValue').value = config.value;
                    
                    configModalInstance.show();
                } else {
                    showAlert('error', data.message || 'Failed to load configuration details');
                }
            })
            .catch(error => {
                console.error('Error loading configuration details:', error);
                showAlert('error', 'Failed to load configuration details: ' + error.message);
            });
    }
    
    /**
     * Save the configuration (create or update)
     */
    function saveConfiguration() {
        // Get form data
        const formData = new FormData(configForm);
        const data = {
            key: formData.get('key'),
            value: formData.get('value'),
            value_type: formData.get('value_type'),
            category: formData.get('category'),
            description: formData.get('description'),
            is_sensitive: formData.get('is_sensitive') === 'on'
        };
        
        // Validate form
        if (!data.key || !data.category) {
            showAlert('error', 'Please fill in all required fields');
            return;
        }
        
        let url, method;
        
        if (currentConfigId === null) {
            // Create new
            url = '/admin/config/api/create';
            method = 'POST';
        } else {
            // Update existing
            url = `/admin/config/api/update/${currentConfigId}`;
            method = 'POST';
        }
        
        // Send request
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showAlert('success', data.message || 'Configuration saved successfully');
                    configModalInstance.hide();
                    loadConfigurations();
                } else {
                    showAlert('error', data.message || 'Failed to save configuration');
                }
            })
            .catch(error => {
                console.error('Error saving configuration:', error);
                showAlert('error', 'Failed to save configuration: ' + error.message);
            });
    }
    
    /**
     * Show confirmation dialog for deleting a configuration
     */
    function confirmDeleteConfig(configId) {
        deleteConfigId = configId;
        confirmationModal.show();
    }
    
    /**
     * Delete a configuration
     */
    function deleteConfiguration() {
        if (!deleteConfigId) return;
        
        fetch(`/admin/config/api/delete/${deleteConfigId}`, {
            method: 'DELETE'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showAlert('success', data.message || 'Configuration deleted successfully');
                    confirmationModal.hide();
                    loadConfigurations();
                } else {
                    showAlert('error', data.message || 'Failed to delete configuration');
                }
            })
            .catch(error => {
                console.error('Error deleting configuration:', error);
                showAlert('error', 'Failed to delete configuration: ' + error.message);
            });
        
        deleteConfigId = null;
    }
    
    /**
     * Show an alert message
     * @param {string} type The type of alert ('success', 'error', etc.)
     * @param {string} message The message to display
     */
    function showAlert(type, message) {
        // Check if we have an alert container
        let alertContainer = document.querySelector('.alert-container');
        if (!alertContainer) {
            // Create one
            alertContainer = document.createElement('div');
            alertContainer.className = 'alert-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(alertContainer);
        }
        
        // Create the alert
        const alert = document.createElement('div');
        alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alert.role = 'alert';
        
        // Add content
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Add to container
        alertContainer.appendChild(alert);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    }
});
