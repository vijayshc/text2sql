// Initialize Markdown-it
const md = window.markdownit({
    html: false, // Disable HTML tags in source
    xhtmlOut: false, // Use '/' to close single tags (<br />)
    breaks: true, // Convert '\n' in paragraphs into <br>
    linkify: true, // Autoconvert URL-like text to links
    typographer: true, // Enable some language-neutral replacement + quotes beautification
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return '<pre class="hljs"><code>' +
                       hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                       '</code></pre>';
            } catch (__) {}
        }
        // Use external default escaping
        return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chatHistory');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const agentProgress = document.getElementById('agentProgress');
    const progressStatus = agentProgress.querySelector('.progress-status');
    const teamSelect = document.getElementById('teamSelect');
    const workflowSelect = document.getElementById('workflowSelect');
    const modeSelect = document.getElementById('modeSelect');
    const serverSelect = document.getElementById('serverSelect');
    const autogenTeamCol = document.getElementById('autogenTeamCol');
    const autogenWorkflowCol = document.getElementById('autogenWorkflowCol');
    const mcpServerCol = document.getElementById('mcpServerCol');

    let eventSource = null;
    
    // Variable to track the most recent agent response
    let lastAgentResponse = "Hello! I'm your agent assistant. How can I help you today?";
    
    // Array to store conversation history for follow-up questions
    // This will only include the user questions and final answers, not intermediate steps
    let conversationHistory = [
        // Initialize with the welcome message as the first assistant message
        {
            role: 'assistant',
            content: lastAgentResponse
        }
    ];

    function addMessage(content, type, isFinal = false) {
        const messageElement = document.createElement('div');
        // Use knowledge-base chat message structure
        messageElement.classList.add('message', type === 'user' ? 'user-message' : 'system-message');
        
        // Keep track of the last agent response
        if (type === 'agent') {
            lastAgentResponse = content;
            console.log("Updated lastAgentResponse:", lastAgentResponse);
        }
        
        // If this is a final answer or user message, store it in conversation history
        if (type === 'user' || isFinal) {
            if (type === 'user') {
                // Add to conversation history
                conversationHistory.push({
                    role: 'user',
                    content: content
                });
            } else if (isFinal && type === 'agent') {
                // Add to conversation history (only final answers from agent)
                conversationHistory.push({
                    role: 'assistant',
                    content: content
                });
                
                // Mark this as a final answer for visual distinction
                messageElement.classList.add('final-answer');
            }
            
            // For debugging
            console.log('Updated conversation history:', conversationHistory);
        }
        
        // For non-final agent messages, add a class to indicate they're intermediate steps
        if (type === 'agent' && !isFinal) {
            messageElement.classList.add('intermediate-step');
        }

        // Create avatar
        const avatar = document.createElement('div');
        avatar.classList.add('avatar', type === 'user' ? 'user-avatar' : 'system-avatar');
        avatar.innerHTML = type === 'user' ? '<i class="fas fa-user-circle"></i>' : '<i class="fas fa-robot"></i>';
        
        // Create content container
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content', 'glass');
        if (type === 'agent') {
            // Create a markdown content wrapper like knowledge base
            const markdownWrapper = document.createElement('div');
            markdownWrapper.classList.add('markdown-content');
            markdownWrapper.innerHTML = md.render(content);
            contentDiv.appendChild(markdownWrapper);
            
            // Highlight any code blocks after markdown rendering
            contentDiv.querySelectorAll('pre code').forEach((block) => {
                if (window.hljs) {
                    hljs.highlightElement(block);
                }
            });
        } else {
            contentDiv.textContent = content;
        }
        
        messageElement.appendChild(avatar);
        messageElement.appendChild(contentDiv);

        chatHistory.prepend(messageElement);  // Add new messages at top to match knowledgebase behavior
        // chatHistory.scrollTop = chatHistory.scrollHeight; // Remove bottom scroll for top insertion
    }

    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') {
            try {
                unsafe = JSON.stringify(unsafe, null, 2); // Pretty print JSON if object/array
            } catch (e) {
                unsafe = String(unsafe);
            }
        }
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
     }

    function showProgress(message) {
        agentProgress.style.display = 'block';
        progressStatus.textContent = message || 'Processing...';
        // Ensure server/team/workflow selects stay enabled even when showing progress
        if (serverSelect) serverSelect.disabled = false;
        if (teamSelect) teamSelect.disabled = false;
        if (workflowSelect) workflowSelect.disabled = false;
    }

    function hideProgress() {
        agentProgress.style.display = 'none';
        progressStatus.textContent = '';
        // Ensure server/team/workflow selects stay enabled when hiding progress
        if (serverSelect) serverSelect.disabled = false;
        if (teamSelect) teamSelect.disabled = false;
        if (workflowSelect) workflowSelect.disabled = false;
    }

    // Load available MCP servers
    function loadAvailableServers() {
        if (!serverSelect) return;
        
        fetch('/api/agent/servers')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.servers && data.servers.length > 0) {
                    // Clear existing options (except the first one)
                    while (serverSelect.options.length > 1) {
                        serverSelect.remove(1);
                    }
                    
                    // Add server options
                    data.servers.forEach(server => {
                        const option = document.createElement('option');
                        option.value = server.id;
                        option.textContent = server.name;
                        if (server.description) {
                            option.title = server.description;
                        }
                        serverSelect.appendChild(option);
                    });
                    
                    // Enable the select element
                    serverSelect.disabled = false;
                } else {
                    // If no servers available, disable the select element
                    serverSelect.disabled = true;
                }
            })
            .catch(error => {
                console.error('Error loading MCP servers:', error);
                if (serverSelect) serverSelect.disabled = true;
            });
    }

    // Load AutoGen teams/workflows
    function loadTeams() {
        if (!teamSelect) return;
        
        fetch('/api/agent/teams')
            .then(r=>r.json())
            .then(d=>{
                // reset, keep first None option
                while (teamSelect.options.length > 1) teamSelect.remove(1);
                (d.teams||[]).forEach(t=>{
                    const opt = document.createElement('option');
                    opt.value = t.id; opt.textContent = t.name; teamSelect.appendChild(opt);
                })
            }).catch(()=>{});
    }
    
    function loadWorkflows() {
        if (!workflowSelect) return;
        
        fetch('/api/agent/workflows')
            .then(r=>r.json())
            .then(d=>{
                while (workflowSelect.options.length > 1) workflowSelect.remove(1);
                (d.workflows||[]).forEach(w=>{
                    const opt = document.createElement('option');
                    opt.value = w.id; opt.textContent = w.name; workflowSelect.appendChild(opt);
                })
            }).catch(()=>{});
    }

    // Handle mode selection change
    function handleModeChange() {
        const mode = modeSelect.value;
        
        if (mode === 'mcp') {
            // Show MCP options, hide AutoGen options
            if (mcpServerCol) mcpServerCol.style.display = 'block';
            if (autogenTeamCol) autogenTeamCol.style.display = 'none';
            if (autogenWorkflowCol) autogenWorkflowCol.style.display = 'none';
            loadAvailableServers();
        } else {
            // Show AutoGen options, hide MCP options
            if (autogenTeamCol) autogenTeamCol.style.display = 'block';
            if (autogenWorkflowCol) autogenWorkflowCol.style.display = 'block';
            if (mcpServerCol) mcpServerCol.style.display = 'none';
            loadTeams();
            loadWorkflows();
        }
    }

    // Initialize mode selection
    if (modeSelect) {
        modeSelect.addEventListener('change', handleModeChange);
        handleModeChange(); // Initialize based on default value
    }

    function sendMessage() {
        const query = chatInput.value.trim();
        if (!query) return;

        addMessage(query, 'user');
        chatInput.value = '';
        sendButton.disabled = true;
        chatInput.disabled = true;
        showProgress('Sending query to agent...');
        
        // Clone the conversationHistory for this request to include context
        // Exclude the current query which was just added to the history
        const previousHistory = conversationHistory.slice(0, -1);
        
        // Check if we have the last agent response as the most recent assistant message
        // If not, add it to ensure continuity in the conversation
        const lastAssistantMsg = previousHistory.filter(msg => msg.role === 'assistant').pop();
        if (!lastAssistantMsg || lastAssistantMsg.content !== lastAgentResponse) {
            console.log("Adding missing last agent response to history:", lastAgentResponse);
            // Add the last agent response to the conversation history
            previousHistory.push({
                role: 'assistant',
                content: lastAgentResponse
            });
        }

        // Determine endpoint and payload based on mode
        const mode = modeSelect ? modeSelect.value : 'autogen';
        let endpoint, payload;
        
        if (mode === 'mcp') {
            // Use legacy MCP server endpoint
            endpoint = '/api/agent/chat';
            const serverId = serverSelect ? serverSelect.value : '';
            payload = {
                query: query,
                server_id: serverId || undefined,
                conversation_history: previousHistory
            };
        } else {
            // Use AutoGen endpoint
            const useAutogen = (teamSelect && teamSelect.value) || (workflowSelect && workflowSelect.value);
            if (!useAutogen) {
                hideProgress();
                sendButton.disabled = false;
                chatInput.disabled = false;
                addMessage('Select a Team or Workflow before sending.', 'agent');
                return;
            }
            
            endpoint = '/api/agent/autogen/chat';
            payload = {
                query,
                team_id: teamSelect && teamSelect.value ? parseInt(teamSelect.value, 10) : undefined,
                workflow_id: workflowSelect && workflowSelect.value ? parseInt(workflowSelect.value, 10) : undefined,
                conversation_history: previousHistory
            };
        }

        // Send POST to endpoint and stream updates
        fetch(endpoint, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(async response => {
            if (!response.ok) throw new Error(`Server responded ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            // Read streaming chunks
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let parts = buffer.split('\n\n');
                buffer = parts.pop();
                for (const part of parts) {
                    if (part.startsWith('data:')) {
                        const jsonStr = part.replace(/^data:\s*/, '');
                        try {
                            const update = JSON.parse(jsonStr);
                            handleUpdate(update);
                        } catch (e) {
                            console.error('Failed to parse update', e, jsonStr);
                        }
                    }
                }
            }
        })
        .catch(error => {
            console.error('Streaming fetch error:', error);
            addMessage(`Error: ${error.message}`, 'agent');
        })
        .finally(() => {
            hideProgress();
            sendButton.disabled = false;
            chatInput.disabled = false;
        });
    }

    function handleUpdate(update) {
        switch (update.type) {
            case 'status':
                showProgress(update.message);
                break;
            case 'llm_response':
                hideProgress();
                // Check if this is the final response from the LLM (marked by the backend)
                // If is_final flag exists and is true, or if we can identify this is likely a final answer
                const content = update.content ? update.content.toLowerCase() : '';
                const isLikelyFinalAnswer = 
                    content.startsWith("final answer:") || 
                    content.includes("in conclusion") ||
                    content.startsWith("to summarize") ||
                    content.includes("here's the answer") ||
                    content.includes("the answer is") ||
                    // Add more patterns that indicate a final answer
                    content.includes("to answer your question") ||
                    content.includes("the result shows");
                    
                if (update.is_final === true || isLikelyFinalAnswer) {
                    console.log("Adding FINAL answer to history:", update.content);
                    addMessage(update.content, 'agent', true); // true marks this as a final answer
                } else {
                    console.log("Adding intermediate response:", update.content);
                    addMessage(update.content, 'agent', false); // intermediate response
                }
                break;
            case 'tool_call':
                hideProgress();
                // Tool calls are always intermediate steps
                addMessage(`Calling ${update.tool_name} with args ${JSON.stringify(update.arguments)}`, 'agent', false);
                break;
            case 'tool_confirmation_request':
                hideProgress();
                // Prompt user for confirmation (for MCP mode)
                if (window.showConfirmationDialog) {
                    window.showConfirmationDialog(update.tool_name, update.arguments)
                        .then(decision => {
                            // Send decision to server
                            fetch('/api/agent/tool-confirmation', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ call_id: update.call_id, confirmed: decision })
                            });
                            // Optionally notify user
                            addMessage(`User ${decision ? 'confirmed' : 'cancelled'} execution of ${update.tool_name}`, 'agent', false);
                        });
                }
                break;
            case 'confirm_request':
                hideProgress();
                // Prompt user for confirmation (for AutoGen mode)
                if (window.showConfirmationDialog) {
                    window.showConfirmationDialog(update.tool_name, update.arguments)
                        .then(decision => {
                            // Send decision to server
                            fetch('/agent/confirm_tool', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ call_id: update.call_id, confirm: decision })
                            });
                            // Optionally notify user
                            addMessage(`User ${decision ? 'confirmed' : 'cancelled'} execution of ${update.tool_name}`, 'agent', false);
                        });
                }
                break;
            case 'tool_result':
                hideProgress();
                // Tool results are intermediate steps
                addMessage(update.result || update.content, 'agent', false);
                break;
            case 'done':
                hideProgress();
                // The done message might be a final summary
                if (update.final_answer) {
                    console.log("Adding final answer from 'done' event:", update.final_answer);
                    addMessage(update.final_answer, 'agent', true); // This is the final answer to store
                } else {
                    // Check if we need to ensure the last message is marked as final
                    // This is a fallback in case no message was explicitly marked as final
                    const hasNoFinalAnswer = !conversationHistory.some(
                        msg => msg.role === 'assistant' && 
                        conversationHistory.indexOf(msg) > conversationHistory.findIndex(
                            m => m.role === 'user' && m.content === query
                        )
                    );
                    
                    if (hasNoFinalAnswer && lastAgentResponse) {
                        console.log("No final answer detected, marking last response as final:", lastAgentResponse);
                        // Add the last agent response to history
                        conversationHistory.push({
                            role: 'assistant',
                            content: lastAgentResponse
                        });
                        console.log("Updated conversation history with last response:", conversationHistory);
                    }
                }
                break;
            case 'error':
                hideProgress();
                // Errors are considered final answers in a conversation
                addMessage(update.message, 'agent', true);
                break;
            default:
                console.warn('Unknown update type:', update.type);
        }
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (event) => {
        // Send on Enter, allow Shift+Enter for newline
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Prevent default newline behavior
            sendMessage();
        }
    });
    
    // Add event delegation for expanding/collapsing intermediate steps
    chatHistory.addEventListener('click', (event) => {
        // Check if the click is on the "Show more" overlay of an intermediate step
        const intermediateStep = event.target.closest('.intermediate-step');
        if (intermediateStep) {
            intermediateStep.classList.toggle('expanded');
        }
    });
});
