package cn.vove7.andro_accessibility_api.demo.script;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.util.Log;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import cn.vove7.andro_accessibility_api.demo.service.ToolBarService;
import timber.log.Timber;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.InputStreamReader;
import java.util.concurrent.ExecutionException;
import java.lang.reflect.Type;

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
    private static final String SCRIPTS_DIR = "scripts";
    private final ExecutorService executor = Executors.newFixedThreadPool(3);

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
                    // INSTANCE.initScripts();
                }
            }
        }
        return INSTANCE;
    }

    public void init(String deviceName, String serverName) {
        try {
            uninit();
            // 启动Python环境
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(applicationContext));
            }
            py = Python.getInstance();
            
            // 设置Python脚本路径
            File scriptDir = new File(context.getFilesDir(), SCRIPTS_DIR);
            Timber.d("Python脚本目录: %s", scriptDir.getAbsolutePath());

            // 确保脚本目录在Python路径最前面
            PyObject sysModule = py.getModule("sys");
            PyObject pathList = sysModule.get("path");
            pathList.callAttr("insert", 0, scriptDir.getAbsolutePath());

            // 执行Begin入口函数
            try {
                mainModule = py.getModule("CMain");
                mainModule.callAttr("Begin", deviceName, serverName, true);
                Timber.d("Python Begin()函数执行成功");
            } catch (Exception e) {
                Timber.e(e, "执行Python Begin()函数失败");
                if (e.getCause() != null) {
                    Timber.e("Cause: %s", e.getCause().getMessage());
                }
            }
        } catch (Exception e) {
            Timber.e(e, "初始化失败");
        }
    }

    public void uninit() {
        if (py != null) {
            try {
                if (mainModule != null) {
                    mainModule.callAttr("End");
                    mainModule = null;
                }
                // Python实例不需要显式关闭
                py = null;
            } catch (Exception e) {
                Timber.e(e, "关闭旧Python实例失败");
            }
        }
    }

    private void initScripts() {
        try {
            File scriptsDir = new File(context.getFilesDir(), SCRIPTS_DIR);
            // 如果scripts目录不存在，创建并复制初始脚本
            if (!scriptsDir.exists()) {
                Log.i(TAG, "First run, initializing scripts directory");
                if (!scriptsDir.mkdirs()) {
                    Log.e(TAG, "Failed to create scripts directory");
                }
                Log.i(TAG, "安装后第一次运行，初始化脚本目录");
                copyScriptsFromAssets(context, scriptsDir);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize script engine", e);
        }
    }

    private static void copyScriptsFromAssets(Context context, File scriptsDir) {
        try {
            // 列出assets/scripts目录下的所有文件
            String[] files = context.getAssets().list(SCRIPTS_DIR);
            if (files != null) {
                for (String fileName : files) {
                    // 跳过隐藏文件
                    if (fileName.startsWith(".")) continue;
                    
                    String assetPath = SCRIPTS_DIR + "/" + fileName;
                    File targetFile = new File(scriptsDir, fileName);
                    
                    // 从assets复制文件
                    try (InputStream in = context.getAssets().open(assetPath);
                         OutputStream out = new FileOutputStream(targetFile)) {
                        
                        byte[] buffer = new byte[1024];
                        int read;
                        while ((read = in.read(buffer)) != -1) {
                            out.write(buffer, 0, read);
                        }
                        out.flush();
                        // Log.i(TAG, "Copied script: " + fileName);
                    }
                }
            }
        } catch (IOException e) {
            Log.e(TAG, "Failed to copy scripts from assets", e);
        }
    }

    public void syncFiles(String serverIP) {
        if (!checkNetwork()) {
            Timber.e("网络不可用，无法同步文件");
            return;
        }
        executor.execute(() -> {
            try {
                String baseUrl = "http://" + serverIP + ":5000";
                Map<String, Long> remoteVersions = getRemoteVersions(baseUrl);
                Map<String, Long> localVersions = loadLocalVersions();

                // 创建需要同步的文件列表
                List<String> toUpdate = new ArrayList<>();
                for (Map.Entry<String, Long> entry : remoteVersions.entrySet()) {
                    String filename = entry.getKey();
                    Long localTime = localVersions.getOrDefault(filename, 0L);
                    if (entry.getValue() > localTime) {
                        toUpdate.add(filename);
                    }
                }

                if (toUpdate.isEmpty()) {
                    Timber.d("所有文件均为最新版本");
                    return;
                }

                // 并行下载文件
                List<Future<?>> futures = new ArrayList<>();
                for (String filename : toUpdate) {
                    futures.add(executor.submit(() -> {
                        try {
                            downloadFile(baseUrl, filename);
                        } catch (IOException e) {
                            throw new RuntimeException(e);
                        }
                    }));
                }

                // 等待所有下载完成
                for (Future<?> future : futures) {
                    try {
                        future.get();
                    } catch (ExecutionException e) {
                        Timber.e(e.getCause(), "文件下载失败");
                    }
                }

                // 保存新版本信息
                saveLocalVersions(remoteVersions);
                Timber.i("文件同步完成，共更新 %d 个文件", toUpdate.size());
                Timber.d("更新文件列表: %s", toUpdate);

                Timber.d("远程版本 vs 本地版本对比结果:");
                for (Map.Entry<String, Long> entry : remoteVersions.entrySet()) {
                    String status = entry.getValue() > localVersions.getOrDefault(entry.getKey(), 0L) 
                        ? "需要更新" : "已是最新";
                    Timber.d("文件 %-20s 远程版本:%-10d 本地版本:%-10d 状态:%s",
                            entry.getKey(), entry.getValue(), 
                            localVersions.getOrDefault(entry.getKey(), 0L), status);
                }

            } catch (Exception e) {
                Timber.e(e, "文件同步失败");
            } finally {
                Timber.d("文件同步线程结束");
            }
        });
    }

    private Map<String, Long> getRemoteVersions(String baseUrl) throws IOException {
        Timber.d("正在获取远程版本信息...");
        HttpURLConnection conn = (HttpURLConnection) new URL(baseUrl + "/timestamps").openConnection();
        conn.setRequestMethod("GET");
        
        try (InputStream in = conn.getInputStream()) {
            Type type = new TypeToken<Map<String, Long>>(){}.getType();
            Map<String, Long> versions = new Gson().fromJson(new InputStreamReader(in), type);
            Timber.d("获取到 %d 个文件的远程版本信息", versions.size());
            return versions;
        } catch (Exception e) {
            Timber.e(e, "获取远程版本失败");
            throw e;
        }
    }

    private void downloadFile(String baseUrl, String filename) throws IOException {
        Timber.d("开始下载文件: %s", filename);
        long startTime = System.currentTimeMillis();
        
        String url = baseUrl + "/file/" + filename;
        File targetFile = new File(context.getFilesDir(), filename);
        
        // 创建父目录
        if (!targetFile.getParentFile().exists()) {
            targetFile.getParentFile().mkdirs();
        }

        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        try (InputStream in = conn.getInputStream();
             FileOutputStream out = new FileOutputStream(targetFile)) {
            
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = in.read(buffer)) != -1) {
                out.write(buffer, 0, bytesRead);
            }
            Timber.d("文件 %s 下载完成 (耗时 %dms)", filename, System.currentTimeMillis()-startTime);
        }
    }

    private Map<String, Long> loadLocalVersions() {
        Timber.d("加载本地版本信息");
        File versionFile = new File(context.getFilesDir(), "version.txt");
        if (!versionFile.exists()) return new HashMap<>();

        try (FileReader reader = new FileReader(versionFile)) {
            Type type = new TypeToken<Map<String, Long>>(){}.getType();
            Map<String, Long> versions = new Gson().fromJson(reader, type);
            Timber.d("已加载 %d 个本地文件版本", versions.size());
            return versions;
        } catch (IOException e) {
            return new HashMap<>();
        }
    }

    private void saveLocalVersions(Map<String, Long> versions) throws IOException {
        Timber.i("保存 %d 个文件的版本信息", versions.size());
        File versionFile = new File(context.getFilesDir(), "version.txt");
        try (FileWriter writer = new FileWriter(versionFile)) {
            new Gson().toJson(versions, writer);
        }
    }

    private boolean checkNetwork() {
        ConnectivityManager cm = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo activeNetwork = cm.getActiveNetworkInfo();
        return activeNetwork != null && activeNetwork.isConnected();
    }
} 
