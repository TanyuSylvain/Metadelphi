/**
 * API Client for LLM GUI Backend
 * Handles all communication with the FastAPI backend
 */

export class APIClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    /**
     * Fetch all available models from the backend
     * @returns {Promise<Array>} Array of model objects
     */
    async getModels() {
        try {
            const response = await fetch(`${this.baseURL}/models/`);
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const data = await response.json();
            return data.models;
        } catch (error) {
            console.error('Error fetching models:', error);
            throw error;
        }
    }

    /**
     * Get information about a specific provider
     * @param {string} providerName - Provider ID (e.g., 'mistral', 'qwen')
     * @returns {Promise<Object>} Provider information
     */
    async getProviderInfo(providerName) {
        try {
            const response = await fetch(`${this.baseURL}/models/providers/${providerName}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch provider info: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching provider info:', error);
            throw error;
        }
    }

    /**
     * Send a chat message and get complete response
     * @param {string} message - User message
     * @param {string} conversationId - Conversation ID
     * @param {string} modelId - Model ID to use
     * @returns {Promise<Object>} Response object
     */
    async sendMessage(message, conversationId, modelId) {
        try {
            const response = await fetch(`${this.baseURL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    conversation_id: conversationId,
                    model: modelId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    /**
     * Send a chat message and stream the response
     * @param {string} message - User message
     * @param {string} conversationId - Conversation ID
     * @param {string} modelId - Model ID to use
     * @param {Function} onChunk - Callback for each chunk
     * @param {boolean} thinking - Enable thinking mode
     * @returns {Promise<void>}
     */
    async streamMessage(message, conversationId, modelId, onChunk, thinking = false, webSearch = false) {
        try {
            const body = {
                message,
                conversation_id: conversationId,
                model: modelId
            };
            if (thinking !== null && thinking !== undefined) {
                body.thinking = thinking;
            }
            if (webSearch) {
                body.web_search = true;
            }

            const response = await fetch(`${this.baseURL}/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                onChunk(chunk);
            }
        } catch (error) {
            console.error('Error streaming message:', error);
            throw error;
        }
    }

    /**
     * Get conversation info (metadata only)
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object|null>} Conversation info or null if not found
     */
    async getConversationInfo(conversationId) {
        try {
            const response = await fetch(`${this.baseURL}/conversations/${conversationId}/info`);
            if (!response.ok) {
                if (response.status === 404) {
                    return null;
                }
                throw new Error(`Failed to fetch conversation info: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching conversation info:', error);
            throw error;
        }
    }

    /**
     * Get conversation history
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} Conversation history
     */
    async getConversationHistory(conversationId) {
        try {
            const response = await fetch(`${this.baseURL}/conversations/${conversationId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch conversation: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching conversation:', error);
            throw error;
        }
    }

    /**
     * List all conversations
     * @param {number} limit - Maximum number of conversations
     * @param {number} offset - Offset for pagination
     * @returns {Promise<Object>} Conversations list
     */
    async listConversations(limit = 50, offset = 0) {
        try {
            const response = await fetch(
                `${this.baseURL}/conversations?limit=${limit}&offset=${offset}`
            );
            if (!response.ok) {
                throw new Error(`Failed to list conversations: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error listing conversations:', error);
            throw error;
        }
    }

    /**
     * Delete a conversation
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} Deletion result
     */
    async deleteConversation(conversationId) {
        try {
            const response = await fetch(`${this.baseURL}/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`Failed to delete conversation: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error deleting conversation:', error);
            throw error;
        }
    }

    /**
     * Delete all conversations
     * @returns {Promise<Object>} Deletion result
     */
    async deleteAllConversations() {
        try {
            const response = await fetch(`${this.baseURL}/conversations`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`Failed to delete all conversations: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error deleting all conversations:', error);
            throw error;
        }
    }

    /**
     * Check API health
     * @returns {Promise<Object>} Health status
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            if (!response.ok) {
                throw new Error(`Health check failed: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error checking health:', error);
            throw error;
        }
    }

    /**
     * Stream a multi-agent debate response
     * @param {string} message - User message
     * @param {string} conversationId - Conversation ID
     * @param {Object} config - Multi-agent configuration
     * @param {Object} config.models - Per-role model configuration
     * @param {string} config.models.moderator - Moderator model ID
     * @param {string} config.models.expert - Expert model ID
     * @param {string} config.models.critic - Critic model ID
     * @param {number} config.maxIterations - Maximum debate iterations
     * @param {number} config.scoreThreshold - Score threshold for passing
     * @param {Object} callbacks - Event callbacks
     * @param {Function} callbacks.onPhaseStart - Called when a phase starts
     * @param {Function} callbacks.onExpertAnswer - Called when expert provides answer
     * @param {Function} callbacks.onCriticReview - Called when critic provides review
     * @param {Function} callbacks.onIterationComplete - Called when iteration completes
     * @param {Function} callbacks.onDone - Called when debate completes
     * @param {Function} callbacks.onError - Called on error
     * @returns {Promise<void>}
     */
    async streamMultiAgentDebate(message, conversationId, config, callbacks) {
        try {
            const body = {
                message,
                conversation_id: conversationId,
                models: config.models,
                max_iterations: config.maxIterations,
                score_threshold: config.scoreThreshold,
                thinking: config.thinking || {
                    moderator: false,
                    expert: false,
                    critic: false
                }
            };

            const response = await fetch(`${this.baseURL}/chat/multi-agent/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process SSE events
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const eventData = JSON.parse(line.slice(6));
                            this._handleMultiAgentEvent(eventData, callbacks);
                        } catch (e) {
                            console.warn('Failed to parse SSE event:', line);
                        }
                    }
                }
            }

            // Process any remaining buffer
            if (buffer.startsWith('data: ')) {
                try {
                    const eventData = JSON.parse(buffer.slice(6));
                    this._handleMultiAgentEvent(eventData, callbacks);
                } catch (e) {
                    // Ignore incomplete event
                }
            }
        } catch (error) {
            console.error('Error in multi-agent debate:', error);
            if (callbacks.onError) {
                callbacks.onError(error.message);
            }
            throw error;
        }
    }

    /**
     * Handle a multi-agent SSE event
     * @private
     */
    _handleMultiAgentEvent(event, callbacks) {
        switch (event.type) {
            case 'moderator_init':
                if (callbacks.onModeratorInit) {
                    callbacks.onModeratorInit(event.analysis);
                }
                if (callbacks.onPhaseChange) {
                    callbacks.onPhaseChange('moderator_init', 0);
                }
                break;
            case 'moderator_synthesize':
                if (callbacks.onModeratorSynthesize) {
                    callbacks.onModeratorSynthesize(event.iteration, event.analysis);
                }
                if (callbacks.onPhaseChange) {
                    callbacks.onPhaseChange('moderator_synthesize', event.iteration);
                }
                break;
            case 'phase_start':
                if (callbacks.onPhaseStart) {
                    callbacks.onPhaseStart(event.phase, event.iteration, event.message);
                }
                if (callbacks.onPhaseChange) {
                    callbacks.onPhaseChange(event.phase, event.iteration);
                }
                break;
            case 'expert_answer':
                if (callbacks.onExpertAnswer) {
                    callbacks.onExpertAnswer(event.iteration, event.answer);
                }
                break;
            case 'critic_review':
                if (callbacks.onCriticReview) {
                    callbacks.onCriticReview(event.iteration, event.review);
                }
                break;
            case 'iteration_complete':
                if (callbacks.onIterationComplete) {
                    callbacks.onIterationComplete(event.iteration, event.status, event.score, event.summary);
                }
                break;
            case 'done':
                if (callbacks.onDone) {
                    callbacks.onDone(event.final_answer, event.was_direct_answer, event.termination_reason, event.total_iterations);
                }
                if (callbacks.onPhaseChange) {
                    callbacks.onPhaseChange('done', 0);
                }
                break;
            case 'error':
                if (callbacks.onError) {
                    callbacks.onError(event.error);
                }
                break;
            default:
                console.warn('Unknown multi-agent event type:', event.type);
        }
    }

    /**
     * Stream a coworking agent response
     * @param {string} message - User message
     * @param {string} conversationId - Conversation ID
     * @param {string} modelId - Model ID to use
     * @param {string} workspacePath - Workspace directory path
     * @param {boolean} thinking - Enable thinking mode
     * @param {number} maxIterations - Max ReAct loop iterations
     * @param {Object} callbacks - Event callbacks
     * @returns {Promise<void>}
     */
    async streamCoworkingChat(message, conversationId, modelId, workspacePath, thinking, maxIterations, webSearch, callbacks) {
        try {
            const body = {
                message,
                conversation_id: conversationId,
                model: modelId,
                workspace_path: workspacePath,
                thinking: thinking || false,
                max_iterations: maxIterations || 25
            };
            if (webSearch) {
                body.web_search = true;
            }

            const response = await fetch(`${this.baseURL}/chat/coworking/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process SSE events
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const eventData = JSON.parse(line.slice(6));
                            this._handleCoworkingEvent(eventData, callbacks);
                        } catch (e) {
                            console.warn('Failed to parse coworking SSE event:', line);
                        }
                    }
                }
            }

            // Process remaining buffer
            if (buffer.startsWith('data: ')) {
                try {
                    const eventData = JSON.parse(buffer.slice(6));
                    this._handleCoworkingEvent(eventData, callbacks);
                } catch (e) {
                    // Ignore incomplete
                }
            }
        } catch (error) {
            console.error('Error in coworking chat:', error);
            if (callbacks.onError) {
                callbacks.onError(error.message);
            }
            throw error;
        }
    }

    /**
     * Handle a coworking agent SSE event
     * @private
     */
    _handleCoworkingEvent(event, callbacks) {
        switch (event.type) {
            case 'previous_files':
                if (callbacks.onPreviousFiles) {
                    callbacks.onPreviousFiles(event.files, event.deleted_files || []);
                }
                break;
            case 'plan':
            case 'plan_ready':
                if (callbacks.onPlanReady) callbacks.onPlanReady(event.steps || []);
                break;
            case 'thinking_chunk':
                if (callbacks.onReasoningChunk) callbacks.onReasoningChunk(1, event.content);
                break;
            case 'round_start':
                if (callbacks.onRoundStart) callbacks.onRoundStart(event.round);
                break;
            case 'reasoning_chunk':
                if (callbacks.onReasoningChunk) callbacks.onReasoningChunk(event.round, event.content);
                break;
            case 'tool_start':
                if (callbacks.onToolStart) {
                    callbacks.onToolStart(
                        event.round || 1,
                        event.tool_name,
                        event.tool_input,
                        event.tool_call_id || null
                    );
                }
                break;
            case 'tool_result':
                if (callbacks.onToolResult) {
                    callbacks.onToolResult(
                        event.round || 1,
                        event.tool_name,
                        event.output,
                        event.success,
                        event.tool_call_id || null
                    );
                }
                break;
            case 'round_complete':
                if (callbacks.onRoundComplete) callbacks.onRoundComplete(event.round);
                break;
            case 'file_created':
                if (callbacks.onFileCreated) callbacks.onFileCreated(event.file_path, event.file_size);
                break;
            case 'file_deleted':
                if (callbacks.onFileDeleted) callbacks.onFileDeleted(event.file_path);
                break;
            case 'session_notice':
                if (callbacks.onSessionNotice) callbacks.onSessionNotice(event.message);
                break;
            case 'response_chunk':
            case 'final_chunk':
                if (callbacks.onFinalChunk) callbacks.onFinalChunk(event.content);
                break;
            case 'final_start':
                if (callbacks.onFinalStart) callbacks.onFinalStart();
                break;
            case 'citations':
                if (callbacks.onCitations) callbacks.onCitations(event.citations);
                break;
            case 'done':
                if (callbacks.onDone) {
                    callbacks.onDone(
                        event.final_answer,
                        event.generated_files || [],
                        event.deleted_files || []
                    );
                }
                break;
            case 'error':
                if (callbacks.onError) callbacks.onError(event.error);
                break;
            default:
                console.warn('Unknown coworking event type:', event.type);
        }
    }

    /**
     * Send a multi-agent chat message and get complete response (non-streaming)
     * @param {string} message - User message
     * @param {string} conversationId - Conversation ID
     * @param {Object} config - Multi-agent configuration
     * @returns {Promise<Object>} Response object
     */
    async sendMultiAgentMessage(message, conversationId, config) {
        try {
            const body = {
                message,
                conversation_id: conversationId,
                models: config.models,
                max_iterations: config.maxIterations,
                score_threshold: config.scoreThreshold,
                thinking: config.thinking || {
                    moderator: false,
                    expert: false,
                    critic: false
                }
            };

            const response = await fetch(`${this.baseURL}/chat/multi-agent/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Error sending multi-agent message:', error);
            throw error;
        }
    }

    /**
     * Get conversation information
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} Conversation metadata
     */
    async getConversationInfo(conversationId) {
        try {
            const response = await fetch(
                `${this.baseURL}/conversations/${conversationId}/info`
            );

            if (!response.ok) {
                throw new Error('Failed to get conversation info');
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting conversation info:', error);
            throw error;
        }
    }

    /**
     * Open a native macOS folder picker and return the selected path.
     * @returns {Promise<string|null>} Selected path or null if cancelled
     */
    async selectWorkspace() {
        try {
            const response = await fetch(`${this.baseURL}/chat/coworking/select-workspace`);
            if (!response.ok) {
                throw new Error(`Failed to select workspace: ${response.statusText}`);
            }
            const data = await response.json();
            return data.path || null;
        } catch (error) {
            console.error('Error selecting workspace:', error);
            throw error;
        }
    }

    /**
     * Open a file from the workspace with the default application.
     * @param {string} workspacePath - Workspace directory path
     * @param {string} filePath - File path relative to workspace
     * @returns {Promise<Object>} Result object
     */
    async openFile(workspacePath, filePath) {
        try {
            const response = await fetch(`${this.baseURL}/chat/coworking/open-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace_path: workspacePath,
                    file_path: filePath
                })
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to open file');
            }
            return await response.json();
        } catch (error) {
            console.error('Error opening file:', error);
            throw error;
        }
    }

    /**
     * Validate and restore coworking session file state.
     * @param {string} conversationId - Conversation ID
     * @param {string} workspacePath - Absolute workspace directory path
     * @returns {Promise<Object>} Current coworking session file state
     */
    async getCoworkingSessionState(conversationId, workspacePath) {
        try {
            const params = new URLSearchParams({
                conversation_id: conversationId,
                workspace_path: workspacePath
            });
            const response = await fetch(
                `${this.baseURL}/chat/coworking/session-state?${params.toString()}`
            );
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load coworking session state');
            }
            return await response.json();
        } catch (error) {
            console.error('Error loading coworking session state:', error);
            throw error;
        }
    }

    /**
     * Switch conversation mode between simple and debate
     * @param {string} conversationId - Conversation ID
     * @param {string} targetMode - Target mode ('simple' or 'debate')
     * @param {Object} modelConfig - Model configuration for debate mode (optional)
     * @returns {Promise<Object>} Response object
     */
    async switchMode(conversationId, targetMode, modelConfig = null) {
        try {
            const body = {
                target_mode: targetMode,
                debate_config: modelConfig
            };

            const response = await fetch(
                `${this.baseURL}/conversations/${conversationId}/switch-mode`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                }
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to switch mode');
            }

            return await response.json();
        } catch (error) {
            console.error('Error switching mode:', error);
            throw error;
        }
    }
}
