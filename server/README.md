# Android 远程控制系统

一个基于 WebSocket 的 Android 设备远程控制系统，支持多设备管理和命令执行。

## 系统架构

### 服务端 (server/)
- Flask + Flask-SocketIO 提供 WebSocket 服务
- Vue.js + Bootstrap 实现 Web 控制台
- SQLite 数据库保存设备信息

### 客户端 (client/)
- Python SocketIO 客户端
- 支持命令行测试和 Android 集成模式
- 基于 Chaquopy 实现 Python-Java 交互

## 核心功能

### 1. 设备管理
- 设备自动注册和状态监控
- 多设备并行管理
- 设备状态持久化存储

### 2. 命令系统
- 支持命令行测试和 APP 集成两种模式
- 内置多种设备控制命令：
  * 点击 <x> <y>: 模拟点击
  * 屏幕内容: 获取屏幕文本
  * 返回/主屏幕: 导航控制
  * 应用管理: 打开/关闭/安装/卸载
  * 截屏: 屏幕截图

### 3. Web 控制台
- 实时设备列表显示
- 命令输入和执行
- 命令历史记录
- 执行结果实时反馈

## 最近更新

### 1. 命令系统重构
- 添加条件编译支持
- 实现命令注册机制
- 支持命令行测试模式

### 2. 设备管理优化
- 改进设备状态同步
- 优化设备连接机制
- 添加设备信息持久化

### 3. 界面优化
- 添加命令控制台
- 优化设备选择机制
- 改进命令响应显示

## 待开发功能
1. 设备截图预览
2. 设备状态定时检查
3. 命令执行历史记录
4. 批量命令执行