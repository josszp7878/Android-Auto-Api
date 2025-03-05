// 在文件顶部添加一个简单的控制台日志，确认文件被加载
console.log('LogManager.js 已加载');

/**
 * 日志管理器
 * 负责日志的加载、过滤、显示和交互
 */
class LogManager {
  constructor(socket) {
    // 确保使用传入的 socket 实例
    if (!socket) {
      console.error('LogManager: 没有提供 socket 实例');
      return;
    }
    
    this.socket = socket;
    console.log('LogManager: 使用提供的 socket 实例');
    
    this.logs = []; // 所有日志的缓存
    this.filteredLogs = []; // 过滤后的日志
    this.currentPage = 1;
    this.perPage = 100;
    this.filterText = '';
    this.filterType = 'text'; // 'text', 'device', 'tag', 'regex'
    this.currentDate = new Date().toISOString().split('T')[0]; // 当前日期 YYYY-MM-DD
    this.autoScroll = true;
    this.loadingLogs = false;
    this.showLogs = false;
    this.logsPanelWidth = '40%';
    
    // 回调函数
    this.onLogsUpdated = null;
    this.onFilterChanged = null;
    this.onVisibilityChanged = null;
    this.onWidthChanged = null;
    
    // 初始化Socket.IO事件监听
    this.initSocketEvents();
    
    console.log('LogManager 初始化完成');
  }
  
