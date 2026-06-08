// content/search-enhancer.js - 搜索结果增强

// 等待页面加载完成
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

function init() {
  const hostname = window.location.hostname;
  
  if (hostname.includes('baidu.com')) {
    enhanceBaiduSearch();
  } else if (hostname.includes('google.com')) {
    enhanceGoogleSearch();
  }
}

// ==================== 百度搜索增强 ====================
function enhanceBaiduSearch() {
  console.log('[VerityLens] 百度搜索增强已启动');
  
  // 等待搜索结果加载
  waitForElement('#content_left').then(() => {
    observeSearchResults('baidu');
  });
}

function enhanceGoogleSearch() {
  console.log('[VerityLens] Google 搜索增强已启动');
  
  // 等待搜索结果加载
  waitForElement('#search').then(() => {
    observeSearchResults('google');
  });
}

// 等待元素出现
function waitForElement(selector, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    
    function check() {
      const element = document.querySelector(selector);
      if (element) {
        resolve(element);
      } else if (Date.now() - startTime > timeout) {
        reject(new Error(`Timeout waiting for ${selector}`));
      } else {
        setTimeout(check, 500);
      }
    }
    
    check();
  });
}

// 监听搜索结果变化（百度是 SPA，Google 也是）
function observeSearchResults(engine) {
  const observer = new MutationObserver(() => {
    setTimeout(() => analyzeSearchResults(engine), 1000);
  });
  
  const target = engine === 'baidu' 
    ? document.querySelector('#content_left')
    : document.querySelector('#search');
  
  if (target) {
    observer.observe(target, { childList: true, subtree: true });
  }
  
  // 立即分析一次
  setTimeout(() => analyzeSearchResults(engine), 1000);
}

// 分析搜索结果
function analyzeSearchResults(engine) {
  console.log(`[VerityLens] 分析 ${engine} 搜索结果...`);
  
  const results = engine === 'baidu' 
    ? analyzeBaiduResults()
    : analyzeGoogleResults();
  
  // 标记广告和垃圾结果
  markResults(results, engine);
  
  // 显示官方结果提示
  if (results.official) {
    showOfficialSiteNotification(results.official, engine);
  }
}

// 分析百度搜索结果
function analyzeBaiduResults() {
  const items = document.querySelectorAll('#content_left > .result, #content_left > .c-container');
  const results = {
    official: null,
    ads: [],
    spam: []
  };
  
  items.forEach((item, index) => {
    const titleEl = item.querySelector('h3');
    const linkEl = item.querySelector('a');
    const title = titleEl?.textContent || '';
    const url = linkEl?.href || '';
    
    // 判断是否为广告
    const isAd = item.querySelector('.c-icon-ad, .ec-tuiguang, [data-is-ad]') ||
                 item.classList.contains('ec-tuiguang');
    
    if (isAd) {
      results.ads.push({ index, element: item, title, url });
    } else {
      // 判断是否为官方网站
      if (isOfficialSite(title, url)) {
        const page = Math.floor(index / 10) + 1;
        const position = (index % 10) + 1;
        
        if (!results.official || results.official.index > index) {
          results.official = { index, page, position, title, url, element: item };
        }
      }
    }
  });
  
  console.log('[VerityLens] 百度分析结果:', results);
  return results;
}

// 分析 Google 搜索结果
function analyzeGoogleResults() {
  const items = document.querySelectorAll('div.g, div[data-sokoban-container] > div');
  const results = {
    official: null,
    ads: [],
    spam: []
  };
  
  let index = 0;
  items.forEach((item) => {
    // 过滤无效的 item
    const linkEl = item.querySelector('a[href]');
    if (!linkEl) return;
    
    const titleEl = item.querySelector('h3');
    const title = titleEl?.textContent || '';
    const url = linkEl.href || '';
    
    // 判断是否为广告
    const adLabel = item.querySelector('[aria-label*="广告"], [data-text*="Ad"]');
    const isAd = adLabel || url.includes('googleadservices');
    
    if (isAd) {
      results.ads.push({ index, element: item, title, url });
    } else {
      // 判断是否为官方网站
      if (isOfficialSite(title, url)) {
        const page = Math.floor(index / 10) + 1;
        const position = (index % 10) + 1;
        
        if (!results.official || results.official.index > index) {
          results.official = { index, page, position, title, url, element: item };
        }
      }
    }
    
    index++;
  });
  
  console.log('[VerityLens] Google 分析结果:', results);
  return results;
}

