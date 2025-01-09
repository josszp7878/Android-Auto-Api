package cn.vove7.andro_accessibility_api.demo.script;

import android.app.AlertDialog;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

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
    private boolean versionChecked = false;
    private static final long ANR_TIMEOUT = 10000; // 10秒
    private Handler mHandler;
    private ExecutorService executorService;

    private ScriptEngine(MainActivity context) {
        this.context = context.getApplicationContext();
        applicationContext = this.context;
        this.fileServer = FileServer.getInstance(context);
        this.scriptLastModified = new HashMap<>();
        this.executor = Executors.newSingleThreadExecutor();
        this.mainHandler = new Handler(Looper.getMainLooper());
        mHandler = new Handler(Looper.getMainLooper());
        executorService = Executors.newSingleThreadExecutor();
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
        
        // 使用 FileServer 单例检查和更新脚本
        fileServer.checkAndUpdateScripts(success -> initPython(deviceName, serverName));
    }

    private void initPython(String deviceName, String serverName) {
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(applicationContext));
            }
            
            if (py == null) {
                py = Python.getInstance();
            }

            // 设置Python脚本路径
            File scriptDir = fileServer.getScriptDir();
            Timber.d("Python脚本目录: %s", scriptDir.getAbsolutePath());
            
            PyObject sysModule = py.getModule("sys");
            PyObject pathList = sysModule.get("path");
            pathList.callAttr("insert", 0, scriptDir.getAbsolutePath());

            // 执行Begin入口函数
            try {
                mainModule = py.getModule("CMain");
                mainModule.callAttr("Begin", deviceName, serverName);
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

    // 添加ANR监控
    private void monitorANR(Runnable task) {
        final Object lock = new Object();
        final AtomicBoolean finished = new AtomicBoolean(false);

        executorService.execute(() -> {
            try {
                task.run();
            } finally {
                finished.set(true);
                synchronized (lock) {
                    lock.notify();
                }
            }
        });

        // 监控超时
        mHandler.postDelayed(() -> {
            if (!finished.get()) {
                Log.w(TAG, "检测到可能的ANR，正在处理...");
                // 可以在这里添加一些恢复措施
            }
        }, ANR_TIMEOUT);
    }
} 