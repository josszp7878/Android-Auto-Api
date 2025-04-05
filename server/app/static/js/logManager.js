// 在文件顶部添加一个简单的控制台日志，确认文件被加载
console.log('LogManager.js 已加载');

/**
 * 日志管理器
 * 负责日志的加载、过滤、显示和交互
 */
class LogManager {
  static LOG_TYPES = {
    SYSTEM: 'SYSTEM',
    ERROR: 'ERROR',
    CMD: 'CMD',
    SCREEN: 'SCREEN'
  };

  constructor(socket) {
    // 初始化存根方法
    this.addLog = (level, tag, message) => {
      console.error('LogManager未完成初始化时被调用');
      return { level, tag, message };
    };

    // 确保socket存在
    if (!socket) {
      console.error('LogManager: 必须传入有效的socket实例');
      return;
    }
    this.socket = socket;

    // 重新绑定实际方法
    this.addLog = this._addLog.bind(this);
    this.handleScroll = this._handleScroll.bind(this);
    
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
    this.isScrolling = false; // 添加滚动状态标记
    this.scrollTimeout = null; // 滚动超时处理
    this.hasMoreLogs = false;
    
    // 回调函数
    this.onLogsUpdated = null;
    this.onFilterChanged = null;
    this.onVisibilityChanged = null;
    this.onWidthChanged = null;
    
    // 添加滚动状态变化回调
    this.onScrollStateChanged = null;
    
    // 新增命令历史缓存
    this.cmdHistoryCache = [];
    
    // 新增系统日志存储
    this._systemLogs = [];
    
    // 新增日志统计信息
    this._logStats = {
      start: 0,
      end: 0,
      total: 0
    };
    
    // 新增回调配置
    this.callbacks = {
      onLogsUpdated: null,
      onScrollToBottom: null,
      onStatsUpdated: null
    };
    
    // 初始化完成后才注册事件监听
    this._initComplete = true;
    this.initSocketEvents();
    
    // 新增指令历史请求
    this.socket.emit('B2S_GetCommands');
    
    console.log('LogManager 初始化完成');

    // 绑定方法上下文
    this.processCmdLog = this.processCmdLog.bind(this);
    this.scrollToBottom = this.scrollToBottom.bind(this);
  }
  
  // 实际addLog方法
  _addLog(data) {
    if (!data || !data.message) {
        console.error('收到无效的日志数据:', data);
        return;
    }

    // 确保count属性存在
    if (!data.count) {
        data.count = 1;
    }
    
    console.log('添加日志:', data);
    this.logs.push(data);
    if (this.matchesFilter(data)) {
        this.filteredLogs.push(data);
        if (this.filteredLogs.length > this.perPage) {
            this.filteredLogs.shift();
        }
        // 使用安全调用
        this.onLogsUpdated?.(this.filteredLogs);
    }
    this.processCmdLog(data);
    // 在日志面板中显示日志
    const logElement = this.renderLog(data);
    this._logContainer.appendChild(logElement);
    
    // 如果日志有result字段，显示结果
    if (data.result) {
        const resultElement = document.createElement('div');
        resultElement.className = `log-result log-${data.level}`;
        resultElement.textContent = ``;
        this._logContainer.appendChild(resultElement);
    }
    
    // 添加日志后直接滚动到底部
    if (this.autoScroll) {
        this.scrollToBottom();
    }
  }
  
