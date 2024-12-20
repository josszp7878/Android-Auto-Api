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
    private final ScriptManager fileServer;
    private final ExecutorService executor;
    private final Handler mainHandler;

    private ScriptEngine(Context context) {
        this.context = context.getApplicationContext();
        applicationContext = this.context;
        this.fileServer = new ScriptManager(this.context);
        this.scriptLastModified = new HashMap<>();
        this.executor = Executors.newSingleThreadExecutor();
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    public static ScriptEngine getInstance(Context context) {
        if (INSTANCE == null) {
            synchronized (ScriptEngine.class) {
                if (INSTANCE == null) {
                    INSTANCE = new ScriptEngine(context);
                }
            }
        }
        return INSTANCE;
    }

    public void init() {
        Timber.tag(TAG).d("初始化ScriptEngine");
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

            // 执行main入口函数
            try {
                mainModule = py.getModule("main");
                mainModule.callAttr("main");
                Timber.d("Python main()函数执行成功");
            } catch (Exception e) {
                Timber.e(e, "执行Python main()函数失败");
                // 打印更详细的错误信息
                if (e.getCause() != null) {
                    Timber.e("Cause: %s", e.getCause().getMessage());
                }
            }
        } catch (Exception e) {
            Timber.e(e, "初始化Python环境失败");
        }
    }
} 