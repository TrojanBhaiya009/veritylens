// background/service-worker.js - 后台服务

// 安装时创建右键菜单
chrome.runtime.onInstalled.addListener((details) => {
  console.log('[VerityLens] 插件已安装/更新', details.reason);
  
  // 创建右键菜单
  chrome.contextMenus.create({
    id: 'verify-selection',
    title: '🔍 用 VerityLens 核查选中内容',
    contexts: ['selection']
  });
  
  // 创建设置菜单
  chrome.contextMenus.create({
    id: 'open-settings',
    title: '⚙️ 设置',
    contexts: ['action']  // 点击插件图标时显示
  });
});

// 监听右键菜单点击
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'verify-selection') {
    const selectedText = info.selectionText;
    
    console.log('[VerityLens] 右键核查:', selectedText.substring(0, 50) + '...');
    
    // 发送到 content script 处理
    chrome.tabs.sendMessage(tab.id, {
      action: 'verify-text',
      text: selectedText
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[VerityLens] 发送消息失败:', chrome.runtime.lastError);
        // 如果 content script 未加载，打开 popup
        chrome.action.openPopup();
      }
    });
    
    // 同时保存到 storage，供 popup 读取
    chrome.storage.local.set({ pendingVerification: selectedText });
    
    // 打开 popup 显示结果
    chrome.action.openPopup();
  }
  
  if (info.menuItemId === 'open-settings') {
    chrome.runtime.openOptionsPage();
  }
});

// 监听来自 popup 的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'verify-text') {
    // 执行核查
    verifyText(request.text).then(result => {
      sendResponse({ success: true, result });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    
    return true;  // 异步响应
  }
});

// 核查文本
async function verifyText(text) {
  console.log('[VerityLens] 开始核查:', text.substring(0, 50) + '...');
  
  // 从 storage 读取用户配置
  const config = await chrome.storage.sync.get([
    'provider',
    'apiKey',
    'model',
    'baseUrl',
    'temperature'
  ]);
  
  if (!config.apiKey) {
    throw new Error('请先在设置中配置 API Key');
  }
  
  // 调用 LLM API
  const result = await callLLM(text, config);
  
  // 保存结果
  await chrome.storage.local.set({ lastVerification: result });
  
  return result;
}

// 调用 LLM API
async function callLLM(text, config) {
  const prompt = `请验证以下信息的真实性，并以 JSON 格式返回结果：

信息: ${text}

请返回严格的 JSON 格式（不要有任何其他文本）：
{
  "verdict": "True" | "False" | "Partially True" | "Unverifiable",
  "confidence": 0.0-1.0 之间的数字,
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
        temperature: config.temperature || 0.3
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

    case 'openrouter':
      apiUrl = 'https://openrouter.ai/api/v1/chat/completions';
      headers = {
        'Authorization': `Bearer ${config.apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://veritylens.com',
        'X-Title': 'VerityLens'
      };
      body = {
        model: config.model || 'openai/gpt-4o',
        messages: [{ role: 'user', content: prompt }],
        temperature: config.temperature || 0.3
      };
      break;

    case 'ollama':
      apiUrl = `${config.baseUrl || 'http://localhost:11434'}/api/chat`;
      headers = {
        'Content-Type': 'application/json'
      };
      body = {
        model: config.model || 'llama3.2',
        messages: [{ role: 'user', content: prompt }],
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
    throw new Error(error.error?.message || 'API 调用失败');
  }

  const data = await response.json();

  // 解析响应
  let content;
  if (config.provider === 'openai' || config.provider === 'openrouter') {
    content = data.choices[0].message.content;
  } else if (config.provider === 'anthropic') {
    content = data.content[0].text;
  } else if (config.provider === 'google') {
    content = data.candidates[0].content.parts[0].text;
  } else if (config.provider === 'ollama') {
    content = data.message.content;
  }

  // 提取 JSON
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error('无法解析 API 响应');
  }

  return JSON.parse(jsonMatch[0]);
}

// 监听插件图标点击（如果没有 popup）
chrome.action.onClicked.addListener((tab) => {
  // 如果有 popup.html，这个事件不会触发
  // 这里可以处理没有 popup 的情况
  console.log('[VerityLens] 插件图标被点击');
});
