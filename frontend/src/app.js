/**
 * Main Application Module
 * Orchestrates all components and handles chat logic
 * Supports both simple (single-agent) and multi-agent debate modes
 */

import { APIClient } from './utils/api.js';
import { generateUUID, getStorage, setStorage } from './utils/helpers.js';
import { MessageComponent } from './components/MessageComponent.js';
import { ModelSelector } from './components/ModelSelector.js';
import { Sidebar } from './components/Sidebar.js';
import { ModeSelector } from './components/ModeSelector.js';
import { MultiAgentConfig } from './components/MultiAgentConfig.js';
import { ProgressIndicator } from './components/ProgressIndicator.js';
import { DebateViewer } from './components/DebateViewer.js';
import ModeratorStatusIndicator from './components/ModeratorStatusIndicator.js';
import { CoworkingConfig } from './components/CoworkingConfig.js';
import { ToolExecutionViewer } from './components/ToolExecutionViewer.js';

export class ChatApp {
    constructor() {
        // Initialize API client
        this.apiClient = new APIClient();

        // Get DOM elements
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.modelSelectElement = document.getElementById('modelSelect');
        this.thinkingToggle = document.getElementById('thinkingToggle');
        this.markdownToggle = document.getElementById('markdownToggle');
        this.sidebarElement = document.getElementById('sidebar');

        // Multi-agent elements
        this.modeSelectorElement = document.getElementById('modeSelector');
        this.multiAgentConfigElement = document.getElementById('multiAgentConfig');
        this.progressIndicatorElement = document.getElementById('progressIndicator');
        this.debateViewerElement = document.getElementById('debateViewer');

        // Verify all required elements exist
        if (!this.messagesContainer || !this.messageInput || !this.sendBtn ||
            !this.modelSelectElement || !this.thinkingToggle || !this.markdownToggle || !this.sidebarElement) {
            console.error('Missing required DOM elements:', {
                messages: !!this.messagesContainer,
                input: !!this.messageInput,
                sendBtn: !!this.sendBtn,
                modelSelect: !!this.modelSelectElement,
                thinkingToggle: !!this.thinkingToggle,
                sidebar: !!this.sidebarElement
            });
            throw new Error('Failed to find required DOM elements');
        }

        // Initialize components
        this.messageComponent = new MessageComponent(this.messagesContainer);
        this.modelSelector = new ModelSelector(this.modelSelectElement, this.apiClient);
        this.sidebar = new Sidebar(
            this.sidebarElement,
            this.apiClient,
            (conversationId) => this.selectConversation(conversationId),
            () => this.createNewConversation()
        );

        // Initialize multi-agent components (if elements exist)
        this.modeSelector = null;
        this.multiAgentConfig = null;
        this.progressIndicator = null;
        this.debateViewer = null;

        if (this.modeSelectorElement) {
            this.modeSelector = new ModeSelector(this.modeSelectorElement);
        }
        if (this.multiAgentConfigElement) {
            this.multiAgentConfig = new MultiAgentConfig(this.multiAgentConfigElement, this.apiClient);
        }

        // Progress indicator in the debate panel
        this.progressIndicatorElement = document.getElementById('progressIndicator');
        if (this.progressIndicatorElement) {
            this.progressIndicator = new ProgressIndicator(this.progressIndicatorElement);
        }

        // Initialize moderator components
        const moderatorStatusElement = document.getElementById('moderatorStatus');
        const moderatorInitElement = document.getElementById('moderatorInit');
        this.moderatorStatusIndicator = moderatorStatusElement ?
            new ModeratorStatusIndicator(moderatorStatusElement) : null;

        // Initialize debate viewer with moderator init container
        if (this.debateViewerElement) {
            this.debateViewer = new DebateViewer(this.debateViewerElement, moderatorInitElement);
        }

        // Initialize coworking components
        this.coworkingConfigElement = document.getElementById('coworkingConfig');
        this.coworkingConfig = null;
        if (this.coworkingConfigElement) {
            this.coworkingConfig = new CoworkingConfig(this.coworkingConfigElement);
        }

        this.toolExecutionViewerElement = document.getElementById('toolExecutionViewer');
        this.toolExecutionViewer = null;
        if (this.toolExecutionViewerElement) {
            this.toolExecutionViewer = new ToolExecutionViewer(this.toolExecutionViewerElement);
        }

        // Conversation state
        this.conversationId = this.loadOrCreateConversationId();
        this.messageComponent.setConversationId(this.conversationId);
        if (this.debateViewer) {
            this.debateViewer.setConversationId(this.conversationId);
        }
        this.isProcessing = false;
        this.isThinkingEnabled = false;
        this.isMarkdownEnabled = true;
        this.isMultiAgentMode = false;
        this.isCoworkingMode = false;

        // Debate panel visibility state
        this.debatePanelVisible = false;
        this.debatePanelToggleOn = true; // Toggle button state (on = will show panel when debate starts)
        this.currentDebateId = null;
        this.currentDebateIteration = 0;

        // Initialize the app
        this.initialize();
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            // Initialize model selector (fetches models from API)
            await this.modelSelector.initialize();

            // Initialize multi-agent components
            if (this.modeSelector) {
                this.modeSelector.initialize();
                this.isMultiAgentMode = this.modeSelector.isMultiAgentMode();
                this.isCoworkingMode = this.modeSelector.isCoworkingMode();
            }

            // Initialize coworking components
            if (this.coworkingConfig) {
                this.coworkingConfig.initialize();
            }
            if (this.toolExecutionViewer) {
                this.toolExecutionViewer.initialize();
            }
            if (this.multiAgentConfig) {
                await this.multiAgentConfig.initialize();
                this.updateMultiAgentUIVisibility();
            }
            if (this.progressIndicator) {
                this.progressIndicator.initialize();
            }
            if (this.debateViewer) {
                this.debateViewer.initialize();
            }

            // Load conversations list
            await this.sidebar.loadConversations();

            // Set current conversation in sidebar
            this.sidebar.setCurrentConversation(this.conversationId);

            // Set up event listeners
            this.setupEventListeners();

            // Load conversation history if exists
            await this.loadConversationHistory();

            // Set initial chat container width based on mode and panel state
            if (!this.isMultiAgentMode || !this.debatePanelToggleOn) {
                this.hideDebatePanel();
            }
            if (!this.isCoworkingMode) {
                this.hideCoworkingPanel();
            }

            // Focus input
            this.messageInput.focus();
        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.messageComponent.addErrorMessage(
                'Failed to initialize chat. Please refresh the page.'
            );
        }
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Send button click
        this.sendBtn.addEventListener('click', () => this.sendMessage());

