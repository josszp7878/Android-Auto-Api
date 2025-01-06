package cn.vove7.andro_accessibility_api.demo.script;

import android.os.Build;
import android.util.Log;
import android.os.Handler;
import android.os.Looper;
import android.app.AlertDialog;

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

public class FileServer {
    private static final String TAG = "FileServer";
    public String UrlBase() {
        return "http://" + context.getServerIP();
    }
    private final MainActivity context;
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();

    public FileServer(MainActivity context) {
        this.context = context;
    }

    public void checkAndUpdateScripts(UpdateCallback callback) {
        new Thread(() -> {
            try {
                boolean success = false;
                String errorMsg = null;
                
                try {
                    JSONObject currentVersions = getCurrentVersions();
                    JSONObject remoteVersions = fetchRemoteVersions();
                    Iterator<String> keys = remoteVersions.keys();
                    
                    while (keys.hasNext()) {
                        String filename = keys.next();
                        String remoteVersion = remoteVersions.getString(filename);
                        String currentVersion = currentVersions.optString(filename, "0");

                        if (Long.parseLong(remoteVersion) > Long.parseLong(currentVersion)) {
                            Timber.tag(TAG).d("检测到脚本更新: %s", filename);
                            downloadScript(filename);
                            success = true;
                        }
                    }

                    if (success) {
                        saveVersions(remoteVersions);
                        Timber.tag(TAG).d("脚本版本信息已更新");
                    }
                } catch (Exception e) {
                    Timber.e(e, "更新脚本失败");
                    errorMsg = "更新失败: " + e.getMessage();
                }
                
                final String finalErrorMsg = errorMsg;
                final boolean finalSuccess = success;
                
                new Handler(Looper.getMainLooper()).post(() -> {
                    if (!finalSuccess && finalErrorMsg != null) {
                        showMessage("更新提示", "脚本" + finalErrorMsg + "，将使用本地脚本继续运行");
                    }
                    callback.onComplete(finalSuccess);
                });
            } catch (Exception e) {
                Timber.e(e, "检查更新失败");
                new Handler(Looper.getMainLooper()).post(() -> {
                    showMessage("更新提示", "检查更新失败，将使用本地脚本继续运行");
                    callback.onComplete(false);
                });
            }
        }).start();
    }

    private void showMessage(String title, String message) {
        new AlertDialog.Builder(context)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("确定", null)
            .show();
    }

    public interface UpdateCallback {
        void onComplete(boolean success);
    }

    private void downloadScript(String filename) throws IOException {
        Timber.tag(TAG).d("正在下载: %s", filename);
        URL url = new URL(UrlBase() + ":" + Port + "/scripts/" + filename);
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

    private static final int Port = 5000;

    private JSONObject fetchRemoteVersions() throws IOException {
        Timber.tag(TAG).d("获取远程文件时间戳...");
        String urlStr = UrlBase() + ":" + Port + "/timestamps";
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
                Timber.tag(TAG).d("收到响应: %s", jsonStr);
                if(jsonStr.isEmpty()){
                    throw new RuntimeException("收到响应为空");
                }
                JSONObject remoteVersions = new JSONObject(jsonStr);
                Iterator<String> keys = remoteVersions.keys();
                while (keys.hasNext()) {
                    String filename = keys.next();
                    if (filename.startsWith("_")) {
                        Timber.tag(TAG).d("忽略文件: %s", filename);
                        keys.remove();
                    }
                }
                return remoteVersions;
            }
        } catch (Exception e) {
            Timber.tag(TAG).e(e, "请求失败: %s", e.getMessage());
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
        Timber.tag(TAG).d("脚本目录: %s", dir.getAbsolutePath());
        return dir;
    }
} 