package cn.vove7.andro_accessibility_api.demo.script;

import android.annotation.SuppressLint;
import android.content.Context;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.File;
import java.util.HashMap;
import java.util.Map;
import android.util.Log;

import java.io.IOException;
import android.os.Handler;
import android.os.Looper;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ScriptEngine {

    private static final String TAG = "ScriptEngine";
    private static volatile ScriptEngine INSTANCE;
    private Python py;
    private PyObject pythonModule;
    private final Map<String, Long> scriptLastModified;
    private static final long CHECK_INTERVAL = 5000;
    private long lastCheckTime;
    private final Context context;
    private final ScriptManager scriptManager;
    private final ExecutorService executor;
    private final Handler mainHandler;

    private ScriptEngine(Context context) {
        this.context = context.getApplicationContext();
        this.scriptManager = new ScriptManager(this.context);
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

    // 初始化脚本引擎
    public void init() {
        Log.d(TAG, "初始化ScriptEngine, ");

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(context));
        }
        py = Python.getInstance();
        
        File scriptDir = scriptManager.getScriptDir();
        Log.d("ScriptEngine", "脚本目录: " + scriptDir.getAbsolutePath());
        
        PyObject sysPath = py.getModule("sys").get("path");
        sysPath.callAttr("insert", 0, scriptDir.getAbsolutePath());
        
        executor.execute(() -> {
            try {
                Log.d("ScriptEngine", "正在检查脚本更新...");
                if (scriptManager.checkAndUpdateScripts()) {
                    Log.d("ScriptEngine", "脚本已更新到新版本");
                    mainHandler.post(this::loadScripts);
                } else {
                    Log.d("ScriptEngine", "脚本已是最新版本");
                }
            } catch (IOException e) {
                Log.e("ScriptEngine", "检查脚本更新失败: " + e.getMessage(), e);
            }
        });
        
        loadScripts();
    }

    @SuppressLint("LogNotTimber")
    private void loadScripts() {
        File scriptsDir = scriptManager.getScriptDir();
        Log.d("ScriptEngine", "开始加载脚本目录中的文件...");
        
        File[] scriptFiles = scriptsDir.listFiles((dir, name) -> name.endsWith(".py"));
        if (scriptFiles != null) {
            Log.d("ScriptEngine", "找到 " + scriptFiles.length + " 个Python脚本文件");
            for (File script : scriptFiles) {
                loadScript(script);
            }
        } else {
            Log.e("ScriptEngine", "脚本目录为空或无法访问");
        }
    }

    private void loadScript(File scriptFile) {
        try {
            String moduleName = scriptFile.getName().replace(".py", "");
            Log.d("ScriptEngine", "正在加载脚本模块: " + moduleName);
            
            // 直接使用Python的import机制
            PyObject importlib = py.getModule("importlib");
            this.pythonModule = importlib.callAttr("import_module", moduleName);
            
            Log.d("ScriptEngine", "脚本加载成功: " + moduleName);
            scriptLastModified.put(scriptFile.getAbsolutePath(), scriptFile.lastModified());
            
        } catch (Exception e) {
            Log.e("ScriptEngine", "加载脚本时出错: " + scriptFile.getName(), e);
            e.printStackTrace();
        }
    }

    public void checkAndReloadScripts() {
        long currentTime = System.currentTimeMillis();
        if (currentTime - lastCheckTime < CHECK_INTERVAL) {
            return;
        }
        lastCheckTime = currentTime;

        // 使用线程池执行检查
        executor.execute(() -> {
            Log.d("ScriptEngine", "检查脚本是否需要重新加载...");
            File scriptsDir = scriptManager.getScriptDir();
            File[] scriptFiles = scriptsDir.listFiles((dir, name) -> name.endsWith(".py"));
            if (scriptFiles != null) {
                for (File script : scriptFiles) {
                    String path = script.getAbsolutePath();
                    Long lastModified = scriptLastModified.get(path);
                    if (lastModified == null || lastModified < script.lastModified()) {
                        Log.d("ScriptEngine", "检测到脚本变更，重新加载: " + script.getName());
                        // 在主线程加载脚本
                        mainHandler.post(() -> loadScript(script));
                    }
                }
            }
        });
    }

    public PyObject executeCommand(String command) {
        try {
            if (pythonModule != null) {
                Log.d("ScriptEngine", "执行命令: " + command);
                PyObject doFunction = pythonModule.get("do");
                if (doFunction != null) {
                    PyObject result = doFunction.call(command);
                    Log.d("ScriptEngine", "命令执行结果: " + result.toString());
                    return result;
                } else {
                    Log.e("ScriptEngine", "找不到 do 函数");
                }
            } else {
                Log.e("ScriptEngine", "Python模块未加载");
            }
        } catch (Exception e) {
            Log.e("ScriptEngine", "执行命令出错: " + command, e);
        }
        return null;
    }

    public PyObject getModule(String name) {
        try {
            // 先检查模块是否已加载
            PyObject sys = py.getModule("sys");
            PyObject modules = sys.get("modules");
            
            // 如果模块已加载，先移除它
            if (modules != null && modules.callAttr("__contains__", name).toBoolean()) {
                modules.callAttr("pop", name);
            }
            
            // 重新加载模块
            return py.getModule(name);
        } catch (Exception e) {
            Log.e("ScriptEngine", "Error loading module: " + name, e);
            return null;
        }
    }

    public void reloadModule(String name) {
        try {
            PyObject importlib = py.getModule("importlib");
            PyObject module = getModule(name);
            if (module != null) {
                importlib.callAttr("reload", module);
            }
        } catch (Exception e) {
            Log.e("ScriptEngine", "Error reloading module: " + name, e);
        }
    }

    @Override
    protected void finalize() throws Throwable {
        try {
            executor.shutdown(); // 关闭线程池
            PyObject sys = py.getModule("sys");
            PyObject modules = sys.get("modules");
            if (modules != null) {
                modules.callAttr("clear");
            }
        } catch (Exception e) {
            Log.e("ScriptEngine", "Error cleaning up", e);
        }
        super.finalize();
    }
} 