document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let dataTable = null;
    let progressInterval = null;
    let selectedTables = []; // Move this declaration here to avoid duplicate initialization
    const workspaceSelect = document.getElementById('workspaceSelect');
    const queryInput = document.getElementById('queryInput');
    const submitButton = document.getElementById('submitQuery');
    const viewSchemaBtn = document.getElementById('viewSchemaBtn');
    const schemaModal = new bootstrap.Modal(document.getElementById('schemaModal'));
    
    // Table mention variables
    let tableMentionDropdown = null;
    let mentionActive = false;
    let mentionStartPosition = 0;
    let currentMentionText = '';
    let tableNames = [];
    let activeDropdownIndex = -1;
    let mentionAnchorPosition = { top: 0, left: 0 };
    
    // Event Listeners
    workspaceSelect.addEventListener('change', function() {
        updateWorkspaceDescription();
        // Reload table names when workspace changes
        fetchTableNames();
        // Reset selected tables when workspace changes
        selectedTables = [];
        updateSelectedTablesDisplay();
    });
    queryInput.addEventListener('keydown', handleQueryKeydown);
    queryInput.addEventListener('input', handleQueryInput);
    queryInput.addEventListener('blur', function(e) {
        // Don't hide dropdown if clicking inside it
        if (tableMentionDropdown && !tableMentionDropdown.contains(e.relatedTarget)) {
            hideTableMentionDropdown();
        }
    });
    submitButton.addEventListener('click', submitQuery);
    viewSchemaBtn.addEventListener('click', loadSchema);
    document.addEventListener('click', function(e) {
        // Hide dropdown when clicking outside
        if (tableMentionDropdown && !tableMentionDropdown.contains(e.target) && e.target !== queryInput) {
            hideTableMentionDropdown();
        }
    });

    // Initialize workspace description, fetch table names, and empty table state
    updateWorkspaceDescription();
    fetchTableNames();
    initializeEmptyTable();
    
    // Create or get dropdown element
    function getTableMentionDropdown() {
        if (!tableMentionDropdown) {
            tableMentionDropdown = document.createElement('div');
            tableMentionDropdown.className = 'table-mention-dropdown';
            tableMentionDropdown.style.display = 'none';
            document.body.appendChild(tableMentionDropdown);
        }
        return tableMentionDropdown;
    }
    
    // Show dropdown with table suggestions
    function showTableMentionDropdown(suggestions) {
        const dropdown = getTableMentionDropdown();
        
        // Position the dropdown near the @ symbol
        dropdown.style.top = (mentionAnchorPosition.top + window.scrollY + 24) + 'px'; // Positioned just below the @ symbol
        dropdown.style.left = mentionAnchorPosition.left + 'px'; // Aligned with @ symbol
        
        // Clear and populate dropdown
        dropdown.innerHTML = '';
        
        if (suggestions.length === 0) {
            dropdown.innerHTML = '<div class="no-results">No matching tables found</div>';
        } else {
            suggestions.forEach((table, index) => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                if (index === activeDropdownIndex) {
                    item.classList.add('active');
                }
                item.innerHTML = `
                    <span class="item-name">${table.name}</span>
                    <span class="item-description">${table.description || ''}</span>
                `;
                item.addEventListener('click', () => selectTableFromDropdown(table.name, table.description));
                dropdown.appendChild(item);
            });
        }
        
        dropdown.style.display = 'block';
    }
    
    // Hide suggestion dropdown
    function hideTableMentionDropdown() {
        if (tableMentionDropdown) {
            tableMentionDropdown.style.display = 'none';
            mentionActive = false;
            currentMentionText = '';
            activeDropdownIndex = -1;
        }
    }
    
    // Handle key inputs in query input
    function handleQueryKeydown(e) {
        if (mentionActive && tableMentionDropdown && tableMentionDropdown.style.display !== 'none') {
            const items = tableMentionDropdown.querySelectorAll('.dropdown-item');
            
            // Navigate through dropdown with keyboard
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeDropdownIndex = Math.min(activeDropdownIndex + 1, items.length - 1);
                updateActiveItem(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeDropdownIndex = Math.max(activeDropdownIndex - 1, 0);
                updateActiveItem(items);
            } else if (e.key === 'Enter' && activeDropdownIndex >= 0) {
                e.preventDefault();
                const activeSuggestion = items[activeDropdownIndex].querySelector('.item-name').textContent;
                selectTableFromDropdown(activeSuggestion);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideTableMentionDropdown();
            } else if (e.key === 'Tab') {
                e.preventDefault();
                if (activeDropdownIndex >= 0) {
                    const activeSuggestion = items[activeDropdownIndex].querySelector('.item-name').textContent;
                    selectTableFromDropdown(activeSuggestion);
                }
            }
        } else if (e.key === 'Enter') {
            // Check if Ctrl key is pressed with Enter
            if (e.ctrlKey) {
                e.preventDefault();
                submitQuery();
            }
            // If Enter is pressed without Ctrl, let the default behavior add a newline
        }
    }
    
    // Update the highlighted item in the dropdown
    function updateActiveItem(items) {
        items.forEach((item, index) => {
            if (index === activeDropdownIndex) {
                item.classList.add('active');
                // Scroll item into view if needed
                const containerRect = tableMentionDropdown.getBoundingClientRect();
                const itemRect = item.getBoundingClientRect();
                
                if (itemRect.bottom > containerRect.bottom) {
                    tableMentionDropdown.scrollTop += (itemRect.bottom - containerRect.bottom);
                }
                if (itemRect.top < containerRect.top) {
                    tableMentionDropdown.scrollTop -= (containerRect.top - itemRect.top);
                }
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    // Handle input changes for mention detection and suggestion
    function handleQueryInput(e) {
        const cursorPos = queryInput.selectionStart;
        const text = queryInput.value;
        
        // Detect @ symbol immediately before cursor
        if (text.charAt(cursorPos - 1) === '@') {
            mentionActive = true;
            mentionStartPosition = cursorPos - 1;
            currentMentionText = '';
            
            // Get the exact position of the @ symbol for dropdown placement
            const inputRect = queryInput.getBoundingClientRect();
            const inputStyle = window.getComputedStyle(queryInput);
            const inputPaddingLeft = parseFloat(inputStyle.paddingLeft);
            const inputPaddingTop = parseFloat(inputStyle.paddingTop);
            
            // Create a temporary span to measure text width up to @
            const tempSpan = document.createElement('span');
            tempSpan.style.font = inputStyle.font;
            tempSpan.style.position = 'absolute';
            tempSpan.style.left = '-9999px';
            tempSpan.style.whiteSpace = 'pre';
            tempSpan.textContent = text.substring(0, mentionStartPosition);
            document.body.appendChild(tempSpan);
            
            // Calculate position
            const atSymbolPosition = tempSpan.getBoundingClientRect().width;
            document.body.removeChild(tempSpan);
            
            // Store dropdown position
            mentionAnchorPosition = {
                top: inputRect.top + inputPaddingTop,
                left: inputRect.left + inputPaddingLeft + atSymbolPosition
            };
            
            // Show suggestions with empty query
            fetchTableSuggestions('');
        } else if (mentionActive) {
            // If we're already in mention mode, update the current mention text
            const mentionEndPos = cursorPos;
            currentMentionText = text.substring(mentionStartPosition + 1, mentionEndPos);
            
            if (currentMentionText === '' || /\s/.test(currentMentionText)) {
                // If mention text is empty or contains whitespace, exit mention mode
                hideTableMentionDropdown();
            } else {
                // Otherwise fetch updated suggestions
                fetchTableSuggestions(currentMentionText);
            }
        }
    }
    
    // Fetch table suggestions based on query
    function fetchTableSuggestions(query) {
        const workspace = workspaceSelect.value;
        
        fetch(`/api/tables/suggestions?workspace=${encodeURIComponent(workspace)}&query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.suggestions && data.suggestions.length > 0) {
                    activeDropdownIndex = 0;
                    showTableMentionDropdown(data.suggestions);
                } else {
                    showTableMentionDropdown([]);
                }
            })
            .catch(error => {
                console.error('Error fetching table suggestions:', error);
                hideTableMentionDropdown();
            });
    }
    
    // Add a function to style the @table mentions in the input 
    function styleMentionsInInput() {
        // We need to style any @tableName patterns in the input
        const text = queryInput.value;
        
        // Find all instances of @tableName in the text
        selectedTables.forEach(tableName => {
            const tablePattern = new RegExp(`@${tableName}\\b`, 'g');
            
            // Create a temporary div to work with the input's content
            const tempDiv = document.createElement('div');
            tempDiv.textContent = text;
            
            // Replace the pattern with a styled span
            const styledText = tempDiv.textContent.replace(tablePattern, match => 
                `<span class="mention-highlight">${match}</span>`
            );
            
            // Apply the highlighted text to an overlay
            let highlightOverlay = document.querySelector('.query-highlight-overlay');
            if (!highlightOverlay) {
                highlightOverlay = document.createElement('div');
                highlightOverlay.className = 'query-highlight-overlay';
                highlightOverlay.style.position = 'absolute';
                highlightOverlay.style.top = '0';
                highlightOverlay.style.left = '0';
                highlightOverlay.style.right = '0';
                highlightOverlay.style.bottom = '0';
                highlightOverlay.style.pointerEvents = 'none';
                highlightOverlay.style.zIndex = '1';
                queryInput.parentNode.style.position = 'relative';
                queryInput.parentNode.insertBefore(highlightOverlay, queryInput.nextSibling);
            }
            
            highlightOverlay.innerHTML = styledText;
        });
    }
    
    // Select a table from the dropdown
    function selectTableFromDropdown(tableName, tableDescription) {
        if (!selectedTables) selectedTables = [];
        
        console.log('Before selection - Selected tables:', selectedTables); // Debug log
        
        if (selectedTables.includes(tableName)) {
            // Table already selected, don't add duplicate
            hideTableMentionDropdown();
            return;
        }
        
        // Add to selected tables
        selectedTables.push(tableName);
        console.log('After adding - Selected tables:', selectedTables); // Debug log
        
        // Replace the @mention text with a clean table reference
        const cursorPos = queryInput.selectionStart;
        let textBefore = queryInput.value.substring(0, mentionStartPosition);
        let textAfter = queryInput.value.substring(mentionStartPosition + currentMentionText.length + 1);
        
        // Insert the table name directly (without markers)
        const displayText = `@${tableName} `;
        queryInput.value = textBefore + displayText + textAfter;
        
        // Set cursor position after replacement
        queryInput.selectionStart = mentionStartPosition + displayText.length;
        queryInput.selectionEnd = mentionStartPosition + displayText.length;
        
        // Update the selected tables display
        updateSelectedTablesDisplay();
        
        // Hide dropdown and refocus input
        hideTableMentionDropdown();
        queryInput.focus();
    }
    
    // Update removeSelectedTable to handle styling
    function removeSelectedTable(tableName) {
        // Find and remove the table reference from the input
        const tableRef = `@${tableName}`;
        queryInput.value = queryInput.value.replace(tableRef, '');
        
        // Remove the table from our selected tables array
        selectedTables = selectedTables.filter(t => t !== tableName);
        
        // Update the selected tables display
        updateSelectedTablesDisplay();
        
        // Update styling if needed
        if (selectedTables.length === 0) {
            queryInput.style.color = ''; // Reset to default color
            queryInput.removeAttribute('data-has-mentions');
        }
    }
    
    // Show selected tables visually below the input field
    function updateSelectedTablesDisplay() {
        // Find the container using the direct class name
        const container = document.querySelector('.selected-tables-container');
        if (!container) {
            console.error('Selected tables container not found');
            return;
        }
        
        // Clear existing badges
        container.innerHTML = '';
        
        // Add new badges for selected tables
        if (selectedTables && selectedTables.length > 0) {
            selectedTables.forEach(table => {
                const badge = document.createElement('div');
                badge.className = 'table-badge';
                badge.innerHTML = `${table}<span class="remove-table" data-table="${table}">&times;</span>`;
                container.appendChild(badge);
                
                // Add click handler to view table info
                badge.addEventListener('click', function(e) {
                    if (!e.target.classList.contains('remove-table')) {
                        showTableInfo(table);
                    }
                });
            });
            
            // Add click handlers for remove buttons
            container.querySelectorAll('.remove-table').forEach(btn => {
                btn.addEventListener('click', function() {
                    const tableToRemove = this.getAttribute('data-table');
                    removeSelectedTable(tableToRemove);
                });
            });
        }
    }
    
    // Prepare input for submission - replace any @table mentions with proper format if needed
    function prepareInputForSubmission() {
        // You can use this function to format the query before sending to backend
        // For now we just return the current input text as is
        return queryInput.value;
    }

    // Replace the real input with a visual representation that shows tables as colored tags
    function highlightTablesInInput() {
        const inputField = queryInput;
        const inputContainer = inputField.parentElement;
        
        // Ensure we're working with the actual input field
        if (!inputField || inputField.tagName !== 'TEXTAREA') return;
        
        // Get the existing display element or create a new one
        let highlightedDisplay = inputContainer.querySelector('.highlighted-input');
        if (!highlightedDisplay) {
            // Create container for highlighted input that will overlay the real input
            highlightedDisplay = document.createElement('div');
            highlightedDisplay.className = 'highlighted-input';
            highlightedDisplay.style.position = 'absolute';
            highlightedDisplay.style.top = '0';
            highlightedDisplay.style.left = '0';
            highlightedDisplay.style.width = '100%';
            highlightedDisplay.style.height = '100%';
            highlightedDisplay.style.padding = window.getComputedStyle(inputField).padding;
            highlightedDisplay.style.backgroundColor = 'transparent';
            highlightedDisplay.style.pointerEvents = 'none';
            
            // Add the display element
            inputContainer.style.position = 'relative';
            inputContainer.appendChild(highlightedDisplay);
        }
        
        // Format the content with highlighted tables
        let html = inputField.value;
        
        // Replace table references with colored spans
        selectedTables.forEach(table => {
            const tableRef = `@${table}`;
            const tableTag = `<span class="highlighted-table">${tableRef}</span>`;
            html = html.split(tableRef).join(tableTag);
        });
        
        // Set the formatted content
        highlightedDisplay.innerHTML = html;
    }
    
    // Show detailed information about a specific table
    async function showTableInfo(tableName) {
        try {
            showLoading();
            
            // First load the schema
            const response = await fetch(`/api/schema?workspace=${workspaceSelect.value}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load schema');
            }

            // Format schema data into HTML
            const schemaHtml = formatSchemaData(result.schema);
            document.getElementById('schemaContent').innerHTML = schemaHtml;

            // Initialize filtering and set selected table
            initializeSchemaFiltering(result.schema);
            
            // Set the table filter dropdown to this specific table
            const tableFilter = document.getElementById('tableFilter');
            if (tableFilter) {
                tableFilter.value = tableName;
                // Trigger change event to update display
                const event = new Event('change');
                tableFilter.dispatchEvent(event);
            }
            
            // Show the schema modal
            schemaModal.show();
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    }
    
    // Fetch available table names for the current workspace
    function fetchTableNames() {
        const workspace = workspaceSelect.value;
        fetch(`/api/tables/suggestions?workspace=${encodeURIComponent(workspace)}`)
            .then(response => response.json())
            .then(data => {
                if (data.suggestions) {
                    tableNames = data.suggestions.map(s => s.name);
                }
            })
            .catch(error => console.error('Error fetching table names:', error));
    }

    function initializeEmptyTable() {
        if (dataTable) {
            dataTable.destroy();
        }
        
        $('#resultsTable').html('<thead><tr><th>No Results</th></tr></thead><tbody><tr><td>Run a query to see results</td></tr></tbody>');
        
        dataTable = $('#resultsTable').DataTable({
            responsive: true,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            language: {
                search: "Filter results:",
                lengthMenu: "Show _MENU_ entries per page",
                emptyTable: "No results available"
            }
        });
    }

    function initializeDataTable(columns, data) {
        // Destroy existing DataTable if it exists
        if (dataTable) {
            dataTable.destroy();
        }

        // Clear and rebuild table structure
        const table = $('#resultsTable');
        table.empty();
        
        // Create thead with columns
        const thead = $('<thead>').appendTo(table);
        const headerRow = $('<tr>').appendTo(thead);
        columns.forEach(col => {
            $('<th>').text(col).appendTo(headerRow);
        });
        
        // Create tbody
        $('<tbody>').appendTo(table);

        // Initialize DataTable with data
        dataTable = table.DataTable({
            data: data,
            columns: columns.map(col => ({ 
                title: col,
                data: null,
                render: function(data, type, row, meta) {
                    return row[meta.col] ?? '';
                }
            })),
            responsive: true,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            language: {
                search: "Filter results:",
                lengthMenu: "Show _MENU_ entries per page",
                emptyTable: "No results available"
            }
        });
    }

    function showLoading() {
        loadingSpinner.classList.remove('d-none');
    }

    function hideLoading() {
        loadingSpinner.classList.add('d-none');
    }

    function updateWorkspaceDescription() {
        const selectedOption = workspaceSelect.selectedOptions[0];
        const description = selectedOption.getAttribute('data-description') || '';
        document.querySelector('.workspace-description').textContent = description;
    }

    function updateProgress(step, totalSteps = 4) {
        const progressBar = document.querySelector('#queryProgress');
        const progressStatus = progressBar.querySelector('.progress-status');
        const progressPercentage = progressBar.querySelector('.progress-percentage');
        const progressBarInner = progressBar.querySelector('.progress-bar');
        
        const currentStep = step + 1;
        const percentage = Math.round((currentStep / totalSteps) * 100);
        
        progressBar.classList.remove('d-none');
        progressBarInner.style.width = `${percentage}%`;
        progressBarInner.setAttribute('aria-valuenow', percentage);
        progressPercentage.textContent = `${percentage}%`;
        
        const stepMessages = {
            0: "Analyzing query intent...",
            1: "Identifying relevant tables...",
            2: "Selecting relevant columns...",
            3: "Generating SQL query..."
        };
        
        progressStatus.textContent = stepMessages[step] || "Processing...";
    }

    async function pollQueryProgress(queryId) {
        try {
            const response = await fetch(`/api/query/progress/${queryId}`);
            
            // Check if we got a 408 status code (timeout)
            if (response.status === 408) {
                clearInterval(progressInterval);
                const result = await response.json();
                showTimeoutWarning(result.error || "Query processing timed out after 2 minutes");
                document.querySelector('#queryProgress').classList.add('d-none');
                return;
            }
            
            if (!response.ok) {
                clearInterval(progressInterval);
                const result = await response.json();
                showError(result.error || "An error occurred while processing your query");
                document.querySelector('#queryProgress').classList.add('d-none');
                return;
            }
            
            const progress = await response.json();
            
            if (progress.error) {
                clearInterval(progressInterval);
                // Check if it's a timeout error based on message content
                if (progress.error.includes('timed out')) {
                    showTimeoutWarning(progress.error);
                } else {
                    showError(progress.error);
                }
                document.querySelector('#queryProgress').classList.add('d-none');
                return;
            }
            
            // Update progress bar and steps
            if (progress.steps && progress.steps.length > 0) {
                updateProgress(progress.current_step - 1);
                displaySteps(progress.steps, progress.current_step - 1);
            }
            
            // If query is complete, display results and stop polling
            if (progress.status === 'completed' && progress.result) {
                clearInterval(progressInterval);
                displayResults(progress.result);
                document.querySelector('#queryProgress').classList.add('d-none');
            } else if (progress.status === 'error') {
                clearInterval(progressInterval);
                // Check if it's a timeout error based on message content
                if (progress.error && progress.error.includes('timed out')) {
                    showTimeoutWarning(progress.error || 'The query processing timed out');
                } else {
                    showError(progress.error || 'An error occurred while processing your query');
                }
                document.querySelector('#queryProgress').classList.add('d-none');
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }

    function clearAllResults() {
        try {
            // Clear SQL tab
            const sqlCodeElement = document.getElementById('sqlCode');
            if (sqlCodeElement) {
                sqlCodeElement.textContent = '';
                sqlCodeElement.innerHTML = '';
            }
            
            // Clear explanation tab
            const explanationElement = document.getElementById('explanationText');
            if (explanationElement) {
                explanationElement.innerHTML = '';
            }
            
            // Clear steps tab content
            const stepsContainer = document.getElementById('steps-container');
            if (stepsContainer) {
                stepsContainer.innerHTML = '';
            }
            
            // Also clear the steps tab itself
            const stepsTab = document.getElementById('steps');
            if (stepsTab) {
                stepsTab.innerHTML = '';
            }
            
            // Reset DataTable with empty state
            initializeEmptyTable();
        } catch (error) {
            console.error('Error clearing results:', error);
        }
    }

    async function submitQuery() {
        const query = queryInput.value.trim();
        if (!query) {
            showError('Please enter a query');
            return;
        }

        // Clear previous results
        clearAllResults();

        // Reset UI state and show progress bar
        document.querySelector('#queryProgress').classList.remove('d-none');
        updateProgress(0);
        
        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    workspace: workspaceSelect.value,
                    tables: selectedTables  // Include selected tables
                })
            });
            
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Failed to process query');
            }
            
            const result = await response.json();
            
            // Start polling for progress
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            progressInterval = setInterval(() => pollQueryProgress(result.query_id), 500);
            
        } catch (error) {
            showError(error.message);
            document.querySelector('#queryProgress').classList.add('d-none');
        }
    }

    function displayResults(result) {
        // Format and display SQL with syntax highlighting
        const sqlCode = document.getElementById('sqlCode');
        sqlCode.className = 'sql';
        sqlCode.textContent = result.sql || '';
        
        // Format SQL keywords
        const formattedSQL = result.sql.replace(
            /\b(SELECT|FROM|WHERE|JOIN|ON|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|AND|OR|AS|DISTINCT|INNER|LEFT|RIGHT|OUTER|UNION|ALL|LIMIT|OFFSET|DESC|ASC)\b/gi,
            match => `<span class="sql-keyword">${match}</span>`
        );
        sqlCode.innerHTML = formattedSQL;
        
        // Display explanation
        document.getElementById('explanationText').innerHTML = result.explanation || '';
        
        // Handle data table results
        if (result.chart_data && result.chart_data.data) {
            const columns = result.chart_data.columns;
            const data = result.chart_data.data;
            
            if (dataTable) {
                dataTable.destroy();
            }
            
            const table = $('#resultsTable');
            table.empty();
            
            const thead = $('<thead>').appendTo(table);
            const headerRow = $('<tr>').appendTo(thead);
            columns.forEach(col => {
                $('<th>').text(col).appendTo(headerRow);
            });
            
            $('<tbody>').appendTo(table);
            
            // Initialize DataTable with improved configuration
            dataTable = table.DataTable({
                data: data,
                columns: columns.map(col => ({
                    data: col,
                    title: col,
                    render: function(data, type, row) {
                        if (type === 'display') {
                            // Handle long text content
                            if (data && data.length > 50) {
                                return `<span title="${data}">${data.substr(0, 50)}...</span>`;
                            }
                        }
                        return data;
                    }
                })),
                responsive: true,
                autoWidth: false,
                dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                     '<"row"<"col-sm-12"tr>>' +
                     '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
                pageLength: 10,
                lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
                columnDefs: [{
                    targets: '_all',
                    className: 'text-wrap'
                }]
            });
        } else {
            initializeEmptyTable();
        }

        // Display steps
        const stepsContainer = document.createElement('div');
        stepsContainer.className = 'steps-timeline';
        
        if (result.steps && result.steps.length > 0) {
            result.steps.forEach((step, index) => {
                const stepElement = document.createElement('div');
                stepElement.className = 'step-item mb-4';
                stepElement.innerHTML = `
                    <div class="d-flex align-items-start">
                        <div class="step-number bg-primary text-white rounded-circle p-2 me-3">
                            ${index + 1}
                        </div>
                        <div class="step-content">
                            <h6 class="mb-1">${step.step}</h6>
                            <p class="text-muted mb-2">${step.description}</p>
                            ${step.result ? `
                                <div class="step-result bg-light p-3 rounded">
                                    <pre class="mb-0"><code>${typeof step.result === 'object' ? 
                                        JSON.stringify(step.result, null, 2) : step.result}</code></pre>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
                stepsContainer.appendChild(stepElement);
            });
        } else {
            stepsContainer.innerHTML = '<p class="text-muted">No processing steps available</p>';
        }
        
        // Clear and update steps tab content
        const stepsTab = document.getElementById('steps');
        stepsTab.innerHTML = '';
        stepsTab.appendChild(stepsContainer);
    }

    async function loadSchema() {
        showLoading();
        try {
            const response = await fetch(`/api/schema?workspace=${workspaceSelect.value}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load schema');
            }

            // Format schema data into HTML
            const schemaHtml = formatSchemaData(result.schema);
            document.getElementById('schemaContent').innerHTML = schemaHtml;

            // Update table filter dropdown and set up filtering
            initializeSchemaFiltering(result.schema);

            schemaModal.show();
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    }

    function formatSchemaData(schemaData) {
        return schemaData.map(table => {
            const primaryKeys = table.columns
                .filter(col => col.is_primary_key)
                .map(col => col.name);
                
            return `
                <div class="schema-table-container" data-table="${table.name}">
                    <h4>${table.name}</h4>
                    ${table.description ? `<p class="text-muted mb-3">${table.description}</p>` : ''}
                    <table class="table table-sm table-striped schema-table">
                        <thead>
                            <tr>
                                <th>Column</th>
                                <th>Type</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${table.columns.map(col => `
                                <tr ${col.is_primary_key ? 'class="table-primary"' : ''}>
                                    <td>${col.name}</td>
                                    <td>${col.datatype}</td>
                                    <td>${col.description || ''}</td>
                                </tr>
                            `).join('')}
                            ${primaryKeys.length > 0 ? `
                                <tr class="table-primary">
                                    <td colspan="3">
                                        <strong>Primary Key(s):</strong> ${primaryKeys.join(', ')}
                                    </td>
                                </tr>
                            ` : ''}
                        </tbody>
                    </table>
                </div>
            `;
        }).join('\n');
    }

    function initializeSchemaFiltering(schemaData) {
        const tableFilter = document.getElementById('tableFilter');
        tableFilter.innerHTML = '<option value="all">All Tables</option>';
        
        // Add table options
        schemaData
            .map(table => table.name)
            .sort()
            .forEach(tableName => {
                const option = document.createElement('option');
                option.value = tableName;
                option.textContent = tableName;
                tableFilter.appendChild(option);
            });

        // Remove any existing event listener and add a new one
        tableFilter.removeEventListener('change', filterSchemaTables);
        tableFilter.addEventListener('change', filterSchemaTables);
    }

    function filterSchemaTables(event) {
        const selectedTable = event.target.value;
        const tables = document.querySelectorAll('.schema-table-container');
        
        tables.forEach(table => {
            if (selectedTable === 'all' || table.dataset.table === selectedTable) {
                table.style.display = '';
            } else {
                table.style.display = 'none';
            }
        });
    }

    function showError(message) {
        // Create toast notification for error
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function showSuccess(message) {
        // Create toast notification for success
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function displaySteps(steps, currentStep = -1) {
        const stepsContainer = document.getElementById('steps');
        if (!stepsContainer) return;

        // Create steps container if it doesn't exist
        let stepsTimeline = stepsContainer.querySelector('.steps-timeline');
        if (!stepsTimeline) {
            stepsTimeline = document.createElement('div');
            stepsTimeline.className = 'steps-timeline';
            stepsContainer.appendChild(stepsTimeline);
        }

        // Update or create each step
        steps.forEach((step, index) => {
            let stepElement = stepsContainer.querySelector(`.step-item[data-step="${index}"]`);
            const isCurrentStep = index === currentStep;
            const isPastStep = index < currentStep;
            
            if (!stepElement) {
                stepElement = document.createElement('div');
                stepElement.className = 'step-item mb-4';
                stepElement.setAttribute('data-step', index);
                stepsTimeline.appendChild(stepElement);
            }

            stepElement.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="step-number ${isPastStep ? 'bg-success' : isCurrentStep ? 'bg-primary' : 'bg-secondary'} text-white rounded-circle p-2 me-3">
                        ${isPastStep ? '<i class="fas fa-check"></i>' : (index + 1)}
                    </div>
                    <div class="step-content">
                        <h6 class="mb-1">${step.step || step.name}</h6>
                        <p class="text-muted mb-2">${step.description}</p>
                        ${step.result ? `
                            <div class="step-result bg-light p-3 rounded">
                                <pre class="mb-0"><code>${typeof step.result === 'object' ? 
                                    JSON.stringify(step.result, null, 2) : step.result}</code></pre>
                            </div>
                        ` : ''}
                    </div>
                </div>
                ${isCurrentStep ? '<div class="current-step-indicator pulsing"></div>' : ''}
            `;

            // Add visual state classes
            stepElement.classList.remove('completed', 'current', 'pending');
            if (isPastStep) {
                stepElement.classList.add('completed');
            } else if (isCurrentStep) {
                stepElement.classList.add('current');
            } else {
                stepElement.classList.add('pending');
            }
        });

        // Show the steps tab if it was hidden
        const stepsTab = document.querySelector('[href="#steps"]');
        if (stepsTab) {
            const tab = new bootstrap.Tab(stepsTab);
            tab.show();
        }
    }

    // Remove all other displaySteps function definitions and update handleResponse accordingly
    function handleResponse(response) {
        if (response.steps) {
            displaySteps(response.steps);
            $('#steps-tab').show();
        } else {
            $('#steps-tab').hide();
        }
        
        $('.results-container').show();
        $('#loading').hide();
    }

    // Initialize UI elements
    const resultsContainer = document.querySelector('.results-container');
    const loadingIndicator = document.getElementById('loading');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const sqlCode = document.getElementById('sql-code');
    const stepsContainer = document.getElementById('steps-container');
    const explanationContainer = document.getElementById('explanation-container');
    
    // Handle form submission
    submitButton.addEventListener('click', function() {
        const query = queryInput.value.trim();
        if (!query) {
            showError('Please enter a query');
            return;
        }

        // Show loading state
        loadingIndicator.style.display = 'block';
        resultsContainer.style.display = 'block';
        errorContainer.style.display = 'none';
        
        // Make API request
        fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.style.display = 'none';
            
            if (data.error) {
                showError(data.error);
                return;
            }

            // Display SQL
            sqlCode.textContent = data.sql || 'No SQL generated';
            Prism.highlightElement(sqlCode);

            // Display explanation
            if (data.explanation) {
                explanationContainer.innerHTML = `<p class="mb-3">${data.explanation}</p>`;
                explanationContainer.style.display = 'block';
            } else {
                explanationContainer.style.display = 'none';
            }

            // Display steps
            displaySteps(data.steps);
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            showError('An error occurred while processing your request');
            console.error('Error:', error);
        });
    });

    // Show error message
    function showError(message) {
        errorContainer.style.display = 'block';
        errorMessage.textContent = message;
        resultsContainer.style.display = 'none';
    }

    // Handle example queries
    document.querySelectorAll('.example-query').forEach(example => {
        example.addEventListener('click', function() {
            queryInput.value = this.textContent;
            submitButton.click();
        });
    });

    // Copy SQL button

    function showTimeoutWarning(message) {
        // Create toast notification for timeout warnings - using a different style than regular errors
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-warning border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('data-bs-autohide', 'false'); // Don't auto-hide timeout warnings
        
        // Add an icon and more detailed message for timeouts
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-clock me-2"></i><strong>Query Timeout:</strong> ${message}
                    <div class="mt-2 small">Try simplifying your query or filtering to fewer tables.</div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, {
            autohide: false // Ensure timeout warnings stay visible until dismissed
        });
        bsToast.show();
        
        // Also display a message in the results area
        const resultsTab = document.getElementById('results');
        if (resultsTab) {
            const timeoutMessage = document.createElement('div');
            timeoutMessage.className = 'alert alert-warning mt-3';
            timeoutMessage.innerHTML = `
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Query Processing Timeout</h5>
                <p>${message}</p>
                <hr>
                <p class="mb-0">Suggestions:</p>
                <ul>
                    <li>Try a simpler query with fewer conditions</li>
                    <li>Specify tables using the @ mention feature to focus the query</li>
                    <li>Break down your question into smaller parts</li>
                </ul>
            `;
            resultsTab.innerHTML = '';
            resultsTab.appendChild(timeoutMessage);
            
            // Show the results tab
            const resultsTabLink = document.querySelector('[href="#results"]');
            if (resultsTabLink) {
                const tab = new bootstrap.Tab(resultsTabLink);
                tab.show();
            }
        }
        
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

});