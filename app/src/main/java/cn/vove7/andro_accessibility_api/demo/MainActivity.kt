package cn.vove7.andro_accessibility_api.demo

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.ArrayAdapter
import androidx.activity.ComponentActivity
import androidx.appcompat.app.AppCompatActivity
import cn.vove7.andro_accessibility_api.AccessibilityApi
import cn.vove7.andro_accessibility_api.demo.actions.*
import cn.vove7.andro_accessibility_api.demo.databinding.ActivityMainBinding
import cn.vove7.auto.AutoApi
import cn.vove7.auto.utils.jumpAccessibilityServiceSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import android.widget.Toast
import androidx.annotation.RequiresApi
import cn.vove7.andro_accessibility_api.demo.service.ScreenCapture
import android.util.Log
import cn.vove7.andro_accessibility_api.demo.script.ScriptEngine
import cn.vove7.andro_accessibility_api.demo.script.PythonServices

class MainActivity : AppCompatActivity() {

    private val binding by lazy {
        ActivityMainBinding.inflate(layoutInflater)
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
        val actions = mutableListOf(
            BaseNavigatorAction(),
            PickScreenText(),
            SiblingTestAction(),
            DrawableAction(),
            WaitAppAction(),
            SelectTextAction(),
            ViewFinderWithLambda(),
            TextMatchAction(),
            ClickTextAction(),
            ClickAction(),
            TraverseAllAction(),
            SmartFinderAction(),
            CoroutineStopAction(),
            ToStringTestAction(),
            InstrumentationSendKeyAction(),
            InstrumentationSendTextAction(),
            InstrumentationInjectInputEventAction(),
            InstrumentationShotScreenAction(),
            SendImeAction(),
            ContinueGestureAction(),
            object : Action() {
                override val name = "Stop"
                override suspend fun run(act: ComponentActivity) {
                    actionJob?.cancel()
                }
            },
            object : Action() {
                override val name = "To Background"
                override suspend fun run(act: ComponentActivity) {
//                    if (!AccessibilityApi.isServiceEnable) {
//                        act.runOnUiThread {
//                            Toast.makeText(act, "请申请无障碍权限，否则功能可能不正常。", Toast.LENGTH_SHORT).show()
//                        }
//                    } else {
                        (act as MainActivity).start()
//                    }
                }
            }
        )

        binding.listView.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, actions)
        binding.listView.setOnItemClickListener { _, _, position, _ ->
            onActionClick(actions[position])
        }
        binding.acsCb.setOnCheckedChangeListener { buttonView, isChecked ->
            if (isChecked && !AccessibilityApi.isServiceEnable) {
                buttonView.isChecked = false
                jumpAccessibilityServiceSettings(AccessibilityApi.BASE_SERVICE_CLS)
            }
        }
    }

    @SuppressLint("LogNotTimber")
    @RequiresApi(Build.VERSION_CODES.O)
    private fun start() {
        // 隐藏应用
        moveTaskToBack(true)
        // 初始化并启动脚本引擎
        try {
            val scriptEngine = ScriptEngine.getInstance(this)
            scriptEngine.init()
        } catch (e: Exception) {
            Log.e("MainActivity", "Failed to start script engine", e)
            runOnUiThread {
                Toast.makeText(this, "脚本引擎启动失败: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }

        // 强制执行新任务
        //onActionClick(ClickAction(), force = true)
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
}
