/**
 * Tool Execution Viewer Component
 * Displays coworking agent progress: plan, tool calls, and generated files
 */

import { SmartScroller } from '../utils/smartScroller.js';

export class ToolExecutionViewer {
    constructor(containerElement, apiClient) {
        this.container = containerElement;
        this.apiClient = apiClient;
        this.toolCalls = [];
        this.generatedFiles = [];
        this.deletedFiles = [];
        this.workspacePath = '';
        this.baseURL = 'http://localhost:8000';
        const scrollElement = containerElement.closest('.coworking-panel') || containerElement.parentElement;
        this.smartScroller = scrollElement ? new SmartScroller(scrollElement) : null;
    }

    initialize() {
        this.render();
    }

    clear() {
        this.toolCalls = [];
        this.generatedFiles = [];
        this.deletedFiles = [];
        this.smartScroller?.reset();
        this.render();
    }

    clearForNewMessage() {
        this.toolCalls = [];
        // Keep session-level file state across messages
        this.smartScroller?.reset();
        this.render();
    }

    setGeneratedFiles(files) {
        this.setFileState(files, this.deletedFiles);
    }

    setDeletedFiles(files) {
        this.setFileState(this.generatedFiles, files);
    }

    setFileState(generatedFiles = [], deletedFiles = []) {
        this.generatedFiles = generatedFiles.map(f => ({ path: f.path, size: f.size }));
        this.deletedFiles = deletedFiles.map(file =>
            typeof file === 'string' ? { path: file } : { path: file.path }
        );
        this.render();
    }

    setWorkspacePath(path) {
        this.workspacePath = path;
    }

    addToolStart(toolName, toolInput, round = null, toolCallId = null) {
        this.toolCalls.push({
            id: toolCallId,
            round,
            name: toolName,
            input: toolInput,
            output: null,
            success: null,
            status: 'running'
        });
        this.render();
        this.smartScroller?.scrollToBottomIfNeeded();
    }

    addToolResult(toolName, output, success, round = null, toolCallId = null) {
        let target = null;

        if (toolCallId) {
            target = this.toolCalls.find(tc => tc.id === toolCallId);
        }

        if (!target) {
            for (let i = this.toolCalls.length - 1; i >= 0; i--) {
                if (
                    this.toolCalls[i].name === toolName &&
                    this.toolCalls[i].status === 'running' &&
                    (round === null || this.toolCalls[i].round === round)
                ) {
                    target = this.toolCalls[i];
                    break;
                }
            }
        }

        if (target) {
            target.output = output;
            target.success = success;
            target.status = success ? 'done' : 'error';
        }

        this.render();
        this.smartScroller?.scrollToBottomIfNeeded();
    }

    addFileCreated(filePath, fileSize) {
        // Avoid duplicates
        const deletedIdx = this.deletedFiles.findIndex(f => f.path === filePath);
        if (deletedIdx >= 0) {
            this.deletedFiles.splice(deletedIdx, 1);
        }
        const existing = this.generatedFiles.find(f => f.path === filePath);
        if (existing) {
            existing.size = fileSize;
        } else {
            this.generatedFiles.push({ path: filePath, size: fileSize });
        }
        this.render();
    }

    addFileDeleted(filePath) {
        this.generatedFiles = this.generatedFiles.filter(f => f.path !== filePath);
        if (!this.deletedFiles.find(f => f.path === filePath)) {
            this.deletedFiles.push({ path: filePath });
        }
        this.render();
    }

