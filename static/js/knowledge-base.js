/**
 * Knowledge Base JS - Handles knowledge base chat UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Tags handling
    const selectedTags = [];
    let availableTags = [];
    const tagSearchInput = document.getElementById('tagSearchInput');
    const tagDropdown = document.getElementById('tagDropdown');
    const selectedTagsContainer = document.getElementById('selectedTags');
    const clearTagsBtn = document.getElementById('clearTagsBtn');
    
    // Radio buttons for search type
    const searchKnowledgeRadio = document.getElementById('search-knowledge');
    const searchMetadataRadio = document.getElementById('search-metadata');
    const tagSelectionContainer = document.querySelector('.tag-selection-container');
    
    // Add event listeners to toggle tag selection container visibility
    if (searchKnowledgeRadio && searchMetadataRadio && tagSelectionContainer) {
        // Set initial state
        tagSelectionContainer.style.display = searchKnowledgeRadio.checked ? 'block' : 'none';
        
        // Add event listeners for radio button changes
        searchKnowledgeRadio.addEventListener('change', function() {
            tagSelectionContainer.style.display = 'block';
        });
        
        searchMetadataRadio.addEventListener('change', function() {
            tagSelectionContainer.style.display = 'none';
        });
    }
    
    // Load available tags
    loadAvailableTags();
    
    // Track the currently selected item in dropdown
    let currentFocusIndex = -1;
    
    // Handle tag input for @ mentions
    tagSearchInput.addEventListener('input', function(e) {
        const value = e.target.value;
        currentFocusIndex = -1; // Reset focus index on input change
        
        // Show dropdown only when @ is typed
        if (value.includes('@')) {
            const searchTerm = value.split('@').pop().toLowerCase();
            showTagDropdown(searchTerm);
        } else {
            hideTagDropdown();
        }
    });
    
    // Handle tag input focus
    tagSearchInput.addEventListener('focus', function(e) {
        // If the input already has @, show the dropdown
        if (e.target.value.includes('@')) {
            const searchTerm = e.target.value.split('@').pop().toLowerCase();
            showTagDropdown(searchTerm);
        }
    });
    
    // Handle keyboard navigation for the dropdown
    tagSearchInput.addEventListener('keydown', function(e) {
        // Special handling for down arrow - if dropdown is hidden but @ is in input, show it first
        if (e.key === 'ArrowDown' && tagDropdown.classList.contains('d-none') && tagSearchInput.value.includes('@')) {
            e.preventDefault();
            const searchTerm = tagSearchInput.value.split('@').pop().toLowerCase();
            showTagDropdown(searchTerm);
            // Wait for dropdown to populate before focusing first item
            setTimeout(() => {
                const items = tagDropdown.querySelectorAll('.tag-item');
                if (items.length > 0) {
                    currentFocusIndex = 0;
                    updateFocusedItem(items);
                }
            }, 50);
            return;
        }
        
        // If dropdown is visible, handle keyboard navigation
        if (!tagDropdown.classList.contains('d-none')) {
            const items = tagDropdown.querySelectorAll('.tag-item');
            const itemCount = items.length;
            
            if (itemCount === 0) return;
            
            // Handle arrow down
            if (e.key === 'ArrowDown') {
                e.preventDefault(); // Prevent cursor from moving in input field
                currentFocusIndex = (currentFocusIndex < itemCount - 1) ? currentFocusIndex + 1 : 0;
                updateFocusedItem(items);
            }
            // Handle arrow up
            else if (e.key === 'ArrowUp') {
                e.preventDefault();
                currentFocusIndex = (currentFocusIndex > 0) ? currentFocusIndex - 1 : itemCount - 1;
                updateFocusedItem(items);
            }
            // Handle enter key to select tag
            else if (e.key === 'Enter' && currentFocusIndex >= 0) {
                e.preventDefault();
                const selectedTag = items[currentFocusIndex].textContent;
                addTag(selectedTag);
                hideTagDropdown();
                tagSearchInput.value = '';
            }
            // Handle escape key to close dropdown
            else if (e.key === 'Escape') {
                hideTagDropdown();
            }
        }
    });
    
    // Handle click outside to hide dropdown
    document.addEventListener('click', function(e) {
        if (!tagSearchInput.contains(e.target) && !tagDropdown.contains(e.target)) {
            hideTagDropdown();
        }
    });
    
    // Handle clear tags button
    clearTagsBtn.addEventListener('click', function() {
        clearTags();
    });
    
    // Function to load available tags
    function loadAvailableTags() {
        fetch('/api/knowledge/tags')
            .then(response => response.json())
            .then(data => {
                if (data.success && Array.isArray(data.tags)) {
                    availableTags = data.tags;
                }
            })
            .catch(error => console.error('Error loading tags:', error));
    }
    
    // Function to show tag dropdown with filtered tags
    function showTagDropdown(searchTerm) {
        // Filter tags based on search term
        const filteredTags = availableTags.filter(tag => 
            tag.toLowerCase().includes(searchTerm.toLowerCase()) && 
            !selectedTags.includes(tag)
        );
        
        // Clear dropdown
        tagDropdown.innerHTML = '';
        currentFocusIndex = -1;  // Reset focus index when showing dropdown
        
        if (filteredTags.length === 0) {
            tagDropdown.classList.add('d-none');
            return;
        }
        
        // Add filtered tags to dropdown
        filteredTags.forEach(tag => {
            const tagItem = document.createElement('div');
            tagItem.className = 'tag-item';
            tagItem.textContent = tag;
            tagItem.addEventListener('click', () => {
                addTag(tag);
                hideTagDropdown();
                tagSearchInput.value = '';
            });
            tagDropdown.appendChild(tagItem);
        });
        
        tagDropdown.classList.remove('d-none');
    }
    
    // Function to update the focused item in the dropdown
    function updateFocusedItem(items) {
        // Remove focus from all items
        for (let i = 0; i < items.length; i++) {
            items[i].classList.remove('tag-item-focused');
        }
        
        // Add focus to the selected item
        if (currentFocusIndex >= 0) {
            items[currentFocusIndex].classList.add('tag-item-focused');
            items[currentFocusIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    // Function to hide tag dropdown
    function hideTagDropdown() {
        tagDropdown.classList.add('d-none');
    }
    
    // Function to add a tag
    function addTag(tag) {
        if (!selectedTags.includes(tag)) {
            selectedTags.push(tag);
            renderSelectedTags();
        }
    }
    
    // Function to remove a tag
    function removeTag(tag) {
        const index = selectedTags.indexOf(tag);
        if (index !== -1) {
            selectedTags.splice(index, 1);
            renderSelectedTags();
        }
    }
    
    // Function to clear all tags
    function clearTags() {
        selectedTags.length = 0;
        renderSelectedTags();
    }
    
    // Function to render selected tags
    function renderSelectedTags() {
        selectedTagsContainer.innerHTML = '';
        
        selectedTags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'selected-tag';
            tagElement.innerHTML = `${tag} <span class="tag-remove"><i class="fas fa-times"></i></span>`;
            
            const removeBtn = tagElement.querySelector('.tag-remove');
            removeBtn.addEventListener('click', () => removeTag(tag));
            
            selectedTagsContainer.appendChild(tagElement);
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