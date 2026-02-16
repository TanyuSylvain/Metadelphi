/**
 * Message Component
 * Handles rendering and managing chat messages
 */

import { MarkdownRenderer } from '../utils/markdown.js';
import { getStorage, setStorage, purifyContent, copyToClipboard } from '../utils/helpers.js';
import { ThinkParser } from '../utils/thinkParser.js';

export class MessageComponent {
    constructor(messagesContainer) {
        this.container = messagesContainer;
        this.renderer = new MarkdownRenderer();
        // Store raw content for assistant messages to support re-rendering
        this.messageContents = new Map();
        // Store response-only content (without thinking) for copy button
        this.messageResponseContents = new Map();
        // Current conversation ID for debate message persistence
        this.conversationId = null;
    }

    /**
     * Set the current conversation ID for debate message persistence
     * @param {string} conversationId - The conversation ID
     */
    setConversationId(conversationId) {
        this.conversationId = conversationId;
    }

    /**
     * Get storage key for debate messages
     * @returns {string} Storage key
     */
    getDebateStorageKey() {
        return `debateMessages_${this.conversationId}`;
    }

    /**
     * Store debate message metadata for persistence
     * @param {string} content - Message content
     * @param {string} debateId - Debate ID
     * @param {number} iteration - Iteration number
     */
    storeDebateMetadata(content, debateId, iteration) {
        if (!this.conversationId) return;

        const key = this.getDebateStorageKey();
        const stored = getStorage(key, []);

        // Use content hash for matching (first 100 chars + length)
        const contentKey = content.substring(0, 100) + '_' + content.length;

        // Check if already stored
        const existing = stored.find(m => m.contentKey === contentKey);
        if (!existing) {
            stored.push({ contentKey, debateId, iteration });
            setStorage(key, stored);
        }
    }

    /**
     * Get debate metadata for a message content
     * @param {string} content - Message content
     * @returns {Object|null} Debate metadata or null
     */
    getDebateMetadata(content) {
        if (!this.conversationId) return null;

        const key = this.getDebateStorageKey();
        const stored = getStorage(key, []);

        const contentKey = content.substring(0, 100) + '_' + content.length;
        return stored.find(m => m.contentKey === contentKey) || null;
    }

    /**
     * Clear debate metadata for current conversation
     */
    clearDebateMetadata() {
        if (!this.conversationId) return;
        const key = this.getDebateStorageKey();
        localStorage.removeItem(key);
    }

