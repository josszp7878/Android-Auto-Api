package cn.vove7.andro_accessibility_api.demo.script

import android.annotation.SuppressLint
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import android.view.Gravity
import cn.vove7.andro_accessibility_api.demo.MainActivity
import cn.vove7.andro_accessibility_api.demo.service.ScreenCapture
import cn.vove7.auto.AutoApi
import cn.vove7.auto.api.back
import cn.vove7.auto.api.click as clickAt
import cn.vove7.auto.api.home
import cn.vove7.auto.viewfinder.ScreenTextFinder
import cn.vove7.auto.viewnode.ViewNode
import kotlinx.coroutines.runBlocking
import java.io.File
import com.chaquo.python.PyObject
import androidx.core.content.ContextCompat
import cn.vove7.andro_accessibility_api.demo.service.ToolBarService
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import cn.vove7.auto.api.swipe as gestureSwipe
import android.view.accessibility.AccessibilityNodeInfo
import android.app.usage.UsageStats
import android.app.usage.UsageStatsManager
import android.app.usage.UsageEvents
import android.os.UserManager
import androidx.annotation.RequiresApi
import java.lang.ref.WeakReference
import android.os.Process
import timber.log.Timber
import android.view.WindowManager
import android.util.DisplayMetrics

/**
 * Python服务接口的Kotlin实现
 */
class PythonServices {
    @Suppress("DEPRECATION")
    companion object {
        private const val TAG = "PythonServices"

        @SuppressLint("StaticFieldLeak")
        private lateinit var context: MainActivity

        // 缓存应用的包名和显示名称
        private val appNameToPackageMap = mutableMapOf<String, String>()

        // 在companion object中添加常用桌面包名列表
        @JvmStatic
        private val LAUNCHER_PACKAGES = setOf(
            "com.android.launcher3",         // 原生Android
            "com.google.android.apps.nexuslauncher", // Pixel
            "com.sec.android.app.launcher",  // 三星
            "com.huawei.android.launcher",   // 华为
            "com.miui.home",                 // 小米
            "com.oppo.launcher",             // OPPO
            "com.vivo.launcher",             // vivo
            "com.realme.launcher",           // Realme
            "com.oneplus.launcher"           // 一加
        )

        private var contextRef: WeakReference<Context>? = null

        // 修改PythonServices.kt中的回调注册方法
        private var inputCallback: PyObject? = null

        // 添加一个标志，表示是否已经显示过权限提示
        private var permissionAlertShown = false        

        /**
         * 初始化 Context 和应用信息
         */
        @JvmStatic
        fun init(context: MainActivity) {
            this.context = context
            loadInstalledApps()
            contextRef = WeakReference(context.applicationContext)
            ToolBarService.logI("PythonServices 初始化完成")
        }

        @JvmStatic
        fun checkPermission(permission: String): Boolean {
            val result = when {
                permission == "android.permission.PACKAGE_USAGE_STATS" -> {
                    val appContext = context.applicationContext
                    val pm = appContext.packageManager
                    val mode = pm.checkPermission(
                        permission,
                        appContext.packageName
                    )
                    mode == PackageManager.PERMISSION_GRANTED
                }
                else -> ContextCompat.checkSelfPermission(context, permission) == 
                       PackageManager.PERMISSION_GRANTED
            }
            
            // 如果权限被拒绝，但还没有显示过提示，则显示一次提示
            if (!result && !permissionAlertShown) {
                toast("Permission denied: ${permission.substringAfterLast(".")}")
                permissionAlertShown = true // 标记已经显示过提示
            }
            
            return result
        }
        /**
         * 加载已安装应用的信息
         */
        @SuppressLint("QueryPermissionsNeeded")
        private fun loadInstalledApps() {
            val packageManager = context.packageManager
            val packages = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getInstalledPackages(
                    PackageManager.PackageInfoFlags.of(
                        PackageManager.GET_META_DATA.toLong()
                    )
                )
            } else {
                packageManager.getInstalledPackages(PackageManager.GET_META_DATA)
            }
            for (packageInfo in packages) {
                val appName =
                    packageManager.getApplicationLabel(packageInfo.applicationInfo).toString()
//                Timber.tag(TAG).i("Found app: %s, package: %s", appName, packageInfo.packageName)
                appNameToPackageMap[appName] = packageInfo.packageName
            }
        }

        /**
         * 通过显示名称获取包名
         */
        @JvmStatic
        fun getPackageName(appName: String): String? {
            return appNameToPackageMap[appName]
        }

