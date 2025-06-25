# -*- coding: utf-8 -*-
"""
RPC 标准化格式使用指南

本文档说明了RPC方法的标准化返回格式规范，以及如何正确使用callRPC函数。

## RPC返回格式规范

所有RPC方法必须返回一个字典，包含以下键之一：

1. 成功时：{'result': 实际结果数据}
2. 失败时：{'error': 错误消息字符串}

## callRPC函数行为

callRPC函数会自动处理标准化返回格式：
- 如果RPC方法返回 {'error': '错误消息'}，callRPC会打印错误并返回None
- 如果RPC方法返回 {'result': 数据}，callRPC会返回数据部分
- 兼容旧格式 {'success': True/False, 'data': ...}

## 示例用法

### 1. RPC方法定义示例

```python
from RPC import RPC

class ExampleClass:
    @RPC()
    def getUserInfo(self, userId: str) -> dict:
        \"\"\"获取用户信息\"\"\"
        try:
            if not userId:
                return {
                    'error': '用户ID不能为空'
                }
            
            # 执行业务逻辑
            userInfo = self._queryUser(userId)
            if not userInfo:
                return {
                    'error': f'用户不存在: {userId}'
                }
            
            return {
                'result': {
                    'userId': userId,
                    'name': userInfo['name'],
                    'email': userInfo['email'],
                    'lastLogin': userInfo['lastLogin']
                }
            }
        except Exception as e:
            return {
                'error': f'获取用户信息失败: {str(e)}'
            }
    
    @RPC()
    def updateUserStatus(self, userId: str, status: str) -> dict:
        \"\"\"更新用户状态\"\"\"
        try:
            success = self._updateStatus(userId, status)
            if success:
                return {
                    'result': {
                        'userId': userId,
                        'newStatus': status,
                        'updateTime': datetime.now().isoformat()
                    }
                }
            else:
                return {
                    'error': f'更新用户状态失败: {userId}'
                }
        except Exception as e:
            return {
                'error': f'更新用户状态异常: {str(e)}'
            }
```

### 2. 调用RPC方法示例

```python
from RPC import callRPC

# 成功调用示例
userInfo = callRPC('device1', 'ExampleClass', 'getUserInfo', {
    'args': ['user123']
})
if userInfo:
    print(f"用户名: {userInfo['name']}")
    print(f"邮箱: {userInfo['email']}")
else:
    print("获取用户信息失败")  # callRPC已经打印了具体错误

# 失败调用示例
result = callRPC('device1', 'ExampleClass', 'getUserInfo', {
    'args': ['']  # 空用户ID，会导致错误
})
# 输出: RPC调用失败: ExampleClass.getUserInfo - 用户ID不能为空
# result = None

# 带参数的调用示例
updateResult = callRPC('device1', 'ExampleClass', 'updateUserStatus', {
    'args': ['user123', 'active']
})
if updateResult:
    print(f"状态更新成功: {updateResult['newStatus']}")
```

### 3. 已升级的RPC方法列表

以下RPC方法已经升级到标准格式：

#### _Device.py
- `getAppList()` - 获取设备的App列表

#### SDevice.py  
- `getDeviceInfo()` - 获取设备信息
- `captureScreen()` - 截屏
- `getScores(appName, date)` - 获取收益

#### CDevice.py
- `getDeviceInfo()` - 获取设备信息  
- `setDeviceName(name)` - 设置设备名称
- `getScore(appName, date)` - 获取收益

#### _App.py
- `getScores(date)` - 获取收益分数
- `getCurrentPageInfo()` - 获取当前页面信息
- `getAppList()` - 获取所有应用列表

### 4. 迁移指南

如果你有使用旧格式的RPC方法，请按以下步骤迁移：

#### 旧格式：
```python
@RPC()
def oldMethod(self):
    try:
        # 业务逻辑
        return {
            'success': True,
            'data': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

#### 新格式：
```python
@RPC()
def newMethod(self):
    try:
        # 业务逻辑
        return {
            'result': result
        }
    except Exception as e:
        return {
            'error': f'操作失败: {str(e)}'
        }
```

### 5. 注意事项

1. **错误消息**: 错误消息应该包含足够的上下文信息，便于调试
2. **类型提示**: 返回类型应该标注为 `-> dict`
3. **异常处理**: 所有RPC方法都应该有适当的异常处理
4. **兼容性**: callRPC函数仍然兼容旧格式，但建议尽快迁移到新格式

## 测试你的RPC方法

```python
# 测试RPC方法是否符合标准格式
def test_rpc_method():
    result = your_rpc_method()
    
    # 检查返回值是否为字典
    assert isinstance(result, dict), "RPC方法必须返回字典"
    
    # 检查是否包含正确的键
    assert 'result' in result or 'error' in result, "返回字典必须包含'result'或'error'键"
    
    # 检查不应该同时包含两个键
    assert not ('result' in result and 'error' in result), "不应该同时包含'result'和'error'键"
    
    print("RPC方法格式检查通过!")
```

## 更新日志

- 2025-01-XX: 实施RPC标准化格式规范
- 修改了callRPC函数以支持新格式
- 升级了主要RPC方法到新格式
- 保持了向后兼容性
""" 