import re
import sys

def test_toPos(strPos):
    """解析位置字符串，支持多种格式
    
    格式说明:
    - 纯坐标: "100,200" -> (None, (100,200,None,None))
    - 文本+坐标: "文本100,-50" -> ("文本", (100,-50,None,None))
    - 单轴坐标: "文本y-100" -> ("文本", (None,-100,None,None))
    - 单轴多值: "文本y-100,50" -> ("文本", (None,-100,None,50)) (50也解析为y轴)
    - 双轴坐标: "文本x100,y-50" -> ("文本", (100,-50,None,None))
    - 多坐标: "文本100,200,300,400" -> ("文本", (100,200,300,400))
    """
    try:
        if not strPos or not strPos.strip():
            return None, None
        
        # 1. 预处理：去掉所有括号和空格
        text = strPos.strip()
        # 去掉所有括号
        text = re.sub(r'[\(（\)）]', '', text)
        
        # 2. 检查是否是纯坐标形式 (如 "100,200")
        if re.match(r'^\d+\s*,\s*\d+$', text):
            values = [int(v.strip()) for v in text.split(',')]
            return None, (values[0], values[1], None, None)
        
        # 3. 查找第一个坐标标识出现的位置
        coords_match = re.search(r'([xXyY][-+]?\d+)|(\d+,)', text)
        
        if not coords_match:
            # 检查是否有单个数字结尾
            num_match = re.search(r'(\d+)$', text)
            if num_match:
                # 提取文本和坐标
                pos = num_match.start()
                coord_part = text[pos:]
                text_part = text[:pos].strip()
                
                # 处理单个数字结尾
                values = [int(coord_part), None, None, None]
                return text_part, tuple(values)
            # 无坐标信息
            return text, None
            
        # 4. 分离文本和坐标
        pos = coords_match.start()
        coord_part = text[pos:]
        text_part = text[:pos].strip()
        
        # 5. 初始化坐标数组
        coords = [None, None, None, None]
        
        # 6. 查找所有轴标识和数字
        axis_values = re.findall(r'([xXyY])([-+]?\d+)', coord_part)
        
        # 7. 处理所有轴标识
        has_x = False
        has_y = False
        
        for axis, value in axis_values:
            value = int(value)
            if axis.upper() == 'X':
                has_x = True
                # 放入第一个空的X轴位置
                if coords[0] is None:
                    coords[0] = value
                elif coords[2] is None:
                    coords[2] = value
            else:  # Y轴
                has_y = True
                # 放入第一个空的Y轴位置
                if coords[1] is None:
                    coords[1] = value
                elif coords[3] is None:
                    coords[3] = value
        
        # 8. 正确提取纯数字
        # 排除跟在x或y后面的数字，只提取独立的数字
        # 使用更精确的正则表达式来匹配独立数字
        # 方法：先提取所有数字，然后排除掉跟在x或y后面的数字
        all_numbers = re.findall(r'([-+]?\d+)', coord_part)
        axis_numbers = [match[1] for match in axis_values]  # 已处理的带轴标识的数字
        
        # 只保留不是轴标识一部分的数字
        plain_values = []
        for num in all_numbers:
            if num not in axis_numbers:
                plain_values.append(num)
        
        # 9. 处理这些数字
        if plain_values:
            # 单轴模式
            if has_x and not has_y:
                # 只有X轴，其他数字也视为X轴
                x_idx = 0 if coords[0] is None else 2
                for val in plain_values:
                    if x_idx <= 2:
                        coords[x_idx] = int(val)
                        x_idx += 2
            elif has_y and not has_x:
                # 只有Y轴，其他数字也视为Y轴
                y_idx = 1 if coords[1] is None else 3
                for val in plain_values:
                    if y_idx <= 3:
                        coords[y_idx] = int(val)
                        y_idx += 2
            else:
                # 无轴或双轴模式，按顺序填充
                idx = 0
                for val in plain_values:
                    while idx < 4 and coords[idx] is not None:
                        idx += 1
                    if idx < 4:
                        coords[idx] = int(val)
                        idx += 1
        
        # 10. 返回结果
        return text_part, tuple(coords)
        
    except Exception as e:
        print(f"解析位置字符串失败: {strPos}, 错误: {e}")
        return None, None

# 测试用例
test_cases = [
    "100,200",                      # 纯坐标
    "文本100,-50",                  # 文本+坐标
    "文本(100,-50)",                # 带括号
    "文本 (100, -50)",              # 带括号和空格
    "文本x100",                     # 单X轴
    "文本y-100",                    # 单Y轴
    "文本(x100)",                   # 带括号的单X轴
    "文本(y-100)",                  # 带括号的单Y轴
    "文本x100,200",                 # X轴+数字
    "文本y-100,50",                 # Y轴+数字 (50应被视为y轴的值)
    "文本(y-100,50)",               # 带括号的Y轴+数字
    "文本x100,y-50",                # 双轴
    "文本(x100,y-50)",              # 带括号的双轴
    "文本100,200,300,400",          # 多坐标
    "文本(100,200,300,400)",        # 带括号的多坐标
    "去.钱y-100",                   # 现实场景示例1
    "去.钱(y-100)",                 # 现实场景示例2
    "Confirm Button(x300,y500)"     # 英文文本示例
]

def run_tests():
    for i, test in enumerate(test_cases, 1):
        result = test_toPos(test)
        print(f"测试 {i}: '{test}' => {result}")

def test_single(input_str):
    result = test_toPos(input_str)
    print(f"解析 '{input_str}' => {result}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 如果提供了命令行参数，测试该参数
        test_single(sys.argv[1])
    else:
        # 否则运行所有测试用例
        run_tests()
