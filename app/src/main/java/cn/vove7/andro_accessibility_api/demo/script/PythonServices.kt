package cn.vove7.andro_accessibility_api.demo.script

import cn.vove7.auto.api.click
import cn.vove7.auto.viewfinder.ScreenTextFinder
import kotlinx.coroutines.runBlocking
import timber.log.Timber

/**
 * Python服务接口的Kotlin实现
 */
class PythonServices {
    companion object {
        private const val TAG = "PythonServices"

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
    }
} 