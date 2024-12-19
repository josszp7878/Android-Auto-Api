package cn.vove7.andro_accessibility_api.demo.script

import android.accessibilityservice.AccessibilityService
import android.annotation.SuppressLint
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import cn.vove7.andro_accessibility_api.demo.service.ScreenCapture
import cn.vove7.auto.AutoApi
import cn.vove7.auto.api.back
import cn.vove7.auto.api.click
import cn.vove7.auto.api.home
import cn.vove7.auto.viewfinder.ScreenTextFinder
import kotlinx.coroutines.runBlocking
import timber.log.Timber
import java.io.File
import android.util.Base64

/**
 * Python服务接口的Kotlin实现
 */
class PythonServices {
    companion object {
        private const val TAG = "PythonServices"
        @SuppressLint("StaticFieldLeak")
        private lateinit var context: Context

        /**
         * 初始化 Context
         */
        @JvmStatic
        fun init(context: Context) {
            this.context = context.applicationContext
        }

        /**
         * 点击屏幕指定位置
         * 使用gesture_api中的click实现
         */
        @JvmStatic
        fun clickPosition(x: Float, y: Float): Boolean {
            Timber.i("Click position: $x, $y")
            return try {
                runBlocking {
                    click(x.toInt(), y.toInt())
                }
                true
            } catch (e: Exception) {
                Timber.e(e, "Click position failed")
                false
            }
        }

        /**
         * 获取屏幕上的所有文本
         * 使用ScreenTextFinder实现
         */
        @JvmStatic
        fun getScreenText(): String {
            Timber.i("Get screen text")
            return try {
                runBlocking {
                    ScreenTextFinder().find().joinToString("\n\n")
                }
            } catch (e: Exception) {
                Timber.e(e, "Get screen text failed")
                return ""
            }
        }

        /**
         * 返回上一个界面
         */
        @JvmStatic
        fun goBack(): Boolean {
            Timber.i("Go back")
            return back();
        }

        /**
         * 返回主屏幕
         */
        @JvmStatic
        fun goHome(): Boolean {
            Timber.i("Go home")
           return home()
        }

        /**
         * 打开指定的APP
         */
        @JvmStatic
        fun openApp(packageName: String): Boolean {
            Timber.i("Open app: $packageName")
            return try {
                val intent = context.packageManager.getLaunchIntentForPackage(packageName)
                if (intent != null) {
                    context.startActivity(intent)
                    true
                } else {
                    Timber.e("App not found: $packageName")
                    false
                }
            } catch (e: Exception) {
                Timber.e(e, "Open app failed")
                false
            }
        }

        /**
         * 关闭指定的APP
         */
        @JvmStatic
        fun closeApp(packageName: String): Boolean {
            Timber.i("Close app: $packageName")
            return try {
                val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                am.killBackgroundProcesses(packageName)
                true
            } catch (e: Exception) {
                Timber.e(e, "Close app failed")
                false
            }
        }


        /**
         * 检查指定APP是否安装
         */
        @JvmStatic
        fun isAppInstalled(packageName: String): Boolean {
            Timber.i("Check if app is installed: $packageName")
            return try {
                context.packageManager.getPackageInfo(packageName, 0)
                true
            } catch (e: PackageManager.NameNotFoundException) {
                Timber.e("App not installed: $packageName")
                false
            }
        }

        /**
         * 卸载指定的APP
         */
        @JvmStatic
        fun uninstallApp(packageName: String): Boolean {
            Timber.i("Uninstall app: $packageName")
            return try {
                val intent = Intent(Intent.ACTION_DELETE)
                intent.data = Uri.parse("package:$packageName")
                context.startActivity(intent)
                true
            } catch (e: Exception) {
                Timber.e(e, "Uninstall app failed")
                false
            }
        }
               /**
         * 安装指定的APP
         */
        @JvmStatic
        fun installApp(apkFileName: String): Boolean {
            Timber.i("Install app: $apkFileName")
            return try {
                val file = File(context.getExternalFilesDir(null), apkFileName)
                if (file.exists()) {
                    val intent = Intent(Intent.ACTION_VIEW)
                    intent.setDataAndType(Uri.fromFile(file), "application/vnd.android.package-archive")
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    context.startActivity(intent)
                    true
                } else {
                    Timber.e("APK file not found: $apkFileName")
                    false
                }
            } catch (e: Exception) {
                Timber.e(e, "Install app failed")
                false
            }
        } 

        /**
         * 截屏
         */
        @JvmStatic
        fun takeScreenshot(): String {
            Timber.i("Taking screenshot using ScreenCapture service")
            return try {
                // 调用新的全屏截图方法
                val data = ScreenCapture.getInstance().takeScreenshot()
                if (data != null) {
                    // 返回 Base64 编码的字符串
                    Base64.encodeToString(data, Base64.DEFAULT)
                } else {
                    "截屏失败"
                }
            } catch (e: SecurityException) {
                Timber.e(e, "权限不足，无法截屏")
                "截屏失败: 权限不足"
            } catch (e: Exception) {
                Timber.e(e, "Take screenshot failed")
                "截屏失败: ${e.message}"
            }
        }
    }
} 