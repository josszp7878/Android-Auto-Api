"""
坐标转换工具类 - 解决OCR截屏坐标与无障碍服务点击坐标不匹配问题
"""

from _G import _G_


class CoordinateConverter_:
    """坐标转换工具类 - 解决截屏坐标与点击坐标不匹配问题"""
    
    def __init__(self):
        self.screenWidth = 0
        self.screenHeight = 0
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.statusBarHeight = 0
        self.navigationBarHeight = 0
        self.isInitialized = False
        self._init()
        
    def _init(self):
        """初始化屏幕信息"""
        log = _G_.Log()
        log.i("开始初始化坐标转换器")
        
        try:
            # 优先尝试Java层接口
            if self.initFromJava():
                log.i("使用Java层接口初始化成功")
                self.isInitialized = True
                return
            
            # Java层失败则使用默认值
            log.w("Java层接口失败，使用默认参数")
            self.setDefaultValues()
            
        except Exception as e:
            log.ex(e, "初始化屏幕信息失败，使用默认参数")
            self.setDefaultValues()
    
    def initFromJava(self):
        """从Java层获取屏幕参数"""
        log = _G_.Log()
        try:
            # 检查是否有android对象
            android = _G_.android
            if android is None:
                log.w("Android对象未初始化")
                return False
            
            # 调用Java层的getScreenParams方法
            params = android.getScreenParams()
            if params is None:
                log.w("Java层getScreenParams返回None")
                return False
            
            # 检查是否有错误
            if 'error' in params:
                log.w(f"Java层返回错误: {params['error']}")
                return False
            
            # 提取参数
            self.screenWidth = params.get('screenWidth', 0)
            self.screenHeight = params.get('screenHeight', 0)
            self.statusBarHeight = params.get('statusBarHeight', 0)
            self.navigationBarHeight = params.get('navigationBarHeight', 0)
            self.windowWidth = params.get('windowWidth', 0)
            self.windowHeight = params.get('windowHeight', 0)
            
            # 验证参数有效性
            if self.screenWidth <= 0 or self.screenHeight <= 0:
                log.w(f"Java层返回无效屏幕尺寸: "
                      f"{self.screenWidth}x{self.screenHeight}")
                return False
            
            log.i("Java层屏幕参数:")
            log.i(f"  屏幕尺寸: {self.screenWidth}x{self.screenHeight}")
            log.i(f"  状态栏高度: {self.statusBarHeight}")
            log.i(f"  导航栏高度: {self.navigationBarHeight}")
            log.i(f"  窗口尺寸: {self.windowWidth}x{self.windowHeight}")
            log.i(f"  DPI: {params.get('densityDpi', 'N/A')}")
            device_info = (f"{params.get('manufacturer', 'N/A')} "
                           f"{params.get('model', 'N/A')}")
            log.i(f"  设备: {device_info}")
            
            return True
            
        except Exception as e:
            log.ex(e, "Java层获取屏幕参数失败")
            return False
    
    def setDefaultValues(self):
        """设置默认值"""
        log = _G_.Log()
        self.screenWidth = 1080
        self.screenHeight = 2400
        self.statusBarHeight = 30
        self.navigationBarHeight = 56
        self.windowWidth = self.screenWidth
        self.windowHeight = (self.screenHeight - self.statusBarHeight - 
                             self.navigationBarHeight)
        
        log.i("使用默认屏幕参数:")
        log.i(f"  屏幕尺寸: {self.screenWidth}x{self.screenHeight}")
        log.i(f"  状态栏高度: {self.statusBarHeight}")
        log.i(f"  导航栏高度: {self.navigationBarHeight}")
        log.i(f"  窗口尺寸: {self.windowWidth}x{self.windowHeight}")
        
        self.isInitialized = True
    
    def updateScreenshotScale(self, screenshotWidth, screenshotHeight):
        """更新截屏缩放比例"""
        if self.screenWidth > 0 and self.screenHeight > 0:
            self.scaleX = self.screenWidth / screenshotWidth
            self.scaleY = self.screenHeight / screenshotHeight
            _G_.Log().log(f"截屏缩放比例: X={self.scaleX:.3f}, "
                          f"Y={self.scaleY:.3f}")
    
    def screenToWindow(self, screenX, screenY):
        """屏幕坐标转窗口坐标 - 核心转换方法
        
        Args:
            screenX: OCR识别的屏幕X坐标
            screenY: OCR识别的屏幕Y坐标
            
        Returns:
            tuple: (windowX, windowY) 无障碍服务可用的窗口坐标
        """
        try:
            if not self.isInitialized:
                _G_.Log().log("坐标转换器未初始化，使用原始坐标")
                return int(screenX), int(screenY)
            
            # 1. 应用缩放比例（如果截屏经过缩放）
            realX = screenX * self.scaleX
            realY = screenY * self.scaleY
            
            # 2. 坐标系统修正（根据实际测试修复）
            # 实际测试发现：OCR识别的坐标需要加上偏移量才能正确点击
            # 这可能是因为OCR基于的坐标系统与无障碍服务的坐标系统不一致
            windowX = realX
            windowY = realY + self.statusBarHeight  # 改为加上状态栏高度
            
            # 3. 边界检查
            windowX = max(0, min(windowX, self.screenWidth - 1))
            windowY = max(0, min(windowY, self.screenHeight - 1))
            
            msg = f"坐标转换: 屏幕({screenX},{screenY}) -> " \
                  f"窗口({windowX:.0f},{windowY:.0f})"
            _G_.Log().log(msg)
            
            return int(windowX), int(windowY)
            
        except Exception as e:
            _G_.Log().ex(e, "坐标转换失败")
            return int(screenX), int(screenY)
    
    def windowToScreen(self, windowX, windowY):
        """窗口坐标转屏幕坐标（用于验证）"""
        try:
            # 减去状态栏高度
            screenX = windowX
            screenY = windowY - self.statusBarHeight
            
            # 应用缩放比例
            if self.scaleX > 0 and self.scaleY > 0:
                screenX = screenX / self.scaleX
                screenY = screenY / self.scaleY
            
            return int(screenX), int(screenY)
            
        except Exception as e:
            _G_.Log().ex(e, "坐标反转换失败")
            return int(windowX), int(windowY)
    
    def getScreenInfo(self):
        """获取屏幕信息（用于调试）"""
        return {
            'screenWidth': self.screenWidth,
            'screenHeight': self.screenHeight,
            'statusBarHeight': self.statusBarHeight,
            'navigationBarHeight': self.navigationBarHeight,
            'windowWidth': self.windowWidth,
            'windowHeight': self.windowHeight,
            'scaleX': self.scaleX,
            'scaleY': self.scaleY,
            'isInitialized': self.isInitialized
        }
