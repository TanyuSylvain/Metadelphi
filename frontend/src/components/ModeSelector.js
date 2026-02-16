/**
 * Mode Selector Component
 * Toggles between Simple (single-agent) and Multi-Agent Debate modes
 */

export class ModeSelector {
    constructor(containerElement) {
        this.container = containerElement;
        this.currentMode = 'simple';  // 'simple' | 'multi-agent' | 'coworking'
        this.onChangeCallback = null;

        // Load saved preference
        const savedMode = localStorage.getItem('chatMode');
        if (savedMode === 'simple' || savedMode === 'multi-agent' || savedMode === 'coworking') {
            this.currentMode = savedMode;
        }
    }

    /**
     * Initialize the mode selector
     */
    initialize() {
        this.render();
        this.setupEventListeners();
    }

    /**
     * Render the mode selector UI
     */
    render() {
        this.container.innerHTML = `
            <div class="mode-selector">
                <button
                    class="mode-btn ${this.currentMode === 'simple' ? 'active' : ''}"
                    data-mode="simple"
                    title="Single agent answers directly"
                >
                    <span class="mode-icon">&#x1F916;</span>
                    <span class="mode-label">Simple</span>
                </button>
                <button
                    class="mode-btn ${this.currentMode === 'multi-agent' ? 'active' : ''}"
                    data-mode="multi-agent"
                    title="Moderator-Expert-Critic debate for complex questions"
                >
                    <span class="mode-icon">&#x1F465;</span>
                    <span class="mode-label">Debate</span>
                </button>
                <button
                    class="mode-btn ${this.currentMode === 'coworking' ? 'active' : ''}"
                    data-mode="coworking"
                    title="Agent with tools for file operations, code execution, and document generation"
                >
                    <span class="mode-icon">&#x1F6E0;</span>
                    <span class="mode-label">Coworking</span>
                </button>
            </div>
        `;
    }

    /**
     * Set up event listeners for mode buttons
     */
    setupEventListeners() {
        const buttons = this.container.querySelectorAll('.mode-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                this.setMode(mode);
            });
        });
    }

    /**
     * Set the current mode
     * @param {string} mode - 'simple' or 'multi-agent'
     */
    setMode(mode) {
        if (mode !== 'simple' && mode !== 'multi-agent' && mode !== 'coworking') {
            return;
        }

        this.currentMode = mode;
        localStorage.setItem('chatMode', mode);

        // Update UI
        const buttons = this.container.querySelectorAll('.mode-btn');
        buttons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Trigger callback
        if (this.onChangeCallback) {
            this.onChangeCallback(mode);
        }
    }

    /**
     * Get the current mode
     * @returns {string} Current mode ('simple' or 'multi-agent')
     */
    getMode() {
        return this.currentMode;
    }

    /**
     * Check if multi-agent mode is active
     * @returns {boolean} True if multi-agent mode
     */
    isMultiAgentMode() {
        return this.currentMode === 'multi-agent';
    }

    /**
     * Check if coworking mode is active
     * @returns {boolean} True if coworking mode
     */
    isCoworkingMode() {
        return this.currentMode === 'coworking';
    }

    /**
     * Set mode silently without triggering the onChange callback.
     * Used to revert the UI when a mode switch fails.
     * @param {string} mode - 'simple', 'multi-agent', or 'coworking'
     */
    setModeSilent(mode) {
        if (mode !== 'simple' && mode !== 'multi-agent' && mode !== 'coworking') {
            return;
        }

        this.currentMode = mode;
        localStorage.setItem('chatMode', mode);

        // Update UI
        const buttons = this.container.querySelectorAll('.mode-btn');
        buttons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
    }

    /**
     * Register callback for mode changes
     * @param {Function} callback - Callback function(mode)
     */
    onChange(callback) {
        this.onChangeCallback = callback;
    }
}
