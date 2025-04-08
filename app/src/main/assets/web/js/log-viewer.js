let logContainer = document.getElementById('log-container');
let autoScroll = true;
let logBuffer = []; // 用于存储日志内容

// 防止滚动事件清空日志
logContainer.addEventListener('scroll', function(e) {
    // 检测是否用户手动滚动
    if (logContainer.scrollHeight - logContainer.scrollTop > logContainer.clientHeight + 50) {
        autoScroll = false; // 用户向上滚动，暂停自动滚动
    } else {
        autoScroll = true; // 滚动到底部，恢复自动滚动
    }
    
    // 阻止默认行为和冒泡，防止触发其他事件
    e.stopPropagation();
});

// 添加日志的函数
function addLog(logText) {
    // 保存到缓冲区
    logBuffer.push(logText);
    
    // 限制缓冲区大小，防止内存占用过多
    if (logBuffer.length > 1000) {
        logBuffer.shift(); // 移除最旧的日志
    }
    // 更新显示
    updateLogDisplay();
}

// 更新日志显示
function updateLogDisplay() {
    // 保留当前滚动位置
    const wasAtBottom = autoScroll;
    const scrollTop = logContainer.scrollTop;
    
    // 更新内容
    logContainer.innerHTML = logBuffer.join('<br>');
    
    // 恢复滚动位置
    if (wasAtBottom) {
        logContainer.scrollTop = logContainer.scrollHeight;
    } else {
        logContainer.scrollTop = scrollTop;
    }
}

// 清空日志的函数
function clearLog() {
    logBuffer = [];
    logContainer.innerHTML = '';
    autoScroll = true;
}

// 监听清空按钮点击
document.getElementById('clear-log').addEventListener('click', clearLog);

// 日志增量加载
let lastLogIndex = 0;

// 定期刷新日志
function refreshLogs() {
    fetch(`/api/logs?start=${lastLogIndex}`)
        .then(response => response.json())
        .then(newLogs => {
            if (newLogs.length > 0) {
                // 添加新日志
                newLogs.forEach(log => addLog(log));
                lastLogIndex += newLogs.length;
            }
        })
        .catch(error => console.error('Error fetching logs:', error));
}

// 每秒刷新一次日志
setInterval(refreshLogs, 1000); 