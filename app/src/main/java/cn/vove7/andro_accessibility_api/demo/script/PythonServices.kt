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
import android.util.Base64
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
import java.util.concurrent.CompletableFuture
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.PackageManagerCompat
import cn.vove7.andro_accessibility_api.demo.service.ToolBarService
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Python服务接口的Kotlin实现
 */
class PythonServices {
    companion object {
        private const val TAG = "PythonServices"

        @SuppressLint("StaticFieldLeak")
        private lateinit var context: MainActivity

        // 缓存应用的包名和显示名称
        private val appNameToPackageMap = mutableMapOf<String, String>()

        /**
         * 初始化 Context 和应用信息
         */
        @JvmStatic
        fun init(context: MainActivity) {
            this.context = context
            loadInstalledApps()
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
            Timber.tag(TAG).i("Click position: $x, $y")
            return try {
                runBlocking {
                    clickAt(x, y)
                }
                true
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Click position failed")
                false
            }
        }

        @JvmStatic
        fun move(x: Int, y: Int): Boolean {
            return try {
                ToolBarService.getInstance()?.get()?.moveCursor(x, y)
                true
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Click position failed")
                false
            }
        }
        /**
         * 返回上一个界面
         */
        @JvmStatic
        fun goBack(): Boolean {
            Timber.tag(TAG).i("Go back")
            return back();
        }

        /**
         * 返回主屏幕
         */
        @JvmStatic
        fun goHome(): Boolean {
            Timber.tag(TAG).i("Go home")
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

        /**
         * 截屏
         */
        @JvmStatic
        fun takeScreenshot(): String {
            Timber.tag(TAG).i("Taking screenshot using ScreenCapture service")
            return try {
                // 调用新的全屏截图方法
                return ScreenCapture.getInstance().captureScreen()
            } catch (e: SecurityException) {
                Timber.tag(TAG).e(e, "权限不足，无法截屏")
                "截屏失败: 权限不足"
            } catch (e: Exception) {
                Timber.tag(TAG).e(e, "Take screenshot failed")
                "截屏失败: ${e.message}"
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

        fun checkPermission(permission: String): Boolean {
            return ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED;
        }

        fun requestPermission(permission: String) {
            ActivityCompat.requestPermissions(context, arrayOf(permission), MainActivity.REQUEST_CODE_PERMISSIONS);
        }

        @JvmStatic
        fun getScreenText(): String {
            val screenCapture = ScreenCapture.getInstance()
            var result = ""
            val latch = CountDownLatch(1)
            
            screenCapture?.recognizeText({ text ->
                result = text as String
                latch.countDown()
            }, false)
            
            // 等待结果，最多等待10秒
            latch.await(10, TimeUnit.SECONDS)
            return result
        }

        @JvmStatic
        fun getScreenInfo(): List<Map<String, String>> {
            val screenCapture = ScreenCapture.getInstance()
            val result = mutableListOf<Map<String, String>>()
            val latch = CountDownLatch(1)
            
            screenCapture?.recognizeText({ textBlockInfos ->
                @Suppress("UNCHECKED_CAST")
                val infos = textBlockInfos as List<ScreenCapture.TextBlockInfo>
                result.addAll(infos.map { textBlockInfo ->
                    mapOf(
                        "t" to textBlockInfo.text,
                        "b" to "${textBlockInfo.bounds.left},${textBlockInfo.bounds.top},${textBlockInfo.bounds.right},${textBlockInfo.bounds.bottom}"
                    )
                })
                latch.countDown()
            }, true)
            
            // 等待结果，最多等待10秒
            latch.await(10, TimeUnit.SECONDS)
            return result
        }

        @JvmStatic
        fun showToast(message: String, duration: Int = Toast.LENGTH_LONG, gravity: Int = Gravity.BOTTOM, 
                      xOffset: Int = 0, yOffset: Int = 100) {
            val handler = Handler(Looper.getMainLooper())
            handler.post {
                try {
                    val toast = Toast.makeText(context, message, duration)
                    toast.setGravity(gravity, xOffset, yOffset)
                    toast.show()
                } catch (e: Exception) {
                    Timber.e(e, "Show toast failed")
                }
            }
        }

        // 添加Toast常量供Python使用
        @JvmStatic val TOAST_LENGTH_SHORT = Toast.LENGTH_SHORT
        @JvmStatic val TOAST_LENGTH_LONG = Toast.LENGTH_LONG
        @JvmStatic val TOAST_GRAVITY_TOP = Gravity.TOP
        @JvmStatic val TOAST_GRAVITY_CENTER = Gravity.CENTER
        @JvmStatic val TOAST_GRAVITY_BOTTOM = Gravity.BOTTOM
    }
} 