package cn.vove7.andro_accessibility_api.demo.service;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.Image;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.hardware.display.VirtualDisplay;
import android.media.projection.MediaProjectionManager;
import android.util.DisplayMetrics;
import android.util.Log;
import android.widget.ImageView;

import java.nio.ByteBuffer;
import java.io.IOException;
import java.io.OutputStream;
import android.content.ContentValues;
import android.net.Uri;
import android.provider.MediaStore;
import android.os.Environment;
import android.content.ContentResolver;

import androidx.core.app.NotificationCompat;
import androidx.appcompat.app.AlertDialog;

import java.io.ByteArrayOutputStream;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import android.graphics.Point;
import android.graphics.PointF;
import android.graphics.Rect;

import android.os.PowerManager;
import android.os.Build;

import cn.vove7.andro_accessibility_api.demo.MainActivity;
import cn.vove7.andro_accessibility_api.demo.R;


/** @noinspection ALL*/
public class ScreenCapture extends Service {
    private MediaProjection mediaProjection;
    private final IBinder binder = new LocalBinder();
    
    public class LocalBinder extends Binder {
        public ScreenCapture getService() {
            return ScreenCapture.this;
        }
    }

    boolean isBound = false;
    private MediaProjectionManager mediaProjectionManager;
    private boolean isInitialized = false;
    public static final int REQUEST_CODE_SCREEN_CAPTURE = 1000;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private int lastWidth = -1;
    private int lastHeight = -1;
    private PowerManager.WakeLock wakeLock;
    private static final int NOTIFICATION_ID = 1001;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d("ScreenCapture", "Service onCreate called");
        acquireWakeLock();
    }

    private void initialize() {
        if (!isInitialized) {
            mediaProjectionManager = (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
            startForegroundService();
            isInitialized = true;
            Log.d("ScreenCapture", "Service initialized");
        }
    }

    public static ServiceConnection Begin(Activity activity) {
        // 创建通知渠道
        NotificationChannel serviceChannel = new NotificationChannel(
                activity.getString(R.string.your_channel_id),
                "Screen Capture Service",
                NotificationManager.IMPORTANCE_DEFAULT
        );
        NotificationManager manager = activity.getSystemService(NotificationManager.class);
        manager.createNotificationChannel(serviceChannel);

        // 创建 ServiceConnection
        ServiceConnection serviceConnection = new ServiceConnection() {
            @Override
            public void onServiceConnected(ComponentName name, IBinder service) {
                LocalBinder binder = (LocalBinder) service;
                ScreenCapture screenCapture = binder.getService();
                screenCapture.initialize();
                screenCapture.isBound = true;
                if (activity instanceof MainActivity) {
                    ((MainActivity) activity).setScreenCapture(screenCapture);
                }
                Log.d("ScreenCapture", "Service connected");
            }

            @Override
            public void onServiceDisconnected(ComponentName name) {
                Log.d("ScreenCapture", "Service disconnected");
                if (activity instanceof MainActivity) {
                    ((MainActivity) activity).setScreenCapture(null);
                }
            }
        };

        // 先启动服务
        Intent serviceIntent = new Intent(activity, ScreenCapture.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            activity.startForegroundService(serviceIntent);
        } else {
            activity.startService(serviceIntent);
        }
        
        // 再绑定服务
        boolean bound = activity.bindService(serviceIntent, serviceConnection, Context.BIND_AUTO_CREATE);
        Log.d("ScreenCapture", "Service started and bound: " + bound);
        return serviceConnection;
    }

    public void End() {
        Log.d("ScreenCapture", "stopService called", new Exception("Stop service stack trace"));
        if (isBound) {
            Log.d("ScreenCapture", "Service is bound, stopping foreground and self");
            stopForeground(true);
            stopSelf();
            isBound = false;
        } else {
            Log.d("ScreenCapture", "Service is not bound when trying to stop");
        }
    }
    public void requestScreenCapturePermission(Activity activity) {
        Intent intent = mediaProjectionManager.createScreenCaptureIntent();
        activity.startActivityForResult(intent, REQUEST_CODE_SCREEN_CAPTURE);
    }

    private void startForegroundService() {
        String channelId = getString(R.string.your_channel_id);
        
        // 创建通知渠道
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    channelId,
                    "Screen Capture Service",
                    NotificationManager.IMPORTANCE_DEFAULT);
            channel.setLockscreenVisibility(Notification.VISIBILITY_PRIVATE);
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(channel);
        }

        // 创建打开应用的 Intent
        Intent notificationIntent = new Intent(this, MainActivity.class);
        notificationIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0,
                notificationIntent, PendingIntent.FLAG_IMMUTABLE);

        // 构建通知
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, channelId)
                .setContentTitle("屏幕截图服务")
                .setContentText("服务正在运行中")
                .setSmallIcon(R.drawable.icon_background)
                .setOngoing(true)
                .setContentIntent(pendingIntent)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setCategory(NotificationCompat.CATEGORY_SERVICE)
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE);

        startForeground(NOTIFICATION_ID, builder.build());
    }

    private void saveImageToGallery(Bitmap bitmap) {
        if (bitmap == null) {
            Log.e("ScreenCapture", "Cannot save null bitmap");
            return;
        }

        String fileName = "screenshot_" + System.currentTimeMillis() + ".jpg";
        ContentValues values = new ContentValues();
        values.put(MediaStore.Images.Media.DISPLAY_NAME, fileName);
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
        
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            values.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES);
            values.put(MediaStore.Images.Media.IS_PENDING, 1);
        }

        ContentResolver resolver = getContentResolver();
        Uri imageUri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);

        try {
            if (imageUri != null) {
                try (OutputStream out = resolver.openOutputStream(imageUri)) {
                    if (out != null) {
                        bitmap.compress(Bitmap.CompressFormat.JPEG, 100, out);
                        Log.d("ScreenCapture", "Screenshot saved to gallery: " + fileName);
                    } else {
                        Log.e("ScreenCapture", "Failed to open output stream");
                    }
                }
                
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                    values.clear();
                    values.put(MediaStore.Images.Media.IS_PENDING, 0);
                    resolver.update(imageUri, values, null, null);
                }
            } else {
                Log.e("ScreenCapture", "Failed to create image URI");
            }
        } catch (IOException e) {
            Log.e("ScreenCapture", "Error saving screenshot: " + e.getMessage());
        }
    }

    @SuppressLint("WrongConstant")
    private void ensureVirtualDisplay(int width, int height) {
        if (width != lastWidth || height != lastHeight || virtualDisplay == null || imageReader == null) {
            releaseLastCapture();
            
            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2);
            
            virtualDisplay = mediaProjection.createVirtualDisplay("ScreenCapture",
                    width, height, 160, DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                    imageReader.getSurface(), null, null);
                    
            lastWidth = width;
            lastHeight = height;
            Log.d("ScreenCapture", "Created new virtual display");
        }
    }

    public byte[] takeScreenshot(int x, int y, int width, int height) {
        Log.d("ScreenCapture", "takeScreenshot with params: x=" + x + ", y=" + y + ", width=" + width + ", height=" + height);
        if (mediaProjection == null) return null;

        // 获取屏幕尺寸
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        int screenWidth = metrics.widthPixels;
        int screenHeight = metrics.heightPixels;

        // 如果是全屏截图
        if (x < 0 || y < 0) {
            x = 0;
            y = 0;
            width = screenWidth;
            height = screenHeight;
        }

        // 确保截图区域不超出屏幕范围
        if (x + width > screenWidth) width = screenWidth - x;
        if (y + height > screenHeight) height = screenHeight - y;
        if (width <= 0 || height <= 0) return null;

        // 创建屏的VirtualDisplay
        ensureVirtualDisplay(screenWidth, screenHeight);
        Image image = null;

        try {
            int maxTries = 3;
            int tries = 0;
            while ((image = imageReader.acquireLatestImage()) == null && tries < maxTries) {
                tries++;
                Thread.sleep(50);
            }

            if (image != null) {
                try {
                    Image.Plane[] planes = image.getPlanes();
                    Image.Plane plane = planes[0];
                    ByteBuffer buffer = plane.getBuffer();

                    int pixelStride = plane.getPixelStride();
                    int rowStride = plane.getRowStride();
                    
                    // 创建目标区域的像素数组
                    byte[] pixels = new byte[width * height * 4];
                    int pixelPos = 0;

                    // 只复制指定区域的像素
                    for (int row = 0; row < height; row++) {
                        // 计算源图像中的行位置
                        int srcRow = y + row;
                        int srcRowOffset = srcRow * rowStride;
                        
                        for (int col = 0; col < width; col++) {
                            // 计算源图像中的像素位置
                            int srcCol = x + col;
                            int srcPos = srcRowOffset + srcCol * pixelStride;
                            
                            // 确保不会越界
                            if (srcPos + 3 < buffer.capacity()) {
                                pixels[pixelPos++] = buffer.get(srcPos);
                                pixels[pixelPos++] = buffer.get(srcPos + 1);
                                pixels[pixelPos++] = buffer.get(srcPos + 2);
                                pixels[pixelPos++] = buffer.get(srcPos + 3);
                            }
                        }
                    }

                    // 创建指定区域大小的bitmap
                    Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
                    ByteBuffer pixelBuffer = ByteBuffer.wrap(pixels);
                    bitmap.copyPixelsFromBuffer(pixelBuffer);

                    ByteArrayOutputStream stream = new ByteArrayOutputStream();
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream);
                    byte[] byteArray = stream.toByteArray();
                    stream.close();

                    return byteArray;
                } finally {
                    image.close();
                }
            }
        } catch (Exception e) {
            Log.e("ScreenCapture", "Error taking screenshot: " + e.getMessage());
            e.printStackTrace();
        }
        return null;
    }

    private void releaseLastCapture() {
        if (virtualDisplay != null) {
            virtualDisplay.release();
            virtualDisplay = null;
        }
        if (imageReader != null) {
            imageReader.close();
            imageReader = null;
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        Log.d("ScreenCapture", "Service bound");
        return binder;
    }

    public interface ScreenshotCallback {
        void onScreenshotTaken(Bitmap bitmap);
    }

    public void handlePermissionResult(int resultCode, Intent data) {
        if (resultCode == Activity.RESULT_OK) {
            mediaProjection = mediaProjectionManager.getMediaProjection(resultCode, data);
            Log.d("ScreenCapture", "MediaProjection created successfully");
        } else {
            Log.e("ScreenCapture", "Failed to create MediaProjection");
        }
    }

    public boolean hasScreenCapturePermission() {
        return mediaProjection != null;
    }

    /** 截图
     * Captures a screenshot of the specified region.
     * If x or y is less than 0, it captures the full screen.
     * 
     * @param x      The x-coordinate of the top-left corner of the region to capture.
     * @param y      The y-coordinate of the top-left corner of the region to capture.
     * @param width  The width of the region to capture.
     * @param height The height of the region to capture.
     * @param callback The callback to be executed after the screenshot is taken.
     */
    public void takeScreenshot(int x, int y, int width, int height, ScreenshotCallback callback) {
        Log.d("ScreenCapture", "takeScreenshot called");
        new Thread(() -> {
            byte[] screenshotBytes = takeScreenshot(x, y, width, height);
            if (screenshotBytes != null) {
                try {
                    Bitmap bitmap = BitmapFactory.decodeByteArray(screenshotBytes, 0, screenshotBytes.length);
                    if (bitmap != null) {
                        new Handler(Looper.getMainLooper()).post(() -> callback.onScreenshotTaken(bitmap));
                    } else {
                        Log.e("ScreenCapture", "Failed to decode bitmap");
                    }
                } catch (Exception e) {
                    Log.e("ScreenCapture", "Error decoding bitmap: " + e.getMessage());
                    e.printStackTrace();
                }
            } else {
                Log.e("ScreenCapture", "Failed to take screenshot");
            }
        }).start();
    }

    @Override
    public void onDestroy() {
        Log.d("ScreenCapture", "Service onDestroy called", new Exception("Service destroy stack trace"));
        
        if (mediaProjection != null) {
            Log.d("ScreenCapture", "Releasing mediaProjection");
            mediaProjection.stop();
            mediaProjection = null;
        }
        
        releaseLastCapture();
        
        if (wakeLock != null && wakeLock.isHeld()) {
            Log.d("ScreenCapture", "Releasing wakeLock");
            wakeLock.release();
            wakeLock = null;
        }
        
        Log.d("ScreenCapture", "Service destroyed completely");
        super.onDestroy();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d("ScreenCapture", "Service onStartCommand called with action: " + 
            (intent != null ? intent.getAction() : "null"));
        return START_STICKY;
    }

    @Override
    public boolean onUnbind(Intent intent) {
        Log.d("ScreenCapture", "Service onUnbind called", new Exception("Unbind stack trace"));
        isBound = false;
        return super.onUnbind(intent);
    }

    @Override
    public void onRebind(Intent intent) {
        Log.d("ScreenCapture", "Service onRebind called", new Exception("Rebind stack trace"));
        isBound = true;
        super.onRebind(intent);
    }

    public interface OcrCallback {
        void onTextRecognized(List<TextInfo> textInfos);
    }

    // 添加一个数据类来存储文字信息
    public static class TextInfo {
        public final String text;
        public final Point screenPosition;    // 屏幕像素坐标
        public final PointF normalizedPos;    // 归一化坐标 (0-1)
        public final Rect bounds;             // 文字区域边界

        public TextInfo(String text, Point screenPosition, PointF normalizedPos, Rect bounds) {
            this.text = text;
            this.screenPosition = screenPosition;
            this.normalizedPos = normalizedPos;
            this.bounds = bounds;
        }
    }

    public void captureScreen(Activity activity, ImageView imageView, int x, int y, int width, int height) {
        if (hasScreenCapturePermission()) {
            takeScreenshot(x, y, width, height,  (this::saveImageToGallery));
        } else {
            // 显示解释对话框
            new AlertDialog.Builder(activity)
                    .setTitle("需要屏幕截图权限")
                    .setMessage("由于系统安全限，每次启动应用都需要重新授权屏幕截图权限。")
                    .setPositiveButton("授权", (dialog, which) -> {
                        requestScreenCapturePermission(activity);
                    })
                    .setNegativeButton("取消", null)
                    .show();
        }
    }

    /**
     * 对指定区域进行截图并进行OCR识别
     */
    public void recognizeScreenshot(Activity activity, int x, int y, int width, int height, OcrCallback callback) {
        if (hasScreenCapturePermission()) {
            recognizeScreenshot(x, y, width, height, callback);
        } else {
            new AlertDialog.Builder(activity)
                .setTitle("需要屏幕截图权限")
                .setMessage("由于系统安全限制，每次启动应用都需要重新授权屏幕截图权限。")
                .setPositiveButton("授权", (dialog, which) -> {
                    requestScreenCapturePermission(activity);
                })
                .setNegativeButton("取消", null)
                .show();
        }
    }

    private void recognizeScreenshot(int x, int y, int width, int height, OcrCallback callback) {
        new Thread(() -> {
            byte[] screenshotBytes = takeScreenshot(x, y, width, height);
            if (screenshotBytes != null) {
                try {
                    Bitmap bitmap = BitmapFactory.decodeByteArray(screenshotBytes, 0, screenshotBytes.length);
                    if (bitmap != null) {
                        saveImageToGallery(bitmap);
                        recognizeText(bitmap, x, y, callback);  // 传入截图区域的起始坐标
                    } else {
                        Log.e("ScreenCapture", "Failed to decode bitmap for OCR");
                    }
                } catch (Exception e) {
                    Log.e("ScreenCapture", "Error processing image for OCR: " + e.getMessage());
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void recognizeText(Bitmap bitmap, int screenX, int screenY, OcrCallback callback) {
        TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
        InputImage image = InputImage.fromBitmap(bitmap, 0);
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        float screenWidth = metrics.widthPixels;
        float screenHeight = metrics.heightPixels;

        recognizer.process(image)
                .addOnSuccessListener(text -> {
                    List<TextInfo> textInfos = new ArrayList<>();
                    
                    for (Text.TextBlock block : text.getTextBlocks()) {
                        for (Text.Line line : block.getLines()) {
                            for (Text.Element element : line.getElements()) {
                                Rect imageBounds = element.getBoundingBox();
                                if (imageBounds != null) {
                                    // 计算屏幕坐标
                                    Point screenPos = new Point(
                                        screenX + imageBounds.left,
                                        screenY + imageBounds.top
                                    );

                                    // 计算归一化坐标 (0-1)
                                    PointF normalizedPos = new PointF(
                                        screenPos.x / screenWidth,
                                        screenPos.y / screenHeight
                                    );

                                    // 计算屏幕空间中的边界
                                    Rect screenBounds = new Rect(
                                        screenX + imageBounds.left,
                                        screenY + imageBounds.top,
                                        screenX + imageBounds.right,
                                        screenY + imageBounds.bottom
                                    );

                                    textInfos.add(new TextInfo(
                                        element.getText(),
                                        screenPos,
                                        normalizedPos,
                                        screenBounds
                                    ));
                                }
                            }
                        }
                    }

                    new Handler(Looper.getMainLooper()).post(() -> 
                        callback.onTextRecognized(textInfos));
                })
                .addOnFailureListener(e -> {
                    Log.e("ScreenCapture", "Error recognizing text: " + e.getMessage());
                    new Handler(Looper.getMainLooper()).post(() -> 
                        callback.onTextRecognized(Collections.emptyList()));
                });
    }

    private void acquireWakeLock() {
        if (checkSelfPermission(android.Manifest.permission.WAKE_LOCK) 
                == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            if (wakeLock == null) {
                PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
                wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,
                        "ScreenCapture::WakeLockTag");
                wakeLock.acquire();
                Log.d("ScreenCapture", "WakeLock acquired");
            }
        } else {
            Log.e("ScreenCapture", "No WAKE_LOCK permission");
        }
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        super.onTaskRemoved(rootIntent);
        Log.d("ScreenCapture", "@@@@@@onTaskRemoved called");
        // 服务应该继续运行，不要在这里调用 stopSelf()
    }


}