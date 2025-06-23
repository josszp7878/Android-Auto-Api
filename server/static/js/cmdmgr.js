/**
 * JavaScript版本的命令管理器
 * 仿照Python版本的_CmdMgr.py实现
 */

/**
 * 命令类，存储命令信息
 */
class Cmd {
    constructor(func, match = null, doc = null, module = 'default') {
        this.func = func;           // 命令函数
        this.match = match || func.name;    // 命令匹配模式
        this.doc = doc || func.toString();  // 命令文档
        this.module = module;       // 命令所属模块
        this.name = func.name;      // 函数名
        
        // 预编译完整正则表达式
        try {
            this.matchRegex = new RegExp(match, 'i');
        } catch (e) {
            console.error(`正则表达式编译错误 [${this.name}]:`, e);
            this.matchRegex = null;
        }
        
        // 预编译命令名正则表达式(从match中提取)
        this.nameRegex = null;
        if (match) {
            try {
                // 提取命令名部分 - 使用JavaScript风格的命名组
                const cmdKey = CmdMgr.CmdKey;
                const cmdMatches = match.match(new RegExp(`\\(\\?<${cmdKey}>(.*?)\\)`));
                if (cmdMatches) {
                    const searchPattern = cmdMatches[1];
                    // 创建搜索正则，用于_findCommand
                    this.nameRegex = new RegExp(`(${searchPattern})`, 'i');
                }
            } catch (e) {
                console.error(`命令名正则编译错误 [${this.name}]:`, e);
            }
        }
    }
}

/**
 * 命令管理器类
 */
class CmdMgr {
    static instance = null;
    
    // 按模块存储命令，格式: Map<模块名, Map<命令名, Cmd对象>>
    static cmdModules = new Map();
    
    // 模块优先级，数字越小优先级越高
    static modulePriority = new Map([
        ['core', 10],
        ['sheet', 20],
        ['default', 100]
    ]);
    
    // 命令关键字
    static CmdKey = 'CC';
    
    // 预编译正则表达式
    static SPACE_PATTERN = /\s+/g;
    
    // 已注册的模式项，用于检测雷同
    static registeredPatterns = new Map();
    
    /**
     * 单例模式
     */
    static getInstance() {
        if (!CmdMgr.instance) {
            CmdMgr.instance = new CmdMgr();
        }
        return CmdMgr.instance;
    }
    
    /**
     * 处理参数组，将参数包装为带空格的可选结构，并兼容命令和参数之间、参数前后所有空白
     * 用户写正则时只需写一个空格即可，系统自动处理为任意空白
     */
    static processParamSpaces(pattern) {
        try {
            let result = pattern;
            // 1. 命令头部允许任意空白
            result = result.replace(/^\s*/, ''); // 去除头部空白
            // 2. 参数捕获组前后允许空白，参数之间的空格全部替换为\s+
            // 查找所有参数捕获组（除了命令名CC组）- 使用JavaScript风格的命名组
            const paramPattern = /\s*\(\?<([^>]+)>([^)]+)\)(\??)\s*/g;
            result = result.replace(paramPattern, (match, paramName, paramContent, optional) => {
                // 如果是命令名捕获组，不处理
                if (paramName === CmdMgr.CmdKey) {
                    return match;
                }
                // 构建新的参数格式：允许前后空白，参数之间用\s+，所有参数都可选
                return `(?:\\s+(?<${paramName}>${paramContent}))?`;
            });
            // 3. 命令和第一个参数之间允许任意空白
            result = result.replace(/#(\S+)/, '#$1\\s*');
            // 4. 结尾允许多余空白
            return result;
        } catch (e) {
            console.error('processParamSpaces错误:', e, 'pattern:', pattern);
            return pattern;
        }
    }
    
