/**
 * Coworking Configuration Component
 * Provides workspace path selection via native folder picker for the coworking agent mode
 */

export class CoworkingConfig {
    constructor(containerElement, apiClient) {
        this.container = containerElement;
        this.apiClient = apiClient;
        this.workspacePath = localStorage.getItem('coworkingWorkspacePath') || '';
    }

    initialize() {
        this.render();
        this.setupEventListeners();
    }

    render() {
        const displayPath = this.workspacePath || 'No workspace selected';
        const hasPath = !!this.workspacePath;
        this.container.innerHTML = `
            <div class="coworking-config">
                <div class="coworking-config-row">
                    <label class="workspace-label">Workspace:</label>
                    <span class="workspace-path-display ${hasPath ? '' : 'placeholder'}">${this.escapeHtml(displayPath)}</span>
                    <button class="workspace-browse-btn" id="workspaceBrowseBtn">Browse</button>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const browseBtn = this.container.querySelector('#workspaceBrowseBtn');
        if (browseBtn) {
            browseBtn.addEventListener('click', () => this.handleBrowse());
        }
    }

    async handleBrowse() {
        const browseBtn = this.container.querySelector('#workspaceBrowseBtn');
        if (browseBtn) {
            browseBtn.disabled = true;
            browseBtn.textContent = '...';
        }

        try {
            const path = await this.apiClient.selectWorkspace();
            if (path) {
                this.workspacePath = path;
                localStorage.setItem('coworkingWorkspacePath', this.workspacePath);
                this.render();
                this.setupEventListeners();
            }
        } catch (error) {
            console.error('Error selecting workspace:', error);
        } finally {
            if (browseBtn) {
                browseBtn.disabled = false;
                browseBtn.textContent = 'Browse';
            }
        }
    }

    getWorkspacePath() {
        return this.workspacePath;
    }

    show() {
        this.container.style.display = 'block';
    }

    hide() {
        this.container.style.display = 'none';
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
