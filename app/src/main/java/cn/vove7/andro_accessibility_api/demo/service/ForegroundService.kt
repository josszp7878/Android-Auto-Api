package cn.vove7.andro_accessibility_api.demo.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import cn.vove7.auto.core.api.back
import cn.vove7.auto.core.api.printLayoutInfo
import cn.vove7.andro_accessibility_api.demo.R
import cn.vove7.andro_accessibility_api.demo.launchWithExpHandler
import kotlinx.coroutines.delay

/**
 * # ForegroundService
 *
 * Created on 2020/6/11
 * @author Vove
 */
class ForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // 创建通知
        val notification = NotificationCompat.Builder(this, "service_channel")
            .setContentTitle("服务运行中")
            .setSmallIcon(R.drawable.ic_notification)
            .build()

        // 启动前台服务
        startForeground(1, notification)
        
        return START_STICKY
    }

    private fun parseAction(action: String) {
        when (action) {
            ACTION_PRINT_LAYOUT -> {
                launchWithExpHandler {
                    back()
                    delay(1000)
                    printLayoutInfo()
                }
            }
        }

    }

    companion object {
        const val ACTION_PRINT_LAYOUT = "print_layout"
    }
}