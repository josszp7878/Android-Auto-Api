package cn.vove7.andro_accessibility_api.demo.service

import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import androidx.core.app.NotificationCompat
import cn.vove7.andro_accessibility_api.demo.R

class FloatingToolbarService : Service() {

    private lateinit var windowManager: WindowManager
    private lateinit var floatingToolbar: View

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d("FloatingToolbarService", "Service started")
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val inflater = getSystemService(LAYOUT_INFLATER_SERVICE) as LayoutInflater
        floatingToolbar = inflater.inflate(R.layout.floating_toolbar, null)

        val layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )

        layoutParams.gravity = Gravity.TOP or Gravity.START
        layoutParams.x = 0
        layoutParams.y = 100

        windowManager.addView(floatingToolbar, layoutParams)

        // 实现拖动功能
        floatingToolbar.setOnTouchListener(object : View.OnTouchListener {
            private var initialX = 0
            private var initialY = 0
            private var initialTouchX = 0f
            private var initialTouchY = 0f

            override fun onTouch(v: View, event: MotionEvent): Boolean {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = layoutParams.x
                        initialY = layoutParams.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        layoutParams.x = initialX + (event.rawX - initialTouchX).toInt()
                        layoutParams.y = initialY + (event.rawY - initialTouchY).toInt()
                        windowManager.updateViewLayout(floatingToolbar, layoutParams)
                        return true
                    }
                }
                return false
            }
        })

        // 设置按钮点击事件
        floatingToolbar.findViewById<Button>(R.id.startStopButton).setOnClickListener {
            // 开始/停止按钮逻辑
        }

        floatingToolbar.findViewById<Button>(R.id.settingsButton).setOnClickListener {
            // 设置按钮逻辑
        }

        // 将服务设置为前台服务
        val notification = NotificationCompat.Builder(this, "service_channel")
            .setContentTitle("悬浮工具栏")
            .setContentText("悬浮工具栏正在运行")
            .setSmallIcon(R.drawable.ic_notification)
            .build()

        startForeground(1, notification)

        return START_STICKY
    }

    override fun onDestroy() {
        Log.d("FloatingToolbarService", "Service destroyed")
        super.onDestroy()
        windowManager.removeView(floatingToolbar)
    }
} 