// options.js - 设置页面逻辑

document.addEventListener('DOMContentLoaded', () => {
  const providerSelect = document.getElementById('provider');
  const apiKeyInput = document.getElementById('api-key');
  const toggleApiKeyBtn = document.getElementById('toggle-api-key');
  const baseUrlGroup = document.getElementById('base-url-group');
  const baseUrlInput = document.getElementById('base-url');
  const modelInput = document.getElementById('model');
  const modelHelp = document.getElementById('model-help');
  const temperatureInput = document.getElementById('temperature');
  const temperatureValue = document.getElementById('temperature-value');
  const enableSearchEnhancementCheckbox = document.getElementById('enable-search-enhancement');
  
  const saveBtn = document.getElementById('save-btn');
  const testBtn = document.getElementById('test-btn');
  const resetBtn = document.getElementById('reset-btn');
  const statusMessage = document.getElementById('status-message');

  // 加载已保存的设置
  loadSettings();

  // 监听提供商变化
  providerSelect.addEventListener('change', () => {
    updateUIForProvider();
  });

  // 显示/隐藏 API Key
  toggleApiKeyBtn.addEventListener('click', () => {
    const type = apiKeyInput.type === 'password' ? 'text' : 'password';
    apiKeyInput.type = type;
    toggleApiKeyBtn.textContent = type === 'text' ? '隐藏' : '显示';
  });

  // 温度滑块
  temperatureInput.addEventListener('input', () => {
    temperatureValue.textContent = temperatureInput.value;
  });

  // 保存设置
  saveBtn.addEventListener('click', () => {
    saveSettings();
  });

  // 测试连接
  testBtn.addEventListener('click', async () => {
    await testConnection();
  });

  // 重置设置
  resetBtn.addEventListener('click', () => {
    if (confirm('确定要重置所有设置吗？')) {
      resetSettings();
    }
  });

  // 加载设置
  function loadSettings() {
    chrome.storage.sync.get([
      'provider',
      'apiKey',
      'baseUrl',
      'model',
      'temperature',
      'enableSearchEnhancement'
    ], (result) => {
      providerSelect.value = result.provider || 'openai';
      apiKeyInput.value = result.apiKey || '';
      baseUrlInput.value = result.baseUrl || '';
      modelInput.value = result.model || '';
      temperatureInput.value = result.temperature || 0.3;
      temperatureValue.textContent = temperatureInput.value;
      enableSearchEnhancementCheckbox.checked = result.enableSearchEnhancement !== false;

      updateUIForProvider();
    });
  }

  // 保存设置
  function saveSettings() {
    const settings = {
      provider: providerSelect.value,
      apiKey: apiKeyInput.value.trim(),
      baseUrl: baseUrlInput.value.trim(),
      model: modelInput.value.trim(),
      temperature: parseFloat(temperatureInput.value),
      enableSearchEnhancement: enableSearchEnhancementCheckbox.checked
    };

    chrome.storage.sync.set(settings, () => {
      showStatus('设置已保存！', 'success');
    });
  }

  // 测试连接
  async function testConnection() {
    const provider = providerSelect.value;
    const apiKey = apiKeyInput.value.trim();

    if (!apiKey) {
      showStatus('请先输入 API Key', 'error');
      return;
    }

    showStatus('正在测试连接...', 'info');
    testBtn.disabled = true;

    try {
      const testPrompt = '请回复"连接成功"';
      let apiUrl, headers, body;

      switch (provider) {
        case 'openai':
          apiUrl = 'https://api.openai.com/v1/chat/completions';
          headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          };
          body = {
            model: modelInput.value.trim() || 'gpt-4o',
            messages: [{ role: 'user', content: testPrompt }],
            max_tokens: 10
          };
          break;

        case 'anthropic':
          apiUrl = 'https://api.anthropic.com/v1/messages';
          headers = {
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
          };
          body = {
            model: modelInput.value.trim() || 'claude-3-5-sonnet-20241022',
            max_tokens: 10,
            messages: [{ role: 'user', content: testPrompt }]
          };
          break;

        case 'google':
          apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${modelInput.value.trim() || 'gemini-2.0-flash'}:generateContent?key=${apiKey}`;
          headers = {
            'Content-Type': 'application/json'
          };
          body = {
            contents: [{ parts: [{ text: testPrompt }] }]
          };
          break;

        case 'openrouter':
          apiUrl = 'https://openrouter.ai/api/v1/chat/completions';
          headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          };
          body = {
            model: modelInput.value.trim() || 'openai/gpt-4o',
            messages: [{ role: 'user', content: testPrompt }],
            max_tokens: 10
          };
          break;

        case 'ollama':
          apiUrl = `${baseUrlInput.value.trim() || 'http://localhost:11434'}/api/chat`;
          headers = {
            'Content-Type': 'application/json'
          };
          body = {
            model: modelInput.value.trim() || 'llama3.2',
            messages: [{ role: 'user', content: testPrompt }],
            stream: false
          };
          break;

        default:
          throw new Error('不支持的提供商');
      }

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || '连接失败');
      }

      showStatus('连接成功！API Key 有效。', 'success');
    } catch (error) {
      showStatus(`连接失败: ${error.message}`, 'error');
    } finally {
      testBtn.disabled = false;
    }
  }

  // 重置设置
  function resetSettings() {
    chrome.storage.sync.clear(() => {
      providerSelect.value = 'openai';
      apiKeyInput.value = '';
      baseUrlInput.value = '';
      modelInput.value = '';
      temperatureInput.value = 0.3;
      temperatureValue.textContent = '0.3';
      enableSearchEnhancementCheckbox.checked = true;

      updateUIForProvider();
      showStatus('设置已重置！', 'success');
    });
  }

  // 根据选择的提供商更新 UI
  function updateUIForProvider() {
    const provider = providerSelect.value;

    // 显示/隐藏 Base URL
    if (provider === 'ollama' || provider === 'openrouter') {
      baseUrlGroup.style.display = 'block';
      if (provider === 'ollama') {
        baseUrlInput.placeholder = 'http://localhost:11434';
        document.querySelector('#base-url-group .help-text').textContent = 'Ollama 用户：默认为 http://localhost:11434';
      } else {
        baseUrlInput.placeholder = 'https://your-custom-endpoint.com/v1';
        document.querySelector('#base-url-group .help-text').textContent = '留空使用默认 OpenRouter API';
      }
    } else {
      baseUrlGroup.style.display = 'none';
    }

    // 更新模型帮助文本
    const modelHints = {
      openai: 'gpt-4o, gpt-4-turbo, gpt-3.5-turbo',
      anthropic: 'claude-3-5-sonnet-20241022, claude-3-opus-20240229',
      google: 'gemini-2.0-flash, gemini-1.5-pro',
      openrouter: 'openai/gpt-4o, anthropic/claude-3-5-sonnet, google/gemini-2.0-flash',
      ollama: 'llama3.2, mistral, phi3'
    };
    modelHelp.textContent = `可用模型: ${modelHints[provider] || ''}`;
  }

  // 显示状态消息
  function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = type;
    statusMessage.style.display = 'block';

    setTimeout(() => {
      statusMessage.style.display = 'none';
    }, 5000);
  }
});