    render() {
        let html = '';

        // Tool calls section
        if (this.toolCalls.length > 0) {
            html += '<div class="tool-section">';
            html += '<div class="tool-section-title">Tool Calls</div>';
            this.toolCalls.forEach((tc, idx) => {
                const statusIcon = tc.status === 'running' ? '<span class="tool-spinner"></span>' :
                                   tc.status === 'done' ? '&#x2705;' : '&#x274C;';
                const statusClass = tc.status;
                html += `<div class="tool-card ${statusClass}">
                    <div class="tool-card-header" data-tool-idx="${idx}">
                        <span class="tool-status-icon">${statusIcon}</span>
                        <span class="tool-name">${this.escapeHtml(tc.name)}</span>
                        <span class="tool-toggle">&#x25BC;</span>
                    </div>
                    <div class="tool-card-body" id="toolBody${idx}" style="display: none;">
                        <div class="tool-detail">
                            <div class="tool-detail-label">Input:</div>
                            ${this.renderToolInput(tc)}
                        </div>
                        ${tc.output !== null ? `
                        <div class="tool-detail">
                            <div class="tool-detail-label">Output:</div>
                            ${this.renderCodeBlock(tc.output, 'plaintext')}
                        </div>` : ''}
                    </div>
                </div>`;
            });
            html += '</div>';
        }

        // Generated files section
        if (this.generatedFiles.length > 0) {
            html += '<div class="tool-section">';
            html += '<div class="tool-section-title">Generated Files</div>';
            this.generatedFiles.forEach(file => {
                const sizeStr = this.formatSize(file.size);
                const downloadUrl = `${this.baseURL}/chat/coworking/files?workspace_path=${encodeURIComponent(this.workspacePath)}&file_path=${encodeURIComponent(file.path)}`;
                html += `<div class="file-item">
                    <span class="file-icon">&#x1F4C4;</span>
                    <span class="file-open-link" data-file-path="${this.escapeHtml(file.path)}">${this.escapeHtml(file.path)}</span>
                    <span class="file-size">(${sizeStr})</span>
                    <a class="file-download-btn" href="${downloadUrl}" target="_blank" title="Download">&#x2B07;</a>
                </div>`;
            });
            html += '</div>';
        }

        if (this.deletedFiles.length > 0) {
            html += '<div class="tool-section">';
            html += '<div class="tool-section-title">Deleted Files</div>';
            this.deletedFiles.forEach(file => {
                html += `<div class="file-item deleted">
                    <span class="file-icon">&#x1F5D1;</span>
                    <span class="file-deleted-path">${this.escapeHtml(file.path)}</span>
                </div>`;
            });
            html += '</div>';
        }

        if (!html) {
            html = '<div class="tool-empty">Waiting for agent activity...</div>';
        }

        this.container.innerHTML = html;
        this.setupToggleListeners();
        this.setupFileOpenListeners();
    }

    setupToggleListeners() {
        const headers = this.container.querySelectorAll('.tool-card-header');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const idx = header.dataset.toolIdx;
                const body = this.container.querySelector(`#toolBody${idx}`);
                const toggle = header.querySelector('.tool-toggle');
                if (body) {
                    const isHidden = body.style.display === 'none';
                    body.style.display = isHidden ? 'block' : 'none';
                    if (toggle) {
                        toggle.innerHTML = isHidden ? '&#x25B2;' : '&#x25BC;';
                    }
                }
            });
        });
    }

    setupFileOpenListeners() {
        const links = this.container.querySelectorAll('.file-open-link');
        links.forEach(link => {
            link.addEventListener('click', async () => {
                const filePath = link.dataset.filePath;
                if (!filePath || !this.workspacePath || !this.apiClient) return;
                try {
                    await this.apiClient.openFile(this.workspacePath, filePath);
                } catch (error) {
                    console.error('Failed to open file:', error);
                }
            });
        });
    }

    scrollToBottom() {
        const parent = this.container.closest('.coworking-panel') || this.container.parentElement;
        if (parent) {
            parent.scrollTop = parent.scrollHeight;
        }
    }

    formatToolInput(input) {
        if (typeof input === 'string') return input;
        try {
            return JSON.stringify(input, null, 2);
        } catch {
            return String(input);
        }
    }

    formatSize(bytes) {
        if (!bytes) return '0B';
        if (bytes < 1024) return `${bytes}B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
    }

    renderToolInput(tc) {
        const input = tc.input;
        if (tc.name === 'python_execute' && input && typeof input === 'object' && input.code) {
            return this.renderCodeBlock(input.code, 'python');
        }
        if (tc.name === 'bash_execute' && input && typeof input === 'object' && input.command) {
            return this.renderCodeBlock(input.command, 'bash');
        }
        return `<pre class="tool-detail-content">${this.escapeHtml(this.formatToolInput(input))}</pre>`;
    }

    renderCodeBlock(code, language) {
        if (!code) return '<pre class="tool-detail-content"><code></code></pre>';
        try {
            if (typeof hljs !== 'undefined' && language && language !== 'plaintext') {
                const highlighted = hljs.highlight(code, { language }).value;
                return `<pre class="tool-detail-content"><code class="hljs language-${language}">${highlighted}</code></pre>`;
            }
        } catch (e) {
            // fallback to escaped
        }
        return `<pre class="tool-detail-content"><code>${this.escapeHtml(code)}</code></pre>`;
    }

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }
}
