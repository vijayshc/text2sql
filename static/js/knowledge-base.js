/**
 * Knowledge Base JS - Handles knowledge base chat UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
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
        
        // Create loading message
        const loadingMessage = addSystemMessage('Searching knowledge base...', true);
        
        // Clear input
        queryInput.value = '';
        
        let eventSource;
        let sources = [];
        let accumulatedText = '';
        
        // Initialize an empty markdown content div
        updateSystemMessage(loadingMessage, '<div class="streaming-content"></div>');
        const streamingContentDiv = loadingMessage.querySelector('.streaming-content');
        
        // First make a POST request to initiate the query
        fetch('/api/knowledge/query/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('input[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify({ query: query })
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
