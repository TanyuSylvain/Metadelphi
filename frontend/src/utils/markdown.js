/**
 * Markdown Renderer
 * Handles rendering markdown content with syntax highlighting and math equations
 */

// Configure the global marked instance once. marked.use() mutates the global
// object, so calling it repeatedly stacks renderers and can break rendering.
function configureMarked() {
    if (typeof marked === 'undefined' || (marked).__metadelphiConfigured) {
        return;
    }

    marked.use({
        renderer: {
            code(codeOrToken, language) {
                let code, lang;
                if (typeof codeOrToken === 'object' && codeOrToken !== null) {
                    code = codeOrToken.text;
                    lang = codeOrToken.lang || '';
                } else {
                    code = codeOrToken;
                    lang = language || '';
                }

                // Defensive: marked can pass tokens with missing text in some
                // versions or malformed inputs. Treat missing/invalid code as
                // an empty block instead of letting highlight.js crash on it.
                if (typeof code !== 'string') {
                    code = '';
                }
                if (typeof lang !== 'string') {
                    lang = '';
                }

                const escapedCode = code.replace(/&/g, '&amp;')
                                        .replace(/</g, '&lt;')
                                        .replace(/>/g, '&gt;');

                if (typeof hljs !== 'undefined') {
                    if (lang && hljs.getLanguage(lang)) {
                        return `<pre><code class="hljs language-${lang}">${hljs.highlight(code, { language: lang }).value}</code></pre>`;
                    }
                    return `<pre><code class="hljs">${hljs.highlightAuto(code).value}</code></pre>`;
                }
                return `<pre><code>${escapedCode}</code></pre>`;
            }
        }
    });

    marked.__metadelphiConfigured = true;
}

export class MarkdownRenderer {
    constructor() {
        // Check if marked.js is available
        if (typeof marked === 'undefined') {
            console.warn('marked.js not loaded, markdown rendering will be limited');
            this.markedAvailable = false;
        } else {
            this.markedAvailable = true;
            configureMarked();
        }

        // Check if KaTeX is available
        this.katexAvailable = typeof katex !== 'undefined';
    }

    /**
     * Render markdown to HTML
     * @param {string} markdown - Markdown text
     * @returns {string} HTML string
     */
    render(markdown) {
        // Guard against non-string inputs (undefined, null, objects, numbers).
        // marked.parse() expects a string; passing anything else causes
        // "undefined is not an object (evaluating '...replace')" errors.
        if (typeof markdown !== 'string') {
            if (markdown == null) return '';
            markdown = String(markdown);
        }
        if (markdown.length === 0) return '';

        // Process math BEFORE markdown parsing to protect math content
        let mathPlaceholders = null;
        if (this.katexAvailable) {
            const result = this.preProcessMath(markdown);
            markdown = result.text;
            mathPlaceholders = result.placeholders;
        }

        let html;
        if (this.markedAvailable) {
            try {
                html = marked.parse(markdown);
            } catch (error) {
                console.error('Error parsing markdown:', error);
                html = this.escapeHtml(markdown);
            }
        } else {
            // Fallback: basic markdown rendering
            html = this.basicMarkdownRender(markdown);
        }

        // Restore math placeholders
        if (mathPlaceholders) {
            html = this.restoreMathPlaceholders(html, mathPlaceholders);
        }

        return html;
    }

    /**
     * Pre-process math by replacing math delimiters with protected placeholders
     * This prevents marked.js from processing HTML inside math expressions
     * @param {string} text - Markdown text
     * @returns {string} Object with processed text and placeholders
     */
    preProcessMath(text) {
        if (!this.katexAvailable) return { text, placeholders: null };

        if (typeof text !== 'string') {
            text = String(text);
        }

        // Normalize LaTeX delimiters: convert \[ \] to $$ $$ and \( \) to $ $
        text = text.replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$');
        text = text.replace(/\\\((.*?)\\\)/g, '$$$1$$');

        const displayMath = [];
        const inlineMath = [];

        // Use unique delimiters that marked.js won't touch
        // Using a format that won't be interpreted as markdown
        const startDelim = '\x00KATEX';
        const endDelim = 'KATEX\x00';

        // Protect display math $$...$$ first
        text = text.replace(/\$\$([\s\S]*?)\$\$/g, (match, math) => {
            // Decode HTML entities
            math = this.decodeHtmlEntities(math);
            try {
                const rendered = katex.renderToString(math.trim(), {
                    displayMode: true,
                    throwOnError: false
                });
                const placeholder = `${startDelim}DISPLAY${displayMath.length}${endDelim}`;
                displayMath.push(rendered);
                return placeholder;
            } catch (e) {
                return match;
            }
        });

        // Protect inline math $...$ (but not already processed)
        text = text.replace(/\$([^$\n]+?)\$/g, (match, math) => {
            // Decode HTML entities
            math = this.decodeHtmlEntities(math);
            try {
                const rendered = katex.renderToString(math.trim(), {
                    displayMode: false,
                    throwOnError: false
                });
                const placeholder = `${startDelim}INLINE${inlineMath.length}${endDelim}`;
                inlineMath.push(rendered);
                return placeholder;
            } catch (e) {
                return match;
            }
        });

        return {
            text,
            placeholders: { display: displayMath, inline: inlineMath, start: startDelim, end: endDelim }
        };
    }

