package cn.vove7.andro_accessibility_api.demo.service;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ComponentName;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Binder;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.PowerManager;
import android.provider.MediaStore;
import android.util.Base64;
import android.util.DisplayMetrics;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.lang.ref.WeakReference;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;

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

    private final ExecutorService executorService = Executors.newSingleThreadExecutor();

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
                .setSmallIcon(R.drawable.zhangyu)
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
            Begin(MainActivity.getInstance());
            //Log.e("ScreenCapture", "MediaProjection not initialized");
            return null;
        }

        WeakReference<ToolBarService> toolBarServiceRef = ToolBarService.getInstance();
        ToolBarService toolBarService = toolBarServiceRef != null ? toolBarServiceRef.get() : null;

        try {
            Image image = null;
            if (toolBarService != null) {
                toolBarService.hideCursor();
                // 等待UI更新完成
                Thread.sleep(100);
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
                    image = imageReader.acquireLatestImage();
                    if (image != null) {
                        break;
                    }
                    attempt++;
                } catch (Exception e) {
                    attempt++;
                }
            }

            if (image == null) {
                Log.e("ScreenCapture", "Failed to acquire image after " + maxAttempts + " attempts");
            }

            if (toolBarService != null) {
                // 在主线程中恢复光标显示
                toolBarService.showCursor();
            }

            return image;
        } catch (Exception e) {
            Log.e("ScreenCapture", "Screenshot failed", e);
            if (toolBarService != null) {
                // 确保在发生异常时也能恢复光标显示
                toolBarService.showCursor();
            }
            return null;
        }
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

    public Bitmap getBitmapFromImage(Image image) {
        Image.Plane[] planes = image.getPlanes();
        ByteBuffer buffer = planes[0].getBuffer();
        int pixelStride = planes[0].getPixelStride();
        int rowStride = planes[0].getRowStride();
        int rowPadding = rowStride - pixelStride * image.getWidth();

        Bitmap bitmap = Bitmap.createBitmap(
            image.getWidth() + rowPadding / pixelStride,
            image.getHeight(),
            Bitmap.Config.ARGB_8888
        );
        bitmap.copyPixelsFromBuffer(buffer);
        return bitmap;
    }

    public String captureScreen() {
        Image image = takeScreenshot();
        if (image != null) {
            try {
                Bitmap bitmap = getBitmapFromImage(image);

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

    public static class TextBlockInfo {
        public final String text;
        public final Rect bounds;

        public TextBlockInfo(String text, Rect bounds) {
            this.text = text;
            this.bounds = bounds;
        }
    }


    private Bitmap convertImageToBitmap(Bitmap bitmap) {
        // 灰度化处理
        Bitmap grayBitmap = Bitmap.createBitmap(bitmap.getWidth(), bitmap.getHeight(), Bitmap.Config.ARGB_8888);
        for (int y = 0; y < bitmap.getHeight(); y++) {
            for (int x = 0; x < bitmap.getWidth(); x++) {
                int pixel = bitmap.getPixel(x, y);
                int gray = (Color.red(pixel) + Color.green(pixel) + Color.blue(pixel)) / 3;
                grayBitmap.setPixel(x, y, Color.rgb(gray, gray, gray));
            }
        }
        return grayBitmap;
    }

   
    public void recognizeText(Consumer<Object> callback, boolean withPos) {
        Image image = takeScreenshot();
        if (image != null) {
            try {
                Bitmap bitmap = getBitmapFromImage(image);
                InputImage inputImage = InputImage.fromBitmap(bitmap, 0);
                TextRecognizer recognizer = TextRecognition.getClient(new ChineseTextRecognizerOptions.Builder().build());

                // 使用自定义线程执行回调
                Executor customExecutor = Executors.newSingleThreadExecutor();

                recognizer.process(inputImage)
                    .addOnCompleteListener(customExecutor, task -> {
                        try {
                            if (task.isSuccessful()) {
                                Text text = task.getResult();
                                if (withPos) {
                                    List<TextBlockInfo> textBlockInfos = new ArrayList<>();
                                    for (Text.TextBlock block : text.getTextBlocks()) {
                                        String recognizedText = block.getText();
                                        Rect boundingBox = block.getBoundingBox();
                                        if (boundingBox != null) {
                                            textBlockInfos.add(new TextBlockInfo(recognizedText, boundingBox));
                                        }
                                    }
                                    callback.accept(textBlockInfos);
                                } else {
                                    StringBuilder recognizedText = new StringBuilder();
                                    for (Text.TextBlock block : text.getTextBlocks()) {
                                        recognizedText.append(block.getText()).append("\n");
                                    }
                                    callback.accept(recognizedText.toString().trim());
                                }
                            } else {
                                Log.e("ScreenCapture", "Error recognizing text with ML Kit: " + task.getException().getMessage());
                                callback.accept(withPos ? Collections.emptyList() : "");
                            }
                        } finally {
                            image.close();
                            Log.d("ScreenCapture", "Image closed after completion");
                        }
                    });
            } catch (Exception e) {
                Log.e("ScreenCapture", "Error processing image: " + e.getMessage(), e);
                image.close();
                callback.accept(withPos ? Collections.emptyList() : "");
            }
        } else {
            Log.e("ScreenCapture", "Failed to take screenshot: image is null");
            callback.accept(withPos ? Collections.emptyList() : "");
        }
    }

}