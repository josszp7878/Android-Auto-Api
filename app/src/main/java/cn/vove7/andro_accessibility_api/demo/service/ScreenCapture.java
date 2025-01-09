package cn.vove7.andro_accessibility_api.demo.service;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.ServiceInfo;
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

import java.nio.ByteBuffer;
import java.io.IOException;
import java.io.OutputStream;
import android.content.ContentValues;
import android.net.Uri;
import android.provider.MediaStore;
import android.os.Environment;
import android.content.ContentResolver;

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

import android.util.Base64;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import androidx.core.app.NotificationCompat;

import cn.vove7.andro_accessibility_api.demo.MainActivity;
import cn.vove7.andro_accessibility_api.demo.R;

/** @noinspection ALL*/
public class ScreenCapture extends Service {

    private static ScreenCapture screenCapture;
    public static ScreenCapture getInstance() {
        return screenCapture;
    }

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
            isInitialized = true;
            Log.d("ScreenCapture", "Service initialized");
        }
    }

    public static ServiceConnection Begin(Activity activity) {
        Log.d("ScreenCapture", "Attempting to start and bind service");

        // 启动服务
        Intent serviceIntent = new Intent(activity, ScreenCapture.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            activity.startForegroundService(serviceIntent);
        } else {
            activity.startService(serviceIntent);
        }

        // 创建 ServiceConnection
        ServiceConnection serviceConnection = new ServiceConnection() {
            @Override
            public void onServiceConnected(ComponentName name, IBinder service) {
                LocalBinder binder = (LocalBinder) service;
                screenCapture = binder.getService();
                screenCapture.initialize();
                screenCapture.isBound = true;
                screenCapture.requestPermission(activity);
                Log.d("ScreenCapture", "Service connected");
            }

            @Override
            public void onServiceDisconnected(ComponentName name) {
                Log.d("ScreenCapture", "Service disconnected");
                screenCapture.isBound = false;
                screenCapture = null;
            }
        };

        // 绑定服务
        boolean bound = activity.bindService(serviceIntent, serviceConnection, Context.BIND_AUTO_CREATE);
        Log.d("ScreenCapture", "Service started and bound: " + bound);
        return serviceConnection;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d("ScreenCapture", "Service onStartCommand called with action: " + 
            (intent != null ? intent.getAction() : "null"));
        startForegroundService();
        return START_STICKY;
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

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, builder.build(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        } else {
            startForeground(NOTIFICATION_ID, builder.build());
        }
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
    public void requestPermission(Activity activity) {
        if (hasScreenCapturePermission()) return;
        Intent intent = mediaProjectionManager.createScreenCaptureIntent();
        activity.startActivityForResult(intent, REQUEST_CODE_SCREEN_CAPTURE);
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
            
            // 添加短暂延迟让 VirtualDisplay 初始化
            try {
                Thread.sleep(50);
            } catch (InterruptedException e) {
                Log.e("ScreenCapture", "Sleep interrupted", e);
            }
            
            Log.d("ScreenCapture", "Created new virtual display");
        }
    }

    public Image takeScreenshot() {
        Log.d("ScreenCapture", "takeScreenshot called");
        if (mediaProjection == null) {
            Log.e("ScreenCapture", "MediaProjection not initialized");
            return null;
        }

        // 获取屏幕尺寸
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        int screenWidth = metrics.widthPixels;
        int screenHeight = metrics.heightPixels;

        ensureVirtualDisplay(screenWidth, screenHeight);

        // 添加重试机制
        int maxAttempts = 3;
        int attempt = 0;
        while (attempt < maxAttempts) {
            try {
                // 等待一小段时间让 VirtualDisplay 准备就绪
                Thread.sleep(100);
                
                Image image = imageReader.acquireLatestImage();
                if (image != null) {
                    Log.d("ScreenCapture", "Successfully acquired image on attempt " + (attempt + 1));
                    return image;
                }
                Log.w("ScreenCapture", "Failed to acquire image on attempt " + (attempt + 1));
                attempt++;
            } catch (Exception e) {
                Log.e("ScreenCapture", "Error taking screenshot on attempt " + (attempt + 1), e);
                attempt++;
            }
        }
        
        Log.e("ScreenCapture", "Failed to acquire image after " + maxAttempts + " attempts");
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


    private void recognizeText(Image image, OcrCallback callback) {
        TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
        
        // 获取屏幕尺寸
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        float screenWidth = metrics.widthPixels;
        float screenHeight = metrics.heightPixels;

        try {
            // 将 Image 转换为 Bitmap
            Image.Plane[] planes = image.getPlanes();
            ByteBuffer buffer = planes[0].getBuffer();
            int pixelStride = planes[0].getPixelStride();
            int rowStride = planes[0].getRowStride();
            int rowPadding = rowStride - pixelStride * (int)screenWidth;

            // 创建 Bitmap
            Bitmap bitmap = Bitmap.createBitmap((int)screenWidth + rowPadding / pixelStride, 
                                              (int)screenHeight, 
                                              Bitmap.Config.ARGB_8888);
            bitmap.copyPixelsFromBuffer(buffer);

            // 使用 Bitmap 创建 InputImage
            InputImage inputImage = InputImage.fromBitmap(bitmap, 0);

            recognizer.process(inputImage)
                    .addOnSuccessListener(text -> {
                        List<TextInfo> textInfos = new ArrayList<>();
                        
                        for (Text.TextBlock block : text.getTextBlocks()) {
                            for (Text.Line line : block.getLines()) {
                                for (Text.Element element : line.getElements()) {
                                    Rect imageBounds = element.getBoundingBox();
                                    if (imageBounds != null) {
                                        // 计算屏幕坐标
                                        Point screenPos = new Point(
                                            imageBounds.left,
                                            imageBounds.top
                                        );

                                        // 计算归一化坐标 (0-1)
                                        PointF normalizedPos = new PointF(
                                            screenPos.x / screenWidth,
                                            screenPos.y / screenHeight
                                        );

                                        // 计算屏幕空间中的边界
                                        Rect screenBounds = new Rect(
                                            imageBounds.left,
                                            imageBounds.top,
                                            imageBounds.right,
                                            imageBounds.bottom
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

                        bitmap.recycle();  // 释放 Bitmap
                        new Handler(Looper.getMainLooper()).post(() -> 
                            callback.onTextRecognized(textInfos));
                    })
                    .addOnFailureListener(e -> {
                        bitmap.recycle();  // 释放 Bitmap
                        Log.e("ScreenCapture", "Error recognizing text: " + e.getMessage());
                        new Handler(Looper.getMainLooper()).post(() -> 
                            callback.onTextRecognized(Collections.emptyList()));
                    });
        } catch (Exception e) {
            Log.e("ScreenCapture", "Error processing image for OCR: " + e.getMessage());
            new Handler(Looper.getMainLooper()).post(() -> 
                callback.onTextRecognized(Collections.emptyList()));
        }
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

    public String captureScreen() {
        Image image = takeScreenshot();
        if (image != null) {
            try {
                // 从 Image 获取数据
                Image.Plane[] planes = image.getPlanes();
                ByteBuffer buffer = planes[0].getBuffer();
                int pixelStride = planes[0].getPixelStride();
                int rowStride = planes[0].getRowStride();
                int rowPadding = rowStride - pixelStride * image.getWidth();

                // 创建 Bitmap
                Bitmap bitmap = Bitmap.createBitmap(
                    image.getWidth() + rowPadding / pixelStride,
                    image.getHeight(),
                    Bitmap.Config.ARGB_8888
                );
                bitmap.copyPixelsFromBuffer(buffer);

                // 压缩为JPEG
                ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
                bitmap.compress(Bitmap.CompressFormat.JPEG, 100, outputStream);
                byte[] imageBytes = outputStream.toByteArray();
                
                // 转换为base64
                String base64Image = Base64.encodeToString(imageBytes, Base64.NO_WRAP);
                
                // 添加data URI前缀
                return "data:image/jpeg;base64," + base64Image;
                
            } catch (Exception e) {
                Log.e("ScreenCapture", "Error processing image: " + e.getMessage(), e);
            } finally {
                image.close();
                Log.d("ScreenCapture", "Image closed");
            }
        } else {
            Log.e("ScreenCapture", "Failed to take screenshot: image is null");
        }
        return null;
    }

    public void captureScreenText(OcrCallback cb) {
        Image image = takeScreenshot();
        if (image != null) {
            try {
                recognizeText(image, cb);
            } finally {
                image.close();
            }
        } else {
            cb.onTextRecognized(Collections.emptyList());
        }
    }

}