    /**
     * Restore math placeholders with rendered KaTeX HTML
     * @param {string} html - HTML with placeholders
     * @param {object} placeholders - Object containing display and inline math arrays
     * @returns {string} HTML with math restored
     */
    restoreMathPlaceholders(html, placeholders) {
        const { display, inline, start, end } = placeholders;

        // Restore display math placeholders
        display.forEach((rendered, i) => {
            html = html.replace(`${start}DISPLAY${i}${end}`, rendered);
        });

        // Restore inline math placeholders
        inline.forEach((rendered, i) => {
            html = html.replace(`${start}INLINE${i}${end}`, rendered);
        });

        return html;
    }

    /**
     * Basic markdown rendering (fallback)
     * @param {string} text - Text to render
     * @returns {string} HTML string
     */
    basicMarkdownRender(text) {
        let html = this.escapeHtml(text);

        // Code blocks
        html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code>${code.trim()}</code></pre>`;
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

        // Line breaks
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Decode HTML entities (e.g., &#39; -> ')
     * @param {string} text - Text with HTML entities
     * @returns {string} Decoded text
     */
    decodeHtmlEntities(text) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = text;
        return textarea.value;
    }

    /**
     * Check if KaTeX is available
     * @returns {boolean} KaTeX availability
     */
    isKatexAvailable() {
        return this.katexAvailable;
    }

    /**
     * Render code block with language
     * @param {string} code - Code content
     * @param {string} language - Programming language
     * @returns {string} HTML string
     */
    renderCodeBlock(code, language = '') {
        const escapedCode = this.escapeHtml(code);
        const langClass = language ? ` class="language-${language}"` : '';
        return `<pre><code${langClass}>${escapedCode}</code></pre>`;
    }

    /**
     * Render table from markdown
     * @param {string} markdown - Table markdown
     * @returns {string} HTML table
     */
    renderTable(markdown) {
        if (typeof markdown !== 'string') {
            if (markdown == null) return '';
            markdown = String(markdown);
        }
        markdown = markdown.trim();
        if (markdown.length === 0) return '';

        if (this.markedAvailable) {
            try {
                return marked.parse(markdown);
            } catch (error) {
                console.error('Error parsing table markdown:', error);
                return this.escapeHtml(markdown);
            }
        }

        // Basic table parsing
        const lines = markdown.trim().split('\n');
        if (lines.length < 2) return markdown;

        let html = '<table>';

        // Header
        const headers = lines[0].split('|').filter(h => h.trim());
        html += '<thead><tr>';
        headers.forEach(header => {
            html += `<th>${this.escapeHtml(header.trim())}</th>`;
        });
        html += '</tr></thead>';

        // Body
        html += '<tbody>';
        for (let i = 2; i < lines.length; i++) {
            const cells = lines[i].split('|').filter(c => c.trim());
            html += '<tr>';
            cells.forEach(cell => {
                html += `<td>${this.escapeHtml(cell.trim())}</td>`;
            });
            html += '</tr>';
        }
        html += '</tbody></table>';

        return html;
    }

    /**
     * Strip markdown formatting
     * @param {string} markdown - Markdown text
     * @returns {string} Plain text
     */
    stripMarkdown(markdown) {
        if (!markdown) return '';

        let text = markdown;

        // Remove code blocks
        text = text.replace(/```[\s\S]*?```/g, '');

        // Remove inline code
        text = text.replace(/`[^`]+`/g, '');

        // Remove bold/italic
        text = text.replace(/\*\*([^*]+)\*\*/g, '$1');
        text = text.replace(/\*([^*]+)\*/g, '$1');

        // Remove links
        text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

        // Remove headers
        text = text.replace(/^#+\s+/gm, '');

        return text.trim();
    }
}
