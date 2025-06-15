package cn.vove7.andro_accessibility_api.demo.script;

import android.annotation.SuppressLint;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;
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
import java.io.BufferedReader;

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
                }
            }
        }
        return INSTANCE;
    }

    
    public void start(String deviceName, String serverName) {
        try {
            end();
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

    public void end() {
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

    /**
     * 调用Python函数
     * @param functionPath Python函数路径，如 "_G._G_.Log().log"
     * @param args 函数参数
     * @return 函数返回值
     */
    public Object callPythonFunction(String functionPath, Object... args) {
        try {
            if (py == null) {
                Timber.w("Python环境未初始化，无法调用函数: %s", functionPath);
                return null;
            }
            
            // 获取_G模块
            PyObject gModule = py.getModule("_G");
            if (gModule == null) {
                Timber.e("无法获取_G模块");
                return null;
            }
            
            // 获取_G_类
            PyObject gClass = gModule.get("_G_");
            if (gClass == null) {
                Timber.e("无法获取_G_类");
                return null;
            }
            
            // 根据函数路径调用对应的方法
            if (functionPath.equals("_G._G_.Log().log")) {
                // 调用Log().log方法
                PyObject logInstance = gClass.callAttr("Log");
                if (logInstance != null) {
                    PyObject result = logInstance.callAttr("log", args);
                    return result != null ? result.toJava(Object.class) : null;
                }
            }
            // 可以在这里添加更多函数路径的支持
            
            Timber.w("不支持的函数路径: %s", functionPath);
            return null;
            
        } catch (Exception e) {
            Timber.e(e, "调用Python函数失败: %s", functionPath);
            return null;
        }
    }



    // 同步所有脚本文件到本地（清空后重新同步所有文件）
    public void syncFiles(String serverIP) {
        if (!checkNetwork()) {
            Timber.e("网络不可用，无法同步文件");
            return;
        }
        executor.execute(() -> {
            try {
                String baseUrl = "http://" + serverIP + ":5000";
                
                // 获取远程所有文件列表
                Map<String, Long> remoteVersions = getRemoteVersions(baseUrl);
                
                // 清空本地脚本目录
                clearLocalScripts();
                Timber.i("已清空本地脚本目录，准备重新同步 %d 个文件", remoteVersions.size());

                // 并行下载所有文件
                List<Future<?>> futures = new ArrayList<>();
                for (String filename : remoteVersions.keySet()) {
                    futures.add(executor.submit(() -> {
                        try {
                            downloadFile(baseUrl, filename);
                        } catch (IOException e) {
                            throw new RuntimeException(e);
                        }
                    }));
                }

                // 等待所有下载完成
                int successCount = 0;
                int failCount = 0;
                for (Future<?> future : futures) {
                    try {
                        future.get();
                        successCount++;
                    } catch (ExecutionException e) {
                        failCount++;
                        Timber.e(e.getCause(), "文件下载失败");
                    }
                }

                // 注意：全量同步模式下不需要保存版本信息
                
                // 显示同步结果
                final int finalSuccessCount = successCount;
                final int finalFailCount = failCount;
                new Handler(Looper.getMainLooper()).post(() -> {
                    String message = String.format("同步完成: 成功 %d 个，失败 %d 个", finalSuccessCount, finalFailCount);
                    Toast.makeText(context, message, Toast.LENGTH_SHORT).show();
                });
                
                Timber.i("脚本文件同步完成: 成功 %d 个，失败 %d 个", successCount, failCount);
                
            } catch (java.net.ConnectException e) {
                // 处理连接异常
                Timber.e(e, "连接服务器失败: %s", serverIP);
                new Handler(Looper.getMainLooper()).post(() -> {
                    Toast.makeText(context, "连接服务器失败: " + serverIP, Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                Timber.e(e, "同步文件失败");
                new Handler(Looper.getMainLooper()).post(() -> {
                    Toast.makeText(context, "同步文件失败: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                });
            }
        });
    }

    private Map<String, Long> getRemoteVersions(String baseUrl) throws IOException {
        String url = baseUrl + "/timestamps";
        HttpURLConnection connection = null;
        
        try {
            // 创建连接
            connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setConnectTimeout(5000); // 5秒连接超时
            connection.setReadTimeout(5000);    // 5秒读取超时
            connection.setRequestMethod("GET");
            
            // 检查响应码
            int responseCode = connection.getResponseCode();
            if (responseCode != HttpURLConnection.HTTP_OK) {
                throw new IOException("服务器响应错误: " + responseCode);
            }
            
            // 读取响应
            StringBuilder response = new StringBuilder();
            try (InputStreamReader reader = new InputStreamReader(connection.getInputStream());
                 BufferedReader bufferedReader = new BufferedReader(reader)) {
                
                String line;
                while ((line = bufferedReader.readLine()) != null) {
                    response.append(line);
                }
            }
            
            // 解析JSON
            Type type = new TypeToken<Map<String, Long>>(){}.getType();
            return new Gson().fromJson(response.toString(), type);
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
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



    private boolean checkNetwork() {
        ConnectivityManager cm = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo activeNetwork = cm.getActiveNetworkInfo();
        return activeNetwork != null && activeNetwork.isConnected();
    }

    private void clearLocalScripts() {
        Timber.i("开始清空本地脚本目录");
        File scriptsDir = new File(context.getFilesDir(), SCRIPTS_DIR);
        
        if (scriptsDir.exists()) {
            deleteRecursively(scriptsDir);
            Timber.d("已删除脚本目录: %s", scriptsDir.getAbsolutePath());
        }
        
        // 重新创建scripts目录
        if (!scriptsDir.exists()) {
            scriptsDir.mkdirs();
            Timber.d("已重新创建脚本目录: %s", scriptsDir.getAbsolutePath());
        }
        
        // 同时清理根目录下的.py文件和版本文件
        File filesDir = context.getFilesDir();
        File[] rootFiles = filesDir.listFiles();
        if (rootFiles != null) {
            for (File file : rootFiles) {
                if (file.isFile()) {
                    String fileName = file.getName();
                    if (fileName.endsWith(".py") || fileName.equals("version.txt")) {
                        if (file.delete()) {
                            Timber.d("已删除文件: %s", fileName);
                        }
                    }
                }
            }
        }
        
        Timber.i("本地脚本目录清空完成");
    }

    private void deleteRecursively(File file) {
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteRecursively(child);
                }
            }
        }
        file.delete();
    }
    
} 
