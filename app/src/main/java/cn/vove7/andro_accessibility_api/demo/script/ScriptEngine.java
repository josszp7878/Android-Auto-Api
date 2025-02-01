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
import cn.vove7.andro_accessibility_api.demo.service.ToolBarService;
import timber.log.Timber;

public class ScriptEngine {
    private static final String TAG = "ScriptEngine";
    private static volatile ScriptEngine INSTANCE;
    private static Context applicationContext;
    private Python py;
    private PyObject mainModule;
    private final Map<String, Long> scriptLastModified;
    private long lastCheckTime;
    private final Context context;
    private static final long ANR_TIMEOUT = 10000; // 10秒

    private ScriptEngine(ToolBarService context) {
        this.context = context.getApplicationContext();
        applicationContext = this.context;
        this.scriptLastModified = new HashMap<>();
    }

    public static ScriptEngine getInstance(ToolBarService context) {
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
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(applicationContext));
            }
            
            if (py == null) {
                py = Python.getInstance();
            }



            // 设置Python脚本路径
            File scriptDir = new File(context.getFilesDir(), "scripts");
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
} 