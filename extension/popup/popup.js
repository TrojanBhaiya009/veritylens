// popup.js - VerityLens Popup 逻辑

document.addEventListener('DOMContentLoaded', () => {
  const loadingEl = document.getElementById('loading');
  const resultEl = document.getElementById('result');
  const emptyEl = document.getElementById('empty');
  const quickInput = document.getElementById('quick-input');
  const quickVerifyBtn = document.getElementById('quick-verify-btn');
  const openOptionsLink = document.getElementById('open-options');

  // 加载上次验证结果
  chrome.storage.local.get(['lastVerification'], (result) => {
    if (result.lastVerification) {
      showVerificationResult(result.lastVerification);
    }
  });

  // 快速核查按钮
  quickVerifyBtn.addEventListener('click', async () => {
    const text = quickInput.value.trim();
    if (!text) {
      alert('请输入要核查的文本');
      return;
    }

    await verifyText(text);
  });

  // 打开设置页面
  openOptionsLink.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });

  // 核查文本
  async function verifyText(text) {
    // 显示加载中
    emptyEl.style.display = 'none';
    resultEl.style.display = 'none';
    loadingEl.style.display = 'flex';

    try {
      // 从 storage 读取用户配置
      const config = await chrome.storage.sync.get([
        'provider',
        'apiKey',
        'model',
        'baseUrl'
      ]);

      if (!config.apiKey) {
        throw new Error('请先在设置中配置 API Key');
      }

      // 调用 LLM API
      const result = await callLLM(text, config);

      // 保存结果
      chrome.storage.local.set({ lastVerification: result });

      // 显示结果
      showVerificationResult(result);

    } catch (error) {
      alert(`核查失败: ${error.message}`);
      emptyEl.style.display = 'flex';
      resultEl.style.display = 'none';
      loadingEl.style.display = 'none';
    }
  }

  // 调用 LLM API
  async function callLLM(text, config) {
    const prompt = `请验证以下信息的真实性，并以 JSON 格式返回结果：

信息: ${text}

请返回严格的 JSON 格式（不要有任何其他文本）：
{
  "verdict": "True" | "False" | "Partially True" | "Unverifiable",
  "confidence": 0.0-1.0,
  "evidence": "简要说明证据",
  "sources": ["来源URL1", "来源URL2"]
}

只返回 JSON，不要有其他内容。`;

    let apiUrl, headers, body;

    switch (config.provider) {
      case 'openai':
        apiUrl = 'https://api.openai.com/v1/chat/completions';
        headers = {
          'Authorization': `Bearer ${config.apiKey}`,
          'Content-Type': 'application/json'
        };
        body = {
          model: config.model || 'gpt-4o',
          messages: [{ role: 'user', content: prompt }],
          temperature: 0.3
        };
        break;

      case 'anthropic':
        apiUrl = 'https://api.anthropic.com/v1/messages';
        headers = {
          'x-api-key': config.apiKey,
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json'
        };
        body = {
          model: config.model || 'claude-3-5-sonnet-20241022',
          max_tokens: 1024,
          messages: [{ role: 'user', content: prompt }]
        };
        break;

      case 'google':
        apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${config.model || 'gemini-2.0-flash'}:generateContent?key=${config.apiKey}`;
        headers = {
          'Content-Type': 'application/json'
        };
        body = {
          contents: [{ parts: [{ text: prompt }] }]
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
      throw new Error(error.error?.message || 'API 调用失败');
    }

    const data = await response.json();

    // 解析响应
    let content;
    if (config.provider === 'openai') {
      content = data.choices[0].message.content;
    } else if (config.provider === 'anthropic') {
      content = data.content[0].text;
    } else if (config.provider === 'google') {
      content = data.candidates[0].content.parts[0].text;
    }

    // 提取 JSON
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('无法解析 API 响应');
    }

    return JSON.parse(jsonMatch[0]);
  }

  // 显示验证结果
  function showVerificationResult(result) {
    loadingEl.style.display = 'none';
    emptyEl.style.display = 'none';
    resultEl.style.display = 'block';

    const verdictEl = document.getElementById('verdict');
    const confidenceEl = document.getElementById('confidence');
    const evidenceEl = document.getElementById('evidence');
    const sourcesEl = document.getElementById('sources');

    // 判决
    let verdictText, verdictClass;
    switch (result.verdict) {
      case 'True':
        verdictText = '✅ 真实';
        verdictClass = 'true';
        break;
      case 'False':
        verdictText = '❌ 虚假';
        verdictClass = 'false';
        break;
      case 'Partially True':
        verdictText = '⚠️ 部分真实';
        verdictClass = 'partially-true';
        break;
      default:
        verdictText = '❓ 无法验证';
        verdictClass = 'unverifiable';
    }
    verdictEl.textContent = verdictText;
    verdictEl.className = `verdict ${verdictClass}`;

    // 置信度
    confidenceEl.textContent = `置信度: ${(result.confidence * 100).toFixed(0)}%`;

    // 证据
    evidenceEl.textContent = result.evidence;

    // 来源
    if (result.sources && result.sources.length > 0) {
      sourcesEl.innerHTML = `
        <h3>来源</h3>
        <ul>
          ${result.sources.map(src => `<li><a href="${src}" target="_blank">${src}</a></li>`).join('')}
        </ul>
      `;
    } else {
      sourcesEl.innerHTML = '';
    }
  }
});
