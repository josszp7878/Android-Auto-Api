package cn.vove7.andro_accessibility_api.demo

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
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
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import timber.log.Timber

class MainActivity : AppCompatActivity() {

    private val binding by lazy {
        ActivityMainBinding.inflate(layoutInflater)
    }

    private val REQUEST_CODE_PERMISSIONS = 1001
    private val PREFS_NAME = "DevicePrefs"
    private val SERVER_NAME_KEY = "serverName"
    private val DEVICE_NAME_KEY = "deviceName"

    // 封装 ServerIP 属性
    var serverIP: String
        get() = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(SERVER_NAME_KEY, "192.168.31.217") ?: "192.168.31.217"
        set(value) {
            getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit().apply {
                putString(SERVER_NAME_KEY, value)
                apply()
            }
        }

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(binding.root)

        // 初始化 PythonServices 的 Context
        PythonServices.init(this)
        // 启动 ScreenCapture 服务
        ScreenCapture.Begin(this)
        // 启动无障碍服务
        startAccessibilityService()
        // 检查并请求权限
        requestPermissions()

        // 设置按钮点击事件
        val startButton: Button = findViewById(R.id.startButton)
        startButton.setOnClickListener {
            Start()
        }
    }

    private fun enter(device:String, server:String) : Boolean {
        if (server.isEmpty() || device.isEmpty()) {
            Toast.makeText(this, "请先设置设备名和服务器名", Toast.LENGTH_SHORT).show()
            return false;
        }
        if(!areAllPermissionsGranted()) {
            Toast.makeText(this, "部分权限未申请成功，可能会影响使用功能，可以重启应用重新申请", Toast.LENGTH_SHORT).show()
        }
        // 初始化并启动脚本引擎
        //使用 CoroutineScope 和 Dispatchers.IO 在后台线程中执行网络请求
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val scriptEngine = ScriptEngine.getInstance(this@MainActivity)
                scriptEngine.init(device, server)
                // 切换回主线程更新 UI
                withContext(Dispatchers.Main) {
                    // 隐藏应用
                    moveTaskToBack(true)
                }
            } catch (e: Exception) {
                // 切换回主线程更新 UI
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivity, "脚本引擎启动失败: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        return true;
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
        actionJob?.cancel()
        super.onDestroy()
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

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == ScreenCapture.REQUEST_CODE_SCREEN_CAPTURE) {
            val screenCapture = ScreenCapture.getInstance()
            screenCapture?.handlePermissionResult(resultCode, data)
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

    private fun areAllPermissionsGranted(): Boolean {
        val allPermissionsGranted = requiredPermissions.all {
            val ok = checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
            if (ok) {
                Toast.makeText(this, "权限"+it +"未授权", Toast.LENGTH_SHORT).show()
            }
            return ok
        }
        val isAccessibilityEnabled = AccessibilityApi.isServiceEnable
        if (!allPermissionsGranted) {
            Toast.makeText(this, "无障碍服务未开启", Toast.LENGTH_SHORT).show()
        }
        return allPermissionsGranted && isAccessibilityEnabled
    }


    private fun Start() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        var deviceName = prefs.getString(DEVICE_NAME_KEY, "") ?: ""

        // 显示对话框以获取用户输入
        val dialogView = layoutInflater.inflate(R.layout.dialog_device_info, null)
        val serverIPInput = dialogView.findViewById<EditText>(R.id.serverNameInput)
        val deviceNameInput = dialogView.findViewById<EditText>(R.id.deviceNameInput)

        // 设置初始值
        serverIPInput.setText(serverIP)
        deviceNameInput.setText(deviceName)

        AlertDialog.Builder(this)
            .setTitle("设置设备信息")
            .setView(dialogView)
            .setPositiveButton("保存") { _, _ ->
                serverIP = serverIPInput.text.toString()
                val deviceName = deviceNameInput.text.toString()

                // 保存到SharedPreferences
                prefs.edit().apply {
                    putString(DEVICE_NAME_KEY, deviceName)
                    apply()
                }
                enter(deviceName, serverIP)
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun getDeviceInfo(): Pair<String, String> {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val serverName = prefs.getString(SERVER_NAME_KEY, "") ?: ""
        val deviceName = prefs.getString(DEVICE_NAME_KEY, "") ?: ""
        return Pair(serverName, deviceName)
    }

}

