package cn.vove7.andro_accessibility_api.demo.script;

import android.content.Context;
import android.os.Build;
import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.json.JSONObject;
import org.json.JSONException;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import cn.vove7.andro_accessibility_api.demo.MainActivity;
import timber.log.Timber;

public class ScriptManager {
    private static final String TAG = "ScriptManager";
    public String TIMESTAMP_API() {
        return "http://" + context.getServerIP() + "/timestamp";
    }
    public String BASE_URL() {
        return "http://" + context.getServerIP() + "/base";
    }
    private final MainActivity context;
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();
    
    public ScriptManager(MainActivity context) {
        this.context = context;
    }

    public void checkAndUpdateScripts()
    {
        executorService.submit(() -> {
            boolean updated = false;
            try {
                JSONObject currentVersions = getCurrentVersions();
                JSONObject remoteVersions = fetchRemoteVersions();
                Iterator<String> keys = remoteVersions.keys();
                while (keys.hasNext()) {
                    String filename = keys.next();
                    String remoteVersion = remoteVersions.getString(filename);
                    String currentVersion = currentVersions.optString(filename, "0");
                    
                    if (Long.parseLong(remoteVersion) > Long.parseLong(currentVersion)) {
                        Log.d(TAG, "检测到脚本更新: " + filename);
                        downloadScript(filename);
                        updated = true;
                    }
                }
                
                if (updated) {
                    saveVersions(remoteVersions);
                    Log.d(TAG, "脚本版本信息已更新");
                }
            } catch (JSONException | IOException e) {
                Log.e(TAG, "处理版本信息时出错", e);
            }
        });
    }

    private void downloadScript(String filename) throws IOException {
        Log.d(TAG, "正在下载: " + filename);
        URL url = new URL(BASE_URL() + filename);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        try {
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);
            
            conn.setRequestProperty("Accept-Charset", "UTF-8");
            conn.setRequestProperty("Content-Type", "text/plain; charset=utf-8");
            
            if (conn.getResponseCode() != HttpURLConnection.HTTP_OK) {
                String error = "下载失败: HTTP " + conn.getResponseCode();
                Log.e(TAG, error);
                throw new IOException(error);
            }
            
            File scriptDir = new File(context.getFilesDir(), "scripts");
            scriptDir.mkdirs();
            
            File scriptFile = new File(scriptDir, filename);
            try (InputStream in = conn.getInputStream()) {
                StringBuilder content = new StringBuilder();
                try (java.io.BufferedReader reader = new java.io.BufferedReader(
                        new java.io.InputStreamReader(in, StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        content.append(line).append("\n");
                    }
                }
                
                try (FileOutputStream out = new FileOutputStream(scriptFile)) {
                    out.write(content.toString().getBytes(StandardCharsets.UTF_8));
                }
                
                Log.d(TAG, String.format("下载完成: %s (大小: %d bytes)", 
                    filename, scriptFile.length()));
            }
        } catch (IOException e) {
            Log.e(TAG, "下载脚本出错: " + filename, e);
            throw e;
        } finally {
            conn.disconnect();
        }
    }

    private JSONObject getCurrentVersions() {
        File versionFile = new File(context.getFilesDir(), "version.txt");
        if (!versionFile.exists()) {
            return new JSONObject();
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try (InputStream in = Files.newInputStream(versionFile.toPath())) {
                byte[] content = new byte[(int) versionFile.length()];
                in.read(content);
                String jsonStr = new String(content, StandardCharsets.UTF_8);
                return new JSONObject(jsonStr);
            } catch (Exception e) {
                Timber.tag(TAG).e(e, "读取版本信息出错");
                return new JSONObject();
            }
        }
        return null;
    }

    private JSONObject fetchRemoteVersions() throws IOException {
        Timber.tag(TAG).d("获取远程文件时间戳...");
        String urlStr = TIMESTAMP_API();
        Timber.tag(TAG).d("请求URL: %s", urlStr);
        
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        
        try {
            conn.setRequestMethod("GET");
            conn.setDoInput(true);
            conn.setUseCaches(false);
            
            conn.setRequestProperty("User-Agent", "Mozilla/5.0");
            conn.setRequestProperty("Accept", "*/*");
            conn.setRequestProperty("Connection", "close");
            
            Log.d(TAG, "开始建立连接...");
            conn.connect();
            Log.d(TAG, "连接已建立");
            
            int responseCode = conn.getResponseCode();
            Timber.tag(TAG).d("响应码: %s", responseCode);
            
            if (responseCode != HttpURLConnection.HTTP_OK) {
                throw new IOException("获取时间戳失败: HTTP " + responseCode);
            }
            
            try (InputStream in = conn.getInputStream()) {
                StringBuilder response = new StringBuilder();
                byte[] buffer = new byte[1024];
                int bytesRead;
                while ((bytesRead = in.read(buffer)) != -1) {
                    response.append(new String(buffer, 0, bytesRead, StandardCharsets.UTF_8));
                }
                String jsonStr = response.toString();
                Log.d(TAG, "收到响应: " + jsonStr);
                
                JSONObject remoteVersions = new JSONObject(jsonStr);
                Iterator<String> keys = remoteVersions.keys();
                while (keys.hasNext()) {
                    String filename = keys.next();
                    if (filename.startsWith("_")) {
                        Log.d(TAG, "忽略文件: " + filename);
                        keys.remove();
                    }
                }
                return remoteVersions;
            }
        } catch (Exception e) {
            Log.e(TAG, "请求失败: " + e.getMessage(), e);
            throw new IOException("获取时间戳失败: " + e.getMessage());
        } finally {
            conn.disconnect();
        }
    }

    private void saveVersions(JSONObject versions) throws IOException {
        File versionFile = new File(context.getFilesDir(), "version.txt");
        try (FileOutputStream fos = new FileOutputStream(versionFile)) {
            fos.write(versions.toString().getBytes(StandardCharsets.UTF_8));
        }
    }

    public File getScriptDir() {
        File dir = new File(context.getFilesDir(), "scripts");
        Log.d(TAG, "脚本目录: " + dir.getAbsolutePath());
        return dir;
    }
} 