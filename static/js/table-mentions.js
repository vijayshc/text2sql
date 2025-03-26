/**
 * table-mentions.js - Table mention and autocomplete functionality
 */

const tableMentions = {
    tableMentionDropdown: null,
    mentionActive: false,
    mentionStartPosition: 0,
    currentMentionText: '',
    tableNames: [],
    activeDropdownIndex: -1,
    mentionAnchorPosition: { top: 0, left: 0 },

    // Get or create dropdown element for table mentions
    getTableMentionDropdown: function() {
        if (!this.tableMentionDropdown) {
            this.tableMentionDropdown = document.createElement('div');
            this.tableMentionDropdown.className = 'table-mention-dropdown';
            this.tableMentionDropdown.style.display = 'none';
            document.body.appendChild(this.tableMentionDropdown);
        }
        return this.tableMentionDropdown;
    },
    
    // Show dropdown with table suggestions
    showTableMentionDropdown: function(suggestions) {
        const dropdown = this.getTableMentionDropdown();
        
        // Position the dropdown near the @ symbol
        dropdown.style.top = (this.mentionAnchorPosition.top + window.scrollY + 24) + 'px';
        dropdown.style.left = this.mentionAnchorPosition.left + 'px';
        
        // Clear and populate dropdown
        dropdown.innerHTML = '';
        
        if (suggestions.length === 0) {
            dropdown.innerHTML = '<div class="no-results">No matching tables found</div>';
        } else {
            suggestions.forEach((table, index) => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                if (index === this.activeDropdownIndex) {
                    item.classList.add('active');
                }
                item.innerHTML = `
                    <span class="item-name">${table.name}</span>
                    <span class="item-description">${table.description || ''}</span>
                `;
                item.addEventListener('click', () => this.selectTableFromDropdown(table.name, table.description));
                dropdown.appendChild(item);
            });
        }
        
        dropdown.style.display = 'block';
    },
    
    // Hide suggestion dropdown
    hideTableMentionDropdown: function() {
        if (this.tableMentionDropdown) {
            this.tableMentionDropdown.style.display = 'none';
            this.mentionActive = false;
            this.currentMentionText = '';
            this.activeDropdownIndex = -1;
        }
    },
    
    // Handle key inputs in query input
    handleQueryKeydown: function(e) {
        if (tableMentions.mentionActive && tableMentions.tableMentionDropdown && tableMentions.tableMentionDropdown.style.display !== 'none') {
            const items = tableMentions.tableMentionDropdown.querySelectorAll('.dropdown-item');
            
            // Navigate through dropdown with keyboard
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                tableMentions.activeDropdownIndex = Math.min(tableMentions.activeDropdownIndex + 1, items.length - 1);
                tableMentions.updateActiveItem(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                tableMentions.activeDropdownIndex = Math.max(tableMentions.activeDropdownIndex - 1, 0);
                tableMentions.updateActiveItem(items);
            } else if (e.key === 'Enter' && tableMentions.activeDropdownIndex >= 0) {
                e.preventDefault();
                const activeSuggestion = items[tableMentions.activeDropdownIndex].querySelector('.item-name').textContent;
                tableMentions.selectTableFromDropdown(activeSuggestion);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                tableMentions.hideTableMentionDropdown();
            } else if (e.key === 'Tab') {
                e.preventDefault();
                if (tableMentions.activeDropdownIndex >= 0) {
                    const activeSuggestion = items[tableMentions.activeDropdownIndex].querySelector('.item-name').textContent;
                    tableMentions.selectTableFromDropdown(activeSuggestion);
                }
            }
        } else if (e.key === 'Enter') {
            // Check if Ctrl key is pressed with Enter
            if (e.ctrlKey) {
                e.preventDefault();
                queryHandler.submitQuery();
            }
            // If Enter is pressed without Ctrl, let the default behavior add a newline
        }
    },
    
    // Update the highlighted item in the dropdown
    updateActiveItem: function(items) {
        items.forEach((item, index) => {
            if (index === this.activeDropdownIndex) {
                item.classList.add('active');
                // Scroll item into view if needed
                const containerRect = this.tableMentionDropdown.getBoundingClientRect();
                const itemRect = item.getBoundingClientRect();
                
                if (itemRect.bottom > containerRect.bottom) {
                    this.tableMentionDropdown.scrollTop += (itemRect.bottom - containerRect.bottom);
                }
                if (itemRect.top < containerRect.top) {
                    this.tableMentionDropdown.scrollTop -= (containerRect.top - itemRect.top);
                }
            } else {
                item.classList.remove('active');
            }
        });
    },
    
    // Handle input changes for mention detection and suggestion
    handleQueryInput: function(e) {
        const cursorPos = text2sql.queryInput.selectionStart;
        const text = text2sql.queryInput.value;
        
        // Detect @ symbol immediately before cursor
        if (text.charAt(cursorPos - 1) === '@') {
            tableMentions.mentionActive = true;
            tableMentions.mentionStartPosition = cursorPos - 1;
            tableMentions.currentMentionText = '';
            
            // Get the exact position of the @ symbol for dropdown placement
            const inputRect = text2sql.queryInput.getBoundingClientRect();
            const inputStyle = window.getComputedStyle(text2sql.queryInput);
            const inputPaddingLeft = parseFloat(inputStyle.paddingLeft);
            const inputPaddingTop = parseFloat(inputStyle.paddingTop);
            
            // Create a temporary span to measure text width up to @
            const tempSpan = document.createElement('span');
            tempSpan.style.font = inputStyle.font;
            tempSpan.style.position = 'absolute';
            tempSpan.style.left = '-9999px';
            tempSpan.style.whiteSpace = 'pre';
            tempSpan.textContent = text.substring(0, tableMentions.mentionStartPosition);
            document.body.appendChild(tempSpan);
            
            // Calculate position
            const atSymbolPosition = tempSpan.getBoundingClientRect().width;
            document.body.removeChild(tempSpan);
            
            // Store dropdown position
            tableMentions.mentionAnchorPosition = {
                top: inputRect.top + inputPaddingTop,
                left: inputRect.left + inputPaddingLeft + atSymbolPosition
            };
            
            // Show suggestions with empty query
            tableMentions.fetchTableSuggestions('');
        } else if (tableMentions.mentionActive) {
            // If we're already in mention mode, update the current mention text
            const mentionEndPos = cursorPos;
            tableMentions.currentMentionText = text.substring(tableMentions.mentionStartPosition + 1, mentionEndPos);
            
            if (tableMentions.currentMentionText === '' || /\s/.test(tableMentions.currentMentionText)) {
                // If mention text is empty or contains whitespace, exit mention mode
                tableMentions.hideTableMentionDropdown();
            } else {
                // Otherwise fetch updated suggestions
                tableMentions.fetchTableSuggestions(tableMentions.currentMentionText);
            }
        }
    },
    
    // Fetch table suggestions based on query
    fetchTableSuggestions: function(query) {
        const workspace = text2sql.workspaceSelect.value;
        
        fetch(`/api/tables/suggestions?workspace=${encodeURIComponent(workspace)}&query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.suggestions && data.suggestions.length > 0) {
                    tableMentions.activeDropdownIndex = 0;
                    tableMentions.showTableMentionDropdown(data.suggestions);
                } else {
                    tableMentions.showTableMentionDropdown([]);
                }
            })
            .catch(error => {
                console.error('Error fetching table suggestions:', error);
                tableMentions.hideTableMentionDropdown();
            });
    },
    
    // Highlight @table mentions in the input
    styleMentionsInInput: function() {
        // We need to style any @tableName patterns in the input
        const text = text2sql.queryInput.value;
        
        // Find all instances of @tableName in the text
        text2sql.selectedTables.forEach(tableName => {
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
                text2sql.queryInput.parentNode.style.position = 'relative';
                text2sql.queryInput.parentNode.insertBefore(highlightOverlay, text2sql.queryInput.nextSibling);
            }
            
            highlightOverlay.innerHTML = styledText;
        });
    },
    
    // Select a table from the dropdown
    selectTableFromDropdown: function(tableName, tableDescription) {
        console.log('Before selection - Selected tables:', text2sql.selectedTables);
        
        if (text2sql.selectedTables.includes(tableName)) {
            // Table already selected, don't add duplicate
            this.hideTableMentionDropdown();
            return;
        }
        
        // Add to selected tables
        text2sql.selectedTables.push(tableName);
        console.log('After adding - Selected tables:', text2sql.selectedTables);
        
        // Replace the @mention text with a clean table reference
        const cursorPos = text2sql.queryInput.selectionStart;
        let textBefore = text2sql.queryInput.value.substring(0, this.mentionStartPosition);
        let textAfter = text2sql.queryInput.value.substring(this.mentionStartPosition + this.currentMentionText.length + 1);
        
        // Insert the table name directly (without markers)
        const displayText = `@${tableName} `;
        text2sql.queryInput.value = textBefore + displayText + textAfter;
        
        // Set cursor position after replacement
        text2sql.queryInput.selectionStart = this.mentionStartPosition + displayText.length;
        text2sql.queryInput.selectionEnd = this.mentionStartPosition + displayText.length;
        
        // Update the selected tables display
        this.updateSelectedTablesDisplay();
        
        // Hide dropdown and refocus input
        this.hideTableMentionDropdown();
        text2sql.queryInput.focus();
    },
    
    // Remove a selected table
    removeSelectedTable: function(tableName) {
        // Find and remove the table reference from the input
        const tableRef = `@${tableName}`;
        text2sql.queryInput.value = text2sql.queryInput.value.replace(tableRef, '');
        
        // Remove the table from our selected tables array
        text2sql.selectedTables = text2sql.selectedTables.filter(t => t !== tableName);
        
        // Update the selected tables display
        this.updateSelectedTablesDisplay();
        
        // Update styling if needed
        if (text2sql.selectedTables.length === 0) {
            text2sql.queryInput.style.color = ''; // Reset to default color
            text2sql.queryInput.removeAttribute('data-has-mentions');
        }
    },
    
    // Show selected tables visually below the input field
    updateSelectedTablesDisplay: function() {
        // Find the container using the direct class name
        const container = document.querySelector('.selected-tables-container');
        if (!container) {
            console.error('Selected tables container not found');
            return;
        }
        
        // Clear existing badges
        container.innerHTML = '';
        
        // Add new badges for selected tables
        if (text2sql.selectedTables && text2sql.selectedTables.length > 0) {
            text2sql.selectedTables.forEach(table => {
                const badge = document.createElement('div');
                badge.className = 'table-badge';
                badge.innerHTML = `${table}<span class="remove-table" data-table="${table}">&times;</span>`;
                container.appendChild(badge);
                
                // Add click handler to view table info
                badge.addEventListener('click', function(e) {
                    if (!e.target.classList.contains('remove-table')) {
                        schemaManager.showTableInfo(table);
                    }
                });
            });
            
            // Add click handlers for remove buttons
            container.querySelectorAll('.remove-table').forEach(btn => {
                btn.addEventListener('click', function() {
                    const tableToRemove = this.getAttribute('data-table');
                    tableMentions.removeSelectedTable(tableToRemove);
                });
            });
        }
    },
    
    // Fetch available table names for the current workspace
    fetchTableNames: function() {
        const workspace = text2sql.workspaceSelect.value;
        fetch(`/api/tables/suggestions?workspace=${encodeURIComponent(workspace)}`)
            .then(response => response.json())
            .then(data => {
                if (data.suggestions) {
                    this.tableNames = data.suggestions.map(s => s.name);
                }
            })
            .catch(error => console.error('Error fetching table names:', error));
    },
    
    // Replace the real input with a visual representation that shows tables as colored tags
    highlightTablesInInput: function() {
        const inputField = text2sql.queryInput;
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
        text2sql.selectedTables.forEach(table => {
            const tableRef = `@${table}`;
            const tableTag = `<span class="highlighted-table">${tableRef}</span>`;
            html = html.split(tableRef).join(tableTag);
        });
        
        // Set the formatted content
        highlightedDisplay.innerHTML = html;
    },
    
    // Prepare input for submission - replace any @table mentions with proper format if needed
    prepareInputForSubmission: function() {
        // You can use this function to format the query before sending to backend
        // For now we just return the current input text as is
        return text2sql.queryInput.value;
    }
};