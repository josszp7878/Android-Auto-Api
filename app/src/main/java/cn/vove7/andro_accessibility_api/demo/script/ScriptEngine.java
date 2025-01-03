package cn.vove7.andro_accessibility_api.demo.script;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import cn.vove7.andro_accessibility_api.demo.MainActivity;
import timber.log.Timber;

public class ScriptEngine {
    private static final String TAG = "ScriptEngine";
    private static volatile ScriptEngine INSTANCE;
    private static Context applicationContext;
    private Python py;
    private PyObject mainModule;
    private final Map<String, Long> scriptLastModified;
    private static final long CHECK_INTERVAL = 5000;
    private long lastCheckTime;
    private final Context context;
    private final FileServer fileServer;
    private final ExecutorService executor;
    private final Handler mainHandler;

    private ScriptEngine(MainActivity context) {
        this.context = context.getApplicationContext();
        applicationContext = this.context;
        this.fileServer = new FileServer(context);
        this.scriptLastModified = new HashMap<>();
        this.executor = Executors.newSingleThreadExecutor();
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    public static ScriptEngine getInstance(MainActivity context) {
        if (INSTANCE == null) {
            synchronized (ScriptEngine.class) {
                if (INSTANCE == null) {
                    INSTANCE = new ScriptEngine(context);
                }
            }
        }
        return INSTANCE;
    }

    public void init(String deviceName, String serverName) {
        Timber.tag(TAG).d("初始化ScriptEngine with server: %s, device: %s", serverName, deviceName);
        fileServer.checkAndUpdateScripts();
        
        try {
            // 初始化Python
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(applicationContext));
            }
            py = Python.getInstance();

            // 设置Python脚本路径
            File scriptDir = fileServer.getScriptDir();
            Timber.d("Python脚本目录: %s", scriptDir.getAbsolutePath());
            
            PyObject sysModule = py.getModule("sys");
            PyObject pathList = sysModule.get("path");
            pathList.callAttr("insert", 0, scriptDir.getAbsolutePath());

            // 执行Begin入口函数，传入服务器名和设备名
            try {
                mainModule = py.getModule("client");
                mainModule.callAttr("Begin", "_"+deviceName, serverName);
                Timber.d("Python Begin()函数执行成功");
            } catch (Exception e) {
                Timber.e(e, "执行Python Begin()函数失败");
                if (e.getCause() != null) {
                    Timber.e("Cause: %s", e.getCause().getMessage());
                }
            }
        } catch (Exception e) {
            Timber.e(e, "初始化Python环境失败");
        }
    }

    public void uninit() {
        try {
            if (mainModule != null) {
                mainModule.callAttr("End");
                Timber.d("Python End()函数执行成功");
            }
        } catch (Exception e) {
            Timber.e(e, "执行Python End()函数失败");
        }
    }
} 