        // Enter key in input (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea as user types
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 150) + 'px';
        });

        // Model change - update thinking toggle state
        this.modelSelector.onChange((modelId) => {
            setStorage('selectedModel', modelId);
            this.updateThinkingToggleState(modelId);
        });

        // Mode selector change
        if (this.modeSelector) {
            this.modeSelector.onChange(async (mode) => {
                await this.handleModeChange(mode);
            });
        }

        // Thinking toggle change
        this.thinkingToggle.addEventListener('change', (e) => {
            this.isThinkingEnabled = e.target.checked;
            // Save preference per model
            const modelId = this.modelSelector.getSelectedModel();
            if (modelId) {
                setStorage(`thinkingEnabled_${modelId}`, this.isThinkingEnabled);
            }
        });

        // Markdown toggle change
        this.markdownToggle.addEventListener('change', (e) => {
            this.isMarkdownEnabled = e.target.checked;
            setStorage('markdownEnabled', this.isMarkdownEnabled);
            // Re-render all assistant messages with new markdown setting
            this.messageComponent.reRenderAssistantMessages(this.isMarkdownEnabled);
        });

        // Load saved sidebar state
        const sidebarCollapsed = getStorage('sidebarCollapsed') === 'true';
        if (sidebarCollapsed) {
            this.collapseSidebar();
        }

        // Header sidebar toggle button
        const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
        if (sidebarToggleBtn) {
            sidebarToggleBtn.addEventListener('click', () => this.toggleSidebar());
        }

        // Load saved model selection
        const savedModel = getStorage('selectedModel');
        if (savedModel) {
            this.modelSelector.setSelectedModel(savedModel);
        }

        // Load saved markdown preference
        const savedMarkdown = getStorage('markdownEnabled');
        if (savedMarkdown !== null) {
            this.isMarkdownEnabled = savedMarkdown === 'true' || savedMarkdown === true;
            this.markdownToggle.checked = this.isMarkdownEnabled;
        }

        // Initial update of thinking toggle state (will load per-model preference)
        const currentModel = this.modelSelector.getSelectedModel();
        this.updateThinkingToggleState(currentModel);

        // Initialize agent status
        this.agentStatusElement = document.getElementById('agentStatus');

        // Setup resize handles
        try {
            this.setupResizeHandles();
        } catch (error) {
            console.error('Error setting up resize handles:', error);
        }

        // Setup debate panel toggle
        try {
            this.setupDebatePanelToggle();
        } catch (error) {
            console.error('Error setting up debate panel toggle:', error);
        }

        // Setup click-to-expand for debate messages
        try {
            this.setupDebateMessageClickHandler();
        } catch (error) {
            console.error('Error setting up debate message click handler:', error);
        }
    }

    /**
     * Update agent status display
     */
    updateAgentStatus(activeAgent, iteration, phase) {
        if (!this.agentStatusElement) return;

        const agents = [
            { id: 'moderator', label: 'Moderator' },
            { id: 'expert', label: 'Expert' },
            { id: 'critic', label: 'Critic' }
        ];

        let html = '';
        agents.forEach(agent => {
            const isActive = agent.id === activeAgent;
            html += `
                <div class="agent-status-item ${isActive ? 'active' : ''}">
                    <span class="agent-status-dot"></span>
                    <span>${agent.label}</span>
                </div>
            `;
        });

        if (iteration > 0 && phase) {
            html += `<span style="margin-left: auto; font-size: 0.8rem; color: #999;">Round ${iteration}</span>`;
        }

        this.agentStatusElement.innerHTML = html;
        this.agentStatusElement.style.display = 'flex';
    }

    /**
     * Hide agent status
     */
    hideAgentStatus() {
        if (this.agentStatusElement) {
            this.agentStatusElement.style.display = 'none';
        }
    }

    /**
     * Toggle sidebar collapsed state
     */
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            if (sidebar.classList.contains('collapsed')) {
                this.expandSidebar();
            } else {
                this.collapseSidebar();
            }
        }
    }

    /**
     * Collapse sidebar
     */
    collapseSidebar() {
        const sidebar = document.getElementById('sidebar');
        const toggleIcon = document.getElementById('sidebarToggleIcon');
        if (sidebar) {
            sidebar.classList.add('collapsed');
        }
        if (toggleIcon) {
            toggleIcon.innerHTML = '&#x25B6;';  // Right arrow when collapsed
        }
        setStorage('sidebarCollapsed', 'true');
    }

    /**
     * Expand sidebar
     */
    expandSidebar() {
        const sidebar = document.getElementById('sidebar');
        const toggleIcon = document.getElementById('sidebarToggleIcon');
        if (sidebar) {
            sidebar.classList.remove('collapsed');
        }
        if (toggleIcon) {
            toggleIcon.innerHTML = '&#x25C0;';  // Left arrow when expanded
        }
        setStorage('sidebarCollapsed', 'false');
    }

    /**
     * Setup resize handles for sidebar and panel divider
     */
    setupResizeHandles() {
        // Sidebar resize handle
        const sidebarHandle = document.getElementById('sidebarResizeHandle');
        const sidebar = document.getElementById('sidebar');

        if (sidebarHandle && sidebar) {
            // Load saved sidebar width
            const savedWidth = getStorage('sidebarWidth');
            if (savedWidth) {
                sidebar.style.setProperty('--sidebar-width', savedWidth + 'px');
            }

            let isResizing = false;
            let startX = 0;
            let startWidth = 0;

            sidebarHandle.addEventListener('mousedown', (e) => {
                if (sidebar.classList.contains('collapsed')) return;
                isResizing = true;
                startX = e.clientX;
                startWidth = sidebar.offsetWidth;
                sidebarHandle.classList.add('active');
                sidebar.classList.add('resizing');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                const diff = e.clientX - startX;
                const newWidth = Math.min(Math.max(startWidth + diff, 150), 400);
                sidebar.style.setProperty('--sidebar-width', newWidth + 'px');
            });

            document.addEventListener('mouseup', () => {
                if (!isResizing) return;
                isResizing = false;
                sidebarHandle.classList.remove('active');
                sidebar.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Save width
                const width = sidebar.offsetWidth;
                setStorage('sidebarWidth', width);
            });
        }

        // Panel divider resize handle
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');
        const debatePanel = document.getElementById('debatePanel');
        const mainPanel = document.querySelector('.main-panel');

        if (panelDivider && chatContainer && debatePanel && mainPanel) {
            // Load saved panel ratio
            const savedRatio = getStorage('panelRatio');
            if (savedRatio) {
                const ratio = parseFloat(savedRatio);
                mainPanel.style.setProperty('--chat-flex', ratio);
                mainPanel.style.setProperty('--debate-flex', 1 - ratio);
            }

            let isResizing = false;
            let startX = 0;

            panelDivider.addEventListener('mousedown', (e) => {
                isResizing = true;
                startX = e.clientX;
                panelDivider.classList.add('active');
                chatContainer.classList.add('resizing');
                debatePanel.classList.add('resizing');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                const mainRect = mainPanel.getBoundingClientRect();
                const relativeX = e.clientX - mainRect.left;
                const totalWidth = mainRect.width;
                // Calculate ratio (accounting for gap and padding)
                let ratio = relativeX / totalWidth;
                ratio = Math.min(Math.max(ratio, 0.2), 0.8); // Limit between 20% and 80%
                mainPanel.style.setProperty('--chat-flex', ratio);
                mainPanel.style.setProperty('--debate-flex', 1 - ratio);
            });

            document.addEventListener('mouseup', () => {
                if (!isResizing) return;
                isResizing = false;
                panelDivider.classList.remove('active');
                chatContainer.classList.remove('resizing');
                debatePanel.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Save ratio
                const chatFlex = getComputedStyle(mainPanel).getPropertyValue('--chat-flex');
                if (chatFlex) {
                    setStorage('panelRatio', chatFlex);
                }
            });
        }
    }

    /**
     * Setup debate panel toggle switch
     */
    setupDebatePanelToggle() {
        const toggleContainer = document.getElementById('debateToggleContainer');
        const toggleCheckbox = document.getElementById('debatePanelToggle');
        const debatePanel = document.getElementById('debatePanel');
        const panelDivider = document.getElementById('panelDivider');

        if (!toggleCheckbox || !debatePanel) {
            console.log('Debate toggle elements not found, skipping setup');
            return;
        }

        // Load saved toggle state
        try {
            const savedToggleOn = getStorage('debatePanelToggleOn');
            if (savedToggleOn !== null && savedToggleOn !== undefined) {
                this.debatePanelToggleOn = savedToggleOn === true;
            }
        } catch (e) {
            console.error('Error loading debate toggle state:', e);
        }

        // Set initial checkbox state
        toggleCheckbox.checked = this.debatePanelToggleOn;

        toggleCheckbox.addEventListener('change', () => {
            this.debatePanelToggleOn = toggleCheckbox.checked;
            setStorage('debatePanelToggleOn', this.debatePanelToggleOn);

            if (this.debatePanelToggleOn) {
                this.showDebatePanel();
            } else {
                this.hideDebatePanel();
            }
        });
    }

    /**
     * Show debate panel and divider
     */
    showDebatePanel() {
        const debatePanel = document.getElementById('debatePanel');
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');

        if (debatePanel) {
            debatePanel.style.display = 'flex';
            this.debatePanelVisible = true;
        }
        if (panelDivider) {
            panelDivider.classList.add('visible');
        }
        if (chatContainer) {
            chatContainer.classList.remove('full-width');
        }
    }

    /**
     * Hide debate panel and divider
     */
    hideDebatePanel() {
        const debatePanel = document.getElementById('debatePanel');
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');

        if (debatePanel) {
            debatePanel.style.display = 'none';
            this.debatePanelVisible = false;
        }
        if (panelDivider) {
            panelDivider.classList.remove('visible');
        }
        if (chatContainer) {
            chatContainer.classList.add('full-width');
        }
    }

    /**
     * Update debate toggle visibility based on mode
     */
    updateDebateToggleVisibility() {
        const toggleContainer = document.getElementById('debateToggleContainer');
        const toggleCheckbox = document.getElementById('debatePanelToggle');

        if (!toggleContainer) return;

        if (this.isMultiAgentMode) {
            toggleContainer.style.display = 'flex';
            // Sync checkbox state
            if (toggleCheckbox) {
                toggleCheckbox.checked = this.debatePanelToggleOn;
            }
        } else {
            toggleContainer.style.display = 'none';
        }
    }

    /**
     * Setup click handler for debate-generated messages
     */
    setupDebateMessageClickHandler() {
        if (!this.messagesContainer) return;

        this.messagesContainer.addEventListener('click', (e) => {
            const debateMsg = e.target.closest('.message.debate-answer');
            if (!debateMsg) return;

            const debateId = debateMsg.dataset.debateId;
            const iteration = parseInt(debateMsg.dataset.iteration) || 0;

            // If toggle is on but panel is hidden, show it
            if (this.debatePanelToggleOn && !this.debatePanelVisible) {
                this.showDebatePanel();
            }

            // If panel is visible, load and show the corresponding debate
            if (this.debatePanelVisible && this.debateViewer) {
                // Load the specific debate data for this message
                if (debateId && debateId !== this.debateViewer.currentDebateId) {
                    this.debateViewer.loadData(debateId);
                }

                // Expand the corresponding round
                const cardIndex = iteration > 0 ? iteration - 1 : this.debateViewer.iterations.length - 1;
                if (cardIndex >= 0) {
                    this.debateViewer.expandedCard = cardIndex;
                    this.debateViewer.render();

                    // Scroll to the expanded card
                    setTimeout(() => {
                        const card = this.debateViewerElement.querySelector(`.round-card[data-iteration="${cardIndex + 1}"]`);
                        if (card) {
                            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    }, 100);
                }
            }
        });
    }

    /**
     * Update visibility of multi-agent UI components
     */
    updateMultiAgentUIVisibility() {
        // Show/hide multi-agent config based on mode
        if (this.multiAgentConfig) {
            if (this.isMultiAgentMode) {
                this.multiAgentConfig.show();
            } else {
                this.multiAgentConfig.hide();
            }
        }

        // Show/hide coworking config based on mode
        if (this.coworkingConfig) {
            if (this.isCoworkingMode) {
                this.coworkingConfig.show();
            } else {
                this.coworkingConfig.hide();
            }
        }

        // Show/hide simple mode controls (visible in simple and coworking modes)
        const simpleControls = document.querySelector('.model-selector-container');
        const thinkingContainer = document.querySelector('.thinking-toggle');
        if (simpleControls) {
            simpleControls.style.display = this.isMultiAgentMode ? 'none' : 'flex';
        }
        if (thinkingContainer) {
            thinkingContainer.style.display = this.isMultiAgentMode ? 'none' : 'flex';
        }

        // Update debate toggle button visibility
        try {
            this.updateDebateToggleVisibility();
        } catch (error) {
            console.error('Error updating debate toggle visibility:', error);
        }

        // Auto-hide debate panel when not in debate mode
        if (!this.isMultiAgentMode) {
            try {
                this.hideDebatePanel();
            } catch (error) {
                console.error('Error hiding debate panel:', error);
            }

            // Hide agent status bar
            this.hideAgentStatus();

            // Hide moderator status indicator
            if (this.moderatorStatusIndicator) {
                this.moderatorStatusIndicator.hide();
            }
        }

        // Auto-hide coworking panel when not in coworking mode
        if (!this.isCoworkingMode) {
            try {
                this.hideCoworkingPanel();
            } catch (error) {
                console.error('Error hiding coworking panel:', error);
            }
        }
    }

    /**
     * Update thinking toggle enabled/disabled state based on selected model
     * @param {string} modelId - Optional model ID to check (uses current model if not provided)
     */
    updateThinkingToggleState(modelId = null) {
        const currentModelId = modelId || this.modelSelector.getSelectedModel();
        const modelInfo = this.modelSelector.getSelectedModelInfo();
        console.log('Model info:', modelInfo);
        const supportsThinking = modelInfo && modelInfo.supports_thinking;
        const thinkingLocked = modelInfo && modelInfo.thinking_locked;
        console.log('Supports thinking:', supportsThinking, 'Thinking locked:', thinkingLocked);

        const toggleContainer = this.thinkingToggle.closest('.thinking-toggle');

        if (supportsThinking) {
            toggleContainer.classList.remove('disabled');

            if (thinkingLocked) {
                // Thinking is always on and cannot be toggled
                this.thinkingToggle.disabled = true;
                this.thinkingToggle.checked = true;
                this.isThinkingEnabled = true;
            } else {
                // Thinking can be toggled
                this.thinkingToggle.disabled = false;

                // Check if user has a saved preference for this specific model
                const savedThinking = currentModelId ? getStorage(`thinkingEnabled_${currentModelId}`) : null;

                if (savedThinking !== null) {
                    // Restore user preference for this model
                    this.isThinkingEnabled = savedThinking === 'true' || savedThinking === true;
                } else {
                    // No saved preference - default to enabled for thinking-capable models
                    this.isThinkingEnabled = true;
                }

                this.thinkingToggle.checked = this.isThinkingEnabled;
            }
        } else {
            // Model doesn't support thinking at all
            toggleContainer.classList.add('disabled');
            this.thinkingToggle.disabled = true;
            this.isThinkingEnabled = false;
            this.thinkingToggle.checked = false;
        }
    }

    /**
     * Load or create conversation ID
     * @returns {string} Conversation ID
     */
    loadOrCreateConversationId() {
        let convId = getStorage('conversationId');
        if (!convId) {
            convId = generateUUID();
            setStorage('conversationId', convId);
        }
        return convId;
    }

    /**
     * Load conversation history from API
     */
    async loadConversationHistory() {
        try {
            // First check if conversation exists (avoids 404 errors after backend restart)
            const conversationInfo = await this.apiClient.getConversationInfo(this.conversationId);
            if (!conversationInfo) {
                console.log('No existing conversation history (new conversation)');
                return;
            }

            // Load the full history if conversation exists
            const history = await this.apiClient.getConversationHistory(this.conversationId);
            if (history && history.messages && history.messages.length > 0) {
                this.messageComponent.loadMessages(history.messages, this.isMarkdownEnabled);
            }

            // Load most recent debate data from localStorage if available
            if (this.debateViewer) {
                const hasDebateData = this.debateViewer.loadMostRecentData();
                if (hasDebateData && this.isMultiAgentMode && this.debatePanelToggleOn) {
                    this.showDebatePanel();
                }
            }
        } catch (error) {
            // Something went wrong, but we can still continue
            console.log('Could not load conversation history:', error.message);
        }
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        // Route to appropriate handler based on mode
        if (this.isCoworkingMode) {
            await this.sendCoworkingMessage(message);
        } else if (this.isMultiAgentMode) {
            await this.sendMultiAgentMessage(message);
        } else {
            await this.sendSimpleMessage(message);
        }
    }

    /**
     * Send a message in simple (single-agent) mode
     */
    async sendSimpleMessage(message) {
        // Get selected model
        const modelId = this.modelSelector.getSelectedModel();
        if (!modelId) {
            this.messageComponent.addErrorMessage('Please select a model');
            return;
        }

        // Update UI
        this.messageComponent.addUserMessage(message);
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.setProcessing(true);

        // Show typing indicator
        const typingIndicator = this.messageComponent.showTypingIndicator();

        try {
            // Stream response
            let fullResponse = '';

            await this.apiClient.streamMessage(
                message,
                this.conversationId,
                modelId,
                (chunk) => {
                    // Accumulate response
                    fullResponse += chunk;
                    this.messageComponent.updateMessage(
                        typingIndicator,
                        fullResponse,
                        this.isMarkdownEnabled
                    );
                },
                this.isThinkingEnabled
            );

            // Refresh the sidebar to update the conversation title and timestamp
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            console.error('Error sending message:', error);
            this.messageComponent.removeTypingIndicator(typingIndicator);
            this.messageComponent.addErrorMessage(
                `Error: ${error.message}`
            );
        } finally {
            this.setProcessing(false);
            this.messageInput.focus();
        }
    }

    /**
     * Send a message in multi-agent debate mode
     */
    async sendMultiAgentMessage(message) {
        // Get multi-agent config
        const config = this.multiAgentConfig ? this.multiAgentConfig.getConfig() : {
            models: {
                moderator: this.modelSelector.getSelectedModel(),
                expert: this.modelSelector.getSelectedModel(),
                critic: this.modelSelector.getSelectedModel()
            },
            maxIterations: 3,
            scoreThreshold: 80
        };

        // Update UI
        this.messageComponent.addUserMessage(message);
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.setProcessing(true);

        // Generate debate ID for this session
        this.currentDebateId = Date.now().toString();
        this.currentDebateIteration = 0;

        // Show debate panel if toggle is on
        if (this.debatePanelToggleOn) {
            this.showDebatePanel();
        }

        // Clear previous debate display and set new debate ID
        if (this.debateViewer) {
            this.debateViewer.clear(false); // Don't clear storage, just display
            this.debateViewer.setDebateId(this.currentDebateId);
        }

        // Start progress indicator
        if (this.progressIndicator) {
            this.progressIndicator.start(config.maxIterations);
        }

        // Show typing indicator for final answer
        const typingIndicator = this.messageComponent.showTypingIndicator();

        try {
            await this.apiClient.streamMultiAgentDebate(
                message,
                this.conversationId,
                config,
                {
                    onPhaseChange: (phase, iteration) => {
                        // Update moderator status indicator
                        if (this.moderatorStatusIndicator) {
                            this.moderatorStatusIndicator.update(phase, iteration);
                        }
                    },
                    onModeratorInit: (analysis) => {
                        console.log('[Debug] onModeratorInit called');
                        if (this.debateViewer) {
                            this.debateViewer.setModeratorInit(analysis);
                            console.log('[Debug] setModeratorInit complete');
                        } else {
                            console.log('[Debug] debateViewer is null!');
                        }
                    },
                    onModeratorSynthesize: (iteration, analysis) => {
                        console.log(`[Debug] onModeratorSynthesize called for iteration ${iteration}`);
                        if (this.debateViewer) {
                            this.debateViewer.addModeratorSynthesis(iteration, analysis);
                            console.log('[Debug] addModeratorSynthesis complete');
                        } else {
                            console.log('[Debug] debateViewer is null!');
                        }
                    },
                    onPhaseStart: (phase, iteration, msg) => {
                        console.log(`Phase: ${phase}, Iteration: ${iteration}`);
                        if (this.progressIndicator) {
                            this.progressIndicator.setPhase(phase, iteration);
                        }
                        // Update agent status based on phase
                        let activeAgent = 'moderator';
                        if (phase === 'expert_generate' || phase === 'expert_answer') {
                            activeAgent = 'expert';
                        } else if (phase === 'critic_review') {
                            activeAgent = 'critic';
                        }
                        this.updateAgentStatus(activeAgent, iteration, phase);
                    },
                    onExpertAnswer: (iteration, answer) => {
                        console.log(`Expert answer (iteration ${iteration}):`, answer);
                        if (this.debateViewer) {
                            this.debateViewer.addExpertAnswer(iteration, answer);
                        }
                    },
                    onCriticReview: (iteration, review) => {
                        console.log(`Critic review (iteration ${iteration}):`, review);
                        if (this.debateViewer) {
                            this.debateViewer.addCriticReview(iteration, review);
                        }
                    },
                    onIterationComplete: (iteration, status, score, summary) => {
                        console.log(`Iteration ${iteration} complete: ${status}, score: ${score}`);
                        this.currentDebateIteration = iteration;
                    },
                    onDone: (finalAnswer, wasDirectAnswer, terminationReason, totalIterations) => {
                        console.log('Debate complete:', { finalAnswer, wasDirectAnswer, terminationReason, totalIterations });

                        // Remove typing indicator
                        this.messageComponent.removeTypingIndicator(typingIndicator);

                        // Add debate answer message with source badge
                        const iteration = wasDirectAnswer ? 0 : (totalIterations || this.currentDebateIteration);
                        this.messageComponent.addDebateMessage(
                            finalAnswer,
                            this.currentDebateId,
                            iteration,
                            this.isMarkdownEnabled
                        );

                        // Update debate viewer with final answer
                        if (this.debateViewer && !wasDirectAnswer) {
                            this.debateViewer.setFinalAnswer(finalAnswer, terminationReason);
                        }

                        // Complete progress indicator
                        if (this.progressIndicator) {
                            if (wasDirectAnswer) {
                                this.progressIndicator.setDirectAnswer();
                            }
                            this.progressIndicator.complete(terminationReason);
                        }

                        // Collapse all cards when debate ends
                        if (this.debateViewer) {
                            this.debateViewer.expandedCard = null;
                            this.debateViewer.render();
                        }
                        if (this.moderatorStatusIndicator) {
                            this.moderatorStatusIndicator.hide();
                        }

                        // Hide agent status
                        this.hideAgentStatus();
                    },
                    onError: (error) => {
                        console.error('Multi-agent error:', error);
                        this.messageComponent.removeTypingIndicator(typingIndicator);
                        this.messageComponent.addErrorMessage(`Error: ${error}`);

                        if (this.progressIndicator) {
                            this.progressIndicator.showError(error);
                        }

                        // Hide agent status on error
                        this.hideAgentStatus();
                    }
                }
            );

            // Refresh the sidebar
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            console.error('Error in multi-agent debate:', error);
            this.messageComponent.removeTypingIndicator(typingIndicator);
            this.messageComponent.addErrorMessage(`Error: ${error.message}`);

            if (this.progressIndicator) {
                this.progressIndicator.showError(error.message);
            }

            // Hide agent status on error
            this.hideAgentStatus();
        } finally {
            this.setProcessing(false);
            this.messageInput.focus();
        }
    }

    /**
     * Send a message in coworking agent mode
     */
    async sendCoworkingMessage(message) {
        const modelId = this.modelSelector.getSelectedModel();
        if (!modelId) {
            this.messageComponent.addErrorMessage('Please select a model');
            return;
        }

        const workspacePath = this.coworkingConfig ? this.coworkingConfig.getWorkspacePath() : '';
        if (!workspacePath) {
            this.messageComponent.addErrorMessage('Please set a workspace path');
            return;
        }

        // Update UI
        this.messageComponent.addUserMessage(message);
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.setProcessing(true);

        // Show coworking panel
        this.showCoworkingPanel();

        // Clear previous tool execution display
        if (this.toolExecutionViewer) {
            this.toolExecutionViewer.clear();
            this.toolExecutionViewer.setWorkspacePath(workspacePath);
        }

        // Show typing indicator
        const typingIndicator = this.messageComponent.showTypingIndicator();

        try {
            let fullResponse = '';

            await this.apiClient.streamCoworkingChat(
                message,
                this.conversationId,
                modelId,
                workspacePath,
                this.isThinkingEnabled,
                25,
                {
                    onPlan: (steps) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.setPlan(steps);
                        }
                    },
                    onThinkingChunk: (content) => {
                        fullResponse += content;
                        this.messageComponent.updateMessage(
                            typingIndicator,
                            fullResponse,
                            this.isMarkdownEnabled
                        );
                    },
                    onToolStart: (toolName, toolInput) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addToolStart(toolName, toolInput);
                        }
                    },
                    onToolResult: (toolName, output, success) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addToolResult(toolName, output, success);
                        }
                    },
                    onFileCreated: (filePath, fileSize) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addFileCreated(filePath, fileSize);
                        }
                    },
                    onResponseChunk: (content) => {
                        fullResponse += content;
                        this.messageComponent.updateMessage(
                            typingIndicator,
                            fullResponse,
                            this.isMarkdownEnabled
                        );
                    },
                    onDone: (finalAnswer, generatedFiles) => {
                        this.messageComponent.removeTypingIndicator(typingIndicator);
                        if (finalAnswer) {
                            this.messageComponent.addAssistantMessage(
                                finalAnswer,
                                this.isMarkdownEnabled
                            );
                        }
                    },
                    onError: (error) => {
                        console.error('Coworking error:', error);
                        this.messageComponent.removeTypingIndicator(typingIndicator);
                        this.messageComponent.addErrorMessage(`Error: ${error}`);
                    }
                }
            );

            // Refresh sidebar
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            console.error('Error in coworking chat:', error);
            this.messageComponent.removeTypingIndicator(typingIndicator);
            this.messageComponent.addErrorMessage(`Error: ${error.message}`);
        } finally {
            this.setProcessing(false);
            this.messageInput.focus();
        }
    }

    /**
     * Show coworking panel (right side)
     */
    showCoworkingPanel() {
        const coworkingPanel = document.getElementById('coworkingPanel');
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');

        if (coworkingPanel) {
            coworkingPanel.style.display = 'flex';
        }
        if (panelDivider) {
            panelDivider.classList.add('visible');
        }
        if (chatContainer) {
            chatContainer.classList.remove('full-width');
        }
    }

    /**
     * Hide coworking panel
     */
    hideCoworkingPanel() {
        const coworkingPanel = document.getElementById('coworkingPanel');
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');

        if (coworkingPanel) {
            coworkingPanel.style.display = 'none';
        }
        if (panelDivider) {
            panelDivider.classList.remove('visible');
        }
        if (chatContainer) {
            chatContainer.classList.add('full-width');
        }
    }

    /**
     * Handle mode change and transfer context if needed
     */
    async handleModeChange(mode) {
        const targetMode = mode === 'multi-agent' ? 'debate' : (mode === 'coworking' ? 'coworking' : 'simple');
        const wasMultiAgent = this.isMultiAgentMode;
        const wasCoworking = this.isCoworkingMode;
        console.log(`[ModeSwitch] Attempting to switch to ${targetMode}`);

        // Update UI state first
        this.isMultiAgentMode = mode === 'multi-agent';
        this.isCoworkingMode = mode === 'coworking';
        this.updateMultiAgentUIVisibility();

        // Check if mode actually changed
        if (wasMultiAgent === this.isMultiAgentMode && wasCoworking === this.isCoworkingMode) {
            console.log(`[ModeSwitch] Mode unchanged, no action needed`);
            return;
        }

        try {
            // Get config if switching to debate mode
            const debateConfig = this.isMultiAgentMode && this.multiAgentConfig ?
                this.multiAgentConfig.getConfig() : null;

            console.log(`[ModeSwitch] Calling API to switch to ${targetMode} mode...`);

            const response = await this.apiClient.switchMode(
                this.conversationId,
                targetMode,
                debateConfig
            );

            console.log(`[ModeSwitch] API response:`, response);

            if (response.success) {
                console.log(`✓ Mode switched successfully`);
                // Try to show system message, fallback to console if method not available
                if (this.messageComponent.addSystemMessage) {
                    this.messageComponent.addSystemMessage(
                        `Switched to ${targetMode} mode. ${response.message || ''}`
                    );
                } else {
                    console.log(`[ModeSwitch] Success: ${response.message || ''}`);
                }
            } else {
                console.error('Mode switch failed:', response);
                if (this.messageComponent.addErrorMessage) {
                    this.messageComponent.addErrorMessage(`Failed to switch mode: ${response.message || 'Unknown error'}`);
                } else {
                    console.error(`[ModeSwitch] Failed: ${response.message || 'Unknown error'}`);
                }
                // Revert UI on failure
                this.isMultiAgentMode = wasMultiAgent;
                this.isCoworkingMode = wasCoworking;
                this.updateMultiAgentUIVisibility();
            }
        } catch (error) {
            console.error('[ModeSwitch] Error switching mode:', error);

            // If conversation not found, create a new one and retry
            if (error.message && error.message.includes('not found')) {
                console.log('[ModeSwitch] Conversation not found, creating new conversation...');
                await this.createNewConversation();

                // Retry mode switch with new conversation
                try {
                    const debateConfig = this.isMultiAgentMode && this.multiAgentConfig ?
                        this.multiAgentConfig.getConfig() : null;

                    const response = await this.apiClient.switchMode(
                        this.conversationId,
                        targetMode,
                        debateConfig
                    );

                    if (response.success) {
                        console.log(`✓ Mode switched successfully after creating new conversation`);
                        if (this.messageComponent.addSystemMessage) {
                            this.messageComponent.addSystemMessage(
                                `Switched to ${targetMode} mode. ${response.message || ''}`
                            );
                        }
                        return;
                    }
                } catch (retryError) {
                    console.error('[ModeSwitch] Retry failed:', retryError);
                }
            }

            if (this.messageComponent.addErrorMessage) {
                this.messageComponent.addErrorMessage(`Error switching mode: ${error.message}`);
            } else {
                console.error(`[ModeSwitch] Error: ${error.message}`);
            }
            // Revert UI state on error
            this.isMultiAgentMode = wasMultiAgent;
            this.isCoworkingMode = wasCoworking;
            this.updateMultiAgentUIVisibility();
        }
    }

    /**
     * Select an existing conversation
     */
    async selectConversation(conversationId) {
        if (conversationId === this.conversationId) return;

        this.conversationId = conversationId;
        this.messageComponent.setConversationId(conversationId);
        if (this.debateViewer) {
            this.debateViewer.setConversationId(conversationId);
            // Clear without removing storage (we'll load from storage)
            this.debateViewer.clear(false);
        }
        setStorage('conversationId', conversationId);
        this.sidebar.setCurrentConversation(conversationId);

        // Clear and load the selected conversation
        this.messageComponent.clearMessages();
        await this.loadConversationHistory();

        console.log('Switched to conversation:', conversationId);
    }

    /**
     * Create a new conversation
     */
    createNewConversation() {
        this.conversationId = generateUUID();
        this.messageComponent.setConversationId(this.conversationId);
        if (this.debateViewer) {
            this.debateViewer.setConversationId(this.conversationId);
            this.debateViewer.clear();
        }
        setStorage('conversationId', this.conversationId);
        this.sidebar.setCurrentConversation(this.conversationId);
        this.messageComponent.clearMessages();

        console.log('Created new conversation:', this.conversationId);
    }

    /**
     * Set processing state
     * @param {boolean} processing - Whether processing
     */
    setProcessing(processing) {
        this.isProcessing = processing;
        this.sendBtn.disabled = processing;
        this.messageInput.disabled = processing;
    }

    /**
     * Clear conversation
     */
    async clearConversation() {
        if (!confirm('Clear this conversation?')) return;

        try {
            await this.apiClient.deleteConversation(this.conversationId);
            this.messageComponent.clearMessages();

            // Create new conversation
            this.createNewConversation();

            // Refresh the sidebar
            await this.sidebar.loadConversations();

            console.log('Conversation cleared');
        } catch (error) {
            console.error('Error clearing conversation:', error);
            this.messageComponent.addErrorMessage('Failed to clear conversation');
        }
    }

    /**
     * Get current conversation ID
     * @returns {string} Conversation ID
     */
    getConversationId() {
        return this.conversationId;
    }

    /**
     * Get selected model info
     * @returns {Object} Model info
     */
    getSelectedModelInfo() {
        return this.modelSelector.getSelectedModelInfo();
    }
}