  // 初始化Socket.IO事件
  initSocketEvents() {
    console.log('初始化Socket.IO事件监听');
    
    // 调试所有接收到的事件
    this.socket.onAny((event, ...args) => {
      console.log(`LogManager 收到事件: ${event}`, args);
    });
    
    // 接收服务器加载的日志
    this.socket.on('S2B_LoadLogs', (data) => {
      if (!data || !data.logs) {
        console.error('收到无效的日志数据:', data);
        return;
      }

      // 直接使用服务器发送的结构化日志数据
      this.logs = data.logs; 
      this.currentDate = data.date;
      this.parseAndFilterLogs();
    });
    
    // 接收新增的日志
    this.socket.on('S2B_AddLog', (data) => {
      if (!data || !data.message) {
        console.error('收到无效的日志数据:', data);
        return;
      }

      this.logs.push(data);
      if (this.matchesFilter(data)) {
        this.filteredLogs.push(data);
        if (this.filteredLogs.length > this.perPage) {
          this.filteredLogs.shift();
        }

        this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);
      }
    });
  }
  
  // 解析日志条目
  parseLogEntry(logEntry) {
    if (!logEntry || typeof logEntry !== 'string') {
      console.error('无效的日志条目:', logEntry);
      return null;
    }
    
    try {
      // 使用正则表达式匹配新格式，所有部分都是可选的，但至少要有消息
      // 格式: "[HH:MM:SS]@@[tag]##[level]->[message]"
      const regex = /^(?:(\d{2}:\d{2}:\d{2}))?(?:@@([^#]*))?(?:##([^-]*))?(?:->)?(.+)$/;
      const match = logEntry.match(regex);
      
      if (match && match[4]) { // 确保至少有消息部分
        return {
          time: match[1] || new Date().toLocaleTimeString(),
          tag: match[2] || '@',
          level: match[3] || 'i',
          message: match[4]
        };
      }
      
      // 如果没有匹配到消息部分，则整个日志作为消息
      console.warn('无法解析日志格式，将整个日志作为消息:', logEntry);
      return {
        time: new Date().toLocaleTimeString(),
        tag: '@',
        level: 'i',
        message: logEntry
      };
    } catch (error) {
      console.error('解析日志时出错:', error, logEntry);
      return {
        time: new Date().toLocaleTimeString(),
        tag: '@',
        level: 'i',
        message: `[解析错误] ${logEntry}`
      };
    }
  }
  
  // 解析并过滤所有日志
  parseAndFilterLogs() {
    this.loadingLogs = true;
    
    // 解析所有日志
    const parsedLogs = this.logs
      .map(log => this.parseLogEntry(log))
      .filter(log => log !== null);
    
    console.log(`解析了 ${parsedLogs.length} 条日志`);
    
    // 应用过滤
    this.filteredLogs = parsedLogs.filter(log => this.matchesFilter(log));
    
    console.log(`过滤后剩余 ${this.filteredLogs.length} 条日志`);
    
    // 更新加载状态
    this.loadingLogs = false;
    
    // 触发日志更新事件
    this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);
  }
  
  // 检查日志是否匹配当前过滤条件
  matchesFilter(log) {
    if (!this.filterText) return true;
    
    const filter = this.filterText;
    
    if (filter.startsWith('@')) {
      // 按设备名过滤
      const deviceName = filter.substring(1).trim();
      return log.tag.includes(deviceName);
    } else if (filter.startsWith(':')) {
      // 按TAG过滤
      const tag = filter.substring(1).trim();
      return log.tag === tag;
    } else if (filter.startsWith('*')) {
      // 按正则表达式过滤
      try {
        const regexStr = filter.substring(1).trim();
        const regex = new RegExp(regexStr, 'i');
        return regex.test(`${log.time} ${log.tag} ${log.level} ${log.message}`);
      } catch (e) {
        console.error('正则表达式错误:', e);
        return false;
      }
    } else {
      // 按文本内容过滤
      const searchText = filter.toLowerCase();
      return log.message.toLowerCase().includes(searchText) || 
             log.tag.toLowerCase().includes(searchText);
    }
  }
  
  // 设置过滤条件
  setFilter(text) {
    this.filterText = text;
    this.parseAndFilterLogs();
    
    // 返回过滤器类型信息
    let filterInfo = {
      active: !!text,
      type: '文本',
      class: 'text-filter'
    };
    
    if (text) {
      if (text.startsWith('@')) {
        filterInfo.type = '设备';
        filterInfo.class = 'device-filter';
      } else if (text.startsWith(':')) {
        filterInfo.type = '标签';
        filterInfo.class = 'tag-filter';
      } else if (text.startsWith('*')) {
        filterInfo.type = '正则';
        filterInfo.class = 'regex-filter';
      }
    }
    
    // 通知过滤器变化
    this.onFilterChanged && this.onFilterChanged(filterInfo);
    
    return filterInfo;
  }
  
  // 获取当前页的日志
  getCurrentPageLogs() {
    const startIndex = (this.currentPage - 1) * this.perPage;
    const endIndex = startIndex + this.perPage;
    return this.filteredLogs.slice(startIndex, endIndex);
  }
  
  // 刷新日志显示
  refreshDisplay() {
    const logs = this.getCurrentPageLogs();
    const totalPages = Math.ceil(this.filteredLogs.length / this.perPage);
    
    // 更新UI显示
    this.updateLogDisplay(logs);
    this.updatePagination(this.currentPage, totalPages);
    this.updateLogCount();
  }
  
  // 更新日志计数信息
  updateLogCount() {
    const total = this.filteredLogs.length;
    const start = total > 0 ? (this.currentPage - 1) * this.perPage + 1 : 0;
    const end = Math.min(start + this.perPage - 1, total);
    
    // 更新UI显示
    document.getElementById('logCount').textContent = 
      `显示 ${start}-${end}/${total} 条日志`;
  }
  
  // 更新日志显示区域
  updateLogDisplay(logs) {
    const logContainer = document.getElementById('logs-container');
    logContainer.innerHTML = '';

    logs.forEach(log => {
      const logElement = document.createElement('div');
      logElement.className = `log-entry log-${log.level}`;
      logElement.innerHTML = `
        <span class="log-time">${log.time}</span>
        <span class="log-tag">${log.tag}</span>
        <span class="log-message">${log.message}</span>
      `;
      logContainer.appendChild(logElement);
    });

    logContainer.scrollTop = logContainer.scrollHeight;
  }
  
  // 更新分页控件
  updatePagination(currentPage, totalPages) {
    const paginationContainer = document.getElementById('pagination');
    paginationContainer.innerHTML = '';
    
    // 上一页按钮
    const prevButton = document.createElement('button');
    prevButton.textContent = '上一页';
    prevButton.disabled = currentPage <= 1;
    prevButton.onclick = () => this.goToPage(currentPage - 1);
    paginationContainer.appendChild(prevButton);
    
    // 页码按钮
    const maxButtons = 5;
    const startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    const endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    for (let i = startPage; i <= endPage; i++) {
      const pageButton = document.createElement('button');
      pageButton.textContent = i;
      pageButton.className = i === currentPage ? 'active' : '';
      pageButton.onclick = () => this.goToPage(i);
      paginationContainer.appendChild(pageButton);
    }
    
    // 下一页按钮
    const nextButton = document.createElement('button');
    nextButton.textContent = '下一页';
    nextButton.disabled = currentPage >= totalPages;
    nextButton.onclick = () => this.goToPage(currentPage + 1);
    paginationContainer.appendChild(nextButton);
  }
  
  // 跳转到指定页
  goToPage(page) {
    const totalPages = Math.ceil(this.filteredLogs.length / this.perPage);
    if (page < 1 || page > totalPages) return;
    
    this.currentPage = page;
    this.refreshDisplay();
  }
  
  // 加载指定日期的日志
  loadLogs(date) {
    this.currentDate = date;
    this.loadingLogs = true;
    this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);
    this.socket.emit('B2S_GetLogs', { date });
  }
  
  // 清空日志
  clearLogs() {
    this.logs = [];
    this.filteredLogs = [];
    this.currentPage = 1;
    this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);
    this.refreshDisplay();
  }
  
  // 处理日志滚动
  handleScroll(isAtBottom) {
    this.autoScroll = isAtBottom;
  }
  
  // 设置回调函数
  setCallbacks(callbacks) {
    console.log('设置回调函数:', callbacks);
    if (callbacks.onLogsUpdated) {
      this.onLogsUpdated = callbacks.onLogsUpdated;
      console.log('已设置 onLogsUpdated 回调');
    }
    if (callbacks.onFilterChanged) this.onFilterChanged = callbacks.onFilterChanged;
    if (callbacks.onVisibilityChanged) this.onVisibilityChanged = callbacks.onVisibilityChanged;
    if (callbacks.onWidthChanged) this.onWidthChanged = callbacks.onWidthChanged;
  }
  
  // 切换日志面板显示状态
  toggleVisibility() {
    this.showLogs = !this.showLogs;
    
    if (this.showLogs) {
      // 打开日志面板时加载日志
      this.loadLogs();
    }
    
    // 通知可见性变化
    this.onVisibilityChanged && this.onVisibilityChanged(this.showLogs);
    
    return this.showLogs;
  }
  
  // 设置日志面板宽度
  setWidth(width) {
    this.logsPanelWidth = width;
    this.onWidthChanged && this.onWidthChanged(width);
    return width;
  }
} 