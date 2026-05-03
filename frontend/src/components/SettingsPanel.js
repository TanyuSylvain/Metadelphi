/**
 * SettingsPanel Component
 * Slide-out panel for configuring provider API keys and base URLs
 */

export class SettingsPanel {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.panel = null;
        this.isOpen = false;
        this.hasChanges = false;
        this.providerData = {};
        this._onKeyDown = this._onKeyDown.bind(this);
    }

    async open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this.hasChanges = false;

        // Create panel DOM
        this.panel = document.createElement('div');
        this.panel.className = 'settings-panel';
        this.panel.innerHTML = `
            <div class="settings-header">
                <h2>Provider Settings</h2>
            </div>
            <div class="settings-body">
                <div class="settings-loading">Loading settings...</div>
            </div>
            <div class="settings-footer">
                <div class="settings-status" id="settingsStatus"></div>
                <div class="settings-actions">
                    <button class="btn-settings-cancel" id="settingsCancelBtn">Cancel</button>
                    <button class="btn-settings-save" id="settingsSaveBtn">Save</button>
                </div>
            </div>
        `;
        document.body.appendChild(this.panel);

        // Trigger slide-in animation
        requestAnimationFrame(() => {
            this.panel.classList.add('open');
        });

        // Bind events
        document.addEventListener('keydown', this._onKeyDown);
        this.panel.querySelector('#settingsCancelBtn').addEventListener('click', () => this.close());
        this.panel.querySelector('#settingsSaveBtn').addEventListener('click', () => this.save());

        // Fetch and render
        try {
            const data = await this.apiClient.getProviderSettings();
            this.providerData = data.providers;
            this._renderProviders();
        } catch (error) {
            this.panel.querySelector('.settings-body').innerHTML =
                `<div class="settings-error">Failed to load settings: ${error.message}</div>`;
        }
    }

    close() {
        if (!this.isOpen) return;

        if (this.hasChanges) {
            if (!confirm('Discard changes?')) return;
        }

        this.panel.classList.remove('open');
        document.removeEventListener('keydown', this._onKeyDown);

        setTimeout(() => {
            if (this.panel && this.panel.parentNode) {
                this.panel.parentNode.removeChild(this.panel);
            }
            this.panel = null;
            this.isOpen = false;
        }, 300);
    }

    _onKeyDown(e) {
        if (e.key === 'Escape') {
            this.close();
        }
    }

    _renderProviders() {
        const body = this.panel.querySelector('.settings-body');
        let html = '';

        // Derive provider list from API response data, sorted by category
        const providerIds = Object.keys(this.providerData);
        const llmIds = providerIds.filter(id => this.providerData[id].category !== 'tool');
        const toolIds = providerIds.filter(id => this.providerData[id].category === 'tool');

        for (const id of llmIds) {
            html += this._renderProviderSection(id);
        }

        if (toolIds.length > 0) {
            html += `<div class="settings-separator">Tool API Keys</div>`;
            for (const id of toolIds) {
                html += this._renderProviderSection(id);
            }
        }

        body.innerHTML = html;

        // Bind input change tracking
        body.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', () => {
                this.hasChanges = true;
            });
        });

        // Bind visibility toggles
        body.querySelectorAll('.btn-toggle-visibility').forEach(btn => {
            btn.addEventListener('click', () => {
                const input = btn.parentElement.querySelector('input');
                if (input.type === 'password') {
                    input.type = 'text';
                    btn.textContent = '🙈';
                } else {
                    input.type = 'password';
                    btn.textContent = '👁';
                }
            });
        });

        // Bind test buttons
        body.querySelectorAll('.btn-test-connection').forEach(btn => {
            btn.addEventListener('click', () => this._testProvider(btn));
        });
    }

    _renderProviderSection(providerId) {
        const data = this.providerData[providerId] || {};
        const maskedKey = data.api_key_masked || '';
        const baseUrl = data.base_url || '';

        let html = `
            <div class="provider-section" data-provider="${providerId}">
                <div class="provider-section-title">${this._escapeAttr(data.display_name || providerId)}</div>
                <a class="provider-link" href="${data.console_url}" target="_blank" rel="noopener">Get your API key &nearr;</a>
                <div class="provider-field">
                    <label>API Key</label>
                    <div class="field-row">
                        <input type="password"
                               class="provider-key-input"
                               placeholder="Enter API key"
                               value="${this._escapeAttr(maskedKey)}"
                               autocomplete="off"
                               spellcheck="false">
                        <button class="btn-toggle-visibility" title="Show/hide key">👁</button>
                    </div>
                </div>`;

        if (data.has_base_url) {
            html += `
                <div class="provider-field">
                    <label>Base URL</label>
                    <div class="field-row">
                        <input type="text"
                               class="provider-url-input"
                               placeholder="${this._escapeAttr(data.default_base_url || '')}"
                               value="${this._escapeAttr(baseUrl)}"
                               spellcheck="false">
                    </div>
                </div>`;
        }

        html += `
                <div class="provider-test-row">
                    <button class="btn-test-connection" data-provider="${providerId}">
                        Test Connection
                    </button>
                    <span class="test-result" data-provider="${providerId}"></span>
                </div>
            </div>`;

        return html;
    }

    async _testProvider(btn) {
        const providerId = btn.dataset.provider;
        const resultSpan = this.panel.querySelector(`.test-result[data-provider="${providerId}"]`);
        const data = this.providerData[providerId] || {};

        // Check for unsaved changes
        const section = this.panel.querySelector(`.provider-section[data-provider="${providerId}"]`);
        const keyInput = section.querySelector('.provider-key-input');
        const urlInput = section.querySelector('.provider-url-input');
        const keyVal = keyInput.value.trim();
        const urlVal = urlInput ? urlInput.value.trim() : null;

        const keyChanged = keyVal && keyVal !== (data.api_key_masked || '');
        const urlChanged = urlVal !== null && urlVal !== (data.base_url || '');

        if (keyChanged || urlChanged) {
            resultSpan.className = 'test-result error';
            resultSpan.textContent = 'Save changes first to test with new values';
            return;
        }

        // Check if key is set
        if (!data.api_key_set && !keyVal) {
            resultSpan.className = 'test-result error';
            resultSpan.textContent = 'Enter an API key first';
            return;
        }

        // Run test against currently persisted values
        btn.disabled = true;
        btn.textContent = 'Testing...';
        resultSpan.className = 'test-result';
        resultSpan.textContent = '';

        try {
            const result = await this.apiClient.testProvider(providerId);
            if (result.success) {
                resultSpan.className = 'test-result success';
                resultSpan.textContent = `Connected (${result.latency_ms}ms)`;
            } else {
                resultSpan.className = 'test-result error';
                resultSpan.textContent = result.message;
            }
        } catch (error) {
            resultSpan.className = 'test-result error';
            resultSpan.textContent = error.message;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Test Connection';
        }
    }

    async save() {
        const statusEl = this.panel.querySelector('#settingsStatus');
        const updates = {};

        for (const [providerId, data] of Object.entries(this.providerData)) {
            const section = this.panel.querySelector(`.provider-section[data-provider="${providerId}"]`);
            if (!section) continue;

            const keyInput = section.querySelector('.provider-key-input');
            const urlInput = section.querySelector('.provider-url-input');

            const providerUpdates = {};
            const keyVal = keyInput.value.trim();
            const urlVal = urlInput ? urlInput.value.trim() : null;

            // Only include changed values
            if (keyVal && keyVal !== (data.api_key_masked || '')) {
                providerUpdates.api_key = keyVal;
            }

            if (data.has_base_url && urlVal !== null && urlVal !== (data.base_url || '')) {
                providerUpdates.base_url = urlVal;
            }

            if (Object.keys(providerUpdates).length > 0) {
                updates[providerId] = providerUpdates;
            }
        }

        if (Object.keys(updates).length === 0) {
            statusEl.className = 'settings-status info';
            statusEl.textContent = 'No changes to save';
            return;
        }

        try {
            const result = await this.apiClient.updateProviderSettings(updates);
            statusEl.className = 'settings-status success';
            statusEl.textContent = 'Settings saved successfully';
            this.hasChanges = false;

            // Dispatch event so app can refresh model list
            window.dispatchEvent(new CustomEvent('settings-updated'));

            // Close after a short delay
            setTimeout(() => this.close(), 1500);
        } catch (error) {
            statusEl.className = 'settings-status error';
            statusEl.textContent = `Save failed: ${error.message}`;
        }
    }

    _escapeAttr(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}
