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
import timber.log.Timber
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
import androidx.annotation.RequiresApi
import java.lang.ref.WeakReference
import android.os.Process

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
            logI("PythonServices 初始化完成")
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
                    logI("点击位置: $x, $y")
                }
                showUI(true)
                true
            } catch (e: Exception) {
                logEx(e,"点击位置失败: $x, $y")
                false
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
                    logI("滑动位置: $x, $y, $toX, $toY, $duration")
                }
                showUI(true)
                true
            } catch (e: Exception) {
                logEx(e, "滑动失败: $x, $y, $toX, $toY, $duration")
                false
            }
        }
        @JvmStatic
        fun move(x: Int, y: Int): Boolean {
            return try {
                ToolBarService.getInstance()?.get()?.moveCursor(x, y)
                true
            } catch (e: Exception) {
                logEx(e, "移动失败: $x, $y", "move")
                false
            }
        }
        /**
         * 返回上一个界面
         */
        @JvmStatic
        fun goBack(): Boolean {
            logI("返回上一个界面")
            return back();
        }

        /**
         * 返回主屏幕
         */
        @JvmStatic
        fun goHome(): Boolean {
            logI("返回主屏幕")
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
                Timber.tag(TAG).d("App running status after launch: %s", isNowRunning)

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
            Timber.tag(TAG).i("Taking screenshot using ScreenCapture service")
            return try {
                // 隐藏界面，避免影响截图
                showUI(false)
                
                // 延迟一小段时间，确保界面完全隐藏
                Thread.sleep(100)
                
                // 调用原有的截图方法
                val result = ScreenCapture.getInstance().captureScreen()
                
                // 恢复界面显示
                showUI(true)
                
                return result
            } catch (e: SecurityException) {
                // 确保界面恢复显示
                showUI(true)
                
                Timber.tag(TAG).e(e, "权限不足，无法截屏")
                "截屏失败: 权限不足"
            } catch (e: Exception) {
                // 确保界面恢复显示
                showUI(true)
                
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
                showUI(false)
                
                // 延迟一小段时间，确保界面完全隐藏
                Thread.sleep(100)
                
                val screenCapture = ScreenCapture.getInstance()
                var result: Any? = null
                val latch = CountDownLatch(1)
                
                screenCapture?.recognizeText({ text ->
                    result = text
                    latch.countDown()
                }, withPos)
                
                // 等待结果，最多等待10秒
                latch.await(10, TimeUnit.SECONDS)
                
                // 恢复界面显示
                showUI(true)
                
                return result
            } catch (e: Exception) {
                // 确保界面恢复显示
                showUI(true)
                
                Timber.tag(TAG).e(e, "获取屏幕信息失败: ${e.message}")
                throw e
            }
        }

        /**
         * 获取屏幕文本
         * @return 屏幕文本
         */
        @JvmStatic
        fun getScreenText(): String {
            return _getScreenInfo(false) as String
        }

        /**
         * 获取屏幕文本和位置
         * @param withPos 是否返回文本位置
         * @return 屏幕信息
         */
        @JvmStatic
        fun getScreenInfo(): List<Map<String, String>> {
            val result = mutableListOf<Map<String, String>>()
            val textBlockInfos = _getScreenInfo(true) as List<ScreenCapture.TextBlockInfo>
            if (textBlockInfos != null) {
                result.addAll(textBlockInfos.map { textBlockInfo ->
                    mapOf(
                        "t" to textBlockInfo.text,
                        "b" to "${textBlockInfo.bounds.left},${textBlockInfo.bounds.top},${textBlockInfo.bounds.right},${textBlockInfo.bounds.bottom}"
                    )
                })
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
                    logEx(e, "显示Toast失败")
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
                logEx(e, "Invalid direction: $direction")
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
                logI("Sweep $swipeDirection successful")
                true
            } catch (e: Exception) {
                logEx(e, "Sweep $swipeDirection failed")
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
        fun showCursor(visible: Boolean) {
            try {
                val service = ToolBarService.getInstance()?.get()
                if (service != null) {
                    Handler(Looper.getMainLooper()).post {
                        service.showCursor(visible)
                    }
                }
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "控制光标显示失败")
            }
        }
        
        @JvmStatic
        fun showClick(visible: Boolean) {
            val service = ToolBarService.getInstance()?.get()
            if (service != null) {
                // 在主线程上执行UI操作
                Handler(Looper.getMainLooper()).post {
                    service.showClick(visible)
                    logI("调用showClick完成: $visible")
                }
            } else {
                logE("ToolBarService实例不可用")
            }
        }


        @JvmStatic
        fun showLog(visible: Boolean) {
            val service = ToolBarService.getInstance()?.get()
            if (service != null) {
                // 在主线程上执行UI操作
                Handler(Looper.getMainLooper()).post {
                    service.showLog(visible)
                    logI("调用showLog完成: $visible")
                }
            } else {
                logE("ToolBarService实例不可用")
            }
        }

        @JvmStatic
        fun showToolbar(visible: Boolean) {
            val service = ToolBarService.getInstance()?.get()
            if (service != null) {  
                Handler(Looper.getMainLooper()).post {
                    service.showToolbar(visible)
                    logI("调用showToolbar完成: $visible")
                }
            } else {
                logE("ToolBarService实例不可用")
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
                    logI("Current package from accessibility: $packageName")
                    rootNode.recycle()
                    return packageName ?: ""
                }
                
                // 备用方法：通过ActivityManager获取
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val foregroundApp = am.appTasks.firstOrNull()?.taskInfo?.topActivity?.packageName
                    logI("Current package from ActivityManager: $foregroundApp")
                    foregroundApp ?: ""
                } else {
                    // 旧版本Android上的备用方法
                    val tasks = am.getRunningTasks(1)
                    if (!tasks.isNullOrEmpty()) {
                        val packageName = tasks[0].topActivity?.packageName
                        logI("Current package from getRunningTasks: $packageName")
                        packageName ?: ""
                    } else ""
                }
            } catch (e: Exception) {
                logEx(e, "Failed to get current package")
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
                logEx(e, "Failed to get root node")
                null
            }
        }

        /**
         * 获取当前正在运行的应用信息
         * 
         * @param period 查询最近使用应用的时间范围(秒)，默认60秒
         * @return Map<String, Any> 包含包名(packageName)、应用名(appName)和最后使用时间(lastUsed)的Map，失败返回null
         */
        @Suppress("UNREACHABLE_CODE")
        @RequiresApi(Build.VERSION_CODES.LOLLIPOP_MR1)
        @JvmStatic
        fun getCurrentApp(period: Int = 60): Map<String, Any>? {
            // Timber.tag(TAG).i("获取当前运行应用信息")
            return try {
                // 获取Android上下文
                val appContext = context.applicationContext
                
                // 获取UsageStatsManager
                val usageStatsManager = appContext.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
                if (usageStatsManager == null) {
                    logE("获取UsageStatsManager失败，请重新启动应用获取查看应用使用权限")
                    return null
                }
                
                // 获取最近period秒的应用使用情况
                val endTime = System.currentTimeMillis()
                val startTime = endTime - period * 1000L
                
                // 查询应用使用情况
                val usageStatsList = usageStatsManager.queryUsageStats(
                    UsageStatsManager.INTERVAL_DAILY, startTime, endTime)
                
                if (usageStatsList.isNullOrEmpty()) {
                    logW("${period}秒内无最近应用使用记录")
                }
                
                // 找出最近使用的应用
                var recentStats: UsageStats? = null
                var maxLastUsed = 0L
                
                for (stats in usageStatsList) {
                    if (stats.lastTimeUsed > maxLastUsed) {
                        maxLastUsed = stats.lastTimeUsed
                        recentStats = stats
                    }
                }
                
                if (recentStats == null) {
                    logW("未找到最近使用的应用")
                    return null
                }
                
                val packageName = recentStats.packageName
                val pm = appContext.packageManager
                
                try {
                    val appInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        pm.getApplicationInfo(packageName, PackageManager.ApplicationInfoFlags.of(0))
                    } else {
                        @Suppress("DEPRECATION")
                        pm.getApplicationInfo(packageName, 0)
                    }
                    
                    val appName = pm.getApplicationLabel(appInfo).toString()
                    logI("当前应用: $appName ($packageName)")
                    
                    return mapOf(
                        "packageName" to packageName,
                        "appName" to appName,
                        "lastUsed" to recentStats.lastTimeUsed
                    )
                } catch (e: Exception) {
                    logEx(e, "获取应用信息失败")
                    return null
                }
            } catch (e: Exception) {
                logEx(e, "获取当前应用失败")
                return null
            }
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
                    result.toJava(Any::class.java)
                } else {
                    logE("输入回调未注册")
                    null
                }
            } catch (e: Exception) {
                logEx(e, "执行命令失败")
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
                logEx(e, "检查应用前台状态失败")
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
                logEx(e, "检查是否在桌面失败")
            }
            return false
        }

        /**
         * 供脚本直接调用的日志方法
         * @param tag 日志标签
         * @param level 日志级别 (i, d, e, w)
         * @param content 日志内容
         * @param result 可选的结果信息
         */
        @JvmStatic
        fun log(content: String, tag: String = "", level: String = "i") {
            // 调用ToolBarService的addLog方法
            ToolBarService.log(content, tag, level)
        }
        @JvmStatic
        fun logE(content: String, tag: String = "") {
            ToolBarService.log(content, tag, "e")
        }
        @JvmStatic
        fun logW(content: String, tag: String = "") {
            ToolBarService.log(content, tag, "w")
        }
        @JvmStatic
        fun logD(content: String, tag: String = "") {
            ToolBarService.log(content, tag, "d")
        }
        @JvmStatic
        fun logI(content: String, tag: String = "") {
            ToolBarService.log(content, tag, "i")
        }

        @JvmStatic
        fun logC(content: String, tag: String = "") {
            ToolBarService.log(content, tag, "c")
        }

        @JvmStatic
        fun logEx(e: Exception, content: String = "", tag: String = "") {
            val msg = "${content}\n${e.message}\n${e.stackTrace.joinToString("\n")}"
            ToolBarService.log(msg, tag, "e")
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
                logEx(e, "退出应用失败")
            }
        }

    }
} 