// 判断是否为官方网站（启发式）
function isOfficialSite(title, url) {
  if (!url || !title) return false;
  
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;
    
    // 简单启发式：官方站通常在标题中包含品牌名，且域名简洁
    // 这里可以扩展为更复杂的逻辑
    
    // 排除常见非官方网站
    const spamDomains = [
      'zhihu.com', 'baidu.com', 'zhidao.baidu.com', // 知乎、百度知道
      'blog.csdn.net', 'cnblogs.com', // 博客
      'xiaohongshu.com', 'douban.com', // 社交媒体
      'sohu.com', 'sina.com', '163.com' // 门户网站
    ];
    
    if (spamDomains.some(domain => hostname.includes(domain))) {
      return false;
    }
    
    // 官方站特征：域名简短、通常是品牌名.com/.cn
    const officialPatterns = [
      /^https?:\/\/[a-z0-9\-]+\.(com|cn|net|org|io)(\/|$)/i,
      /^https?:\/\/www\.[a-z0-9\-]+\.(com|cn|net|org|io)(\/|$)/i
    ];
    
    return officialPatterns.some(pattern => pattern.test(url));
  } catch {
    return false;
  }
}

// 标记搜索结果
function markResults(results, engine) {
  // 标记广告
  results.ads.forEach(ad => {
    if (!ad.element.querySelector('.vl-ad-label')) {
      const label = document.createElement('div');
      label.className = 'vl-ad-label';
      label.textContent = '🚨 广告';
      label.style.cssText = `
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(239, 68, 68, 0.9);
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        z-index: 1000;
      `;
      ad.element.style.position = 'relative';
      ad.element.appendChild(label);
    }
  });
  
  // 标记官方网站
  if (results.official) {
    const official = results.official;
    if (!official.element.querySelector('.vl-official-label')) {
      const label = document.createElement('div');
      label.className = 'vl-official-label';
      label.textContent = '✅ 官方网站';
      label.style.cssText = `
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(16, 185, 129, 0.9);
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        z-index: 1000;
      `;
      official.element.style.position = 'relative';
      official.element.appendChild(label);
    }
  }
}

// 显示官方网站提示
function showOfficialSiteNotification(official, engine) {
  // 如果已经在第 1 页前 3 位，不提示
  if (official.page === 1 && official.position <= 3) {
    return;
  }
  
  // 移除旧提示
  const oldNotification = document.querySelector('.vl-notification');
  if (oldNotification) {
    oldNotification.remove();
  }
  
  // 创建提示
  const notification = document.createElement('div');
  notification.className = 'vl-notification';
  notification.innerHTML = `
    <div class="vl-notification-content">
      <span class="vl-icon">💡</span>
      <span class="vl-text">
        官方网站「${official.title}」在第 <strong>${official.page}</strong> 页第 <strong>${official.position}</strong> 条
      </span>
      <button class="vl-jump-btn">立即跳转</button>
      <button class="vl-close-btn">×</button>
    </div>
  `;
  
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.95) 0%, rgba(139, 92, 246, 0.95) 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    z-index: 99999;
    animation: vl-slide-down 0.3s ease;
  `;
  
  // 添加样式
  if (!document.querySelector('#vl-styles')) {
    const style = document.createElement('style');
    style.id = 'vl-styles';
    style.textContent = `
      @keyframes vl-slide-down {
        from { transform: translateX(-50%) translateY(-100%); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
      }
      .vl-notification-content {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .vl-icon { font-size: 20px; }
      .vl-text { font-size: 14px; }
      .vl-jump-btn {
        background: white;
        color: #6366f1;
        border: none;
        padding: 6px 16px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }
      .vl-jump-btn:hover {
        background: #f0f0f0;
        transform: translateY(-1px);
      }
      .vl-close-btn {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: none;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
    `;
    document.head.appendChild(style);
  }
  
  document.body.appendChild(notification);
  
  // 绑定事件
  notification.querySelector('.vl-jump-btn').addEventListener('click', () => {
    official.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    notification.remove();
  });
  
  notification.querySelector('.vl-close-btn').addEventListener('click', () => {
    notification.remove();
  });
  
  // 5 秒后自动消失
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 5000);
}
