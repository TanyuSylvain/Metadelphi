/**
 * Model Selector Component
 * Handles model selection and dynamic loading from API
 */

export class ModelSelector {
    constructor(selectElement, apiClient) {
        this.selectElement = selectElement;
        this.apiClient = apiClient;
        this.models = [];
        this.onChangeCallback = null;
        this.imageMode = false; // when true, show only image models
        this.configuredProviders = null; // null = show all, array = filter
    }

    /**
     * Initialize the model selector
     * Fetches models from API and populates the dropdown
     */
    async initialize() {
        try {
            // Show loading state
            this.selectElement.innerHTML = '<option>Loading models...</option>';
            this.selectElement.disabled = true;

            // Fetch models from API
            this.models = await this.apiClient.getModels();

            // Fetch provider settings to filter by configured providers
            try {
                const settingsData = await this.apiClient.getProviderSettings();
                const configured = Object.entries(settingsData.providers)
                    .filter(([_, cfg]) => cfg.api_key_set)
                    .map(([id, _]) => id.toLowerCase());
                if (configured.length > 0) {
                    this.configuredProviders = configured;
                }
            } catch (e) {
                // Settings endpoint may not be available yet; show all models
                console.warn('Could not fetch provider settings for filtering:', e);
            }

            // Populate dropdown
            this.populateModels();

            // Enable selector
            this.selectElement.disabled = false;

            // Set up change listener
            this.selectElement.addEventListener('change', () => {
                if (this.onChangeCallback) {
                    this.onChangeCallback(this.getSelectedModel());
                }
            });

        } catch (error) {
            console.error('Failed to load models:', error);
            this.showError();
        }
    }

    /**
     * Populate the dropdown with models
     */
    populateModels() {
        this.selectElement.innerHTML = '';

        // Group models by provider
        const groupedModels = this.groupModelsByProvider();

        // Add options grouped by provider
        Object.entries(groupedModels).forEach(([provider, models]) => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = provider;

            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.model_id;
                option.textContent = model.model_name;
                option.title = model.description;
                optgroup.appendChild(option);
            });

            this.selectElement.appendChild(optgroup);
        });

        // Select first available (filtered) model by default
        const firstProvider = Object.values(groupedModels)[0];
        if (firstProvider && firstProvider.length > 0) {
            this.selectElement.value = firstProvider[0].model_id;
        }
    }

    /**
     * Filter and repopulate the dropdown based on current imageMode.
     * @param {boolean} imageMode - true = show image models only, false = show text models only
     */
    setImageMode(imageMode) {
        this.imageMode = imageMode;
        this.populateModels();
    }

    /**
     * Group models by provider (filtered by current imageMode)
     * @returns {Object} Models grouped by provider name
     */
    groupModelsByProvider() {
        const grouped = {};

        this.models
            .filter(model => !!model.is_image_model === this.imageMode)
            .filter(model => {
                // If configuredProviders is set, only show models from configured providers
                if (this.configuredProviders && this.configuredProviders.length > 0) {
                    return this.configuredProviders.includes(model.provider);
                }
                return true; // show all if no filter set
            })
            .forEach(model => {
                const providerName = model.provider_name;
                if (!grouped[providerName]) {
                    grouped[providerName] = [];
                }
                grouped[providerName].push(model);
            });

        return grouped;
    }

    /**
     * Show error state
     */
    showError() {
        this.selectElement.innerHTML = '<option>Failed to load models</option>';
        this.selectElement.disabled = true;
    }

    /**
     * Get currently selected model ID
     * @returns {string} Selected model ID
     */
    getSelectedModel() {
        return this.selectElement.value;
    }

    /**
     * Get full model info for selected model
     * @returns {Object|null} Model object or null
     */
    getSelectedModelInfo() {
        const modelId = this.getSelectedModel();
        return this.models.find(m => m.model_id === modelId) || null;
    }

    /**
     * Set selected model by ID
     * @param {string} modelId - Model ID to select
     */
    setSelectedModel(modelId) {
        if (this.models.find(m => m.model_id === modelId)) {
            this.selectElement.value = modelId;
        }
    }

    /**
     * Register callback for model change
     * @param {Function} callback - Callback function
     */
    onChange(callback) {
        this.onChangeCallback = callback;
    }

    /**
     * Get all available models
     * @returns {Array} Array of model objects
     */
    getAllModels() {
        return this.models;
    }

    /**
     * Filter models by provider
     * @param {string} providerName - Provider name
     * @returns {Array} Filtered models
     */
    getModelsByProvider(providerName) {
        return this.models.filter(m => m.provider_name === providerName);
    }

    /**
     * Set which providers are configured (have API keys).
     * Filters the model list to only show models from these providers.
     * @param {Array<string>|null} providerIds - Array of provider IDs, or null to show all
     */
    setConfiguredProviders(providerIds) {
        this.configuredProviders = providerIds;
        this.populateModels();
    }

    /**
     * Refresh models from API
     */
    async refresh() {
        await this.initialize();
    }
}
