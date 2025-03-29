import sys
import _G

def Begin():
    """脚本引擎入口函数"""
    try:
        # 检查环境是否准备好
        from java import PythonServices
        if not hasattr(PythonServices, "isInitialized") or not PythonServices.isInitialized():
            print("Python服务尚未初始化，等待初始化完成...")
            return False
            
        # 初始化全局对象
        import _G
        _G.load()
        return True
    except Exception as e:
        print(f"初始化失败: {e}")
        return False

def End():
    try:
        import CClient
        CClient.CClient_.End()
    except Exception as e:
        _G._G_.Log().ex(e, f'End失败')


def main():
    # 命令行启动支持
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin()


if __name__ == '__main__':
    main()
