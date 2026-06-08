import { useState, useEffect } from 'react';
import './Settings.css';

interface Provider {
  id: string;
  name: string;
  models: string[];
  api_key_required: boolean;
  base_url_required: boolean;
  api_key_placeholder: string;
  base_url_placeholder: string;
  description: string;
}

interface ModelConfig {
  provider: string;
  apiKey: string;
  baseUrl: string;
  model: string;
}

const STORAGE_KEY = 'veritylens_model_config';

export function Settings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<ModelConfig>({
    provider: 'duckduckgo',
    apiKey: '',
    baseUrl: '',
    model: '',
  });
  const [showKey, setShowKey] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  // Load providers and saved config
  useEffect(() => {
    loadProviders();
    loadSavedConfig();
  }, []);

  const loadProviders = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/providers');
      const data = await response.json();
      setProviders(data.providers);
      
      // Set default model for initial provider
      const defaultProvider = data.providers.find((p: Provider) => p.id === 'duckduckgo');
      if (defaultProvider && defaultProvider.models.length > 0) {
        setConfig(prev => ({ ...prev, model: defaultProvider.models[0] }));
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSavedConfig = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setConfig(parsed);
      }
    } catch (error) {
      console.error('Failed to load saved config:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus('idle');
    setErrorMsg('');

    try {
      // Validate
      const provider = providers.find(p => p.id === config.provider);
      if (!provider) {
        throw new Error('Invalid provider selected');
      }

      if (provider.api_key_required && !config.apiKey.trim()) {
        throw new Error(`API key is required for ${provider.name}`);
      }

      if (provider.base_url_required && !config.baseUrl.trim()) {
        throw new Error(`Base URL is required for ${provider.name}`);
      }

      if (!config.model) {
        throw new Error('Please select a model');
      }

      // Save to localStorage
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
      setSaveStatus('success');
      
      // Hide success message after 3 seconds
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error: any) {
      setErrorMsg(error.message);
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    localStorage.removeItem(STORAGE_KEY);
    setConfig({
      provider: 'duckduckgo',
      apiKey: '',
      baseUrl: '',
      model: providers.find(p => p.id === 'duckduckgo')?.models[0] || '',
    });
    setSaveStatus('idle');
    setErrorMsg('');
  };

  const handleProviderChange = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (provider) {
      setConfig(prev => ({
        ...prev,
        provider: providerId,
        model: provider.models[0] || '',
        apiKey: '',
        baseUrl: providerId === 'custom' ? 'http://localhost:11434/v1' : '',
      }));
    }
  };

  const currentProvider = providers.find(p => p.id === config.provider);

  if (loading) {
    return (
      <div className="settings-loading">
        <div className="spinner"></div>
        <p>Loading provider configurations...</p>
      </div>
    );
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h2>⚙️ Model Settings</h2>
        <p className="settings-subtitle">
          Configure your AI model provider. Your API key is stored locally and never sent to our servers.
        </p>
      </div>

      <div className="settings-content">
        {/* Provider Selection */}
        <div className="settings-section">
          <label className="settings-label">AI Provider</label>
          <div className="provider-grid">
            {providers.map(provider => (
              <div
                key={provider.id}
                className={`provider-card ${config.provider === provider.id ? 'selected' : ''}`}
                onClick={() => handleProviderChange(provider.id)}
              >
                <div className="provider-name">{provider.name}</div>
                <div className="provider-description">{provider.description}</div>
                {provider.id === 'duckduckgo' && (
                  <div className="provider-badge free">FREE</div>
                )}
                {provider.id === 'google' && (
                  <div className="provider-badge free-tier">FREE TIER</div>
                )}
                {provider.id === 'openrouter' && (
                  <div className="provider-badge free-tier">FREE CREDITS</div>
                )}
                {provider.id === 'custom' && (
                  <div className="provider-badge local">LOCAL</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* API Key */}
        {currentProvider?.api_key_required && (
          <div className="settings-section">
            <label className="settings-label">
              API Key
              <span className="required">*</required>
            </label>
            <div className="input-with-toggle">
              <input
                type={showKey ? 'text' : 'password'}
                placeholder={currentProvider.api_key_placeholder || 'Enter your API key...'}
                value={config.apiKey}
                onChange={(e) => setConfig(prev => ({ ...prev, apiKey: e.target.value }))}
                className="settings-input"
              />
              <button
                type="button"
                className="toggle-visibility"
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? '🙈' : '👁️'}
              </button>
            </div>
            <div className="input-help">
              {config.provider === 'openai' && (
                <>Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com</a></>
              )}
              {config.provider === 'anthropic' && (
                <>Get your API key from <a href="https://console.anthropic.com" target="_blank" rel="noopener">console.anthropic.com</a></>
              )}
              {config.provider === 'google' && (
                <>Get your API key from <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com</a></>
              )}
              {config.provider === 'openrouter' && (
                <>Get your API key from <a href="https://openrouter.ai/keys" target="_blank" rel="noopener">openrouter.ai</a> (free credits available!)</>
              )}
            </div>
          </div>
        )}

        {/* Base URL (for custom) */}
        {currentProvider?.base_url_required && (
          <div className="settings-section">
            <label className="settings-label">
              Base URL
              <span className="required">*</required>
            </label>
            <input
              type="text"
              placeholder={currentProvider.base_url_placeholder || 'http://localhost:11434/v1'}
              value={config.baseUrl}
              onChange={(e) => setConfig(prev => ({ ...prev, baseUrl: e.target.value }))}
              className="settings-input"
            />
            <div className="input-help">
              For Ollama, use <code>http://localhost:11434/v1</code>. For other OpenAI-compatible APIs, enter their base URL.
            </div>
          </div>
        )}

        {/* Model Selection */}
        <div className="settings-section">
          <label className="settings-label">Model</label>
          {config.provider === 'custom' ? (
            <div>
              <input
                type="text"
                placeholder="Enter custom model name (e.g., llama3.3:70b)"
                value={config.model}
                onChange={(e) => setConfig(prev => ({ ...prev, model: e.target.value }))}
                className="settings-input"
              />
              <div className="input-help">
                For Ollama: use <code>model:tag</code> format (e.g., <code>llama3.3:70b</code>, <code>mistral:7b</code>)
              </div>
            </div>
          ) : (
            <select
              value={config.model}
              onChange={(e) => setConfig(prev => ({ ...prev, model: e.target.value }))}
              className="settings-select"
            >
              {currentProvider?.models.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          )}
        </div>

        {/* Status Messages */}
        {saveStatus === 'success' && (
          <div className="status-message success">
            ✅ Settings saved successfully!
          </div>
        )}
        {saveStatus === 'error' && (
          <div className="status-message error">
            ❌ {errorMsg}
          </div>
        )}

        {/* Action Buttons */}
        <div className="settings-actions">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary"
          >
            {saving ? '💾 Saving...' : '💾 Save Settings'}
          </button>
          <button
            onClick={handleReset}
            className="btn-secondary"
          >
            🔄 Reset to Defaults
          </button>
        </div>

        {/* Tips */}
        <div className="settings-tips">
          <h3>💡 Free / Low-Cost Options</h3>
          <ul>
            <li>
              <strong>DuckDuckGo Chat</strong> — Completely free, no key needed. Uses multiple models automatically.
            </li>
            <li>
              <strong>Google Gemini</strong> — Free tier with generous limits. Get key at <code>aistudio.google.com</code>
            </li>
            <li>
              <strong>OpenRouter</strong> — Aggregates multiple models, offers free credits. Sign up at <code>openrouter.ai</code>
            </li>
            <li>
              <strong>Local (Ollama)</strong> — Run models locally for free. Install from <code>ollama.com</code>
            </li>
          </ul>

          <h3>🔒 Privacy Note</h3>
          <p>
            Your API key is stored only in your browser's localStorage. 
            It is sent directly to the backend (running on your machine) and then to the AI provider you chose.
            We never store your API key on our servers.
          </p>
        </div>
      </div>
    </div>
  );
}
