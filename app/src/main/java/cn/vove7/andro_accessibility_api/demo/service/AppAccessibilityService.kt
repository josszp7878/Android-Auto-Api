package cn.vove7.andro_accessibility_api.demo.service

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.view.accessibility.AccessibilityEvent
import android.util.Log
import android.widget.Toast
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import cn.vove7.andro_accessibility_api.AccessibilityApi
import cn.vove7.andro_accessibility_api.demo.script.PythonServices
import cn.vove7.auto.AppScope
import timber.log.Timber

/**
 * # MyAccessibilityService
 *
 * Created on 2020/6/10
 * @author Vove
 */
class AppAccessibilityService : AccessibilityApi() {

    //启用 页面更新 回调
    override val enableListenPageUpdate: Boolean = true

    override fun onCreate() {
        //must set
        baseService = this
        super.onCreate()
    }

    override fun onDestroy() {
        //must set
        baseService = null
        super.onDestroy()
    }

    //页面更新回调
    override fun onPageUpdate(currentScope: AppScope) {
        Log.d(TAG, "onPageUpdate: $currentScope")
    }

    companion object {
        private const val TAG = "MyAccessibilityService"
    }
}