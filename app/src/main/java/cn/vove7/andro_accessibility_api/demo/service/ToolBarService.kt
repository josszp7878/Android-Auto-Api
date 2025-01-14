package cn.vove7.andro_accessibility_api.demo.service

import android.annotation.SuppressLint
import android.graphics.PixelFormat
import android.os.Build
import android.util.DisplayMetrics
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowManager
import android.widget.Button
import androidx.lifecycle.LifecycleService
import cn.vove7.andro_accessibility_api.demo.R

/**
 * @功能:应用外打开Service 有局限性 特殊界面无法显示
 * @User Lmy
 * @Creat 4/15/21 5:28 PM
 * @Compony 永远相信美好的事情即将发生
 */
class ToolBarService : LifecycleService() {
    private lateinit var windowManager: WindowManager
    private var floatRootView: View? = null // 悬浮窗View

    override fun onCreate() {
        super.onCreate()
        Log.d("ToolBarService", "Service created")
        showWindow() // 服务启动后立即显示悬浮窗口
    }

    /**
     * 显示悬浮窗
     */
    @SuppressLint("ClickableViewAccessibility")
    fun showWindow() {
        if (floatRootView != null) return // 如果已经显示，则不重复添加

        Log.d("ToolBarService", "Attempting to show window")
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val outMetrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(outMetrics)
        val layoutParam = WindowManager.LayoutParams().apply {
            type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            }
            format = PixelFormat.RGBA_8888
            flags = WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
            width = WRAP_CONTENT
            height = WRAP_CONTENT
            gravity = Gravity.LEFT or Gravity.TOP
            x = outMetrics.widthPixels / 2 - width / 2
            y = outMetrics.heightPixels / 2 - height / 2
        }
        floatRootView = LayoutInflater.from(this).inflate(R.layout.floating_toolbar, null)

        // 实现拖动功能
        val touchListener = object : View.OnTouchListener {
            private var initialX = 0
            private var initialY = 0
            private var initialTouchX = 0f
            private var initialTouchY = 0f
            private val clickThreshold = 10 // 点击的阈值

            override fun onTouch(v: View, event: MotionEvent): Boolean {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = layoutParam.x
                        initialY = layoutParam.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        layoutParam.x = initialX + (event.rawX - initialTouchX).toInt()
                        layoutParam.y = initialY + (event.rawY - initialTouchY).toInt()
                        windowManager.updateViewLayout(floatRootView, layoutParam)
                        return true
                    }
                    MotionEvent.ACTION_UP -> {
                        val deltaX = (event.rawX - initialTouchX).toInt()
                        val deltaY = (event.rawY - initialTouchY).toInt()
                        if (Math.abs(deltaX) < clickThreshold && Math.abs(deltaY) < clickThreshold) {
                            v.performClick() // 处理点击事件
                        }
                        return true
                    }
                }
                return false
            }
        }

        floatRootView?.findViewById<Button>(R.id.startStopButton)?.setOnTouchListener(touchListener)
        floatRootView?.findViewById<Button>(R.id.settingsButton)?.setOnTouchListener(touchListener)

        // 设置按钮点击事件
        floatRootView?.findViewById<Button>(R.id.startStopButton)?.setOnClickListener {
            // 开始/停止按钮逻辑
        }

        floatRootView?.findViewById<Button>(R.id.settingsButton)?.setOnClickListener {
            // 设置按钮逻辑
        }

        windowManager.addView(floatRootView, layoutParam)
        Log.d("ToolBarService", "Window shown")
    }

    /**
     * 隐藏悬浮窗
     */
    fun hideWindow() {
        if (floatRootView != null) {
            windowManager.removeView(floatRootView)
            floatRootView = null
        }
    }

    override fun onDestroy() {
        hideWindow() // 销毁服务时隐藏悬浮窗口
        super.onDestroy()
    }
}