        /**
         * 点击屏幕指定位置
         * 使用gesture_api中的click实现
         */
        @JvmStatic
        fun click(x: Int, y: Int): Boolean {
            return try {
                showUI(false)
                runBlocking {
                    clickAt(x, y)
                    ToolBarService.logI("点击位置: $x, $y")
                }
                true
            } catch (e: Exception) {
                ToolBarService.logEx(e,"点击位置失败: $x, $y")
                false
            } finally {
                showUI(true)
            }
        }
        /**
         * 滑动屏幕
         */
        @JvmStatic
        fun swipe(x: Int, y: Int, toX: Int, toY: Int, duration: Int): Boolean {
            return try {
                showUI(false)
                runBlocking {
                    gestureSwipe(x, y, toX, toY, duration)
                    ToolBarService.logI("滑动位置: $x, $y, $toX, $toY, $duration")
                }
                true
            } catch (e: Exception) {
                ToolBarService.logEx(e, "滑动失败: $x, $y, $toX, $toY, $duration")
                false
            } finally {
                showUI(true)
            }
        }
        @JvmStatic
        fun move(x: Int, y: Int): Boolean {
            return try {
                ToolBarService.getInstance()?.get()?.moveCursor(x, y)
                true
            } catch (e: Exception) {
                ToolBarService.logEx(e, "移动失败: $x, $y", "move")
                false
            }
        }
        /**
         * 返回上一个界面
         */
        @JvmStatic
        fun goBack(): Boolean {
            ToolBarService.logI("返回上一个界面")
            return back();
        }

        /**
         * 返回主屏幕
         */
        @JvmStatic
        fun goHome(): Boolean {
            ToolBarService.logI("返回主屏幕")
            return home()
        }

