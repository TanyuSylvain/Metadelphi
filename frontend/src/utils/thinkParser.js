/**
 * ThinkParser - Parses <think>...</think> blocks from LLM responses
 *
 * Stateless parser that re-parses the full accumulated text on every call,
 * making it self-correcting during streaming.
 */
export class ThinkParser {
    /**
     * Parse text into segments of thinking and response content.
     * @param {string} text - The full accumulated text
     * @returns {{segments: Array<{type: string, content: string, complete?: boolean}>, responseOnly: string}}
     */
    static parse(text) {
        if (!text) {
            return { segments: [], responseOnly: '' };
        }

        const segments = [];
        let remaining = text;
        let responseOnly = '';

        while (remaining.length > 0) {
            const thinkStart = remaining.indexOf('<think>');

            if (thinkStart === -1) {
                // No more <think> tags - rest is response content
                if (remaining.length > 0) {
                    segments.push({ type: 'response', content: remaining });
                    responseOnly += remaining;
                }
                break;
            }

            // Add any response content before this <think> tag
            if (thinkStart > 0) {
                const before = remaining.substring(0, thinkStart);
                if (before.trim().length > 0 || responseOnly.length > 0) {
                    segments.push({ type: 'response', content: before });
                    responseOnly += before;
                }
            }

            // Find the closing </think> tag
            const afterOpen = remaining.substring(thinkStart + 7); // length of '<think>'
            const thinkEnd = afterOpen.indexOf('</think>');

            if (thinkEnd === -1) {
                // Incomplete thinking block (still streaming)
                const thinkContent = afterOpen;
                if (thinkContent.length > 0) {
                    segments.push({ type: 'thinking', content: thinkContent, complete: false });
                } else {
                    segments.push({ type: 'thinking', content: '', complete: false });
                }
                break;
            }

            // Complete thinking block
            const thinkContent = afterOpen.substring(0, thinkEnd);
            if (thinkContent.trim().length > 0) {
                segments.push({ type: 'thinking', content: thinkContent, complete: true });
            }
            // Skip empty thinking blocks

            remaining = afterOpen.substring(thinkEnd + 8); // length of '</think>'
        }

        return { segments, responseOnly };
    }

    /**
     * Strip all <think>...</think> blocks from text.
     * Used for copy button to get clean response text.
     * @param {string} text - Text possibly containing think blocks
     * @returns {string} Text with think blocks removed
     */
    static stripThinking(text) {
        if (!text) return '';
        // Remove complete <think>...</think> blocks
        let result = text.replace(/<think>[\s\S]*?<\/think>/g, '');
        // Remove any incomplete <think>... at the end (no closing tag)
        result = result.replace(/<think>[\s\S]*$/, '');
        return result.trim();
    }
}
