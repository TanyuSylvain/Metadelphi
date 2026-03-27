/**
 * SmartScroller - Auto-scroll that pauses when the user scrolls up
 * and resumes when they scroll back to the bottom.
 */

export class SmartScroller {
    constructor(element, { threshold = 30 } = {}) {
        this.element = element;
        this.threshold = threshold;
        this._userScrolledUp = false;

        // wheel/touchmove only fire from user interaction, never from
        // programmatic scrollTop changes — so we can use them directly
        // to detect "user scrolled away from bottom".
        this._onUserGesture = () => {
            if (!this._isAtBottom()) {
                this._userScrolledUp = true;
            }
        };

        // scroll event fires from both user and programmatic scrolls;
        // use it to detect when the user scrolls back to the bottom.
        this._onScroll = () => {
            if (this._isAtBottom()) {
                this._userScrolledUp = false;
            }
        };

        this.element.addEventListener('wheel', this._onUserGesture, { passive: true });
        this.element.addEventListener('touchmove', this._onUserGesture, { passive: true });
        this.element.addEventListener('scroll', this._onScroll, { passive: true });
    }

    _isAtBottom() {
        return (
            this.element.scrollHeight - this.element.scrollTop - this.element.clientHeight <
            this.threshold
        );
    }

    /**
     * Scroll to bottom only if the user hasn't scrolled up.
     */
    scrollToBottomIfNeeded() {
        if (!this._userScrolledUp) {
            this.element.scrollTop = this.element.scrollHeight;
        }
    }

    /**
     * Force scroll to bottom regardless of user scroll state.
     */
    scrollToBottom() {
        this.element.scrollTop = this.element.scrollHeight;
    }

    /**
     * Reset to auto-scroll mode (e.g., when a new user message is sent).
     */
    reset() {
        this._userScrolledUp = false;
    }

    /**
     * Clean up event listeners.
     */
    destroy() {
        this.element.removeEventListener('wheel', this._onUserGesture);
        this.element.removeEventListener('touchmove', this._onUserGesture);
        this.element.removeEventListener('scroll', this._onScroll);
    }
}
