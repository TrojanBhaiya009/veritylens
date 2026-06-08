# VerityLens 浏览器插件

🔍 **搜索增强与事实核查** - 帮您找到真实的搜索结果，一键核查信息真伪。

## ✨ 功能特性

### 1. 搜索增强
- ✅ **标记广告** - 在百度/Google 搜索结果中自动标记广告
- ✅ **识别官方网站** - 自动识别并标记官方网站
- ✅ **智能提示** - 当官方网站不在前 3 条时，提示其位置（第几页第几条）
- ✅ **一键跳转** - 点击提示中的"立即跳转"按钮，自动滚动到官方网站

### 2. 一键核查
- ✅ **选中即查** - 选中任意网页中的文字，右键"用 VerityLens 核查选中内容"
- ✅ **快速核查** - 在插件弹窗中粘贴文本，点击"快速核查"
- ✅ **详细结果** - 显示判决（真实/虚假/部分真实/无法验证）、置信度、证据和来源

### 3. 多模型支持
- ✅ **自带 API Key** - 支持 OpenAI、Anthropic、Google、OpenRouter、Ollama
- ✅ **隐私保护** - API Key 只存储在您的浏览器中，不发送给任何人
- ✅ **灵活配置** - 在设置页面选择提供商、填入 API Key、调整温度参数

## 🚀 安装方法

### 方法 1：加载到 Chrome（开发者模式）

1. **下载代码**
   ```bash
   git clone https://github.com/TrojanBhaiya009/veritylens.git
   cd veritylens/extension
   ```

2. **打开 Chrome 扩展管理页面**
   - 在 Chrome 地址栏输入：`chrome://extensions/`
   - 或者：菜单 → 更多工具 → 扩展程序

3. **启用开发者模式**
   - 右上角打开"开发者模式"开关

4. **加载扩展**
   - 点击"加载已解压的扩展程序"
   - 选择 `veritylens/extension` 目录

5. **完成！**
   - 插件图标会出现在 Chrome 工具栏
   - 右键点击图标可以"选项"打开设置页面

### 方法 2：打包安装（.crx 文件）

> 待发布到 Chrome Web Store 后提供

## 🔧 使用方法

### 搜索增强（自动生效）

1. **打开百度或 Google 搜索**
   - 例如：在百度搜索"苹果官网"
   
2. **查看标记**
   - 广告会被标记为 🚨 广告（红色标签）
   - 官方网站会被标记为 ✅ 官方网站（绿色标签）

3. **查看提示**
   - 如果官方网站不在第 1 页前 3 条，顶部会出现提示：
     ```
     💡 官方网站「苹果官网」在第 2 页第 1 条
     [立即跳转] [×]
     ```
   - 点击"立即跳转"会自动滚动到官方网站

### 一键核查（右键菜单）

1. **选中要核查的文本**
   - 例如在新闻网站中选中一段文字

2. **右键点击**
   - 选择"🔍 用 VerityLens 核查选中内容"

3. **查看结果**
   - 插件弹窗会自动打开
   - 显示核查结果：
     - **判决**：✅ 真实 / ❌ 虚假 / ⚠️ 部分真实 / ❓ 无法验证
     - **置信度**：0-100%
     - **证据**：简要说明
     - **来源**：相关链接

### 快速核查（弹窗输入）

1. **点击插件图标**
   - 打开插件弹窗

2. **粘贴要核查的文本**
   - 在底部文本框中粘贴文本

3. **点击"快速核查"**
   - 等待几秒，查看结果

### 设置（配置 API Key）

1. **打开设置页面**
   - 右键点击插件图标 → "选项"
   - 或者在弹窗中点击"设置"链接

2. **选择 AI 提供商**
   - OpenAI（推荐）
   - Anthropic (Claude)
   - Google (Gemini)
   - OpenRouter（聚合多个模型）
   - Ollama（本地模型）

3. **填入 API Key**
   - OpenAI：`sk-...` 开头
   - Anthropic：`sk-ant-...` 开头
   - Google：`AIza...` 开头
   - OpenRouter：`sk-or-...` 开头
   - Ollama：无需 API Key

4. **（可选）自定义配置**
   - **Base URL**：Ollama 用户填写 `http://localhost:11434`
   - **模型名称**：留空使用默认模型
   - **温度**：调整创造性（0=保守，1=创造性）

