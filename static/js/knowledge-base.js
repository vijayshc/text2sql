/**
 * Knowledge Base JS - Handles knowledge base chat UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Tags handling with new compact UI
    const selectedTags = [];
    let availableTags = [];
    const tagSearchInput = document.getElementById('tagSearchInput');
    const tagOptionsContainer = document.getElementById('tagOptionsContainer');
    const selectedTagsPreview = document.getElementById('selectedTagsPreview');
    const selectedTagsList = document.getElementById('selectedTagsList');
    const clearAllTagsBtn = document.getElementById('clearAllTags');
    const tagFilterText = document.getElementById('tagFilterText');
    const tagCountBadge = document.getElementById('tagCountBadge');
    
    // Radio buttons for search type
    const searchKnowledgeRadio = document.getElementById('search-knowledge');
    const searchMetadataRadio = document.getElementById('search-metadata');
    const tagFilterContainer = document.querySelector('.tag-filter-container');
    
    // Add event listeners to toggle tag filter container visibility
    if (searchKnowledgeRadio && searchMetadataRadio && tagFilterContainer) {
        // Set initial state
        tagFilterContainer.style.display = searchKnowledgeRadio.checked ? 'block' : 'none';
        
        // Add event listeners for radio button changes
        searchKnowledgeRadio.addEventListener('change', function() {
            tagFilterContainer.style.display = 'block';
        });
        
        searchMetadataRadio.addEventListener('change', function() {
            tagFilterContainer.style.display = 'block';
        });
    }
    
    // Load available tags
    loadAvailableTags();
    
    // Handle tag search input
    if (tagSearchInput) {
        tagSearchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            filterTagOptions(searchTerm);
        });
    }
    
    // Handle clear all tags button
    if (clearAllTagsBtn) {
        clearAllTagsBtn.addEventListener('click', function() {
            clearAllTags();
        });
    }
    
    // Function to load available tags
    function loadAvailableTags() {
        fetch('/api/knowledge/tags')
            .then(response => response.json())
            .then(data => {
                if (data.success && Array.isArray(data.tags)) {
                    availableTags = data.tags;
                    renderTagOptions();
                } else {
                    showTagOptionsMessage('No tags available');
                }
            })
            .catch(error => {
                console.error('Error loading tags:', error);
                showTagOptionsMessage('Error loading tags');
            });
    }
    
    // Function to render tag options
    function renderTagOptions(filteredTags = null) {
        if (!tagOptionsContainer) return;
        
        const tagsToShow = filteredTags || availableTags;
        tagOptionsContainer.innerHTML = '';
        
        if (tagsToShow.length === 0) {
            showTagOptionsMessage('No tags found');
            return;
        }
        
        tagsToShow.forEach(tag => {
            const tagOption = document.createElement('div');
            tagOption.className = 'tag-option';
            
            const isSelected = selectedTags.includes(tag);
            tagOption.innerHTML = `
                <input type="checkbox" class="form-check-input" id="tag-${tag}" ${isSelected ? 'checked' : ''}>
                <label class="form-check-label" for="tag-${tag}">${tag}</label>
            `;
            
            const checkbox = tagOption.querySelector('.form-check-input');
            const label = tagOption.querySelector('.form-check-label');
            
            // Handle checkbox change
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    addTag(tag);
                } else {
                    removeTag(tag);
                }
            });
            
            // Handle clicking on the entire option
            tagOption.addEventListener('click', function(e) {
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
            
            tagOptionsContainer.appendChild(tagOption);
        });
    }
    
    // Function to filter tag options based on search term
    function filterTagOptions(searchTerm) {
        if (!searchTerm) {
            renderTagOptions();
            return;
        }
        
        const filteredTags = availableTags.filter(tag => 
            tag.toLowerCase().includes(searchTerm.toLowerCase())
        );
        renderTagOptions(filteredTags);
    }
    
    // Function to show message in tag options container
    function showTagOptionsMessage(message) {
        if (!tagOptionsContainer) return;
        
        tagOptionsContainer.innerHTML = `
            <div class="text-center text-muted py-2">
                <small>${message}</small>
            </div>
        `;
    }
    
    // Function to add a tag
    function addTag(tag) {
        if (!selectedTags.includes(tag)) {
            selectedTags.push(tag);
            updateTagDisplay();
            updateTagCheckboxes();
        }
    }
    
    // Function to remove a tag
    function removeTag(tag) {
        const index = selectedTags.indexOf(tag);
        if (index !== -1) {
            selectedTags.splice(index, 1);
            updateTagDisplay();
            updateTagCheckboxes();
        }
    }
    
    // Function to clear all tags
    function clearAllTags() {
        selectedTags.length = 0;
        updateTagDisplay();
        updateTagCheckboxes();
    }
    
    // Function to update tag display and UI elements
    function updateTagDisplay() {
        updateFilterButtonText();
        updateSelectedTagsPreview();
    }
    
    // Function to update the filter button text and badge
    function updateFilterButtonText() {
        if (!tagFilterText || !tagCountBadge) return;
        
        if (selectedTags.length === 0) {
            tagFilterText.textContent = 'Filter by tags';
            tagCountBadge.classList.add('d-none');
        } else {
            tagFilterText.textContent = `Tags (${selectedTags.length})`;
            tagCountBadge.textContent = selectedTags.length;
            tagCountBadge.classList.remove('d-none');
        }
    }
    
    // Function to update selected tags preview
    function updateSelectedTagsPreview() {
        if (!selectedTagsPreview || !selectedTagsList) return;
        
        if (selectedTags.length === 0) {
            selectedTagsPreview.style.display = 'none';
            return;
        }
        
        selectedTagsPreview.style.display = 'block';
        selectedTagsList.innerHTML = '';
        
        selectedTags.forEach(tag => {
            const tagPill = document.createElement('span');
            tagPill.className = 'selected-tag-pill';
            tagPill.innerHTML = `${tag} <span class="remove-tag" data-tag="${tag}">×</span>`;
            
            const removeBtn = tagPill.querySelector('.remove-tag');
            removeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                removeTag(tag);
            });
            
            selectedTagsList.appendChild(tagPill);
        });
    }
    
    // Function to update checkboxes in the options container
    function updateTagCheckboxes() {
        const checkboxes = tagOptionsContainer.querySelectorAll('.form-check-input');
        checkboxes.forEach(checkbox => {
            const tag = checkbox.id.replace('tag-', '');
            checkbox.checked = selectedTags.includes(tag);
        });
    }
    
    // Initialize markdown-it - the library exposes itself as a function, not as markdownIt
    const md = window.markdownit({
        html: false,
        linkify: true,
        typographer: true,
        highlight: function (str, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(str, { language: lang }).value;
                } catch (__) {}
            }
            return ''; // use external default escaping
        }
    });

    const messagesContainer = document.getElementById('knowledgeMessages');
    const queryInput = document.getElementById('knowledgeQuery');
    const sendButton = document.getElementById('sendQueryBtn');
    
    // Function to add a user message to the chat
    function addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `
            <div class="avatar user-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="message-content">
                <p>${text}</p>
            </div>
        `;
        // Insert at the beginning of the container instead of appending
        if (messagesContainer.firstChild) {
            messagesContainer.insertBefore(messageDiv, messagesContainer.firstChild);
        } else {
            messagesContainer.appendChild(messageDiv);
        }
        messagesContainer.scrollTop = 0; // Scroll to the top where new messages appear
    }
    
    // Function to add a system/AI message to the chat
    function addSystemMessage(html, withSpinner = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        messageDiv.innerHTML = `
            <div class="avatar system-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                ${withSpinner ? '<div class="spinner-border spinner-border-sm text-primary mb-2" role="status"><span class="visually-hidden">Loading...</span></div>' : ''}
                <div class="markdown-content">${html}</div>
            </div>
        `;
        // Insert at the beginning of the container instead of appending
        if (messagesContainer.firstChild) {
            messagesContainer.insertBefore(messageDiv, messagesContainer.firstChild);
        } else {
            messagesContainer.appendChild(messageDiv);
        }
        messagesContainer.scrollTop = 0; // Scroll to the top where new messages appear
        return messageDiv;
    }
    
    // Function to update a system message (e.g., replace loading spinner with content)
    function updateSystemMessage(messageDiv, html) {
        const contentDiv = messageDiv.querySelector('.markdown-content');
        if (contentDiv) {
            contentDiv.innerHTML = html;
        }
        // Remove spinner if present
        const spinner = messageDiv.querySelector('.spinner-border');
        if (spinner) {
            spinner.remove();
        }
    }
    
    // Function to handle sending a query
    function sendQuery() {
        const query = queryInput.value.trim();
        if (!query) return;
        
        // Add the user's query to the chat
        addUserMessage(query);
        
        // Get search type from radio button if it exists
        const isMetadataSearch = document.getElementById('search-metadata') && 
                                document.getElementById('search-metadata').checked;
        
        // Create loading message with appropriate text
        const loadingText = isMetadataSearch ? 'Searching database metadata...' : 'Searching knowledge base...';
        const loadingMessage = addSystemMessage(loadingText, true);
        
        // Clear input
        queryInput.value = '';
        
        // If metadata search is selected, use the metadata search endpoint
        if (isMetadataSearch) {
            // Initialize an empty markdown content div with streaming support
            updateSystemMessage(loadingMessage, '<div class="streaming-content"></div>');
            const streamingContentDiv = loadingMessage.querySelector('.streaming-content');
            let eventSource;
            let sources = [];
            
            // First make the initial POST request to set up the stream
            fetch('/api/metadata/search/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': document.querySelector('input[name="csrf_token"]')?.value || ''
                },
                body: JSON.stringify({
                    query: query,
                    limit: 100
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Now open an EventSource connection to get the streaming response
                    if (eventSource) {
                        eventSource.close();
                    }
                    
                    eventSource = new EventSource(`/api/metadata/search/stream?query=${encodeURIComponent(query)}`);
                    let accumulatedText = '';
                    
                    // Listen for sources event
                    eventSource.addEventListener('sources', function(event) {
                        try {
                            sources = JSON.parse(event.data);
                            // Add sources information at the top if available
                            if (sources && sources.length > 0) {
                                const tagsInfo = `<div class="schema-sources-info">
                                    
                                </div>`;
                                streamingContentDiv.innerHTML = tagsInfo + streamingContentDiv.innerHTML;
                            }
                        } catch (e) {
                            console.error('Error parsing sources:', e);
                        }
                    });
                    
                    // Listen for message events (chunks of text)
                    eventSource.onmessage = function(event) {
                        try {
                            const data = JSON.parse(event.data);
                            if (data.text) {
                                accumulatedText += data.text;
                                // Convert markdown to HTML
                                const answerHtml = md.render(accumulatedText);
                                streamingContentDiv.innerHTML = sources.length > 0 ? 
                                    streamingContentDiv.innerHTML.split('</div>')[0] + '</div>' + answerHtml : 
                                    answerHtml;
                                
                                // Highlight any code blocks
                                streamingContentDiv.querySelectorAll('pre code').forEach((block) => {
                                    hljs.highlightElement(block);
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing message:', e);
                        }
                    };
                    
                    // Listen for done event
                    eventSource.addEventListener('done', function() {
                        eventSource.close();
                        
                      
                    });
                    
                    // Listen for error event
                    eventSource.onerror = function() {
                        eventSource.close();
                        if (!accumulatedText) {
                            updateSystemMessage(loadingMessage, `<p class="text-danger">Error: Failed to stream response</p>`);
                        }
                    };
                    
                } else {
                    updateSystemMessage(loadingMessage, `<p class="text-danger">Error: ${data.error || 'Unknown error occurred'}</p>`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                updateSystemMessage(loadingMessage, `<p class="text-danger">Sorry, an error occurred: ${error.message}</p>`);
            });
            
            return; // Exit function after handling metadata search
        }
        
        // For knowledge base search, continue with existing streaming logic
        let eventSource;
        let sources = [];
        let accumulatedText = '';
        
        // Initialize an empty markdown content div
        updateSystemMessage(loadingMessage, '<div class="streaming-content"></div>');
        const streamingContentDiv = loadingMessage.querySelector('.streaming-content');
        
        // Display tags if any are selected
        let tagsInfo = '';
        if (selectedTags.length > 0) {
            tagsInfo = `<div class="tags-info mb-2"><small class="text-muted">Filtered by tags: ${selectedTags.map(tag => `<span class="badge bg-info text-dark">${tag}</span>`).join(' ')}</small></div>`;
            streamingContentDiv.innerHTML = tagsInfo + streamingContentDiv.innerHTML;
        }
        
        // First make a POST request to initiate the query
        fetch('/api/knowledge/query/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('input[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify({ 
                query: query,
                tags: selectedTags 
            })
        }).then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            // Now establish an SSE connection to stream the response
            // Add timestamp to prevent caching
            eventSource = new EventSource(`/api/knowledge/query/stream?query=${encodeURIComponent(query)}&t=${new Date().getTime()}`);
            
            // Set up event handlers for the EventSource
            // Handle the sources event
            eventSource.addEventListener('sources', function(e) {
                sources = JSON.parse(e.data);
            });
            
            // Handle incoming chunks
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                if (data.text) {
                    accumulatedText += data.text;
                    // Convert markdown to HTML
                    const answerHtml = md.render(accumulatedText);
                    streamingContentDiv.innerHTML = answerHtml;
                    
                    // Highlight any code blocks
                    streamingContentDiv.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                    
                    // Scroll to the bottom
                    //messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            };
            
            // Handle completion
            eventSource.addEventListener('done', function(e) {
                // Add sources information
                let sourcesHtml = '';
                if (sources && sources.length > 0) {
                    // Deduplicate the list of documents
                    const uniqueDocuments = [];
                    const documentSet = new Set();
                    
                    sources.forEach(source => {
                        if (!documentSet.has(source.document)) {
                            documentSet.add(source.document);
                            uniqueDocuments.push(source.document);
                        }
                    });
                    
                    // Create HTML for unique documents list
                    sourcesHtml = '<div class="sources mt-3">' +
                        '<small class="text-muted">Sources:</small>' +
                        '<ul class="source-list">';
                    
                    uniqueDocuments.forEach(document => {
                        sourcesHtml += `<li>${document}</li>`;
                    });
                    
                    sourcesHtml += '</ul></div>';
                }
                
                // Append sources to the message
                streamingContentDiv.insertAdjacentHTML('afterend', sourcesHtml);
                
                // Close the connection
                eventSource.close();
            });
            
            // Handle errors
            eventSource.onerror = function(error) {
                console.error('EventSource error:', error);
                if (accumulatedText) {
                    // Keep what we've got so far
                    console.log('SSE connection closed after partial response');
                } else {
                    updateSystemMessage(loadingMessage, '<p class="text-danger">Sorry, the connection was interrupted while processing your question.</p>');
                }
                eventSource.close();
            };
            
        }).catch(error => {
            console.error('Error:', error);
            updateSystemMessage(loadingMessage, '<p class="text-danger">Sorry, an error occurred while communicating with the server.</p>');
        });
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendQuery);
    
    // Allow pressing Enter to send (Shift+Enter for new line)
    queryInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });
});