/**
 * Coworking Configuration Component
 * Provides workspace path input for the coworking agent mode
 */

export class CoworkingConfig {
    constructor(containerElement) {
        this.container = containerElement;
        this.workspacePath = localStorage.getItem('coworkingWorkspacePath') || '';
    }

    initialize() {
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="coworking-config">
                <div class="coworking-config-row">
                    <label for="workspacePathInput" class="workspace-label">Workspace:</label>
                    <input
                        type="text"
                        id="workspacePathInput"
                        class="workspace-input"
                        placeholder="/path/to/workspace"
                        value="${this.escapeHtml(this.workspacePath)}"
                    />
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const input = this.container.querySelector('#workspacePathInput');
        if (input) {
            input.addEventListener('change', (e) => {
                this.workspacePath = e.target.value.trim();
                localStorage.setItem('coworkingWorkspacePath', this.workspacePath);
            });
            input.addEventListener('input', (e) => {
                this.workspacePath = e.target.value.trim();
            });
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
