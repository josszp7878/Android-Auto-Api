# 确保在导入其他模块前先执行monkey_patch
import eventlet
eventlet.monkey_patch()

# 现在可以安全地导入其他模块
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入并运行服务器
from server.run import main

if __name__ == "__main__":
    main() 