#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server', 'scripts'))

from datetime import datetime
from _App import _App_

def test_parseScore_json():
    """测试parseScore方法的JSON序列化"""
    print("=== 测试parseScore JSON序列化 ===")
    
    # 创建应用实例
    app = _App_("test", {})
    
    # 读取测试数据
    with open('server/data/result.json', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 测试解析
    filter_date = datetime(2025, 2, 25)
    try:
        results = app._parseScore(content, filter_date)
        print(f"解析成功，找到 {len(results)} 条记录")
        
        # 测试JSON序列化
        json_str = json.dumps(results, ensure_ascii=False, indent=2)
        print("JSON序列化成功！")
        print(f"JSON长度: {len(json_str)} 字符")
        
        # 显示前几条记录
        print("\n前几条记录:")
        for i, record in enumerate(results[:3]):
            print(f"  {i+1}. {record}")
            
        # 验证反序列化
        parsed_back = json.loads(json_str)
        print(f"\n反序列化成功，记录数: {len(parsed_back)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_parseScore_json()
    print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}") 