5. **测试连接**
   - 点击"测试连接"验证 API Key 是否有效

6. **保存设置**
   - 点击"保存设置"

## 🔒 隐私说明

**VerityLens 插件完全保护您的隐私：**

- ✅ **API Key 只存在您浏览器** - 使用 `chrome.storage.sync` 存储，不发送给任何人
- ✅ **文本直接发送到 AI API** - 不经过任何中间服务器（除了 AI 提供商的 API）
- ✅ **搜索增强完全本地** - 不发送任何数据到外部服务器
- ✅ **开源代码** - 您可以看到所有代码，没有后门

**对比原版 VerityLens（有后端服务器）：**
- ❌ 用户文本发送到开发者的服务器
- ❌ 用户 API Key 经过开发者的服务器
- ❌ 开发者能看到用户验证了什么

**本插件（纯浏览器版）：**
- ✅ 用户文本 **不离开浏览器**（除了发送到 AI API）
- ✅ 用户 API Key **只存在 localStorage**
- ✅ 开发者（您）**看不到任何用户数据**

## 🛠️ 技术栈

- **Manifest V3** - Chrome 扩展最新标准
- **纯 JavaScript** - 无需编译，直接运行
- **Chrome Storage API** - 同步存储用户配置
- **Fetch API** - 直接调用 AI 提供商 API
- **Content Scripts** - 注入搜索结果页，分析和标记 DOM

## 📂 目录结构

```
extension/
├── manifest.json              # 插件配置
├── popup/                    # 弹窗
│   ├── popup.html            # 弹窗 HTML
│   ├── popup.css             # 弹窗样式
│   └── popup.js             # 弹窗逻辑
├── content/                  # Content Scripts
│   ├── search-enhancer.js   # 搜索增强
│   └── search-enhancer.css  # 搜索增强样式
├── background/              # 后台服务
│   └── service-worker.js    # Service Worker
├── options/                 # 设置页面
│   ├── options.html         # 设置页面 HTML
│   ├── options.css          # 设置页面样式
│   └── options.js          # 设置页面逻辑
└── icons/                  # 图标
    ├── icon-48.png          # 48x48 图标
    └── icon-128.png        # 128x128 图标
```

## 🔍 支持的搜索引擎

- ✅ **百度** - 完美支持（`www.baidu.com/s?...`）
- ✅ **Google** - 完美支持（`www.google.com/search?...`）
- 🚧 **Bing** - 待支持
- 🚧 **搜狗** - 待支持

## 🌐 支持的 AI 提供商

| 提供商 | API Key 格式 | 默认模型 | 说明 |
|--------|--------------|----------|------|
| OpenAI | `sk-...` | `gpt-4o` | 推荐，质量最好 |
| Anthropic | `sk-ant-...` | `claude-3-5-sonnet-20241022` | 长文本理解强 |
| Google | `AIza...` | `gemini-2.0-flash` | 免费额度高 |
| OpenRouter | `sk-or-...` | `openai/gpt-4o` | 聚合多个模型 |
| Ollama | 无需 Key | `llama3.2` | 本地运行，免费 |

## 🐛 已知问题

1. **官方网站识别可能不准确**
   - 目前使用简单启发式算法
   - 计划：使用 AI 模型辅助判断

2. **Google 搜索结果选择器可能失效**
   - Google 经常更新 DOM 结构
   - 如果遇到问题，请提交 Issue

3. **Ollama 需要手动启动**
   - 使用 Ollama 前需要运行 `ollama serve`

## 🚀 未来计划

- [ ] 支持更多搜索引擎（Bing、搜狗、360）
- [ ] 使用 AI 模型辅助识别官方网站
- [ ] 支持中文语音朗读核查结果
- [ ] 发布到 Chrome Web Store
- [ ] 支持 Firefox（Firefox 插件）
- [ ] 支持 Edge（Edge 插件）

## 💡 贡献指南

欢迎提交 PR！

1. Fork 本仓库
2. 创建分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 📝 许可证

MIT License - 自由使用、修改和分发

## 🙏 致谢

- [VerityLens](https://github.com/TrojanBhaiya009/veritylens) - 原作者
- [Chrome Extensions Documentation](https://developer.chrome.com/docs/extensions/)
- [Manifest V3](https://developer.chrome.com/docs/extensions/mv3/)

---

**Made with ❤️ by VerityLens Team**
