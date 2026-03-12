/**
 * Multi-Agent Configuration Panel
 * Allows selection of different models for each role (Moderator, Expert, Critic)
 * and configuration of debate parameters
 */

export class MultiAgentConfig {
    constructor(containerElement, apiClient) {
        this.container = containerElement;
        this.apiClient = apiClient;
        this.models = [];
        this.config = {
            moderator: null,
            expert: null,
            critic: null,
            maxIterations: 3,
            scoreThreshold: 80,
            thinking: {
                moderator: false,
                expert: false,
                critic: false
            }
        };
        this.isExpanded = false;
        this.onChangeCallback = null;

        // Load saved configuration
        this.loadSavedConfig();
    }

    /**
     * Load configuration from localStorage
     */
    loadSavedConfig() {
        const saved = localStorage.getItem('multiAgentConfig');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                this.config = { ...this.config, ...parsed };
            } catch (e) {
                console.warn('Failed to parse saved multi-agent config');
            }
        }
    }

    /**
     * Save configuration to localStorage
     */
    saveConfig() {
        localStorage.setItem('multiAgentConfig', JSON.stringify(this.config));
    }

    /**
     * Initialize the component
     */
    async initialize() {
        try {
            this.models = await this.apiClient.getModels();
            this.sanitizeConfig();
            this.render();
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize multi-agent config:', error);
            this.renderError();
        }
    }

    /**
     * Render the configuration panel
     */
    render() {
        const modelOptions = this.generateModelOptions();

        this.container.innerHTML = `
            <div class="multi-agent-config ${this.isExpanded ? 'expanded' : ''}">
                <div class="config-header" title="Click to ${this.isExpanded ? 'collapse' : 'expand'}">
                    <span class="config-title">Multi-Agent Configuration</span>
                    <span class="config-toggle">${this.isExpanded ? '&#x25B2;' : '&#x25BC;'}</span>
                </div>
                <div class="config-body">
                    <div class="config-section">
                        <h4>Role Models</h4>
                        <div class="role-selectors">
                            <div class="role-selector">
                                <div class="role-header">
                                    <label for="moderator-model">
                                        <span class="role-icon" title="Moderator: Assesses complexity, guides debate, synthesizes answer">M</span>
                                        Moderator
                                    </label>
                                    <div class="thinking-toggle" data-role="moderator">
                                        <label class="toggle-switch">
                                            <input type="checkbox" data-thinking-role="moderator">
                                            <span class="toggle-slider"></span>
                                        </label>
                                        <span class="toggle-label">Thinking</span>
                                    </div>
                                </div>
                                <select id="moderator-model" data-role="moderator">
                                    ${modelOptions}
                                </select>
                            </div>
                            <div class="role-selector">
                                <div class="role-header">
                                    <label for="expert-model">
                                        <span class="role-icon" title="Expert: Generates professional answers">E</span>
                                        Expert
                                    </label>
                                    <div class="thinking-toggle" data-role="expert">
                                        <label class="toggle-switch">
                                            <input type="checkbox" data-thinking-role="expert">
                                            <span class="toggle-slider"></span>
                                        </label>
                                        <span class="toggle-label">Thinking</span>
                                    </div>
                                </div>
                                <select id="expert-model" data-role="expert">
                                    ${modelOptions}
                                </select>
                            </div>
                            <div class="role-selector">
                                <div class="role-header">
                                    <label for="critic-model">
                                        <span class="role-icon" title="Critic: Reviews and provides feedback">C</span>
                                        Critic
                                    </label>
                                    <div class="thinking-toggle" data-role="critic">
                                        <label class="toggle-switch">
                                            <input type="checkbox" data-thinking-role="critic">
                                            <span class="toggle-slider"></span>
                                        </label>
                                        <span class="toggle-label">Thinking</span>
                                    </div>
                                </div>
                                <select id="critic-model" data-role="critic">
                                    ${modelOptions}
                                </select>
                            </div>
                        </div>
                    </div>
                    <div class="config-section">
                        <h4>Debate Settings</h4>
                        <div class="setting-row">
                            <label for="max-iterations">
                                Max Iterations
                                <span class="setting-value">${this.config.maxIterations}</span>
                            </label>
                            <input
                                type="range"
                                id="max-iterations"
                                min="1"
                                max="10"
                                value="${this.config.maxIterations}"
                            />
                        </div>
                        <div class="setting-row">
                            <label for="score-threshold">
                                Score Threshold
                                <span class="setting-value">${this.config.scoreThreshold}</span>
                            </label>
                            <input
                                type="range"
                                id="score-threshold"
                                min="50"
                                max="100"
                                step="5"
                                value="${this.config.scoreThreshold}"
                            />
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Set saved values
        this.setSelectValue('moderator-model', this.config.moderator);
        this.setSelectValue('expert-model', this.config.expert);
        this.setSelectValue('critic-model', this.config.critic);

        // Sync internal state with the actual DOM selection after invalid saved values
        // have been discarded or when the browser auto-selects the first option.
        this.syncConfigFromSelects();

        // Update thinking toggle states based on selected models
        this.updateThinkingToggleState('moderator');
        this.updateThinkingToggleState('expert');
        this.updateThinkingToggleState('critic');
    }

    /**
     * Generate model options HTML grouped by provider
     */
    generateModelOptions() {
        const grouped = {};
        this.models.forEach(model => {
            const provider = model.provider_name;
            if (!grouped[provider]) {
                grouped[provider] = [];
            }
            grouped[provider].push(model);
        });

        let html = '';
        Object.entries(grouped).forEach(([provider, models]) => {
            html += `<optgroup label="${provider}">`;
            models.forEach(model => {
                html += `<option value="${model.model_id}" title="${model.description}">${model.model_name}</option>`;
            });
            html += '</optgroup>';
        });

        return html;
    }

    /**
     * Remove saved model IDs that are no longer available.
     */
    sanitizeConfig() {
        const availableModelIds = new Set(this.models.map(model => model.model_id));
        let changed = false;

        ['moderator', 'expert', 'critic'].forEach(role => {
            const modelId = this.config[role];
            if (modelId && !availableModelIds.has(modelId)) {
                this.config[role] = null;
                this.config.thinking[role] = false;
                changed = true;
            }
        });

        if (changed) {
            this.saveConfig();
        }
    }

    /**
     * Sync internal role selections from the current DOM state.
     */
    syncConfigFromSelects() {
        ['moderator', 'expert', 'critic'].forEach(role => {
            const select = this.container.querySelector(`select[data-role="${role}"]`);
            this.config[role] = select && select.value ? select.value : null;
        });
        this.saveConfig();
    }

    /**
     * Set select element value
     */
    setSelectValue(selectId, value) {
        const select = this.container.querySelector(`#${selectId}`);
        if (select && value) {
            const option = select.querySelector(`option[value="${value}"]`);
            if (option) {
                select.value = value;
            }
        }
    }

    /**
     * Update thinking toggle state based on selected model capabilities
     */
    updateThinkingToggleState(role) {
        const selectElement = this.container.querySelector(`select[data-role="${role}"]`);
        const modelId = selectElement ? selectElement.value : null;
        const modelInfo = modelId ? this.models.find(m => m.model_id === modelId) : null;

        const toggleContainer = this.container.querySelector(`.thinking-toggle[data-role="${role}"]`);
        const toggleInput = this.container.querySelector(`[data-thinking-role="${role}"]`);

        if (!toggleContainer || !toggleInput) return;

        if (!modelInfo) {
            // No model selected
            toggleContainer.classList.add('disabled');
            toggleInput.disabled = true;
            toggleInput.checked = false;
            this.config.thinking[role] = false;
            return;
        }

        const supportsThinking = modelInfo.supports_thinking || false;
        const thinkingLocked = modelInfo.thinking_locked || false;

        if (supportsThinking) {
            toggleContainer.classList.remove('disabled');

            if (thinkingLocked) {
                // Always on, cannot toggle
                toggleInput.disabled = true;
                toggleInput.checked = true;
                this.config.thinking[role] = true;
            } else {
                // Can toggle - check saved preference or default to true
                toggleInput.disabled = false;
                const savedKey = `thinking_${role}_${modelId}`;
                const saved = localStorage.getItem(savedKey);
                if (saved !== null) {
                    this.config.thinking[role] = saved === 'true';
                } else {
                    this.config.thinking[role] = true; // Default ON for thinking models
                }
                toggleInput.checked = this.config.thinking[role];
            }
        } else {
            // Model doesn't support thinking
            toggleContainer.classList.add('disabled');
            toggleInput.disabled = true;
            toggleInput.checked = false;
            this.config.thinking[role] = false;
        }
    }

    /**
     * Render error state
     */
    renderError() {
        this.container.innerHTML = `
            <div class="multi-agent-config error">
                <p>Failed to load configuration options</p>
            </div>
        `;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Toggle expand/collapse
        const header = this.container.querySelector('.config-header');
        if (header) {
            header.addEventListener('click', () => {
                this.isExpanded = !this.isExpanded;
                this.container.querySelector('.multi-agent-config').classList.toggle('expanded', this.isExpanded);
                this.container.querySelector('.config-toggle').innerHTML = this.isExpanded ? '&#x25B2;' : '&#x25BC;';
            });
        }

        // Role model selectors
        const roleSelects = this.container.querySelectorAll('select[data-role]');
        roleSelects.forEach(select => {
            select.addEventListener('change', (e) => {
                const role = e.target.dataset.role;
                this.config[role] = e.target.value;
                this.updateThinkingToggleState(role); // Update thinking toggle state
                this.saveConfig();
                this.triggerChange();
            });
        });

        // Thinking toggle events
        const thinkingToggles = this.container.querySelectorAll('[data-thinking-role]');
        thinkingToggles.forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const role = e.target.dataset.thinkingRole;
                this.config.thinking[role] = e.target.checked;

                // Save per-model preference
                const modelSelect = this.container.querySelector(`select[data-role="${role}"]`);
                const modelId = modelSelect ? modelSelect.value : null;
                if (modelId) {
                    localStorage.setItem(`thinking_${role}_${modelId}`, e.target.checked);
                }

                this.saveConfig();
                this.triggerChange();
            });
        });

        // Max iterations slider
        const maxIterations = this.container.querySelector('#max-iterations');
        if (maxIterations) {
            maxIterations.addEventListener('input', (e) => {
                this.config.maxIterations = parseInt(e.target.value);
                this.container.querySelector('label[for="max-iterations"] .setting-value').textContent = this.config.maxIterations;
                this.saveConfig();
                this.triggerChange();
            });
        }

        // Score threshold slider
        const scoreThreshold = this.container.querySelector('#score-threshold');
        if (scoreThreshold) {
            scoreThreshold.addEventListener('input', (e) => {
                this.config.scoreThreshold = parseInt(e.target.value);
                this.container.querySelector('label[for="score-threshold"] .setting-value').textContent = this.config.scoreThreshold;
                this.saveConfig();
                this.triggerChange();
            });
        }
    }

    /**
     * Trigger change callback
     */
    triggerChange() {
        if (this.onChangeCallback) {
            this.onChangeCallback(this.getConfig());
        }
    }

    /**
     * Get current configuration
     * @returns {Object} Configuration object
     */
    getConfig() {
        const getRoleModel = (role) => {
            const select = this.container.querySelector(`select[data-role="${role}"]`);
            if (select && select.value) {
                return select.value;
            }
            return this.config[role] || this.getDefaultModel();
        };

        const moderatorModel = getRoleModel('moderator');
        const expertModel = getRoleModel('expert');
        const criticModel = getRoleModel('critic');

        return {
            models: {
                moderator: moderatorModel,
                expert: expertModel,
                critic: criticModel
            },
            maxIterations: this.config.maxIterations,
            scoreThreshold: this.config.scoreThreshold,
            thinking: {
                moderator: moderatorModel ? (this.config.thinking.moderator || false) : false,
                expert: expertModel ? (this.config.thinking.expert || false) : false,
                critic: criticModel ? (this.config.thinking.critic || false) : false
            }
        };
    }

    /**
     * Get default model ID
     */
    getDefaultModel() {
        return this.models.length > 0 ? this.models[0].model_id : null;
    }

    /**
     * Register callback for config changes
     * @param {Function} callback - Callback function(config)
     */
    onChange(callback) {
        this.onChangeCallback = callback;
    }

    /**
     * Show the configuration panel
     */
    show() {
        this.container.style.display = 'block';
    }

    /**
     * Hide the configuration panel
     */
    hide() {
        this.container.style.display = 'none';
    }

    /**
     * Expand the panel
     */
    expand() {
        this.isExpanded = true;
        const panel = this.container.querySelector('.multi-agent-config');
        const toggle = this.container.querySelector('.config-toggle');
        if (panel) panel.classList.add('expanded');
        if (toggle) toggle.innerHTML = '&#x25B2;';
    }

    /**
     * Collapse the panel
     */
    collapse() {
        this.isExpanded = false;
        const panel = this.container.querySelector('.multi-agent-config');
        const toggle = this.container.querySelector('.config-toggle');
        if (panel) panel.classList.remove('expanded');
        if (toggle) toggle.innerHTML = '&#x25BC;';
    }
}
