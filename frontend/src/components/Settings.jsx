import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import './Settings.css';

const KNOWN_PROVIDERS = [
  { id: 'openrouter', label: 'OpenRouter', description: 'Routes to all models (OpenAI, Anthropic, Google, xAI, etc.)', url: 'https://openrouter.ai/keys' },
  { id: 'anthropic', label: 'Anthropic (Claude)', description: 'Direct access to Claude models', url: 'https://console.anthropic.com/api-keys' },
  { id: 'openai', label: 'OpenAI', description: 'Direct access to GPT models', url: 'https://platform.openai.com/api-keys' },
  { id: 'google', label: 'Google AI', description: 'Direct access to Gemini models', url: 'https://aistudio.google.com/app/apikey' },
  { id: 'xai', label: 'xAI (Grok)', description: 'Direct access to Grok models', url: 'https://console.x.ai' },
];

const DEFAULT_MODELS = [
  'anthropic/claude-sonnet-4-5',
  'openai/gpt-4o',
  'google/gemini-2.5-pro-preview',
  'x-ai/grok-3',
];

export default function Settings({ onClose }) {
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState('keys');
  const [configuredProviders, setConfiguredProviders] = useState([]);
  const [keyInputs, setKeyInputs] = useState({});
  const [showKey, setShowKey] = useState({});
  const [keySaving, setKeySaving] = useState({});
  const [keyMessages, setKeyMessages] = useState({});

  const [councilModels, setCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [newModelInput, setNewModelInput] = useState('');
  const [configSaving, setConfigSaving] = useState(false);
  const [configMessage, setConfigMessage] = useState('');

  useEffect(() => {
    loadKeys();
    loadCouncilConfig();
  }, []);

  const loadKeys = async () => {
    try {
      const token = getToken();
      const data = await api.listApiKeys(token);
      setConfiguredProviders(data.providers || []);
    } catch (e) {
      console.error('Failed to load API keys', e);
    }
  };

  const loadCouncilConfig = async () => {
    try {
      const token = getToken();
      const data = await api.getCouncilConfig(token);
      setCouncilModels(data.council_models || DEFAULT_MODELS);
      setChairmanModel(data.chairman_model || DEFAULT_MODELS[0]);
    } catch (e) {
      console.error('Failed to load council config', e);
    }
  };

  const handleSaveKey = async (provider) => {
    const key = keyInputs[provider]?.trim();
    if (!key) return;
    setKeySaving((prev) => ({ ...prev, [provider]: true }));
    setKeyMessages((prev) => ({ ...prev, [provider]: '' }));
    try {
      const token = getToken();
      await api.saveApiKey(token, provider, key);
      setKeyMessages((prev) => ({ ...prev, [provider]: 'Saved successfully' }));
      setKeyInputs((prev) => ({ ...prev, [provider]: '' }));
      setConfiguredProviders((prev) =>
        prev.includes(provider) ? prev : [...prev, provider]
      );
    } catch (e) {
      setKeyMessages((prev) => ({ ...prev, [provider]: 'Failed to save' }));
    } finally {
      setKeySaving((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const handleDeleteKey = async (provider) => {
    setKeySaving((prev) => ({ ...prev, [provider]: true }));
    try {
      const token = getToken();
      await api.deleteApiKey(token, provider);
      setConfiguredProviders((prev) => prev.filter((p) => p !== provider));
      setKeyMessages((prev) => ({ ...prev, [provider]: 'Removed' }));
    } catch (e) {
      setKeyMessages((prev) => ({ ...prev, [provider]: 'Failed to remove' }));
    } finally {
      setKeySaving((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const handleAddModel = () => {
    const m = newModelInput.trim();
    if (!m || councilModels.includes(m)) return;
    setCouncilModels((prev) => [...prev, m]);
    setNewModelInput('');
  };

  const handleRemoveModel = (model) => {
    if (councilModels.length <= 2) return;
    setCouncilModels((prev) => prev.filter((m) => m !== model));
    if (chairmanModel === model) setChairmanModel(councilModels.find((m) => m !== model) || '');
  };

  const handleSaveCouncilConfig = async () => {
    setConfigSaving(true);
    setConfigMessage('');
    try {
      const token = getToken();
      await api.saveCouncilConfig(token, councilModels, chairmanModel);
      setConfigMessage('Configuration saved');
    } catch (e) {
      setConfigMessage('Failed to save configuration');
    } finally {
      setConfigSaving(false);
    }
  };

  return (
    <div className="settings-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="settings-panel">
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="settings-close" onClick={onClose}>&#x2715;</button>
        </div>

        <div className="settings-tabs">
          <button
            className={`settings-tab ${activeTab === 'keys' ? 'active' : ''}`}
            onClick={() => setActiveTab('keys')}
          >
            API Keys
          </button>
          <button
            className={`settings-tab ${activeTab === 'council' ? 'active' : ''}`}
            onClick={() => setActiveTab('council')}
          >
            Council Models
          </button>
        </div>

        <div className="settings-content">
          {activeTab === 'keys' && (
            <div className="keys-section">
              <p className="settings-description">
                Add your own API keys to use when running council sessions. Keys are stored encrypted in the database and never exposed in plaintext.
              </p>
              {KNOWN_PROVIDERS.map((provider) => {
                const isConfigured = configuredProviders.includes(provider.id);
                return (
                  <div key={provider.id} className="provider-card">
                    <div className="provider-header">
                      <div className="provider-info">
                        <div className="provider-name-row">
                          <span className="provider-name">{provider.label}</span>
                          {isConfigured && <span className="provider-badge">Configured</span>}
                        </div>
                        <span className="provider-desc">{provider.description}</span>
                      </div>
                    </div>
                    <div className="provider-key-row">
                      <div className="key-input-wrapper">
                        <input
                          type={showKey[provider.id] ? 'text' : 'password'}
                          placeholder={isConfigured ? 'Enter new key to update...' : 'Paste your API key here...'}
                          value={keyInputs[provider.id] || ''}
                          onChange={(e) => setKeyInputs((prev) => ({ ...prev, [provider.id]: e.target.value }))}
                        />
                        <button
                          className="show-key-btn"
                          onClick={() => setShowKey((prev) => ({ ...prev, [provider.id]: !prev[provider.id] }))}
                          title={showKey[provider.id] ? 'Hide key' : 'Show key'}
                        >
                          {showKey[provider.id] ? '🙈' : '👁'}
                        </button>
                      </div>
                      <button
                        className="key-save-btn"
                        onClick={() => handleSaveKey(provider.id)}
                        disabled={keySaving[provider.id] || !keyInputs[provider.id]?.trim()}
                      >
                        {keySaving[provider.id] ? '...' : 'Save'}
                      </button>
                      {isConfigured && (
                        <button
                          className="key-delete-btn"
                          onClick={() => handleDeleteKey(provider.id)}
                          disabled={keySaving[provider.id]}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    {keyMessages[provider.id] && (
                      <div className={`key-message ${keyMessages[provider.id].includes('Fail') ? 'error' : 'success'}`}>
                        {keyMessages[provider.id]}
                      </div>
                    )}
                    <a className="provider-link" href={provider.url} target="_blank" rel="noreferrer">
                      Get key from {provider.label} →
                    </a>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'council' && (
            <div className="council-section">
              <p className="settings-description">
                Configure which models participate in the council deliberation and which model acts as the Chairman to synthesize the final answer.
              </p>

              <div className="council-block">
                <h3>Council Members</h3>
                <p className="council-note">At least 2 models required. Uses OpenRouter model identifiers (e.g., <code>anthropic/claude-sonnet-4-5</code>).</p>
                <div className="model-list">
                  {councilModels.map((model) => (
                    <div key={model} className="model-tag">
                      <span>{model}</span>
                      <button
                        className="model-remove"
                        onClick={() => handleRemoveModel(model)}
                        disabled={councilModels.length <= 2}
                        title={councilModels.length <= 2 ? 'Minimum 2 models required' : 'Remove model'}
                      >
                        &#x2715;
                      </button>
                    </div>
                  ))}
                </div>
                <div className="model-add-row">
                  <input
                    type="text"
                    placeholder="e.g., mistralai/mistral-7b-instruct"
                    value={newModelInput}
                    onChange={(e) => setNewModelInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddModel()}
                  />
                  <button className="model-add-btn" onClick={handleAddModel} disabled={!newModelInput.trim()}>
                    Add
                  </button>
                </div>
              </div>

              <div className="council-block">
                <h3>Chairman Model</h3>
                <p className="council-note">The model that synthesizes the final answer from all council responses and rankings.</p>
                <select
                  className="chairman-select"
                  value={chairmanModel}
                  onChange={(e) => setChairmanModel(e.target.value)}
                >
                  {councilModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
              </div>

              <div className="council-save-row">
                <button
                  className="council-save-btn"
                  onClick={handleSaveCouncilConfig}
                  disabled={configSaving || councilModels.length < 2 || !chairmanModel}
                >
                  {configSaving ? 'Saving...' : 'Save Configuration'}
                </button>
                {configMessage && (
                  <span className={`council-message ${configMessage.includes('Failed') ? 'error' : 'success'}`}>
                    {configMessage}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
