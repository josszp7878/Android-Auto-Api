package cn.vove7.andro_accessibility_api.demo

import MutablePoint
import android.Manifest
import android.annotation.SuppressLint
import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.os.StrictMode
import android.provider.Settings
import android.text.Editable
import android.text.Spannable
import android.text.SpannableString
import android.text.style.ForegroundColorSpan
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.ContextCompat.checkSelfPermission
import cn.vove7.andro_accessibility_api.AccessibilityApi
import cn.vove7.andro_accessibility_api.demo.actions.Action
import cn.vove7.andro_accessibility_api.demo.databinding.ActivityMainBinding
import cn.vove7.andro_accessibility_api.demo.script.PythonServices
import cn.vove7.andro_accessibility_api.demo.script.ScriptEngine
import cn.vove7.andro_accessibility_api.demo.service.ScreenCapture
import cn.vove7.andro_accessibility_api.demo.service.ToolBarService
import cn.vove7.auto.AutoApi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import timber.log.Timber
import java.lang.ref.WeakReference
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    companion object {
        const val REQUEST_CODE_PERMISSIONS = 1001
        const val REQUEST_CODE_OVERLAY_PERMISSION = 1002
        private var instance: WeakReference<MainActivity>? = null

        @JvmStatic
        fun getInstance(): MainActivity? {
            return instance?.get()
        }

        // 缓存状态栏高度
        @JvmStatic
        private var _statusBarHeight: Int = 0
        @JvmStatic
        var statusBarHeight: Int
            get() {
                if (_statusBarHeight == 0) {
                    instance?.get()?.let { activity ->
                        val resourceId = activity.resources.getIdentifier("status_bar_height", "dimen", "android")
                        if (resourceId > 0) {
                            _statusBarHeight = activity.resources.getDimensionPixelSize(resourceId)
                        }
                    }
                }
                return _statusBarHeight
            }
            set(value) {
                _statusBarHeight = value
            }

        @JvmStatic
        fun screenToWindowCoordinates(x: Int, y: Int): Pair<Int, Int> {
            return Pair(x, y - statusBarHeight)
        }

        @JvmStatic
        fun windowToScreenCoordinates(x: Int, y: Int): android.util.Pair<Int, Int> {
            return android.util.Pair(x, y + statusBarHeight)
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

    private val requiredPermissions = arrayOf(
        Manifest.permission.REQUEST_INSTALL_PACKAGES,
        Manifest.permission.WRITE_EXTERNAL_STORAGE
    )

    private val specialPermissions = mapOf(
        Settings.ACTION_MANAGE_OVERLAY_PERMISSION to { Settings.canDrawOverlays(this) },
        Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS to {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            pm.isIgnoringBatteryOptimizations(packageName)
        },
        Settings.ACTION_USAGE_ACCESS_SETTINGS to {
            PythonServices.checkPermission("android.permission.PACKAGE_USAGE_STATS")
        }
    )

    // 添加一个新的映射来存储权限描述和Intent创建函数
    private val specialPermissionDetails = mapOf(
        Settings.ACTION_MANAGE_OVERLAY_PERMISSION to Pair(
            { _: Context -> Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")) },
            "显示悬浮窗权限"
        ),
        Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS to Pair(
            { _: Context -> Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")) },
            "忽略电池优化权限"
        ),
        Settings.ACTION_USAGE_ACCESS_SETTINGS to Pair(
            { _: Context -> Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS) },
            "使用情况访问权限"
        )
    )

    // 添加一个标志，表示是否已经显示过权限提示
    private var permissionAlertShown = false

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        instance = WeakReference(this)
        
        // 初始化状态栏高度
        val resourceId = resources.getIdentifier("status_bar_height", "dimen", "android")
        if (resourceId > 0) {
            statusBarHeight = resources.getDimensionPixelSize(resourceId)
        }
        
        // 添加网络策略
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val builder = StrictMode.VmPolicy.Builder()
            StrictMode.setVmPolicy(builder.build())
        }
        
        // 允许主线程网络操作（不推荐，但可用于测试）
        StrictMode.setThreadPolicy(
            StrictMode.ThreadPolicy.Builder()
                .permitAll()
                .build()
        )
        
        // 初始化 PythonServices 的 Context
        PythonServices.init(this)
        // 启动 ScreenCapture 服务
        ScreenCapture.Begin(this)
        
        // 启动无障碍服务
        startAccessibilityService()
        // 检查并请求权限
        checkPermissions()

        // 请求特殊权限
        specialPermissions.forEach { (action, checker) ->
            requestSpecialPermission(action, checker) {
                if (action == Settings.ACTION_MANAGE_OVERLAY_PERMISSION) {
                    startService(Intent(this, ToolBarService::class.java))
                }
            }
        }
        if (Settings.canDrawOverlays(this)) {
            startService(Intent(this, ToolBarService::class.java))
        } else {
            Timber.tag("MainActivity").e("悬浮窗权限未授予")
        }
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
        checkPermissions()
    }

    // 修改权限检查方法
    private fun checkPermissions() {
        if (permissionAlertShown) return
        
        val missingPermissions = mutableListOf<String>()
        
        for (permission in requiredPermissions) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                missingPermissions.add(permission)
            }
        }
        
        for (permissionName in specialPermissions.keys) {
            if (!specialPermissions[permissionName]!!.invoke()) {
                missingPermissions.add(permissionName)
            }
        }
        
        if (missingPermissions.isNotEmpty()) {
            val permissionNames = missingPermissions.joinToString(", ") { 
                if (specialPermissionDetails.containsKey(it)) {
                    specialPermissionDetails[it]?.second ?: it.substringAfterLast(".")
                } else {
                    it.substringAfterLast(".")
                }
            }
            Toast.makeText(this, "Some permissions are denied: $permissionNames", Toast.LENGTH_LONG).show()
            permissionAlertShown = true
            
            val normalPermissions = missingPermissions.filter { 
                !specialPermissions.containsKey(it) 
            }.toTypedArray()
            
            if (normalPermissions.isNotEmpty()) {
                ActivityCompat.requestPermissions(this, normalPermissions, REQUEST_CODE_PERMISSIONS)
            }
            
            val specialMissingPermissions = missingPermissions.filter { 
                specialPermissions.containsKey(it) 
            }
            
            if (specialMissingPermissions.isNotEmpty()) {
                showSpecialPermissionDialog(specialMissingPermissions)
            }
        }
    }

    // 修改showSpecialPermissionDialog方法
    private fun showSpecialPermissionDialog(permissions: List<String>) {
        if (permissionAlertShown) return
        
        val builder = AlertDialog.Builder(this)
        builder.setTitle("需要特殊权限")
        builder.setMessage("应用需要以下特殊权限才能正常工作：\n" + 
                          permissions.joinToString("\n") { 
                              specialPermissionDetails[it]?.second ?: it 
                          })
        
        builder.setPositiveButton("去设置") { _, _ ->
            if (permissions.isNotEmpty()) {
                val intent = specialPermissionDetails[permissions[0]]?.first?.invoke(this)
                if (intent != null) {
                    try {
                        startActivity(intent)
                    } catch (e: Exception) {
                        Toast.makeText(this, "无法打开设置页面", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
        
        builder.setNegativeButton("取消", null)
        builder.show()
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

    // 修改requestSpecialPermission方法
    private fun requestSpecialPermission(action: String, checkGranted: () -> Boolean, onGranted: () -> Unit) {
        if (checkGranted()) {
            onGranted()
        } else {
            permissionRequests.add(PermissionRequest(action.hashCode(), checkGranted, onGranted))
            
            val intent = if (specialPermissionDetails.containsKey(action)) {
                specialPermissionDetails[action]?.first?.invoke(this) ?: Intent(action)
            } else {
                Intent(action).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
            }
            
            if (action == Settings.ACTION_ACCESSIBILITY_SETTINGS) {
                startActivity(intent)
            } else {
                if (!intent.hasExtra("package")) {
                    intent.data = Uri.parse("package:$packageName")
                }
                startActivityForResult(intent, action.hashCode())
            }
        }
    }

    /**
     * 将应用从后台切换到前台
     * 
     * @return 是否成功将应用切换到前台
     */
    fun moveTaskToFront(): Boolean {
        try {
            val packageName = packageName
            val intent = packageManager.getLaunchIntentForPackage(packageName)
            intent?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or 
                            Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
            if (intent != null) {
                startActivity(intent)
                return true
            }
            return false
        } catch (e: Exception) {
            Timber.e(e, "Failed to bring app to front")
            return false
        }
    }

    // 添加checkSpecialPermission方法
    @SuppressLint("NewApi")
    private fun checkSpecialPermission(permissionName: String): Boolean {
        return when (permissionName) {
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION -> Settings.canDrawOverlays(this)
            Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS -> {
                val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
                pm.isIgnoringBatteryOptimizations(packageName)
            }
            Settings.ACTION_USAGE_ACCESS_SETTINGS -> 
                PythonServices.checkPermission("android.permission.PACKAGE_USAGE_STATS")
            else -> false
        }
    }
}


