"""
RPC API 迁移指南
从旧的 *args, **kwargs 格式迁移到新的 dict 参数格式

更新日期：2024年
"""

import _G

def migration_examples():
    """RPC API 迁移示例"""
    
    g = _G._G_
    
    print("=== RPC API 迁移指南 ===")
    print()
    
    print("1. 基本调用迁移：")
    print("旧格式：g.RPC(device_id, 'ClassName', 'methodName', arg1, arg2)")
    print("新格式：g.RPC(device_id, 'ClassName', 'methodName', {'args': [arg1, arg2]})")
    print()
    
    print("2. 带实例ID的调用迁移：")
    print("旧格式：g.RPC(device_id, 'ClassName', 'methodName', instance_id='id1', arg1, arg2)")
    print("新格式：g.RPC(device_id, 'ClassName', 'methodName', {'id': 'id1', 'args': [arg1, arg2]})")
    print()
    
    print("3. 带关键字参数的调用迁移：")
    print("旧格式：g.RPC(device_id, 'ClassName', 'methodName', arg1, key1=value1, key2=value2)")
    print("新格式：g.RPC(device_id, 'ClassName', 'methodName', {'args': [arg1], 'kwargs': {'key1': value1, 'key2': value2}})")
    print()
    
    print("4. 超时设置迁移：")
    print("旧格式：g.RPC(device_id, 'ClassName', 'methodName', arg1, timeout=15)")
    print("新格式：g.RPC(device_id, 'ClassName', 'methodName', {'args': [arg1], 'timeout': 15})")
    print()
    
    print("5. 复杂调用迁移：")
    print("旧格式：g.RPC(device_id, 'ClassName', 'methodName', instance_id='id1', arg1, arg2, key1=value1, timeout=20)")
    print("新格式：g.RPC(device_id, 'ClassName', 'methodName', {")
    print("    'id': 'id1',")
    print("    'args': [arg1, arg2],")
    print("    'kwargs': {'key1': value1},")
    print("    'timeout': 20")
    print("})")
    print()

def practical_migration_examples():
    """实际迁移示例"""
    
    g = _G._G_
    
    print("=== 实际代码迁移示例 ===")
    print()
    
    # 示例1：无参数调用
    print("示例1：无参数调用")
    print("旧：result = g.RPC(None, '_App_', 'getAppList')")
    print("新：result = g.RPC(None, '_App_', 'getAppList')  # 无变化")
    print()
    
    # 示例2：带参数调用
    print("示例2：带参数调用")
    print("旧：result = g.RPC(device_id, '_App_', 'getScores', date)")
    print("新：result = g.RPC(device_id, '_App_', 'getScores', {'args': [date]})")
    print()
    
    # 示例3：带实例ID调用
    print("示例3：带实例ID调用")
    print("旧：result = g.RPC(None, 'CDevice_', 'getDeviceInfo', instance_id='device123')")
    print("新：result = g.RPC(None, 'CDevice_', 'getDeviceInfo', {'id': 'device123'})")
    print()
    
    # 示例4：复杂调用
    print("示例4：复杂调用")
    print("旧：result = g.RPC(device_id, 'MyService', 'processData', instance_id='service1', [1,2,3], 'avg', timeout=15)")
    print("新：result = g.RPC(device_id, 'MyService', 'processData', {")
    print("    'id': 'service1',")
    print("    'args': [[1,2,3], 'avg'],")
    print("    'timeout': 15")
    print("})")
    print()

def migration_checklist():
    """迁移检查清单"""
    
    print("=== 迁移检查清单 ===")
    print()
    print("□ 1. 将所有位置参数包装到 'args' 列表中")
    print("□ 2. 将 instance_id 参数改为 'id' 键")
    print("□ 3. 将关键字参数包装到 'kwargs' 字典中")
    print("□ 4. 将 timeout 参数移到字典的顶层")
    print("□ 5. 测试所有RPC调用是否正常工作")
    print("□ 6. 更新相关文档和注释")
    print()

def automated_migration_helper():
    """自动化迁移辅助函数"""
    
    print("=== 自动化迁移辅助 ===")
    print()
    print("可以使用以下正则表达式来辅助迁移：")
    print()
    print("查找模式：")
    print("g\\.RPC\\(([^,]+),\\s*([^,]+),\\s*([^,]+),\\s*([^)]+)\\)")
    print()
    print("替换时需要手动分析第四个参数及后续参数的类型：")
    print("- 如果是 instance_id=value，改为 {'id': value}")
    print("- 如果是位置参数，改为 {'args': [...]}")
    print("- 如果是关键字参数，改为 {'kwargs': {...}}")
    print("- 如果是 timeout=value，改为 {'timeout': value}")
    print()

if __name__ == "__main__":
    migration_examples()
    practical_migration_examples()
    migration_checklist()
    automated_migration_helper() 