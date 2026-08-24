document.addEventListener('DOMContentLoaded', () => {
    let conversationId = 'conv_' + Math.random().toString(36).substring(2, 9);
    let activeCustomerId = 'C-100';

    const customerMetadata = {
        'C-100': { name: 'Ananya Sharma', city: 'Mumbai', orders: 'TR-4521 (In Transit), TR-4522 (Delivered)' },
        'C-101': { name: 'Rajesh Kumar', city: 'Delhi', orders: 'TR-4523 (Jewellery / Delivered)' },
        'C-102': { name: 'Priya Patel', city: 'Bengaluru', orders: 'TR-4524 (Footwear / Delivered)' },
        'C-103': { name: 'Vikram Malhotra', city: 'Jaipur', orders: 'TR-4525 (Delayed), TR-4526 (Lost in Transit)' },
        'C-104': { name: 'Sneha Reddy', city: 'Hyderabad', orders: 'TR-4527 (Final Sale Dress), TR-4528 (Cancelled)' }
    };

    const messagesContainer = document.getElementById('messagesContainer');
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const typingIndicator = document.getElementById('typingIndicator');
    const customerSelect = document.getElementById('customerSelect');
    const customerDetails = document.getElementById('customerDetails');
    const resetBtn = document.getElementById('resetBtn');
    const toggleInspectorBtn = document.getElementById('toggleInspectorBtn');
    const closeInspectorBtn = document.getElementById('closeInspectorBtn');
    const inspectorDrawer = document.getElementById('inspectorDrawer');
    const toolCallsList = document.getElementById('toolCallsList');
    const toolCountBadge = document.getElementById('toolCountBadge');

    function updateCustomerCard() {
        const meta = customerMetadata[activeCustomerId];
        if (meta) {
            customerDetails.innerHTML = `
                <div><strong>Name:</strong> <span>${meta.name}</span></div>
                <div><strong>City:</strong> <span>${meta.city}</span></div>
                <div style="margin-top: 4px;"><strong>Orders:</strong> <span style="font-size:11px;">${meta.orders}</span></div>
            `;
        }
    }
    updateCustomerCard();

    customerSelect.addEventListener('change', (e) => {
        activeCustomerId = e.target.value;
        updateCustomerCard();
    });

    // Toggle Inspector Drawer
    toggleInspectorBtn.addEventListener('click', () => {
        inspectorDrawer.classList.toggle('open');
    });
    closeInspectorBtn.addEventListener('click', () => {
        inspectorDrawer.classList.remove('open');
    });

    // Reset Conversation
    resetBtn.addEventListener('click', async () => {
        if (confirm('Reset the current conversation?')) {
            try {
                await fetch(`/api/chat/${conversationId}`, { method: 'DELETE' });
            } catch (e) {
                console.error(e);
            }
            conversationId = 'conv_' + Math.random().toString(36).substring(2, 9);
            messagesContainer.innerHTML = `
                <div class="message assistant-message">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <div class="message-sender">TrendlyBot</div>
                        <div class="message-bubble">
                            <p>Hello! Welcome to <strong>Trendly Support</strong>. 👋</p>
                            <p>I'm here to help you track your shipments, process returns and size exchanges, and answer any questions regarding our shipping and refund policies.</p>
                            <p>How may I assist you today?</p>
                        </div>
                    </div>
                </div>
            `;
            toolCallsList.innerHTML = '<div class="empty-state">No tool calls executed yet in this turn.</div>';
            toolCountBadge.textContent = '0';
        }
    });

    // Quick prompt buttons
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const msg = btn.getAttribute('data-msg');
            userInput.value = msg;
            sendMessage(msg);
        });
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (text) {
            sendMessage(text);
        }
    });

    async function sendMessage(text) {
        userInput.value = '';
        appendMessage('user', text);

        typingIndicator.classList.remove('hidden');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    message: text,
                    customer_id: activeCustomerId
                })
            });

            const data = await res.json();
            typingIndicator.classList.add('hidden');

            if (res.ok) {
                appendMessage('assistant', data.message, data.tool_calls);
                updateInspector(data.tool_calls);
            } else {
                appendMessage('assistant', `⚠️ Error: ${data.detail || 'Failed to process message'}`);
            }
        } catch (err) {
            typingIndicator.classList.add('hidden');
            appendMessage('assistant', `⚠️ Network error: ${err.message}`);
        }
    }

    function appendMessage(role, content, toolCalls) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}-message`;

        const avatar = role === 'user' ? '👤' : '🤖';
        const senderName = role === 'user' ? 'You' : 'TrendlyBot';

        // Format Markdown basic tags (bold, lists, code)
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        let toolTagsHtml = '';
        if (toolCalls && toolCalls.length > 0) {
            toolTagsHtml = `<div style="margin-top: 8px;">` +
                toolCalls.map(tc => `<span class="tool-tag">⚡ ${tc.tool_name}</span> `).join('') +
                `</div>`;
        }

        msgDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-sender">${senderName}</div>
                <div class="message-bubble">
                    <p>${formatted}</p>
                    ${toolTagsHtml}
                </div>
            </div>
        `;

        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function updateInspector(toolCalls) {
        if (!toolCalls || toolCalls.length === 0) {
            toolCountBadge.textContent = '0';
            toolCallsList.innerHTML = '<div class="empty-state">No tool calls executed in the last turn.</div>';
            return;
        }

        toolCountBadge.textContent = toolCalls.length;
        toolCallsList.innerHTML = toolCalls.map(tc => `
            <div class="tool-card">
                <div class="tool-card-header">
                    <span class="tool-card-title">${tc.tool_name}()</span>
                    <span class="tool-card-status ${tc.success ? 'status-success' : 'status-fail'}">
                        ${tc.success ? 'SUCCESS' : 'FAILED'}
                    </span>
                </div>
                <div style="font-size: 11px; margin-bottom: 4px; color: var(--text-secondary);">Arguments:</div>
                <pre class="tool-json">${JSON.stringify(tc.arguments, null, 2)}</pre>
                <div style="font-size: 11px; margin: 6px 0 4px; color: var(--text-secondary);">Result Summary:</div>
                <div style="font-size: 11px; color: #8b949e; line-height: 1.4;">${tc.result_summary}</div>
            </div>
        `).join('');
    }
});
