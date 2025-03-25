package cn.vove7.andro_accessibility_api.demo.utils

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.Toast
import timber.log.Timber

/**
 * UI相关的通用工具类
 */
object UIUtils {
    // Toast显示时长常量
    const val TOAST_LENGTH_SHORT = Toast.LENGTH_SHORT
    const val TOAST_LENGTH_LONG = Toast.LENGTH_LONG
    const val TOAST_LENGTH_VERY_LONG = 5000 // 5秒

    // Toast显示位置常量
    const val TOAST_GRAVITY_TOP = Gravity.TOP
    const val TOAST_GRAVITY_CENTER = Gravity.CENTER
    const val TOAST_GRAVITY_BOTTOM = Gravity.BOTTOM

    // 当前显示的Toast
    private var currentToast: Toast? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    /**
     * 显示Toast消息
     *
     * @param context 上下文
     * @param message 要显示的消息
     * @param duration 显示时长，可选值：TOAST_LENGTH_SHORT, TOAST_LENGTH_LONG, TOAST_LENGTH_VERY_LONG
     * @param gravity 显示位置，可选值：TOAST_GRAVITY_TOP, TOAST_GRAVITY_CENTER, TOAST_GRAVITY_BOTTOM
     * @param xOffset X轴偏移量
     * @param yOffset Y轴偏移量
     */
    fun showToast(
        context: Context, 
        message: String, 
        duration: Int = TOAST_LENGTH_SHORT, 
        gravity: Int = TOAST_GRAVITY_BOTTOM, 
        xOffset: Int = 0, 
        yOffset: Int = 0
    ) {
        try {
            mainHandler.post {
                // 取消之前的Toast
                currentToast?.cancel()
                
                // 创建新的Toast
                currentToast = Toast.makeText(context, message, 
                    if (duration == TOAST_LENGTH_VERY_LONG) TOAST_LENGTH_LONG else duration)
                currentToast?.setGravity(gravity, xOffset, yOffset)
                currentToast?.show()
                
                // 如果是自定义的超长时间，需要延迟再次显示
                if (duration == TOAST_LENGTH_VERY_LONG) {
                    mainHandler.postDelayed({
                        currentToast?.show()
                    }, TOAST_LENGTH_LONG.toLong())
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "显示Toast失败")
        }
    }

    /**
     * 取消当前显示的Toast
     */
    fun cancelToast() {
        mainHandler.post {
            currentToast?.cancel()
            currentToast = null
        }
    }

    /**
     * 在主线程上执行操作
     *
     * @param action 要执行的操作
     */
    fun runOnUiThread(action: () -> Unit) {
        if (Looper.myLooper() == Looper.getMainLooper()) {
            action()
        } else {
            mainHandler.post(action)
        }
    }

    /**
     * 延迟在主线程上执行操作
     *
     * @param delayMillis 延迟时间（毫秒）
     * @param action 要执行的操作
     */
    fun runOnUiThreadDelayed(delayMillis: Long, action: () -> Unit) {
        mainHandler.postDelayed(action, delayMillis)
    }

    /**
     * 移除待执行的操作
     *
     * @param action 要移除的操作
     */
    fun removeCallbacks(action: Runnable) {
        mainHandler.removeCallbacks(action)
    }
} 