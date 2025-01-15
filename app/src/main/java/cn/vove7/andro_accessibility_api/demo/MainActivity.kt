package cn.vove7.andro_accessibility_api.demo

import android.Manifest
import android.annotation.SuppressLint
import android.app.Application
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.PixelFormat
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.os.StrictMode
import android.provider.Settings
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat.checkSelfPermission
import cn.vove7.andro_accessibility_api.AccessibilityApi
import cn.vove7.andro_accessibility_api.demo.actions.Action
import cn.vove7.andro_accessibility_api.demo.databinding.ActivityMainBinding
import cn.vove7.andro_accessibility_api.demo.script.PythonServices
import cn.vove7.andro_accessibility_api.demo.script.ScriptEngine
import cn.vove7.andro_accessibility_api.demo.service.ScreenCapture
import cn.vove7.auto.AutoApi
import cn.vove7.andro_accessibility_api.demo.service.ToolBarService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import timber.log.Timber
import java.lang.ref.WeakReference

class MainActivity : AppCompatActivity() {

    companion object {
        const val REQUEST_CODE_PERMISSIONS = 1001
        const val REQUEST_CODE_OVERLAY_PERMISSION = 1002
        private var instance: WeakReference<MainActivity>? = null

        fun getInstance(): MainActivity? {
            return instance?.get()
        }
    }

    private val binding by lazy {
        ActivityMainBinding.inflate(layoutInflater)
    }

    private val permissionRequests = mutableListOf<PermissionRequest>()
    data class PermissionRequest(
        val requestCode: Int,
        val checkGranted: () -> Boolean,
        val onGranted: () -> Unit
    )

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        instance = WeakReference(this)
        
        // 设置ANR监控
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            Application.getProcessName()?.let { processName ->
                StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder()
                    .detectCustomSlowCalls()
                    .penaltyLog()
                    .build())
            }
        }
        // 初始化 PythonServices 的 Context
        PythonServices.init(this)
        // 启动 ScreenCapture 服务
        ScreenCapture.Begin(this)
        // 启动无障碍服务
        startAccessibilityService()
        // 检查并请求权限
        requestPermissions()
        // 检查悬浮窗权限
        requestSpecialPermission(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            { Settings.canDrawOverlays(this) },
            {
                startService(Intent(this, ToolBarService::class.java))
            }
        )
        // 检查并请求忽略电池优化权限
        requestSpecialPermission(
            Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
            {
                val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
                pm.isIgnoringBatteryOptimizations(packageName)
            },
            {
                // 忽略电池优化权限已授予，执行相关操作
            }
        )
    }

    private fun startAccessibilityService() {
        if (!isAccessibilityServiceEnabled()) {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            runOnUiThread {
                Toast.makeText(this, "请开启无障碍服务", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun isAccessibilityServiceEnabled(): Boolean {
        val serviceName = packageName + "/" + AccessibilityApi.BASE_SERVICE_CLS
        val enabledServices = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        )
        return enabledServices?.contains(serviceName) == true
    }

    @SuppressLint("SetTextI18n")
    override fun onResume() {
        super.onResume()
        binding.acsCb.isChecked = AccessibilityApi.isServiceEnable
        binding.acsCb.isEnabled = AutoApi.serviceType != AutoApi.SERVICE_TYPE_INSTRUMENTATION

        binding.workMode.text = "工作模式：${
            mapOf(
                AutoApi.SERVICE_TYPE_NONE to "无",
                AutoApi.SERVICE_TYPE_ACCESSIBILITY to "无障碍",
                AutoApi.SERVICE_TYPE_INSTRUMENTATION to "Instrumentation",
            )[AutoApi.serviceType]
        } "
    }

    var actionJob: Job? = null

    private fun onActionClick(action: Action, force: Boolean = false) {
        if (action.name == "Stop") {
            actionJob?.cancel()
            return
        }
        // 如果 force=true，则取消当前任务并执行新任务
        if (!force && actionJob?.isCompleted.let { it != null && !it }) {
            runOnUiThread {
                toast("有正在运行的任务")
            }
            return
        }
        // 取消当前任务
        actionJob?.cancel()
        // 启动新任务
        actionJob = launchWithExpHandler {
            action.run(this@MainActivity)
        }
        actionJob?.invokeOnCompletion {
            runOnUiThread {
                when {
                    it is CancellationException -> toast("取消执行")
                    it == null -> toast("执行结束")
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        instance?.clear()
    }



    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == ScreenCapture.REQUEST_CODE_SCREEN_CAPTURE) {
            val screenCapture = ScreenCapture.getInstance()
            screenCapture?.handlePermissionResult(resultCode, data)
        } else {
            permissionRequests.find { it.requestCode == requestCode }?.let { request ->
                if (request.checkGranted()) {
                    request.onGranted()
                    permissionRequests.remove(request)
                } else {
                    Toast.makeText(this, "权限未授予", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
    private val requiredPermissions = arrayOf(
        Manifest.permission.REQUEST_INSTALL_PACKAGES,
        Manifest.permission.WRITE_EXTERNAL_STORAGE
    )
    @SuppressLint("BatteryLife")
    @RequiresApi(Build.VERSION_CODES.M)
    private fun checkBatteryOptimization() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        val packageName = packageName
        if (!powerManager.isIgnoringBatteryOptimizations(packageName)) {
            // 如果没有被忽略电池优化，则弹出设置界面让用户手动添加
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            try {
                startActivity(intent)
            } catch (e: Exception) {
                // 某些设备可能不支持直接跳转，尝试打开电池优化列表
                try {
                    startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
                } catch (e: Exception) {
                    Timber.e(e, "Failed to open battery optimization settings")
                    Toast.makeText(this, "请手动前往设置中添加电池优化白名单", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    @SuppressLint("InlinedApi")
    private fun requestPermissions() {

        // 检查电池优化设置
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            checkBatteryOptimization()
        }
        //普通权限
        val missingPermissions = requiredPermissions.filter {
            checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missingPermissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missingPermissions.toTypedArray(), REQUEST_CODE_PERMISSIONS)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (!grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                // 有权限被拒绝
                Timber.tag("MainActivity").e("Some permissions are denied")
                Toast.makeText(this, "需要所有权限才能继续", Toast.LENGTH_SHORT).show()
            }
        }
    }


    private fun requestSpecialPermission(action: String, checkGranted: () -> Boolean, onGranted: () -> Unit) {
        if (checkGranted()) {
            onGranted()
        } else {
            permissionRequests.add(PermissionRequest(action.hashCode(), checkGranted, onGranted))
            val intent = Intent(action).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            if (action == Settings.ACTION_ACCESSIBILITY_SETTINGS) {
                startActivity(intent) // 不使用 startActivityForResult
            } else {
                intent.data = Uri.parse("package:$packageName")
                startActivityForResult(intent, action.hashCode())
            }
        }
    }


}

