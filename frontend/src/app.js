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
import { SettingsPanel } from './components/SettingsPanel.js';

export class ChatApp {
    constructor() {
        // Initialize API client
        this.apiClient = new APIClient();

        // Settings panel (lazy-initialized)
        this.settingsPanel = null;

        // Get DOM elements
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.modelSelectElement = document.getElementById('modelSelect');
        this.thinkingToggle = document.getElementById('thinkingToggle');
        this.markdownToggle = document.getElementById('markdownToggle');
        this.webSearchToggle = document.getElementById('webSearchToggle');
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
        this.modelSelector = new ModelSelector(this.modelSelectElement, this.apiClient);
        const getModelInfo = (modelId) => {
            const models = this.modelSelector ? this.modelSelector.getAllModels() : [];
            return models.find(m => m.model_id === modelId) || null;
        };
        this.messageComponent = new MessageComponent(this.messagesContainer, getModelInfo);
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
            this.coworkingConfig = new CoworkingConfig(this.coworkingConfigElement, this.apiClient);
        }

        this.toolExecutionViewerElement = document.getElementById('toolExecutionViewer');
        this.toolExecutionViewer = null;
        if (this.toolExecutionViewerElement) {
            this.toolExecutionViewer = new ToolExecutionViewer(this.toolExecutionViewerElement, this.apiClient);
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
        this.isWebSearchEnabled = false;
        this.isMultiAgentMode = false;
        this.isCoworkingMode = false;
        this.isImageMode = false;
        this.imageModeConversationStarted = false; // locks checkbox after first message
        this.imageAspectRatio = getStorage('imageAspectRatio') || '1:1';

        // Debate panel visibility state
        this.debatePanelVisible = false;
        this.debatePanelToggleOn = true; // Toggle button state (on = will show panel when debate starts)
        this.currentDebateId = null;
        this.currentDebateIteration = 0;
        this.activeRunId = null;
        this.activeAbortController = null;
        this.activeMode = null;
        this.cancelRequested = false;
        this.cancellationMessageShown = false;

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
        this.sendBtn.addEventListener('click', () => {
            if (this.isProcessing) {
                this.cancelActiveRun();
                return;
            }
            this.sendMessage();
        });

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

        // Image mode toggle
        const imageModeToggle = document.getElementById('imageModeToggle');
        if (imageModeToggle) {
            imageModeToggle.addEventListener('change', (e) => {
                if (this.imageModeConversationStarted) {
                    // Locked — revert the checkbox silently
                    e.target.checked = this.isImageMode;
                    return;
                }
                this.isImageMode = e.target.checked;
                this.modelSelector.setImageMode(this.isImageMode);
                this.updateMultiAgentUIVisibility();
            });
        }

        // Aspect ratio selector
        const aspectRatioSelect = document.getElementById('aspectRatioSelect');
        if (aspectRatioSelect) {
            aspectRatioSelect.value = this.imageAspectRatio;
            aspectRatioSelect.addEventListener('change', (e) => {
                this.imageAspectRatio = e.target.value;
                setStorage('imageAspectRatio', this.imageAspectRatio);
            });
        }

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

        // Web search toggle change
        if (this.webSearchToggle) {
            this.webSearchToggle.addEventListener('change', (e) => {
                this.isWebSearchEnabled = e.target.checked;
                setStorage('webSearchEnabled', this.isWebSearchEnabled);
            });

            // Load saved web search preference
            const savedWebSearch = getStorage('webSearchEnabled');
            if (savedWebSearch !== null) {
                this.isWebSearchEnabled = savedWebSearch === 'true' || savedWebSearch === true;
                this.webSearchToggle.checked = this.isWebSearchEnabled;
            }
        }

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

        // Settings button
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openSettings());
        }

        // Listen for settings updates to refresh model list
        window.addEventListener('settings-updated', () => this.refreshModelsAfterSettingsChange());

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
     * Open the provider settings panel
     */
    openSettings() {
        if (!this.settingsPanel) {
            this.settingsPanel = new SettingsPanel(this.apiClient);
        }
        this.settingsPanel.open();
    }

    /**
     * Refresh model list after settings change, filtering by configured providers
     */
    async refreshModelsAfterSettingsChange() {
        try {
            const data = await this.apiClient.getProviderSettings();
            const configuredProviders = Object.entries(data.providers)
                .filter(([_, cfg]) => cfg.api_key_set)
                .map(([id, _]) => id.toLowerCase());
            this.modelSelector.setConfiguredProviders(configuredProviders);
        } catch (error) {
            console.error('Error refreshing models after settings change:', error);
        }
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
        const coworkingPanel = document.getElementById('coworkingPanel');
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
            let startChatWidth = 0;

            panelDivider.addEventListener('mousedown', (e) => {
                isResizing = true;
                startX = e.clientX;
                startChatWidth = chatContainer.getBoundingClientRect().width;
                panelDivider.classList.add('active');
                chatContainer.classList.add('resizing');
                if (debatePanel.style.display !== 'none') {
                    debatePanel.classList.add('resizing');
                }
                if (coworkingPanel && coworkingPanel.style.display !== 'none') {
                    coworkingPanel.classList.add('resizing');
                }
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                const cs = getComputedStyle(mainPanel);
                const paddingL = parseFloat(cs.paddingLeft);
                const paddingR = parseFloat(cs.paddingRight);
                const gap = parseFloat(cs.gap) || 0;
                const contentWidth = mainPanel.getBoundingClientRect().width - paddingL - paddingR;
                const fixedSpace = gap * 2 + panelDivider.offsetWidth;
                const flexSpace = Math.max(contentWidth - fixedSpace, 1);

                const diff = e.clientX - startX;
                const newChatWidth = Math.min(Math.max(startChatWidth + diff, flexSpace * 0.2), flexSpace * 0.8);
                const ratio = newChatWidth / flexSpace;
                mainPanel.style.setProperty('--chat-flex', ratio);
                mainPanel.style.setProperty('--debate-flex', 1 - ratio);
            });

            document.addEventListener('mouseup', () => {
                if (!isResizing) return;
                isResizing = false;
                panelDivider.classList.remove('active');
                chatContainer.classList.remove('resizing');
                debatePanel.classList.remove('resizing');
                if (coworkingPanel) coworkingPanel.classList.remove('resizing');
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
     * Hide debate panel and divider (unless coworking panel is visible)
     */
    hideDebatePanel() {
        const debatePanel = document.getElementById('debatePanel');
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');
        const coworkingPanel = document.getElementById('coworkingPanel');

        if (debatePanel) {
            debatePanel.style.display = 'none';
            this.debatePanelVisible = false;
        }
        const coworkingVisible = coworkingPanel && coworkingPanel.style.display !== 'none';
        if (panelDivider && !coworkingVisible) {
            panelDivider.classList.remove('visible');
        }
        if (chatContainer && !coworkingVisible) {
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
        const markdownContainer = document.querySelector('.markdown-toggle');
        const aspectRatioContainer = document.getElementById('aspectRatioSelectorContainer');
        if (simpleControls) {
            simpleControls.style.display = this.isMultiAgentMode ? 'none' : 'flex';
        }
        if (thinkingContainer) {
            thinkingContainer.style.display = (this.isMultiAgentMode || this.isImageMode) ? 'none' : 'flex';
        }
        if (markdownContainer) {
            markdownContainer.style.display = this.isImageMode ? 'none' : 'flex';
        }
        if (aspectRatioContainer) {
            aspectRatioContainer.style.display = this.isImageMode ? 'flex' : 'none';
        }

        // Show/hide web search toggle (visible in simple and coworking modes, hidden in debate and image)
        const webSearchContainer = document.getElementById('webSearchToggleContainer');
        if (webSearchContainer) {
            webSearchContainer.style.display = (this.isMultiAgentMode || this.isImageMode) ? 'none' : 'flex';
        }

        // Show/hide image mode toggle (hidden in debate and coworking modes)
        const imageModeToggleContainer = document.getElementById('imageModeToggleContainer');
        if (imageModeToggleContainer) {
            imageModeToggleContainer.style.display = (this.isMultiAgentMode || this.isCoworkingMode) ? 'none' : 'flex';
        }

        // Update debate toggle button visibility
        try {
            this.updateDebateToggleVisibility();
        } catch (error) {
            console.error('Error updating debate toggle visibility:', error);
        }

        // Manage debate panel visibility based on mode
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
        } else if (this.debatePanelToggleOn) {
            // Re-show debate panel when entering debate mode if toggle is on
            try {
                this.showDebatePanel();
            } catch (error) {
                console.error('Error showing debate panel:', error);
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

            await this.restoreCoworkingSessionState(conversationInfo);

            // Load the full history if conversation exists
            const history = await this.apiClient.getConversationHistory(this.conversationId);

            // Restore image mode if this is an image conversation
            const hasImageMessages = history && history.messages && history.messages.some(
                msg => msg.message_type === 'image_response'
            );
            if (conversationInfo.mode === 'image' || hasImageMessages) {
                this.isImageMode = true;
                this.imageModeConversationStarted = true;
                const imageModeToggle = document.getElementById('imageModeToggle');
                if (imageModeToggle) {
                    imageModeToggle.checked = true;
                    imageModeToggle.disabled = true;
                    imageModeToggle.title = 'Cannot change image mode during a conversation';
                }
                this.modelSelector.setImageMode(true);
                this.updateMultiAgentUIVisibility();
            }

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
     * Restore coworking session file state for the current conversation if applicable.
     * @param {Object} conversationInfo - Conversation metadata
     */
    async restoreCoworkingSessionState(conversationInfo) {
        const workspacePath = this.coworkingConfig ? this.coworkingConfig.getWorkspacePath() : '';
        const metadata = conversationInfo && conversationInfo.metadata ? conversationInfo.metadata : {};
        const hasCoworkingState = Boolean(metadata.coworking_baseline_files);

        if (!workspacePath || (!hasCoworkingState && conversationInfo.mode !== 'coworking')) {
            return;
        }

        try {
            const state = await this.apiClient.getCoworkingSessionState(this.conversationId, workspacePath);
            if (this.toolExecutionViewer) {
                this.toolExecutionViewer.setWorkspacePath(workspacePath);
                this.toolExecutionViewer.setFileState(
                    state.generated_files || [],
                    state.deleted_files || []
                );
            }
        } catch (error) {
            console.warn('Could not restore coworking session state:', error);
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
        } else if (this.isImageMode) {
            await this.sendImageMessage(message);
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
        this.beginRun('simple');
        this.setProcessing(true);

        // Show typing indicator
        const typingIndicator = this.messageComponent.showTypingIndicator();
        let fullResponse = '';

        try {
            await this.apiClient.streamMessage(
                message,
                this.conversationId,
                modelId,
                {
                    onChunk: (chunk) => {
                        // Accumulate response
                        fullResponse += chunk;
                        if (fullResponse.includes('<think')) {
                            this.messageComponent.updateMessageWithThinking(
                                typingIndicator,
                                fullResponse,
                                this.isMarkdownEnabled
                            );
                        } else {
                            this.messageComponent.updateMessage(
                                typingIndicator,
                                fullResponse,
                                this.isMarkdownEnabled
                            );
                        }
                    }
                },
                this.isThinkingEnabled,
                this.isWebSearchEnabled,
                this.getStreamOptions()
            );

            // Collapse all thinking blocks now that streaming is complete
            if (fullResponse.includes('<think')) {
                this.messageComponent.collapseThinkingBlocks(typingIndicator);
            }

            // Extract and apply citation metadata from the stream
            const citationMatch = fullResponse.match(/<!--CITATIONS_JSON(.+?)CITATIONS_JSON-->/s);
            if (citationMatch) {
                try {
                    const citations = JSON.parse(citationMatch[1]);
                    // Strip the metadata from the stored response
                    fullResponse = fullResponse.replace(/\n?\n?<!--CITATIONS_JSON.+?CITATIONS_JSON-->/s, '');
                    const msgId = typingIndicator.dataset.messageId;
                    if (msgId) {
                        this.messageComponent.messageContents.set(msgId, fullResponse);
                    }
                    // Re-render without the metadata
                    if (fullResponse.includes('<think')) {
                        this.messageComponent.updateMessageWithThinking(
                            typingIndicator, fullResponse, this.isMarkdownEnabled
                        );
                    } else {
                        this.messageComponent.updateMessage(
                            typingIndicator, fullResponse, this.isMarkdownEnabled
                        );
                    }
                    // Apply interactive citation markers
                    this.messageComponent.applyCitations(typingIndicator, citations);
                } catch (e) {
                    console.warn('Failed to parse citation metadata:', e);
                }
            }

            // Extract and display metrics from the stream
            const metricsMatch = fullResponse.match(/<!--METRICS_JSON(.+?)METRICS_JSON-->/s);
            if (metricsMatch) {
                try {
                    const metrics = JSON.parse(metricsMatch[1]);
                    // Strip the metrics metadata from the stored response
                    fullResponse = fullResponse.replace(/\n?\n?<!--METRICS_JSON.+?METRICS_JSON-->/s, '');
                    const msgId = typingIndicator.dataset.messageId;
                    if (msgId) {
                        this.messageComponent.messageContents.set(msgId, fullResponse);
                    }
                    // Re-render without the metadata
                    if (fullResponse.includes('<think')) {
                        this.messageComponent.updateMessageWithThinking(
                            typingIndicator, fullResponse, this.isMarkdownEnabled
                        );
                    } else {
                        this.messageComponent.updateMessage(
                            typingIndicator, fullResponse, this.isMarkdownEnabled
                        );
                    }
                    this.messageComponent.addMetricsBar(typingIndicator, metrics);
                } catch (e) {
                    console.warn('Failed to parse metrics metadata:', e);
                }
            }

            // Refresh the sidebar to update the conversation title and timestamp
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            if (error.isCancellation || (this.cancelRequested && this.isAbortError(error))) {
                if (!fullResponse.trim()) {
                    this.messageComponent.removeTypingIndicator(typingIndicator);
                }
                this.showCancellationMessage(error.isCancellation ? error.message : undefined);
            } else {
                console.error('Error sending message:', error);
                if (!fullResponse.trim()) {
                    this.messageComponent.removeTypingIndicator(typingIndicator);
                }
                this.messageComponent.addErrorMessage(error.message);
            }
        } finally {
            this.setProcessing(false);
            await this.refreshSidebarSafely();
            this.resetRunState();
            this.messageInput.focus();
        }
    }

    /**
     * Send a prompt to an image generation model and display the result.
     */
    async sendImageMessage(message) {
        const modelId = this.modelSelector.getSelectedModel();
        if (!modelId) {
            this.messageComponent.addErrorMessage('Please select an image model');
            return;
        }

        this.messageComponent.addUserMessage(message);
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.beginRun('image');
        this.setProcessing(true);

        // Lock image mode toggle after first message
        this.imageModeConversationStarted = true;
        const imageModeToggle = document.getElementById('imageModeToggle');
        if (imageModeToggle) {
            imageModeToggle.disabled = true;
            imageModeToggle.title = 'Cannot change image mode during a conversation';
        }

        const typingIndicator = this.messageComponent.showTypingIndicator();
        let textAcc = '';
        const images = [];

        try {
            const streamOptions = this.getStreamOptions();
            streamOptions.aspect_ratio = this.imageAspectRatio;
            await this.apiClient.streamImageMessage(
                message,
                this.conversationId,
                modelId,
                (event) => {
                    if (event.type === 'text_chunk') {
                        textAcc += event.content;
                        this.messageComponent.updateMessage(typingIndicator, textAcc, this.isMarkdownEnabled);
                    } else if (event.type === 'image') {
                        images.push({ data: event.data, mime_type: event.mime_type || 'image/png' });
                    } else if (event.type === 'error') {
                        throw new Error(event.message);
                    }
                },
                streamOptions
            );

            // Replace typing indicator with full image message
            this.messageComponent.removeTypingIndicator(typingIndicator);
            this.messageComponent.addImageMessage(textAcc, images);

            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            if (this.cancelRequested && this.isAbortError(error)) {
                if (!textAcc.trim() && images.length === 0) {
                    this.messageComponent.removeTypingIndicator(typingIndicator);
                }
                this.showCancellationMessage();
            } else {
                console.error('Error generating image:', error);
                this.messageComponent.removeTypingIndicator(typingIndicator);
                this.messageComponent.addErrorMessage(`Error: ${error.message}`);
            }
        } finally {
            this.setProcessing(false);
            await this.refreshSidebarSafely();
            this.resetRunState();
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
        this.beginRun('debate');
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
                    onDone: (finalAnswer, wasDirectAnswer, terminationReason, totalIterations, metrics) => {
                        console.log('Debate complete:', { finalAnswer, wasDirectAnswer, terminationReason, totalIterations, metrics });

                        // Remove typing indicator
                        this.messageComponent.removeTypingIndicator(typingIndicator);

                        // Add debate answer message with source badge
                        const iteration = wasDirectAnswer ? 0 : (totalIterations || this.currentDebateIteration);
                        const debateMsg = this.messageComponent.addDebateMessage(
                            finalAnswer,
                            this.currentDebateId,
                            iteration,
                            this.isMarkdownEnabled
                        );

                        // Attach metrics bar to the debate message
                        if (metrics && debateMsg) {
                            this.messageComponent.addMetricsBar(debateMsg, metrics);
                        }

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
                    onCancelled: (messageText) => {
                        this.messageComponent.removeTypingIndicator(typingIndicator);
                        if (this.progressIndicator) {
                            this.progressIndicator.complete('cancelled');
                        }
                        if (this.moderatorStatusIndicator) {
                            this.moderatorStatusIndicator.hide();
                        }
                        this.hideAgentStatus();
                        this.showCancellationMessage(messageText);
                    },
                    onError: (error) => {
                        if (this.cancelRequested) return;
                        console.error('Multi-agent error:', error);
                        this.messageComponent.removeTypingIndicator(typingIndicator);
                        this.messageComponent.addErrorMessage(`Error: ${error}`);

                        if (this.progressIndicator) {
                            this.progressIndicator.showError(error);
                        }

                        // Hide agent status on error
                        this.hideAgentStatus();
                    }
                },
                this.getStreamOptions()
            );

            // Refresh the sidebar
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            if (this.cancelRequested && this.isAbortError(error)) {
                this.messageComponent.removeTypingIndicator(typingIndicator);
                if (this.progressIndicator) {
                    this.progressIndicator.complete('cancelled');
                }
                if (this.moderatorStatusIndicator) {
                    this.moderatorStatusIndicator.hide();
                }
                this.hideAgentStatus();
                this.showCancellationMessage();
            } else {
                console.error('Error in multi-agent debate:', error);
                this.messageComponent.removeTypingIndicator(typingIndicator);
                this.messageComponent.addErrorMessage(`Error: ${error.message}`);

                if (this.progressIndicator) {
                    this.progressIndicator.showError(error.message);
                }

                // Hide agent status on error
                this.hideAgentStatus();
            }
        } finally {
            this.setProcessing(false);
            await this.refreshSidebarSafely();
            this.resetRunState();
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
        this.beginRun('coworking');
        this.setProcessing(true);

        // Show coworking panel
        this.showCoworkingPanel();

        // Clear previous tool execution display (keep generated files across messages)
        if (this.toolExecutionViewer) {
            this.toolExecutionViewer.clearForNewMessage();
            this.toolExecutionViewer.setWorkspacePath(workspacePath);
        }

        const transcriptMessage = this.messageComponent.createCoworkingTranscriptMessage();
        const transcriptState = {
            planSteps: [],
            rounds: [],
            finalStarted: false,
            finalAnswer: '',
            citations: []
        };

        const renderTranscript = () => {
            this.messageComponent.updateCoworkingTranscript(
                transcriptMessage,
                transcriptState,
                this.isMarkdownEnabled
            );
        };

        const ensureRound = (roundNumber) => {
            let round = transcriptState.rounds.find(item => item.round === roundNumber);
            if (!round) {
                round = {
                    round: roundNumber,
                    reasoning: '',
                    toolCalls: [],
                    status: 'running'
                };
                transcriptState.rounds.push(round);
                transcriptState.rounds.sort((a, b) => a.round - b.round);
            }
            return round;
        };

        renderTranscript();

        try {
            await this.apiClient.streamCoworkingChat(
                message,
                this.conversationId,
                modelId,
                workspacePath,
                this.isThinkingEnabled,
                25,
                this.isWebSearchEnabled,
                {
                    onPreviousFiles: (files, deletedFiles) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.setFileState(files, deletedFiles);
                        }
                    },
                    onPlanReady: (steps) => {
                        transcriptState.planSteps = steps || [];
                        renderTranscript();
                    },
                    onRoundStart: (round) => {
                        ensureRound(round).status = 'running';
                        renderTranscript();
                    },
                    onReasoningChunk: (round, content) => {
                        const roundState = ensureRound(round);
                        roundState.reasoning += content;
                        renderTranscript();
                    },
                    onToolStart: (round, toolName, toolInput, toolCallId) => {
                        const roundState = ensureRound(round);
                        roundState.toolCalls.push({
                            id: toolCallId,
                            name: toolName,
                            input: toolInput,
                            output: '',
                            success: null,
                            status: 'running'
                        });
                        renderTranscript();
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addToolStart(toolName, toolInput, round, toolCallId);
                        }
                    },
                    onToolResult: (round, toolName, output, success, toolCallId) => {
                        const roundState = ensureRound(round);
                        let toolState = roundState.toolCalls.find(
                            tool => tool.id === toolCallId && tool.id
                        );
                        if (!toolState) {
                            toolState = [...roundState.toolCalls]
                                .reverse()
                                .find(tool => tool.name === toolName && tool.status === 'running');
                        }
                        if (toolState) {
                            toolState.output = output;
                            toolState.success = success;
                            toolState.status = success ? 'done' : 'error';
                        }
                        if (success === false) {
                            roundState.status = 'error';
                        }
                        renderTranscript();
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addToolResult(toolName, output, success, round, toolCallId);
                        }
                    },
                    onRoundComplete: (round) => {
                        const roundState = ensureRound(round);
                        roundState.status = roundState.toolCalls.some(tool => tool.status === 'error')
                            ? 'error'
                            : 'done';
                        renderTranscript();
                    },
                    onFileCreated: (filePath, fileSize) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addFileCreated(filePath, fileSize);
                        }
                    },
                    onFileDeleted: (filePath) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.addFileDeleted(filePath);
                        }
                    },
                    onSessionNotice: (notice) => {
                        if (notice) {
                            this.messageComponent.addSystemMessage(notice);
                        }
                    },
                    onFinalStart: () => {
                        transcriptState.finalStarted = true;
                        renderTranscript();
                    },
                    onFinalChunk: (content) => {
                        transcriptState.finalStarted = true;
                        transcriptState.finalAnswer += content;
                        renderTranscript();
                    },
                    onCitations: (citations) => {
                        transcriptState.citations = citations || [];
                        renderTranscript();
                    },
                    onDone: (finalAnswer, generatedFiles, deletedFiles, metrics) => {
                        if (this.toolExecutionViewer) {
                            this.toolExecutionViewer.setFileState(generatedFiles, deletedFiles);
                        }
                        if (finalAnswer) {
                            transcriptState.finalStarted = true;
                            transcriptState.finalAnswer = finalAnswer;
                        }
                        renderTranscript();
                        if (metrics && transcriptMessage) {
                            this.messageComponent.addMetricsBar(transcriptMessage, metrics);
                        }
                    },
                    onCancelled: (messageText) => {
                        this.showCancellationMessage(messageText);
                    },
                    onError: (error) => {
                        if (this.cancelRequested) return;
                        console.error('Coworking error:', error);
                        this.messageComponent.addErrorMessage(`Error: ${error}`);
                    }
                },
                this.getStreamOptions()
            );

            // Refresh sidebar
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);

        } catch (error) {
            if (this.cancelRequested && this.isAbortError(error)) {
                this.showCancellationMessage();
            } else {
                console.error('Error in coworking chat:', error);
                this.messageComponent.addErrorMessage(`Error: ${error.message}`);
            }
        } finally {
            this.setProcessing(false);
            await this.refreshSidebarSafely();
            this.resetRunState();
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
     * Hide coworking panel (unless debate panel is visible)
     */
    hideCoworkingPanel() {
        const coworkingPanel = document.getElementById('coworkingPanel');
        const panelDivider = document.getElementById('panelDivider');
        const chatContainer = document.querySelector('.chat-container');
        const debatePanel = document.getElementById('debatePanel');

        if (coworkingPanel) {
            coworkingPanel.style.display = 'none';
        }
        const debateVisible = debatePanel && debatePanel.style.display !== 'none';
        if (panelDivider && !debateVisible) {
            panelDivider.classList.remove('visible');
        }
        if (chatContainer && !debateVisible) {
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

        // Block switching out of an active image conversation
        if (this.isImageMode && this.imageModeConversationStarted && targetMode !== 'simple') {
            this.messageComponent.addSystemMessage(
                'Cannot switch to ' + targetMode + ' mode: this is an image generation conversation.'
            );
            const revertMode = wasMultiAgent ? 'multi-agent' : (wasCoworking ? 'coworking' : 'simple');
            this.modeSelector.setModeSilent(revertMode);
            return;
        }

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
                const revertMode = wasMultiAgent ? 'multi-agent' : (wasCoworking ? 'coworking' : 'simple');
                this.modeSelector.setModeSilent(revertMode);
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
            const revertMode = wasMultiAgent ? 'multi-agent' : (wasCoworking ? 'coworking' : 'simple');
            this.modeSelector.setModeSilent(revertMode);
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
        if (this.toolExecutionViewer) {
            this.toolExecutionViewer.clear();
        }
        setStorage('conversationId', conversationId);
        this.sidebar.setCurrentConversation(conversationId);

        // Reset image mode state before loading (will be re-applied if the conversation is an image one)
        this._resetImageModeState();

        // Clear and load the selected conversation
        this.messageComponent.clearMessages();
        await this.loadConversationHistory();

        console.log('Switched to conversation:', conversationId);
    }

    /**
     * Create a new conversation
     */
    /**
     * Reset image mode toggle to unchecked, enabled state (for new/text conversations).
     */
    _resetImageModeState() {
        this.isImageMode = false;
        this.imageModeConversationStarted = false;
        const imageModeToggle = document.getElementById('imageModeToggle');
        if (imageModeToggle) {
            imageModeToggle.checked = false;
            imageModeToggle.disabled = false;
            imageModeToggle.title = '';
        }
        this.modelSelector.setImageMode(false);
        this.updateMultiAgentUIVisibility();
    }

    createNewConversation() {
        this.conversationId = generateUUID();
        this.messageComponent.setConversationId(this.conversationId);
        if (this.debateViewer) {
            this.debateViewer.setConversationId(this.conversationId);
            this.debateViewer.clear();
        }
        if (this.toolExecutionViewer) {
            this.toolExecutionViewer.clear();
        }
        setStorage('conversationId', this.conversationId);
        this.sidebar.setCurrentConversation(this.conversationId);
        this.messageComponent.clearMessages();

        // Re-enable image mode toggle for the new conversation
        this._resetImageModeState();

        console.log('Created new conversation:', this.conversationId);
    }

    /**
     * Set processing state
     * @param {boolean} processing - Whether processing
     */
    setProcessing(processing) {
        this.isProcessing = processing;
        this.sendBtn.disabled = false;
        this.sendBtn.textContent = processing ? 'Cancel' : 'Send';
        this.sendBtn.classList.toggle('cancel-button', processing);
        this.messageInput.disabled = processing;
    }

    beginRun(mode) {
        this.activeMode = mode;
        this.activeRunId = null;
        this.cancelRequested = false;
        this.cancellationMessageShown = false;
        this.activeAbortController = new AbortController();
    }

    resetRunState() {
        this.activeMode = null;
        this.activeRunId = null;
        this.activeAbortController = null;
        this.cancelRequested = false;
        this.cancellationMessageShown = false;
    }

    getStreamOptions() {
        return {
            signal: this.activeAbortController ? this.activeAbortController.signal : undefined,
            onRunStart: (runId) => {
                this.activeRunId = runId;
                if (this.cancelRequested && runId) {
                    this.apiClient.cancelRun(runId).catch((error) => {
                        console.warn('Failed to cancel active run:', error);
                    });
                }
            }
        };
    }

    async cancelActiveRun() {
        if (!this.isProcessing) return;

        this.cancelRequested = true;
        this.showCancellationMessage();

        if (this.activeRunId) {
            try {
                await this.apiClient.cancelRun(this.activeRunId);
            } catch (error) {
                console.warn('Failed to cancel active run:', error);
            }
        }

        if (this.activeAbortController) {
            this.activeAbortController.abort();
        }
    }

    showCancellationMessage(message = 'Current task was cancelled.') {
        if (this.cancellationMessageShown) return;
        this.cancellationMessageShown = true;
        this.messageComponent.addSystemMessage(message);
    }

    isAbortError(error) {
        return error && (
            error.name === 'AbortError' ||
            error.code === 20 ||
            String(error.message || '').toLowerCase().includes('abort')
        );
    }

    async refreshSidebarSafely() {
        try {
            await this.sidebar.loadConversations();
            this.sidebar.setCurrentConversation(this.conversationId);
        } catch (error) {
            console.warn('Failed to refresh sidebar:', error);
        }
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
