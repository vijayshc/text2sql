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

    let eventSource = null;

    function addMessage(content, type) {
        const messageElement = document.createElement('div');
        // Use knowledge-base chat message structure
        messageElement.classList.add('message', type === 'user' ? 'user-message' : 'agent-message');

        // Create avatar
        const avatar = document.createElement('div');
        avatar.classList.add('avatar', type === 'user' ? 'user-avatar' : 'system-avatar');
        avatar.innerHTML = type === 'user' ? '<i class="fas fa-user-circle"></i>' : '<i class="fas fa-robot"></i>';
        // Create content container
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content', 'glass');
        if (type === 'agent') {
            contentDiv.innerHTML = md.render(content);
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
    }

    function hideProgress() {
        agentProgress.style.display = 'none';
        progressStatus.textContent = '';
    }

    function sendMessage() {
        const query = chatInput.value.trim();
        if (!query) return;

        addMessage(query, 'user');
        chatInput.value = '';
        sendButton.disabled = true;
        chatInput.disabled = true;
        showProgress('Sending query to agent...');

        // Send POST to agent/chat and stream updates
        fetch('/agent/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
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
                addMessage(update.content, 'agent');
                break;
            case 'tool_call':
                hideProgress();
                addMessage(`Calling ${update.tool_name} with args ${JSON.stringify(update.arguments)}`, 'agent');
                break;
            case 'tool_result':
                hideProgress();
                addMessage(update.result, 'agent');
                break;
            case 'done':
                hideProgress();
                addMessage('Agent finished processing.', 'agent');
                break;
            case 'error':
                hideProgress();
                addMessage(update.message, 'agent');
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
});