  // 实际滚动处理方法
  _handleScroll(event) {
    // ...滚动处理逻辑
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

      this.logs = data.logs;
      this.hasMoreLogs = data.hasMore;
      this.currentDate = data.date;
      this.parseAndFilterLogs();
      this.scrollToBottom();
    });
    
    // 接收新增的日志
    this.socket.on('S2B_AddLog', (data) => {
      this._addLog(data);
    });
    
    // 添加日志编辑事件监听
    this.socket.on('S2B_EditLog', (data) => {
      // 找到最后一条日志并更新
      if (this.logs.length > 0) {
        const lastLog = this.logs[this.logs.length - 1];
        
        // 如果是日志对象，更新整个日志
        if (typeof data === 'object') {
          Object.assign(lastLog, data);
          
          // 确保count属性存在
          if (typeof lastLog.count === 'undefined') {
            lastLog.count = 1;
          }
          
          // 更新显示消息
          if (lastLog.count > 1) {
            lastLog.displayMessage = `${lastLog.message.split(' (+')[0]} (+${lastLog.count})`;
          } else {
            lastLog.displayMessage = lastLog.message;
          }
          
          // 添加调试日志
          console.log(`更新日志: ID=${lastLog.time}, 消息=${lastLog.message}, 计数=${lastLog.count}`);
          
          // 检查日志是否在当前视图中
          const isInCurrentView = this.filteredLogs.includes(lastLog);
          console.log(`日志是否在当前视图中: ${isInCurrentView}`);
          
          if (isInCurrentView) {
            // 只更新这一条日志，而不是所有日志
            this.updateSingleLog(lastLog);
          } else {
            // 如果不在当前视图中，可能需要更新过滤后的日志列表
            console.log('日志不在当前视图中，尝试更新过滤后的日志列表');
            // 重新应用过滤器
            this.parseAndFilterLogs();
          }
        }
      }
    });
  }
  
  // 添加单条日志更新方法
  updateSingleLog(log) {
    // 由于DOM元素可能没有data-log-id属性，我们需要使用其他方式找到对应的日志元素
    // 方法2: 如果没有Vue，尝试找到最后一个日志元素
    const logElements = document.querySelectorAll('.log-entry');
    if (logElements.length > 0) {
      // 尝试通过时间戳或其他唯一标识找到对应的日志元素
      let targetElement = null;
      
      // 首先尝试找到具有相同时间戳的日志元素
      if (log.time) {
        for (let i = logElements.length - 1; i >= 0; i--) {
          const timeElement = logElements[i].querySelector('.log-time');
          if (timeElement && timeElement.textContent.includes(log.time)) {
            targetElement = logElements[i];
            console.log('通过时间戳找到日志元素:', targetElement);
            break;
          }
        }
      }
      
      // 如果找不到，则使用最后一个元素
      if (!targetElement) {
        targetElement = logElements[logElements.length - 1];
        console.log('使用最后一个日志元素:', targetElement);
      }
      
      const messageElement = targetElement.querySelector('.log-message');
      if (messageElement) {
        console.log('更新消息元素内容');
        messageElement.textContent = log.displayMessage || log.message;
        
        // 如果有重复计数，添加视觉提示
        if (log.count > 1) {
          targetElement.classList.add('repeated-log');
        }
      }
    } else {
      console.log('未找到日志元素，可能需要完全刷新视图');
      // 如果找不到任何日志元素，可能需要完全刷新视图
      this.refreshDisplay();
    }
  }
  
  // 修改后的处理CMD日志方法
  processCmdLog(log) {
    // 只处理命令类型的日志
    if (log.level == 'c') {
      // 提取纯命令内容
      let commandText = log.message;
      
      // 处理格式为 "sender: command" 或 "sender→executor: command" 的消息
      const colonIndex = commandText.indexOf(': ');
      if (colonIndex > -1) {
        // 提取冒号后面的部分作为纯命令内容
        commandText = commandText.substring(colonIndex + 2);
      }
      
      // 将纯命令内容添加到历史记录
      if (commandText) {
        // 如果命令已存在，先移除它
        const existingIndex = this.cmdHistoryCache.indexOf(commandText);
        if (existingIndex !== -1) {
          this.cmdHistoryCache.splice(existingIndex, 1);
        }
        // 将命令添加到历史记录最前面
        this.cmdHistoryCache.unshift(commandText);
        // 限制历史记录数量
        if (this.cmdHistoryCache.length > 50) {
          this.cmdHistoryCache.pop();
        }
      }
    }
  }

  // 解析并过滤所有日志
  parseAndFilterLogs() {
    this.loadingLogs = true;
    
    // 重置命令缓存前保留现有命令
    const prevCache = [...this.cmdHistoryCache];
    this.cmdHistoryCache = [];
    
    this.logs.forEach(this.processCmdLog);
    
    // 合并新旧缓存（保留历史记录）
    this.cmdHistoryCache = [...new Set([...this.cmdHistoryCache, ...prevCache])].slice(0, 100);
    
    // 解析所有日志
    const parsedLogs = this.logs.filter(log => log !== null);
    
    console.log(`解析了 ${parsedLogs.length} 条日志`);
    
    // 应用过滤
    this.filteredLogs = parsedLogs.filter(log => this.matchesFilter(log));
    
    console.log(`过滤后剩余 ${this.filteredLogs.length} 条日志`);
    
    // 更新加载状态
    this.loadingLogs = false;
    
    // 触发日志更新事件
    this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);
    
    // 更新统计信息
    this._updateStats();
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
    // 如果正在滚动,不更新显示
    if(this.isScrolling) {
      return;
    }
    
    // 保存当前滚动位置
    const logContainer = document.querySelector('.console-logs');
    const scrollTop = logContainer.scrollTop;
    const wasAtBottom = (logContainer.scrollHeight - logContainer.scrollTop) === logContainer.clientHeight;

    // 确保所有日志都有正确的displayMessage属性
    this.filteredLogs.forEach(log => {
      if (log.count && log.count > 1) {
        // 确保不重复添加计数信息
        if (log.message.includes(' (+')) {
          log.displayMessage = log.message; // 已经包含计数信息
        } else {
          log.displayMessage = `${log.message} (+${log.count})`;
        }
      } else {
        log.displayMessage = log.message;
      }
    });

    // 更新日志显示
    this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);

    // 恢复滚动位置
    if(wasAtBottom) {
      logContainer.scrollTop = logContainer.scrollHeight;
    } else {
      logContainer.scrollTop = scrollTop;
    }
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
  updateLogDisplay() {
    // 如果使用Vue或其他框架，可能只需要触发数据更新
    // 例如：this.$forceUpdate();
    
    // 如果使用原生DOM操作，可能需要重新渲染日志列表
    const logsContainer = document.querySelector('.console-logs');
    if (logsContainer) {
      // 处理日志显示，添加重复计数显示
      this.filteredLogs.forEach(log => {
        // 确保count属性存在
        if (typeof log.count === 'undefined') {
          log.count = 1;
        }
        
        // 确保count属性存在且大于1
        if (log.count && parseInt(log.count) > 1) {
          console.log(`日志有重复: ${log.message}, 计数: ${log.count}`);
          // 添加显示属性
          log.displayMessage = `${log.message} (+${log.count})`;
        } else {
          log.displayMessage = log.message;
        }
      });
    }
    
    // 通知Vue或其他框架更新视图
    this.onLogsUpdated && this.onLogsUpdated(this.filteredLogs);
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
    this.logs = []; // 清空当前日志
    this.callbacks.onLogsUpdated && this.callbacks.onLogsUpdated([]);
    this.socket.emit('B2S_GetLogs', { date });
  }
  
  // 清空日志
  clearLogs() {
    this._systemLogs = [];
    this.logs = [];
    this.filteredLogs = [];
    this._updateStats();
    this.onLogsUpdated && this.onLogsUpdated([]);
    this.currentPage = 1;
    this.refreshDisplay();
  }
  
  // 处理日志滚动
  handleScroll(event) {
    if(this.scrollTimeout) {
        clearTimeout(this.scrollTimeout);
    }
    
    this.isScrolling = true;
    
    // 滚动结束后200ms恢复状态
    this.scrollTimeout = setTimeout(() => {
        this.isScrolling = false;
        // 如果在底部,恢复自动滚动
        const element = event.target;
        if(element.scrollHeight - element.scrollTop === element.clientHeight) {
            this.autoScroll = true;
        }
        
        // 通知 Vue 实例更新滚动状态
        if(this.onScrollStateChanged) {
            this.onScrollStateChanged(false);
        }
    }, 200);
    
    // 通知 Vue 实例更新滚动状态
    if(this.onScrollStateChanged) {
        this.onScrollStateChanged(true);
    }
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
    if (callbacks.onScrollStateChanged) {
        this.onScrollStateChanged = callbacks.onScrollStateChanged;
    }
    if (callbacks.onStatsUpdated) {
        this.callbacks.onStatsUpdated = callbacks.onStatsUpdated;
    }
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
  
  // 新增获取命令历史方法
  getCommandHistory() {
    return this.cmdHistoryCache;
  }
  
  // 更新统计信息
  _updateStats() {
    if (this._systemLogs.length === 0) return;
    
    this._logStats = {
      start: this._systemLogs[0].time,
      end: this._systemLogs[this._systemLogs.length - 1].time,
      total: this._systemLogs.length
    };
    this.callbacks.onStatsUpdated && this.callbacks.onStatsUpdated(this._logStats);
  }
  
  // 完善分页加载
  loadMoreLogs() {
    if (this.loadingLogs || !this.hasMoreLogs) return;
    
    this.loadingLogs = true;
    this.currentPage++;
    this.socket.emit('B2S_GetLogs', {
      date: this.currentDate,
      page: this.currentPage
    }, (response) => {
      if (response.success) {
        this.logs = [...this.logs, ...response.logs]; // 合并日志
        this.hasMoreLogs = response.hasMore;
        this.parseAndFilterLogs();
      }
      this.loadingLogs = false;
    });
  }
  
  // 新增统一接口
  get systemLogs() {
    return this._systemLogs; 
  }
  
  get logStats() {
    return this._logStats;
  }
  
  // 添加滚动到底部的方法
  scrollToBottom() {
    // 使用 setTimeout 确保在 DOM 更新后执行
    setTimeout(() => {
      const container = document.querySelector('.console-logs');
      if (container) {
        container.scrollTop = container.scrollHeight;
        this.autoScroll = true;
      }
    }, 0);
  }

  // 修改日志显示方法
  renderLog(log) {
    const logElement = document.createElement('div');
    logElement.className = `log-entry log-${log.level}`;
    
    // 创建时间标签
    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.textContent = log.time;
    logElement.appendChild(timeSpan);
    
    // 创建标签标签，不再使用方括号
    const tagSpan = document.createElement('span');
    tagSpan.className = 'log-tag';
    // 如果是命令日志，使用新的格式
    if (log.level === 'c' && log.tag) {
      tagSpan.textContent = `${log.tag}> `;
    } else {
      tagSpan.textContent = log.tag ? `${log.tag}> ` : '';
    }
    logElement.appendChild(tagSpan);
    
    // 创建消息标签
    const messageSpan = document.createElement('span');
    messageSpan.className = 'log-message';
    messageSpan.textContent = log.message;
    logElement.appendChild(messageSpan);
    
    // 如果有结果，添加结果显示
    if (log.result) {
      const resultDiv = document.createElement('div');
      resultDiv.className = `log-result log-${log.level}`;
      resultDiv.textContent = log.result;
      logElement.appendChild(resultDiv);
    }
    
    return logElement;
  }
} 