    /**
     * Create a copy button for assistant messages
     * @param {string} msgId - Message ID to retrieve raw content
     * @returns {HTMLButtonElement} Copy button element
     */
    createCopyButton(msgId) {
        const btn = document.createElement('button');
        btn.className = 'message-copy-btn';
        btn.innerHTML = '&#128203; Copy';  // Clipboard icon + text
        btn.setAttribute('data-tooltip', 'Clean Copy');

        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            // Prefer response-only content (without thinking), fall back to full content
            let raw = this.messageResponseContents.get(msgId) || this.messageContents.get(msgId);
            if (!raw) return;

            // Safety net: strip any remaining thinking tags
            raw = ThinkParser.stripThinking(raw);

            const success = await copyToClipboard(purifyContent(raw));
            if (success) {
                btn.classList.add('copied');
                btn.innerHTML = '&#10003; Copied';
                btn.setAttribute('data-tooltip', 'Copied!');
                setTimeout(() => {
                    btn.classList.remove('copied');
                    btn.innerHTML = '&#128203; Copy';
                    btn.setAttribute('data-tooltip', 'Clean Copy');
                }, 2000);
            }
        });
        return btn;
    }

    /**
     * Add a user message
     * @param {string} content - Message content
     * @returns {HTMLElement} Message element
     */
    addUserMessage(content) {
        return this.addMessage(content, 'user');
    }

    /**
     * Add an assistant message
     * @param {string} content - Message content (markdown)
     * @returns {HTMLElement} Message element
     */
    addAssistantMessage(content = '') {
        const messageEl = this.addMessage(content, 'assistant');
        // Store raw content for re-rendering
        if (messageEl) {
            const msgId = messageEl.dataset.messageId || Date.now().toString() + Math.random().toString();
            messageEl.dataset.messageId = msgId;
            this.messageContents.set(msgId, content);
            // Add copy button for non-empty content
            if (content) {
                messageEl.appendChild(this.createCopyButton(msgId));
            }
        }
        return messageEl;
    }

    /**
     * Add an error message
     * @param {string} content - Error message
     * @returns {HTMLElement} Message element
     */
    addErrorMessage(content) {
        return this.addMessage(content, 'error');
    }

    /**
     * Add a system message (info/status messages)
     * @param {string} content - System message
     * @returns {HTMLElement} Message element
     */
    addSystemMessage(content) {
        return this.addMessage(content, 'system');
    }

    /**
     * Add a debate-generated answer message with source badge
     * @param {string} content - Answer content (markdown)
     * @param {string} debateId - Unique ID for this debate session
     * @param {number} iteration - The final iteration number
     * @param {boolean} isMarkdown - Whether to render as markdown
     * @returns {HTMLElement} Message element
     */
    addDebateMessage(content, debateId, iteration, isMarkdown = true) {
        const messageEl = document.createElement('div');
        const msgId = `debate-${debateId}-${Date.now()}`;

        messageEl.className = 'message assistant debate-answer';
        messageEl.dataset.messageId = msgId;
        messageEl.dataset.debateId = debateId;
        messageEl.dataset.iteration = iteration;

        // Add source badge
        const badge = document.createElement('div');
        badge.className = 'message-source-badge';
        badge.textContent = `Debate Answer (${iteration > 0 ? 'Round ' + iteration : 'Direct'})`;
        messageEl.appendChild(badge);

        // Add content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (isMarkdown) {
            contentDiv.innerHTML = this.renderer.render(content);
        } else {
            contentDiv.style.whiteSpace = 'pre-wrap';
            contentDiv.textContent = content;
        }
        messageEl.appendChild(contentDiv);

        // Store raw content for re-rendering
        this.messageContents.set(msgId, content);

        // Add copy button
        messageEl.appendChild(this.createCopyButton(msgId));

        // Persist debate metadata for reload
        this.storeDebateMetadata(content, debateId, iteration);

        this.container.appendChild(messageEl);
        this.scrollToBottom();

        return messageEl;
    }

    /**
     * Add a message to the chat
     * @param {string} content - Message content
     * @param {string} type - Message type (user, assistant, error)
     * @returns {HTMLElement} Message element
     */
    addMessage(content, type) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;

        if (type === 'assistant' && content) {
            messageEl.innerHTML = this.renderer.render(content);
        } else {
            messageEl.textContent = content;
        }

        this.container.appendChild(messageEl);
        this.scrollToBottom();

        return messageEl;
    }

    /**
     * Update message content
     * @param {HTMLElement} messageEl - Message element
     * @param {string} content - New content
     * @param {boolean} isMarkdown - Whether to render as markdown
     */
    updateMessage(messageEl, content, isMarkdown = false) {
        // Store raw content for this message
        const msgId = messageEl.dataset.messageId;
        if (msgId) {
            this.messageContents.set(msgId, content);
        }

        if (isMarkdown) {
            messageEl.innerHTML = this.renderer.render(content);
        } else {
            // Preserve line breaks in raw mode
            messageEl.style.whiteSpace = 'pre-wrap';
            messageEl.textContent = content;
        }

        // Add copy button if content exists and button doesn't
        if (content && msgId && !messageEl.querySelector('.message-copy-btn')) {
            messageEl.appendChild(this.createCopyButton(msgId));
        }

        this.scrollToBottom();
    }

    /**
     * Update message with thinking block support
     * Parses <think>...</think> blocks and renders them in collapsible sections
     * @param {HTMLElement} messageEl - Message element
     * @param {string} fullText - Full accumulated text including think tags
     * @param {boolean} isMarkdown - Whether to render response as markdown
     */
    updateMessageWithThinking(messageEl, fullText, isMarkdown = false) {
        const msgId = messageEl.dataset.messageId;
        if (msgId) {
            this.messageContents.set(msgId, fullText);
        }

        const { segments, responseOnly } = ThinkParser.parse(fullText);

        if (msgId) {
            this.messageResponseContents.set(msgId, responseOnly);
        }

        // Preserve user's open/closed state for existing thinking blocks before rebuilding
        const existingBlocks = messageEl.querySelectorAll('.thinking-block');
        const openStates = [];
        existingBlocks.forEach((block, index) => {
            openStates[index] = block.hasAttribute('open');
        });

        // Build HTML from segments
        let html = '';
        let thinkingBlockIndex = 0;
        for (const segment of segments) {
            if (segment.type === 'thinking') {
                // Use preserved state if available, otherwise default to open for new blocks during streaming
                const shouldBeOpen = openStates[thinkingBlockIndex] !== undefined
                    ? openStates[thinkingBlockIndex]
                    : true; // New blocks default to open
                const openAttr = shouldBeOpen ? ' open' : '';
                const streamingClass = segment.complete ? '' : ' streaming';
                const label = segment.complete ? 'Thinking (complete)' : 'Thinking...';
                html += `<details class="thinking-block"${openAttr}>`;
                html += `<summary class="thinking-summary">`;
                html += `<span class="thinking-arrow">&#9654;</span>`;
                html += `<span class="thinking-label${streamingClass}">${label}</span>`;
                html += `</summary>`;
                html += `<div class="thinking-content">${this._escapeHtml(segment.content)}</div>`;
                html += `</details>`;
                thinkingBlockIndex++;
            } else if (segment.type === 'response') {
                if (isMarkdown) {
                    html += `<div class="response-content">${this.renderer.render(segment.content)}</div>`;
                } else {
                    html += `<div class="response-content" style="white-space: pre-wrap;">${this._escapeHtml(segment.content)}</div>`;
                }
            }
        }

        messageEl.innerHTML = html;

        // Re-add copy button
        if (fullText && msgId) {
            messageEl.appendChild(this.createCopyButton(msgId));
        }

        this.scrollToBottom();
    }

    /**
     * Collapse all thinking blocks in a message (close all <details> elements)
     * @param {HTMLElement} messageEl - Message element
     */
    collapseThinkingBlocks(messageEl) {
        const thinkingBlocks = messageEl.querySelectorAll('.thinking-block[open]');
        thinkingBlocks.forEach(block => {
            block.removeAttribute('open');
        });
    }

    /**
     * Check if content contains thinking tags
     * @param {string} content - Message content
     * @returns {boolean}
     */
    hasThinkingContent(content) {
        return content && content.includes('<think>');
    }

    /**
     * Escape HTML entities for safe insertion
     * @param {string} text - Raw text
     * @returns {string} Escaped HTML
     */
    _escapeHtml(text) {
        const el = document.createElement('div');
        el.textContent = text;
        return el.innerHTML;
    }

    /**
     * Show typing indicator
     * @returns {HTMLElement} Typing indicator element
     */
    showTypingIndicator() {
        const messageEl = this.addAssistantMessage('');
        messageEl.innerHTML = '<span class="typing">Thinking</span>';
        return messageEl;
    }

    /**
     * Remove typing indicator
     * @param {HTMLElement} typingEl - Typing indicator element
     */
    removeTypingIndicator(typingEl) {
        if (typingEl && typingEl.parentNode) {
            typingEl.parentNode.removeChild(typingEl);
        }
    }

    /**
     * Clear all messages
     */
    clearMessages() {
        this.container.innerHTML = '';
        this.messageContents.clear();
        this.messageResponseContents.clear();
    }

    /**
     * Re-render all assistant messages with new markdown setting
     * @param {boolean} isMarkdown - Whether to render as markdown
     */
    reRenderAssistantMessages(isMarkdown) {
        const assistantMessages = this.container.querySelectorAll('.message.assistant');
        assistantMessages.forEach(messageEl => {
            const msgId = messageEl.dataset.messageId;
            if (msgId && this.messageContents.has(msgId)) {
                const content = this.messageContents.get(msgId);

                // Handle debate-answer messages differently (preserve badge and copy button)
                if (messageEl.classList.contains('debate-answer')) {
                    const contentDiv = messageEl.querySelector('.message-content');
                    if (contentDiv) {
                        if (isMarkdown) {
                            contentDiv.style.whiteSpace = '';
                            contentDiv.innerHTML = this.renderer.render(content);
                        } else {
                            contentDiv.style.whiteSpace = 'pre-wrap';
                            contentDiv.textContent = content;
                        }
                    }
                } else {
                    // Regular assistant message - innerHTML wipes copy button, so re-add it
                    if (this.hasThinkingContent(content)) {
                        // Re-render with thinking block support (adds its own copy button)
                        this.updateMessageWithThinking(messageEl, content, isMarkdown);
                    } else {
                        if (isMarkdown) {
                            messageEl.style.whiteSpace = '';
                            messageEl.innerHTML = this.renderer.render(content);
                        } else {
                            messageEl.style.whiteSpace = 'pre-wrap';
                            messageEl.textContent = content;
                        }
                        // Re-add copy button after innerHTML replacement
                        if (content) {
                            messageEl.appendChild(this.createCopyButton(msgId));
                        }
                    }
                }
            }
        });
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }

    /**
     * Get all messages
     * @returns {Array} Array of message objects
     */
    getMessages() {
        const messages = [];
        const messageElements = this.container.querySelectorAll('.message');

        messageElements.forEach(el => {
            const type = el.classList.contains('user') ? 'user' :
                        el.classList.contains('assistant') ? 'assistant' : 'error';
            messages.push({
                type,
                content: el.textContent
            });
        });

        return messages;
    }

    /**
     * Load messages from history
     * @param {Array} messages - Array of message objects
     * @param {boolean} isMarkdown - Whether to render as markdown
     */
    loadMessages(messages, isMarkdown = true) {
        this.clearMessages();
        messages.forEach(msg => {
            if (msg.role === 'user') {
                this.addUserMessage(msg.content);
            } else if (msg.role === 'assistant') {
                // Check if this is a debate message
                const debateMetadata = this.getDebateMetadata(msg.content);
                if (debateMetadata) {
                    this.addDebateMessage(
                        msg.content,
                        debateMetadata.debateId,
                        debateMetadata.iteration,
                        isMarkdown
                    );
                } else if (this.hasThinkingContent(msg.content)) {
                    // Message contains <think> blocks - render with collapsible thinking
                    const messageEl = this.addMessage('', 'assistant');
                    const msgId = Date.now().toString() + Math.random().toString();
                    messageEl.dataset.messageId = msgId;
                    this.updateMessageWithThinking(messageEl, msg.content, isMarkdown);
                } else {
                    this.addAssistantMessage(msg.content);
                }
            }
        });
    }
}