        /**
         * 打开指定的APP
         */
        @JvmStatic
        fun openApp(appName: String): Boolean {
            val packageName = getPackageName(appName)
            if (packageName == null) {
                Timber.tag(TAG).e("App not found: $appName")
                return false
            }

            Timber.tag(TAG).i("Attempting to open app: %s with package: %s", appName, packageName)

            // 使用 AutoApi 启动应用
            return try {
                AutoApi.launchPackage(packageName)

                // 等待并检查启动结果
                Thread.sleep(1000)
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                val isNowRunning =
                    am.runningAppProcesses?.any { it.processName == packageName } ?: false
                Timber.tag(TAG).d("App running state after launch: %s", isNowRunning)

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val foregroundApp =
                        am.appTasks.firstOrNull()?.taskInfo?.topActivity?.packageName
                    Timber.tag(TAG).d("Current foreground app: %s", foregroundApp)
                }

                true
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Failed to launch app using AutoApi")
                false
            }
        }

        /**
         * 关闭指定的APP
         */
        @JvmStatic
        fun closeApp(appName: String): Boolean {
            val packageName = getPackageName(appName)
            if (packageName == null) {
                Timber.tag(TAG).e("App not found: $appName")
                return false
            }
            Timber.tag(TAG).i("Close app: $appName")
            return try {
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                am.killBackgroundProcesses(packageName)
                true
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Close app failed")
                false
            }
        }

        /**
         * 检查指定APP是否安装
         */
        @JvmStatic
        fun isAppInstalled(appName: String): Boolean {
            val packageName = getPackageName(appName)
            if (packageName == null) {
                Timber.tag(TAG).e("App not found: $appName")
                return false
            }
            Timber.tag(TAG).i("Check if app is installed: $appName")
            return try {
                context.packageManager.getPackageInfo(packageName, 0)
                true
            } catch (e: PackageManager.NameNotFoundException) {
                Timber.tag(TAG).e("App not installed: $appName")
                false
            }
        }

        /**
         * 卸载指定的APP
         */
        @JvmStatic
        fun uninstallApp(appName: String): Boolean {
            val packageName = getPackageName(appName)
            if (packageName == null) {
                Timber.tag(TAG).e("App not found: $appName")
                return false
            }
            Timber.tag(TAG).i("Uninstall app: $appName")
            return try {
                val intent = Intent(Intent.ACTION_DELETE)
                intent.data = Uri.parse("package:$packageName")
                context.startActivity(intent)
                true
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Uninstall app failed")
                false
            }
        }

        /**
         * 安装指定的APP
         */
        @JvmStatic
        fun installApp(apkFileName: String): Boolean {
            Timber.tag(TAG).i("Install app: $apkFileName")
            return try {
                val file = File(context.getExternalFilesDir(null), apkFileName)
                if (file.exists()) {
                    val intent = Intent(Intent.ACTION_VIEW)
                    intent.setDataAndType(
                        Uri.fromFile(file),
                        "application/vnd.android.package-archive"
                    )
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    context.startActivity(intent)
                    true
                } else {
                    Timber.tag(TAG).e("APK file not found: $apkFileName")
                    false
                }
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Install app failed")
                false
            }
        }

        @JvmStatic
        fun findTextNodes(): Array<ViewNode> {
            return try {
                runBlocking {
                    ScreenTextFinder().find()
                }
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Failed to find text nodes")
                emptyArray()
            }
        }

        @JvmStatic
        fun getFilesDir(subDir: String? = null, create: Boolean = false): String {
            val baseDir = context.filesDir
            return when {
                subDir == null -> baseDir.absolutePath
                create -> {
                    val dir = File(baseDir, subDir)
                    if (!dir.exists() && create) {
                        try {
                            dir.mkdirs()
                        } catch (e: Exception) {
                            Timber.tag(TAG).e(e, "创建目录失败: %s", subDir)
                        }
                    }
                    dir.absolutePath
                }
                else -> File(baseDir, subDir).absolutePath
            }
        }

        /**
         * 唤起应用切换界面
         */
        @JvmStatic
        fun showRecentApps(): Boolean {
            Timber.tag(TAG).i("Show recent apps")
            return try {
                // 使用 AutoApi 调用系统的最近任务界面
                AutoApi.recents()
                
                // 等待界面切换
                Thread.sleep(200)
                
                // 检查是否成功切换到最近任务界面
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val currentApp = am.appTasks.firstOrNull()?.taskInfo?.topActivity?.packageName
                    val isRecentScreen = currentApp?.contains("systemui") == true || 
                                       currentApp?.contains("launcher") == true
                    Timber.tag(TAG).d("Current app after showing recents: %s", currentApp)
                    isRecentScreen
                } else {
                    true
                }
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Show recent apps failed")
                false
            }
        }

 

        /**
         * 截屏
         */
        @JvmStatic
        fun takeScreenshot(): String {
            // Timber.tag(TAG).i("Taking screenshot using ScreenCapture service")
            return try {
                val result = ScreenCapture.getInstance().captureScreen()
                return result
            } catch (e: SecurityException) {
                Timber.tag(TAG).e(e, "权限不足，无法截屏")
                "截屏失败: 权限不足"
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Take screenshot failed")
                "截屏失败: ${e.message}"
            }
        }

        /**
         * 获取屏幕信息
         * @param withPos 是否返回文本位置
         * @return 屏幕信息
         */
        @JvmStatic
        fun _getScreenInfo(withPos: Boolean = false): Any? {
            try {
                // 隐藏界面，避免影响屏幕内容识别
                // 延迟一小段时间，确保界面完全隐藏
                // Thread.sleep(100)
                
                val screenCapture = ScreenCapture.getInstance()
                var result: Any? = null
                val latch = CountDownLatch(1)
                
                screenCapture?.recognizeText({ text ->
                    result = text
                    latch.countDown()
                }, withPos)
                
                // 等待异步操作完成，最多等待10秒
                val success = latch.await(10, TimeUnit.SECONDS)
                if (!success) {
                    ToolBarService.logE("屏幕识别超时")
                    return null
                }
                
                return result
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "获取屏幕信息失败: ${e.message}")
                ToolBarService.logEx(e, "获取屏幕信息失败")
                return null
            }
        }

        /**
         * 获取屏幕文本
         * @return 屏幕文本
         */
        @JvmStatic
        fun getScreenText(): String {
            val result = _getScreenInfo(false)
            return if (result is String) result else ""
        }

        /**
         * 获取屏幕文本和位置
         * @param withPos 是否返回文本位置
         * @return 屏幕信息
         */
        @JvmStatic
        fun getScreenInfo(): List<Map<String, String>> {
            val result = mutableListOf<Map<String, String>>()
            try {
                val textBlockInfos = _getScreenInfo(true)
                if (textBlockInfos is List<*>) {
                    @Suppress("UNCHECKED_CAST")
                    val typedList = textBlockInfos as List<ScreenCapture.TextBlockInfo>
                    result.addAll(typedList.map { textBlockInfo ->
                        mapOf(
                            "t" to textBlockInfo.text,
                            "b" to "${textBlockInfo.bounds.left},${textBlockInfo.bounds.top},${textBlockInfo.bounds.right},${textBlockInfo.bounds.bottom}"
                        )
                    })
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "处理屏幕信息失败")
            }
            return result
        }

        /**
         * 显示Toast消息
         */
        @JvmStatic
        fun toast(
            msg: String, 
            duration: Int = Toast.LENGTH_SHORT, 
            gravity: Int = Gravity.BOTTOM, 
            xOffset: Int = 0, 
            yOffset: Int = 0
        ) {
            Handler(Looper.getMainLooper()).post {
                try {
                    contextRef?.get()?.let { context ->
                        val toast = Toast.makeText(context, msg, duration)
                        toast.setGravity(gravity, xOffset, yOffset)
                        toast.show()
                    }
                } catch (e: Exception) {
                    ToolBarService.logEx(e, "显示Toast失败")
                }
            }
        }

        // 添加Toast常量供Python使用
        @JvmStatic val TOAST_LENGTH_SHORT = Toast.LENGTH_SHORT
        @JvmStatic val TOAST_LENGTH_LONG = Toast.LENGTH_LONG
        @JvmStatic val TOAST_LENGTH_VERY_LONG = 5000  // 自定义5秒显示时间
        @JvmStatic val TOAST_GRAVITY_TOP = Gravity.TOP
        @JvmStatic val TOAST_GRAVITY_CENTER = Gravity.CENTER
        @JvmStatic val TOAST_GRAVITY_BOTTOM = Gravity.BOTTOM

        enum class SwipeDirection {
            CR, CL, CU, CD,  // Center Right, Center Left, Center Up, Center Down
            ER, EL, EU, ED   // Edge Right, Edge Left, Edge Up, Edge Down
        }

        /**
         * 执行经典滑动手势
         */
        @JvmStatic
        fun sweep(direction: String, duration: Int): Boolean {
            val swipeDirection = try {
                SwipeDirection.valueOf(direction.toUpperCase())
            } catch (e: IllegalArgumentException) {
                ToolBarService.logEx(e, "Invalid direction: $direction")
                return false
            }

            val metrics = context.resources.displayMetrics
            val width = metrics.widthPixels
            val height = metrics.heightPixels

            val (startX, startY, endX, endY) = when (swipeDirection) {
                SwipeDirection.CR -> listOf(width / 2, height / 2, width - 100, height / 2)
                SwipeDirection.CL -> listOf(width / 2, height / 2, 100, height / 2)
                SwipeDirection.CU -> listOf(width / 2, height / 2, width / 2, 100)
                SwipeDirection.CD -> listOf(width / 2, height / 2, width / 2, height - 100)
                SwipeDirection.ER -> listOf(100, height / 2, width - 100, height / 2)
                SwipeDirection.EL -> listOf(width - 100, height / 2, 100, height / 2)
                SwipeDirection.EU -> listOf(width / 2, height - 100, width / 2, 100)
                SwipeDirection.ED -> listOf(width / 2, 100, width / 2, height - 100)
            }

            return try {
                runBlocking {
                    gestureSwipe(startX, startY, endX, endY, duration)
                }
                // ToolBarService.log("Sweep $swipeDirection successful")
                true
            } catch (e: Exception) {
                ToolBarService.logEx(e, "Sweep $swipeDirection failed")
                false
            }
        }

        // 添加Context获取方法
        @JvmStatic
        fun getContext(): Context {
            return context
        }

        @JvmStatic
        fun showUI(visible: Boolean) {
            try {
                val service = ToolBarService.getInstance()?.get()
                if (service != null) {
                    Handler(Looper.getMainLooper()).post {
                        service.showUI(visible)
                    }
                }
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "控制界面显示失败")
            }
        }
       
        @JvmStatic
        fun showClick(visible: Boolean) {
            val service = ToolBarService.getInstance()?.get()
            if (service != null) {
                // 在主线程上执行UI操作
                Handler(Looper.getMainLooper()).post {
                    service.showClick(visible)
                    ToolBarService.logI("调用showClick完成: $visible")
                }
            } else {
                ToolBarService.logE("ToolBarService实例不可用")
            }
        }

        /**
         * 获取当前前台应用的包名
         */
        @JvmStatic
        fun getCurrentPackage(): String {
            // Timber.tag(TAG).i("Getting current package name")
            return try {
                // 尝试通过无障碍服务获取
                val rootNode = AutoApi.AutoImpl?.rootInActiveWindow()
                if (rootNode != null) {
                    val packageName = rootNode.packageName?.toString()
                    ToolBarService.logI("Current package from accessibility: $packageName")
                    rootNode.recycle()
                    return packageName ?: ""
                }
                
                // 备用方法：通过ActivityManager获取
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val foregroundApp = am.appTasks.firstOrNull()?.taskInfo?.topActivity?.packageName
                    ToolBarService.logI("Current package from ActivityManager: $foregroundApp")
                    foregroundApp ?: ""
                } else {
                    // 旧版本Android上的备用方法
                    val tasks = am.getRunningTasks(1)
                    if (!tasks.isNullOrEmpty()) {
                        val packageName = tasks[0].topActivity?.packageName
                        ToolBarService.logI("Current package from getRunningTasks: $packageName")
                        packageName ?: ""
                    } else ""
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "Failed to get current package")
                ""
            }
        }

 
        /**
         * 获取当前根节点
         */
        @JvmStatic
        fun getRootNode(): AccessibilityNodeInfo? {
            return try {
                AutoApi.AutoImpl?.rootInActiveWindow()
            } catch (e: Exception) {
                ToolBarService.logEx(e, "Failed to get root node")
                null
            }
        }

        /**
         * 获取当前最前台的应用信息
         * 
         * @return Map<String, Any> 包含包名(packageName)、应用名(appName)和最后使用时间(lastUsed)的Map，失败返回null
         */
        @JvmStatic
        fun getCurrentApp(): Map<String, Any>? {
            return try {
                val appContext = context.applicationContext
                var packageName: String? = null
                val period = 10
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
                    try {
                        val usageStatsManager = appContext.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
                        if (usageStatsManager != null) {
                            packageName = getCurrentForegroundAppFromEvents(usageStatsManager, period)
                            // 如果通过事件无法获取，则尝试传统方法
                            if (packageName.isNullOrEmpty()) {
                                ToolBarService.logI("通过Stats获取前台应用")
                                packageName = getCurrentForegroundAppFromStats(usageStatsManager, period)
                            }
                        }
                    } catch (e: Exception) {
                        ToolBarService.logEx(e, "UsageStatsManager获取前台应用失败")
                    }
                }
                
                // 如果UsageStatsManager失败，尝试ActivityManager作为备用方案
                if (packageName.isNullOrEmpty() && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    ToolBarService.logI("通过ActivityManager获取前台应用")
                    packageName = getCurrentForegroundAppFromActivityManager()
                }
                
                // 如果都失败了，直接返回null
                if (packageName.isNullOrEmpty()) {
                    return null
                }
                
                // 根据包名获取应用信息
                val pm = appContext.packageManager
                try {
                    val appInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        pm.getApplicationInfo(packageName, PackageManager.ApplicationInfoFlags.of(0))
                    } else {
                        @Suppress("DEPRECATION")
                        pm.getApplicationInfo(packageName, 0)
                    }
                    
                    val appName = pm.getApplicationLabel(appInfo).toString()
                    
                    return mapOf(
                        "packageName" to packageName,
                        "appName" to appName
                    )
                } catch (e: Exception) {
                    ToolBarService.logEx(e, "获取应用信息失败: $packageName")
                    
                    // 即使无法获取应用名称，也返回包名信息
                    return mapOf(
                        "packageName" to packageName,
                        "appName" to packageName
                    )
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "获取当前前台应用失败")
                return null
            }
        }

        /**
         * 通过UsageEvents获取当前前台应用（最准确的方法）
         * 可以实时检测应用前台/后台切换事件
         */
        @JvmStatic
        private fun getCurrentForegroundAppFromEvents(usageStatsManager: UsageStatsManager, period: Int): String? {
            return try {
                val currentTime = System.currentTimeMillis()
                val startTime = currentTime - period * 1000L // 查看过去10秒的事件
                
                // 检查设备是否解锁（Android R以上需要）
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    val userManager = context.getSystemService(Context.USER_SERVICE) as? UserManager
                    if (userManager?.isUserUnlocked != true) {
                        ToolBarService.logW("设备已锁定，无法获取使用事件")
                        return null
                    }
                }
                
                val usageEvents = usageStatsManager.queryEvents(startTime, currentTime)
                var lastForegroundApp: String? = null
                var lastEventTime = 0L
                
                val event = UsageEvents.Event()
                while (usageEvents.hasNextEvent()) {
                    usageEvents.getNextEvent(event)
                    
                    // 查找最近的前台事件
                    if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED && 
                        event.timeStamp > lastEventTime) {
                        lastForegroundApp = event.packageName
                        lastEventTime = event.timeStamp
                    }
                }                
                return lastForegroundApp
            } catch (e: Exception) {
                ToolBarService.logEx(e, "通过Events获取前台应用失败")
                return null
            }
        }

        /**
         * 通过UsageStats获取当前前台应用（传统方法）
         */
        @JvmStatic
        private fun getCurrentForegroundAppFromStats(usageStatsManager: UsageStatsManager, period: Int): String? {
            return try {
                val endTime = System.currentTimeMillis()
                val startTime = endTime - period * 1000L
                
                val usageStatsList = usageStatsManager.queryUsageStats(
                    UsageStatsManager.INTERVAL_DAILY, startTime, endTime)
                
                if (!usageStatsList.isNullOrEmpty()) {
                    var recentStats: UsageStats? = null
                    var maxLastUsed = 0L
                    
                    for (stats in usageStatsList) {
                        if (stats.lastTimeUsed > maxLastUsed) {
                            maxLastUsed = stats.lastTimeUsed
                            recentStats = stats
                        }
                    }
                    
                    if (recentStats != null) {
                        // ToolBarService.logI("通过Stats获取前台应用: ${recentStats.packageName}")
                        return recentStats.packageName
                    }
                }
                
                return null
            } catch (e: Exception) {
                ToolBarService.logEx(e, "通过Stats获取前台应用失败")
                return null
            }
        }

        /**
         * 通过ActivityManager获取当前前台应用（备用方案）
         * 虽然受限制，但某些情况下仍然可用
         */
        @JvmStatic
        private fun getCurrentForegroundAppFromActivityManager(): String? {
            return try {
                val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
                if (activityManager != null) {
                    // 方法1：尝试通过RunningAppProcesses获取
                    val runningProcesses = activityManager.runningAppProcesses
                    for (processInfo in runningProcesses) {
                        if (processInfo.importance == ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND) {
                            val packageName = processInfo.pkgList?.firstOrNull()
                            if (!packageName.isNullOrEmpty() && packageName != context.packageName) {
                                ToolBarService.logI("通过ActivityManager获取前台应用: $packageName")
                                return packageName
                            }
                        }
                    }
                    
                    // 方法2：尝试通过RunningTasks获取（需要权限，但可以试试）
                    try {
                        @Suppress("DEPRECATION")
                        val runningTasks = activityManager.getRunningTasks(1)
                        if (runningTasks.isNotEmpty()) {
                            val topActivity = runningTasks[0].topActivity
                            val packageName = topActivity?.packageName
                            if (!packageName.isNullOrEmpty() && packageName != context.packageName) {
                                ToolBarService.logI("通过RunningTasks获取前台应用: $packageName")
                                return packageName
                            }
                        }
                    } catch (e: SecurityException) {
                        ToolBarService.logW("没有权限使用getRunningTasks")
                    }
                }
                
                return null
            } catch (e: Exception) {
                ToolBarService.logEx(e, "通过ActivityManager获取前台应用失败")
                return null
            }
        }

        /**
         * 清除前台应用缓存
         * 强制下次调用getCurrentApp()时重新获取
         */
        @JvmStatic
        fun clearForegroundAppCache() {
            ToolBarService.logI("前台应用缓存已清除")
        }


        /**
         * 注册输入回调
         * 简化版本，直接接收Python函数对象
         */
        @JvmStatic
        fun onInput(callback: PyObject) {
            inputCallback = callback
        }

        /**
         * 执行命令
         */
        @JvmStatic
        fun doCommand(command: String): Any? {
            return try {
                if (inputCallback != null) {
                    // 直接调用Python函数
                    val result = inputCallback!!.call(command)
                    if(result != null) {
                        result.toJava(Any::class.java)
                    } else {
                        null
                    }
                } else {
                    ToolBarService.logE("输入回调未注册")
                    null
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "执行命令失败")
                null
            }
        }

        // 添加检查应用是否在前台的方法
        @JvmStatic
        fun isAppForeground(): Boolean {
            try {
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                val tasks = am.getRunningTasks(1)
                if (tasks.isNotEmpty()) {
                    val topActivity = tasks[0].topActivity
                    return topActivity?.packageName == context.packageName
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "检查应用前台状态失败")
            }
            return false
        }

        @JvmStatic
        fun isOnHomeScreen(): Boolean {
            try {
                // 获取当前应用包名
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                val tasks = am.getRunningTasks(1)
                if (tasks.isNotEmpty()) {
                    val packageName = tasks[0].topActivity?.packageName ?: ""
                    
                    // 常见桌面应用包名列表
                    val launcherPackages = setOf(
                        "com.android.launcher3",         // 原生Android
                        "com.google.android.apps.nexuslauncher",  // Pixel
                        "com.sec.android.app.launcher",  // 三星
                        "com.huawei.android.launcher",   // 华为
                        "com.miui.home",                 // 小米
                        "com.oppo.launcher",             // OPPO
                        "com.vivo.launcher",             // vivo
                        "com.realme.launcher",           // Realme
                        "com.oneplus.launcher"           // 一加
                    )
                    
                    // 检查是否在已知桌面包名列表中
                    return launcherPackages.contains(packageName) ||
                           packageName.contains("launcher", ignoreCase = true) ||
                           packageName.contains("home", ignoreCase = true)
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "检查是否在桌面失败")
            }
            return false
        }


        
        /**
         * 设置设备名称
         * 通过ToolBarService保存设备名称
         */
        @JvmStatic
        fun setName(deviceName: String): Boolean {
            return try {
                val service = ToolBarService.getInstance()?.get()
                if (service != null) {
                    service.deviceName = deviceName
                    ToolBarService.logI("设备名称已保存: $deviceName")
                    true
                } else {
                    ToolBarService.logE("ToolBarService实例不可用，无法设置设备名称")
                    false
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "设置设备名称失败: $deviceName")
                false
            }
        }

        /**
         * 获取设备名称
         * 从ToolBarService获取设备名称
         */
        @JvmStatic
        fun getName(): String? {
            return try {
                val service = ToolBarService.getInstance()?.get()
                if (service != null) {
                    val deviceName = service.deviceName
                    if (deviceName.isNotEmpty()) {
                        ToolBarService.logI("获取设备名称: $deviceName")
                        deviceName
                    } else {
                        ToolBarService.logI("设备名称未设置")
                        null
                    }
                } else {
                    ToolBarService.logE("ToolBarService实例不可用，无法获取设备名称")
                    null
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "获取设备名称失败")
                null
            }
        }

        /**
         * 获取服务器IP地址
         * 从ToolBarService获取服务器IP
         */
        @JvmStatic
        fun getServerIP(): String {
            return try {
                val service = ToolBarService.getInstance()?.get()
                if (service != null) {
                    val serverIP = service.serverIP
                    ToolBarService.logI("获取服务器IP: $serverIP")
                    serverIP
                } else {
                    ToolBarService.logE("ToolBarService实例不可用，无法获取服务器IP")
                    ""
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "获取服务器IP失败")
                ""
            }
        }

        /**
         * 设置服务器IP地址
         * 通过ToolBarService保存服务器IP
         */
        @JvmStatic
        fun setServerIP(serverIP: String): Boolean {
            return try {
                val service = ToolBarService.getInstance()?.get()
                if (service != null) {
                    service.serverIP = serverIP
                    ToolBarService.logI("服务器IP已保存: $serverIP")
                    true
                } else {
                    ToolBarService.logE("ToolBarService实例不可用，无法设置服务器IP")
                    false
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "设置服务器IP失败: $serverIP")
                false
            }
        }       
       

        /**
         * 退出应用
         */
        @JvmStatic
        fun exitApp() {
            try {
                // 使用Handler确保在主线程上执行
                Handler(Looper.getMainLooper()).post {
                    // 先停止ToolBarService
                    val context = contextRef?.get() ?: return@post
                    context.stopService(Intent(context, ToolBarService::class.java))
                    
                    // 等待一小段时间确保服务停止
                    Handler(Looper.getMainLooper()).postDelayed({
                        // 获取MainActivity实例
                        val activity = MainActivity.getInstance()
                        activity?.let {
                            // 结束活动
                            it.finish()
                            
                            // 使用延迟确保活动有时间结束
                            Handler(Looper.getMainLooper()).postDelayed({
                                // 强制退出应用
                                Process.killProcess(Process.myPid())
                                System.exit(0)
                            }, 300)
                        } ?: run {
                            // 如果找不到活动，直接强制退出
                            Process.killProcess(Process.myPid())
                            System.exit(0)
                        }
                    }, 200)
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "退出应用失败")
            }
        }

        /**
         * 读取指定文件的内容
         * @param fileName 文件名，相对于files/scripts目录
         * @return 文件内容，如果失败返回错误信息
         */
        @JvmStatic
        fun readFileContent(fileName: String): String {
            return try {
                val scriptsDir = File(context.filesDir, "scripts")
                val targetFile = File(scriptsDir, fileName)
                
                ToolBarService.logI("尝试读取文件: ${targetFile.absolutePath}")
                
                if (!targetFile.exists()) {
                    val errorMsg = "文件不存在: ${targetFile.absolutePath}"
                    ToolBarService.logE(errorMsg)
                    return errorMsg
                }
                
                if (!targetFile.canRead()) {
                    val errorMsg = "文件无法读取: ${targetFile.absolutePath}"
                    ToolBarService.logE(errorMsg)
                    return errorMsg
                }
                
                val content = targetFile.readText(Charsets.UTF_8)
                ToolBarService.logI("文件读取成功: ${fileName}, 大小: ${content.length} 字符")
                content
                
            } catch (e: Exception) {
                val errorMsg = "读取文件失败: ${fileName}, 错误: ${e.message}"
                ToolBarService.logEx(e, errorMsg)
                errorMsg
            }
        }

        /**
         * 列出scripts目录下的所有文件
         * @return 文件列表字符串，每行一个文件
         */
        @JvmStatic
        fun listScriptsFiles(): String {
            return try {
                val scriptsDir = File(context.filesDir, "scripts")
                ToolBarService.logI("列出目录: ${scriptsDir.absolutePath}")
                
                if (!scriptsDir.exists()) {
                    val errorMsg = "scripts目录不存在: ${scriptsDir.absolutePath}"
                    ToolBarService.logE(errorMsg)
                    return errorMsg
                }
                
                if (!scriptsDir.isDirectory()) {
                    val errorMsg = "scripts不是目录: ${scriptsDir.absolutePath}"
                    ToolBarService.logE(errorMsg)
                    return errorMsg
                }
                
                val files = scriptsDir.listFiles()
                if (files == null || files.isEmpty()) {
                    val msg = "scripts目录为空: ${scriptsDir.absolutePath}"
                    ToolBarService.logI(msg)
                    return msg
                }
                
                val fileList = StringBuilder()
                fileList.append("scripts目录 (${scriptsDir.absolutePath}) 包含 ${files.size} 个文件:\n")
                
                files.sortedBy { it.name }.forEach { file ->
                    val fileInfo = when {
                        file.isDirectory() -> "[目录] ${file.name}/"
                        file.isFile() -> "[文件] ${file.name} (${file.length()} 字节)"
                        else -> "[其他] ${file.name}"
                    }
                    fileList.append("$fileInfo\n")
                }
                
                val result = fileList.toString()
                ToolBarService.logI("文件列表获取成功，共 ${files.size} 个项目")
                result
                
            } catch (e: Exception) {
                val errorMsg = "列出文件失败: ${e.message}"
                ToolBarService.logEx(e, errorMsg)
                errorMsg
            }
        }

        /**
         * 获取屏幕参数 - 统一接口
         * @return 包含所有屏幕参数的Map
         */
        @JvmStatic
        fun getScreenParams(): Map<String, Any> {
            return try {
                val result = mutableMapOf<String, Any>()
                
                // 获取屏幕尺寸
                val context = contextRef?.get() ?: throw IllegalStateException("Context not available")
                val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
                val display = windowManager.defaultDisplay
                
                when {
                    Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1 -> {
                        val metrics = DisplayMetrics()
                        display.getRealMetrics(metrics)
                        result["screenWidth"] = metrics.widthPixels
                        result["screenHeight"] = metrics.heightPixels
                        result["density"] = metrics.density
                        result["densityDpi"] = metrics.densityDpi
                        result["scaledDensity"] = metrics.scaledDensity
                    }
                    else -> {
                        @Suppress("DEPRECATION")
                        result["screenWidth"] = display.width
                        @Suppress("DEPRECATION")
                        result["screenHeight"] = display.height
                        result["density"] = context.resources.displayMetrics.density
                        result["densityDpi"] = context.resources.displayMetrics.densityDpi
                        result["scaledDensity"] = context.resources.displayMetrics.scaledDensity
                    }
                }
                
                // 获取状态栏高度
                result["statusBarHeight"] = getStatusBarHeight()
                
                // 获取导航栏高度
                result["navigationBarHeight"] = getNavigationBarHeight()
                
                // 判断是否有导航栏
                result["hasNavigationBar"] = hasNavigationBar()
                
                // 计算窗口尺寸
                val screenWidth = result["screenWidth"] as Int
                val screenHeight = result["screenHeight"] as Int
                val statusBarHeight = result["statusBarHeight"] as Int
                val navigationBarHeight = result["navigationBarHeight"] as Int
                
                result["windowWidth"] = screenWidth
                result["windowHeight"] = screenHeight - statusBarHeight - navigationBarHeight
                
                // 添加系统信息
                result["sdkVersion"] = Build.VERSION.SDK_INT
                result["manufacturer"] = Build.MANUFACTURER
                result["model"] = Build.MODEL
                result["brand"] = Build.BRAND
                
                ToolBarService.logI("获取屏幕参数成功: $result")
                result
                
            } catch (e: Exception) {
                ToolBarService.logEx(e, "获取屏幕参数失败")
                mapOf(
                    "screenWidth" to 0,
                    "screenHeight" to 0,
                    "statusBarHeight" to 0,
                    "navigationBarHeight" to 0,
                    "windowWidth" to 0,
                    "windowHeight" to 0,
                    "density" to 1.0f,
                    "densityDpi" to 160,
                    "scaledDensity" to 1.0f,
                    "hasNavigationBar" to false,
                    "sdkVersion" to Build.VERSION.SDK_INT,
                    "manufacturer" to Build.MANUFACTURER,
                    "model" to Build.MODEL,
                    "brand" to Build.BRAND,
                    "error" to e.message
                )
            }
        }
        
        /**
         * 获取状态栏高度
         */
        @JvmStatic
        private fun getStatusBarHeight(): Int {
            return try {
                val context = contextRef?.get() ?: return MainActivity.statusBarHeight
                val resourceId = context.resources.getIdentifier("status_bar_height", "dimen", "android")
                if (resourceId > 0) {
                    context.resources.getDimensionPixelSize(resourceId)
                } else {
                    MainActivity.statusBarHeight
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "获取状态栏高度失败")
                // 根据DPI估算默认高度
                val density = contextRef?.get()?.resources?.displayMetrics?.densityDpi ?: 420
                when {
                    density >= 560 -> 36 // XXXHDPI
                    density >= 420 -> 30 // XXHDPI
                    density >= 320 -> 25 // XHDPI
                    density >= 240 -> 19 // HDPI
                    else -> 15 // MDPI
                }
            }
        }
        
        /**
         * 获取导航栏高度
         */
        @JvmStatic
        private fun getNavigationBarHeight(): Int {
            return try {
                val context = contextRef?.get() ?: return 0
                
                // 检查是否有导航栏
                if (!hasNavigationBar()) {
                    return 0
                }
                
                val resourceId = context.resources.getIdentifier("navigation_bar_height", "dimen", "android")
                if (resourceId > 0) {
                    context.resources.getDimensionPixelSize(resourceId)
                } else {
                    // 根据DPI估算默认高度
                    val density = context.resources.displayMetrics.densityDpi
                    when {
                        density >= 560 -> 63 // XXXHDPI
                        density >= 420 -> 56 // XXHDPI
                        density >= 320 -> 42 // XHDPI
                        density >= 240 -> 32 // HDPI
                        else -> 24 // MDPI
                    }
                }
            } catch (e: Exception) {
                ToolBarService.logEx(e, "获取导航栏高度失败")
                0
            }
        }
        
        /**
         * 判断是否有导航栏
         */
        @JvmStatic
        private fun hasNavigationBar(): Boolean {
            return try {
                val context = contextRef?.get() ?: return false
                
                // 方法1: 检查配置
                val id = context.resources.getIdentifier("config_showNavigationBar", "bool", "android")
                if (id > 0) {
                    val hasNavBarConfig = context.resources.getBoolean(id)
                    if (hasNavBarConfig) {
                        return true
                    }
                }
                
                // 方法2: 检查屏幕尺寸差异
                val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
                val display = windowManager.defaultDisplay
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1) {
                    val realMetrics = DisplayMetrics()
                    display.getRealMetrics(realMetrics)
                    val displayMetrics = DisplayMetrics()
                    display.getMetrics(displayMetrics)
                    
                    // 如果真实高度大于显示高度，说明有导航栏
                    return realMetrics.heightPixels > displayMetrics.heightPixels
                }
                
                // 方法3: 检查是否有物理按键
                val hasMenuKey = android.view.ViewConfiguration.get(context).hasPermanentMenuKey()
                val hasBackKey = android.view.KeyCharacterMap.deviceHasKey(android.view.KeyEvent.KEYCODE_BACK)
                
                return !hasMenuKey && !hasBackKey
                
            } catch (e: Exception) {
                ToolBarService.logEx(e, "检查导航栏失败")
                false
            }
        }
        
        /**
         * 屏幕坐标转窗口坐标 - 使用Java层的坐标转换
         */
        @JvmStatic
        fun convertScreenToWindow(x: Int, y: Int): Pair<Int, Int> {
            return try {
                val statusBarHeight = getStatusBarHeight()
                val windowX = x
                val windowY = y + statusBarHeight
                
                ToolBarService.logI("Java层坐标转换: 屏幕($x,$y) -> 窗口($windowX,$windowY)")
                Pair(windowX, windowY)
            } catch (e: Exception) {
                ToolBarService.logEx(e, "Java层坐标转换失败")
                Pair(x, y)
            }
        }

    }
} 