    /**
     * 注册命令装饰器
     * 增强：自动在正则头部加^\\s*，结尾加\\s*$，参数间空白全部兼容
     */
    static reg(pattern, module = 'default') {
        return function(func) {
            const funcName = func.name;
            const abbr = funcName[0] + funcName.substring(1).replace(/[a-z]/g, '');
            
            let finalPattern = pattern;
            
            if (pattern.includes('#')) {
                // 使用正则表达式查找 #命令名|别名 格式
                const match = pattern.match(/\s*#([^\s\(]+)\s*/);
                if (match) {
                    const cmdPattern = match[0];
                    let cmdName = match[1];
                    
                    // 提取命令名的每个部分进行雷同检查
                    const cmdParts = cmdName.split('|');
                    // 添加函数名和缩写到检查列表
                    cmdParts.push(funcName.toLowerCase(), abbr.toLowerCase());
                    
                    // 检查是否有雷同匹配
                    for (const item of cmdParts) {
                        const normalizedItem = item.trim().toLowerCase();
                        if (CmdMgr.registeredPatterns.has(normalizedItem)) {
                            const existingCmd = CmdMgr.registeredPatterns.get(normalizedItem);
                            // 避免与自己比较
                            if (existingCmd !== funcName) {
                                console.error(`命令匹配模式雷同: '${normalizedItem}' 在 ${funcName} 和 ${existingCmd} 之间重复`);
                            }
                        } else {
                            CmdMgr.registeredPatterns.set(normalizedItem, funcName);
                        }
                    }
                    
                    // 始终添加函数名和缩写到命令别名中
                    cmdName = `${cmdName}|${funcName}|${abbr.toLowerCase()}`;
                    
                    // 替换命令名模式 - 使用JavaScript风格的命名组
                    const namePattern = `(?<${CmdMgr.CmdKey}>${cmdName})`;
                    finalPattern = pattern.replace(cmdPattern, namePattern);
                } else {
                    console.error(`${pattern} 没有匹配指令名`);
                    return func;
                }
            }
            
            // 将所有Python风格的命名组转换为JavaScript风格
            finalPattern = finalPattern.replace(/\(\?P<([^>]+)>/g, '(?<$1>');
            
            // 处理参数之间的空格（增强版）
            finalPattern = CmdMgr.processParamSpaces(finalPattern);
            
            // 添加开始和结束锚点，并允许头尾多余空白
            if (!finalPattern.startsWith('^')) {
                finalPattern = '^\\s*' + finalPattern;
            }
            if (!finalPattern.endsWith('$')) {
                finalPattern = finalPattern + '\\s*$';
            }
            
            // 测试正则表达式是否有效
            try {
                new RegExp(finalPattern, 'i');
            } catch (e) {
                console.error(`正则表达式编译错误 [${funcName}]:`, e, 'pattern:', finalPattern);
                return func;
            }
            
            // 创建命令对象并添加到注册表
            const cmd = new Cmd(func, finalPattern, func.toString(), module);
            CmdMgr._addCommand(cmd);
            
            return func;
        };
    }
    
    /**
     * 添加命令到模块命令集合
     */
    static _addCommand(cmd) {
        const moduleName = cmd.module;
        const funcName = cmd.name;
        
        // 查找或创建模块命令集合
        if (!CmdMgr.cmdModules.has(moduleName)) {
            CmdMgr.cmdModules.set(moduleName, new Map());
        }
        
        const moduleCommands = CmdMgr.cmdModules.get(moduleName);
        moduleCommands.set(funcName, cmd);
    }
    
    /**
     * 清除所有命令
     */
    static clear() {
        CmdMgr.cmdModules.clear();
        CmdMgr.registeredPatterns.clear();
    }
    
    /**
     * 按优先级对模块进行排序
     */
    static _sort() {
        // 更新所有模块的默认优先级
        for (const moduleName of CmdMgr.cmdModules.keys()) {
            if (!CmdMgr.modulePriority.has(moduleName)) {
                CmdMgr.modulePriority.set(moduleName, 100);
            }
        }
        
        // 转换为数组并排序
        const sortedModules = Array.from(CmdMgr.cmdModules.entries())
            .sort((a, b) => {
                const priorityA = CmdMgr.modulePriority.get(a[0]) || 999;
                const priorityB = CmdMgr.modulePriority.get(b[0]) || 999;
                return priorityA - priorityB;
            });
        
        // 重建cmdModules
        CmdMgr.cmdModules.clear();
        for (const [moduleName, commands] of sortedModules) {
            CmdMgr.cmdModules.set(moduleName, commands);
        }
    }
    
    /**
     * 查找命令
     */
    static _findCommand(cmdName, moduleName = null) {
        if (!cmdName) return null;
        
        cmdName = cmdName.toLowerCase();
        
        // 尝试匹配所有命令的正则表达式，找到最长的匹配
        let bestMatch = null;
        let bestMatchLength = -1;
        
        // 使用已排序的模块列表
        for (const [modName, moduleCommands] of CmdMgr.cmdModules) {
            if (moduleName && modName !== moduleName) {
                continue;
            }
            
            // 遍历模块中的所有命令
            for (const cmd of moduleCommands.values()) {
                // 使用预编译的正则表达式
                if (cmd.nameRegex) {
                    try {
                        const cmdMatches = cmd.nameRegex.exec(cmdName);
                        if (cmdMatches) {
                            const matchLength = cmdMatches[0].length;
                            if (matchLength > bestMatchLength) {
                                bestMatch = cmd;
                                bestMatchLength = matchLength;
                            }
                        }
                    } catch (e) {
                        console.error(`命令名匹配失败: ${cmd.name}`, e);
                    }
                } else {
                    // 如果没有预编译的正则表达式，尝试匹配函数名
                    if (cmd.name.toLowerCase() === cmdName) {
                        const matchLength = cmd.name.length;
                        if (matchLength > bestMatchLength) {
                            bestMatch = cmd;
                            bestMatchLength = matchLength;
                        }
                    }
                }
            }
        }
        
        return bestMatch;
    }
    
    /**
     * 清理参数值，去除多余空格
     */
    static _cleanParam(value) {
        if (value != null) {
            // 去除前后空格
            value = value.trim();
            // 替换多余空格为单个空格
            value = value.replace(CmdMgr.SPACE_PATTERN, ' ');
        }
        return value;
    }
    
    /**
     * 执行命令
     * @param {object} cmd - 命令对象
     * @returns {object} 执行结果
     */
    static async do(cmd) {
        // 清除cmd中的result
        delete cmd.result;
        
        if (!cmd) return cmd;
        
        let cmdStr = cmd.cmd || '';
        cmdStr = cmdStr.trim();
        if (cmdStr === '') return cmd;
        
        try {
            let bestMatch = null;
            let bestMatchLength = -1;
            let matchResult = null;
            
            // 使用已排序的模块列表
            for (const [moduleName, moduleCommands] of CmdMgr.cmdModules) {
                // 遍历模块中的所有命令
                for (const cmdObj of moduleCommands.values()) {
                    if (!cmdObj.matchRegex) continue;
                    
                    try {
                        // 使用预编译的正则表达式
                        const match = cmdObj.matchRegex.exec(cmdStr);
                        if (match) {
                            // 获取命令名匹配长度
                            const groups = CmdMgr._extractNamedGroups(match, cmdObj.matchRegex);
                            const cmdMatch = groups[CmdMgr.CmdKey];
                            const matchLength = cmdMatch ? cmdMatch.length : 0;
                            
                            if (matchLength > bestMatchLength) {
                                bestMatch = cmdObj;
                                matchResult = match;
                                bestMatchLength = matchLength;
                            }
                        }
                    } catch (e) {
                        console.error(`命令: ${cmdStr} 正则表达式错误: ${cmdObj.match}`, e);
                        continue;
                    }
                }
            }
            
            if (!bestMatch) {
                console.error(`命令: ${cmdStr} 未找到`);
                return null;
            }
            
            // 提取参数
            const groups = CmdMgr._extractNamedGroups(matchResult, bestMatch.matchRegex);
            const args = {};
            
            for (const [key, value] of Object.entries(groups)) {
                // 跳过命令关键字
                if (key !== CmdMgr.CmdKey) {
                    args[key] = CmdMgr._cleanParam(value);
                }
            }
            
            cmd.name = bestMatch.name.toLowerCase();
            
            // 合并参数
            const params = cmd.params || {};
            const finalArgs = { ...args, ...params, cmd };
            
            console.log(`执行命令 <${cmd.name}>: ${cmdStr}`);
            
            // 执行命令函数
            const result = await bestMatch.func(finalArgs);
            cmd.result = result;
            
            console.log('命令执行结果:', result);
            
        } catch (e) {
            console.error('执行命令出错:', cmdStr, e);
            cmd.result = `执行命令出错: ${e.message}`;
        }
        
        return cmd;
    }
    
    /**
     * 从正则匹配结果中提取命名组（模拟Python的groupdict）
     */
    static _extractNamedGroups(match, regex) {
        const groups = {};
        
        // JavaScript原生支持命名组，直接使用groups属性
        if (match.groups) {
            Object.assign(groups, match.groups);
        }
        
        return groups;
    }
    
    /**
     * 设置模块优先级
     */
    static setModulePriority(moduleName, priority) {
        CmdMgr.modulePriority.set(moduleName, priority);
        CmdMgr._sort();
    }
    
    /**
     * 获取帮助信息
     */
    static getHelp(commandName = null) {
        if (!commandName) {
            // 返回所有命令概览
            let result = '可用命令:\n';
            for (const [moduleName, commands] of CmdMgr.cmdModules) {
                result += `\n[模块: ${moduleName}]\n`;
                for (const cmd of commands.values()) {
                    result += `  ${cmd.name}: ${cmd.match}\n`;
                }
            }
            return result;
        } else {
            // 返回特定命令帮助
            const cmd = CmdMgr._findCommand(commandName);
            if (!cmd) {
                return `无效指令: ${commandName}`;
            }
            
            // 提取函数注释中的文档信息
            const docInfo = CmdMgr._extractFunctionDoc(cmd.func);
            
            let helpText = `命令: ${cmd.name}\n`;
            helpText += `正则: ${cmd.match}\n\n`;
            
            if (docInfo) {
                helpText += `功能: ${docInfo.功能 || '未定义'}\n`;
                helpText += `中文名: ${docInfo.中文名 || '未定义'}\n`;
                if (docInfo.参数 && docInfo.参数.length > 0) {
                    helpText += `参数:\n`;
                    docInfo.参数.forEach(param => {
                        helpText += `  ${param}\n`;
                    });
                }
                if (docInfo.示例 && docInfo.示例.length > 0) {
                    helpText += `示例:\n`;
                    docInfo.示例.forEach(example => {
                        helpText += `  ${example}\n`;
                    });
                }
            }
            
            return helpText;
        }
    }
    
    /**
     * 提取函数注释中的文档信息
     */
    static _extractFunctionDoc(func) {
        try {
            const funcStr = func.toString();
            
            // 查找函数内的注释块
            const commentMatch = funcStr.match(/\/\*\*([\s\S]*?)\*\//);
            if (!commentMatch) return null;
            
            const commentContent = commentMatch[1];
            const docInfo = {
                功能: null,
                指令名: null,
                中文名: null,
                参数: [],
                示例: []
            };
            
            // 解析注释内容
            const lines = commentContent.split('\n');
            let currentSection = null;
            
            for (let line of lines) {
                line = line.trim().replace(/^\*\s?/, ''); // 移除注释标记
                
                if (line.startsWith('功能：')) {
                    docInfo.功能 = line.substring(3).trim();
                } else if (line.startsWith('指令名：')) {
                    docInfo.指令名 = line.substring(4).trim();
                } else if (line.startsWith('中文名：')) {
                    docInfo.中文名 = line.substring(4).trim();
                } else if (line.startsWith('参数：')) {
                    currentSection = '参数';
                } else if (line.startsWith('示例：')) {
                    currentSection = '示例';
                    const example = line.substring(3).trim();
                    if (example) docInfo.示例.push(example);
                } else if (currentSection === '参数' && line.trim()) {
                    docInfo.参数.push(line.trim());
                } else if (currentSection === '示例' && line.trim()) {
                    docInfo.示例.push(line.trim());
                }
            }
            
            return docInfo;
        } catch (e) {
            console.error('解析函数文档失败:', e);
            return null;
        }
    }
}

// 创建全局注册函数
const regCmd = CmdMgr.reg;

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CmdMgr, Cmd, regCmd };
} else {
    window.CmdMgr = CmdMgr;
    window.Cmd = Cmd;
    window.regCmd = regCmd;
} 