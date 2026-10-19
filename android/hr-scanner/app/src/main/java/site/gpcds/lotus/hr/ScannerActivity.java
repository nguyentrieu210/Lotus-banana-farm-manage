package site.gpcds.lotus.hr;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.util.Size;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.activity.ComponentActivity;
import androidx.annotation.NonNull;
import androidx.camera.core.Camera;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.LifecycleOwner;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.mlkit.vision.barcode.BarcodeScanner;
import com.google.mlkit.vision.barcode.BarcodeScannerOptions;
import com.google.mlkit.vision.barcode.BarcodeScanning;
import com.google.mlkit.vision.barcode.ZoomSuggestionOptions;
import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.common.InputImage;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

public class ScannerActivity extends ComponentActivity {
    public static final String EXTRA_QR = "qr";
    private static final int REQUEST_CAMERA = 22;
    private PreviewView previewView;
    private Camera camera;
    private BarcodeScanner mlScanner;
    private ProcessCameraProvider provider;
    private final AtomicBoolean busy = new AtomicBoolean(false);
    private final AtomicBoolean completed = new AtomicBoolean(false);
    private ExecutorService imageExecutor;
    private TextView message;
    private Button torchButton;
    private Button zoomButton;
    private boolean torchEnabled;
    private float zoomRatio=1.0f;

    private int dp(float d) { return (int)(getResources().getDisplayMetrics().density*d+0.5f); }
    private TextView text(String value,int sp,int color) {
        TextView view=new TextView(this);view.setText(value);view.setTextColor(color);
        view.setTextSize(sp);view.setGravity(Gravity.CENTER);return view;
    }

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        imageExecutor=Executors.newSingleThreadExecutor();
        FrameLayout root=new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        previewView=new PreviewView(this);
        previewView.setImplementationMode(PreviewView.ImplementationMode.COMPATIBLE);
        previewView.setScaleType(PreviewView.ScaleType.FILL_CENTER);
        root.addView(previewView,new FrameLayout.LayoutParams(-1,-1));

        // Overlay does not crop analyzer image. ML Kit always sees the FULL camera frame.
        View reticle=new View(this);
        reticle.setBackgroundColor(Color.TRANSPARENT);
        android.graphics.drawable.GradientDrawable border=new android.graphics.drawable.GradientDrawable();
        border.setColor(0x16000000);border.setStroke(dp(3),Color.WHITE);border.setCornerRadius(dp(16));
        reticle.setBackground(border);
        FrameLayout.LayoutParams rp=new FrameLayout.LayoutParams(dp(272),dp(272),Gravity.CENTER);
        root.addView(reticle,rp);

        LinearLayout top=new LinearLayout(this);
        top.setOrientation(LinearLayout.VERTICAL);
        top.setBackgroundColor(0x85000000);
        Button close=new Button(this);close.setText("‹  Đóng");close.setAllCaps(false);
        close.setOnClickListener(v->finish());
        top.addView(close,new LinearLayout.LayoutParams(dp(110),dp(50)));
        TextView title=text("Quét QR trên căn cước",20,Color.WHITE);
        title.setTypeface(null,Typeface.BOLD);
        top.addView(title,new LinearLayout.LayoutParams(-1,dp(48)));
        FrameLayout.LayoutParams tp=new FrameLayout.LayoutParams(-1,dp(116),Gravity.TOP);
        root.addView(top,tp);

        LinearLayout bottom=new LinearLayout(this);
        bottom.setOrientation(LinearLayout.VERTICAL);
        bottom.setPadding(dp(16),dp(14),dp(16),dp(24));
        bottom.setBackgroundColor(0xA9000000);
        message=text("Đưa mã QR vào giữa hình. Camera tự lấy nét.",15,Color.WHITE);
        bottom.addView(message,new LinearLayout.LayoutParams(-1,dp(54)));
        LinearLayout actions=new LinearLayout(this);
        actions.setGravity(Gravity.CENTER);
        torchButton=new Button(this);torchButton.setText("Bật đèn");torchButton.setAllCaps(false);
        torchButton.setOnClickListener(v->toggleTorch());
        actions.addView(torchButton,new LinearLayout.LayoutParams(dp(136),dp(52)));
        zoomButton=new Button(this);zoomButton.setText("Phóng to 2×");zoomButton.setAllCaps(false);
        zoomButton.setOnClickListener(v->toggleZoom());
        actions.addView(zoomButton,new LinearLayout.LayoutParams(dp(136),dp(52)));
        bottom.addView(actions,new LinearLayout.LayoutParams(-1,dp(58)));
        FrameLayout.LayoutParams bp=new FrameLayout.LayoutParams(-1,dp(162),Gravity.BOTTOM);
        root.addView(bottom,bp);
        setContentView(root);
        if(ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)
            ==PackageManager.PERMISSION_GRANTED) startCamera();
        else requestPermissions(new String[]{Manifest.permission.CAMERA},REQUEST_CAMERA);
    }

    @Override public void onRequestPermissionsResult(int requestCode,@NonNull String[] perms,@NonNull int[] results) {
        super.onRequestPermissionsResult(requestCode,perms,results);
        if(requestCode==REQUEST_CAMERA) {
            if(results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED) startCamera();
            else {message.setText("Cần cho phép camera để quét QR.");}
        }
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> future=ProcessCameraProvider.getInstance(this);
        future.addListener(()-> {
            try {
                if(isFinishing()||isDestroyed())return;
                provider=future.get();
                Preview preview=new Preview.Builder().build();
                preview.setSurfaceProvider(previewView.getSurfaceProvider());
                ImageAnalysis analysis=new ImageAnalysis.Builder()
                    .setTargetResolution(new Size(1280,720))
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build();
                provider.unbindAll();
                camera=provider.bindToLifecycle(this,CameraSelector.DEFAULT_BACK_CAMERA,preview,analysis);
                float maxZoom=3.0f;
                if(camera.getCameraInfo().getZoomState().getValue()!=null)
                    maxZoom=Math.min(5f,camera.getCameraInfo().getZoomState().getValue().getMaxZoomRatio());
                ZoomSuggestionOptions autoZoom=new ZoomSuggestionOptions.Builder(ratio-> {
                    if(camera==null || completed.get())return false;
                    camera.getCameraControl().setZoomRatio(ratio);
                    zoomRatio=ratio;
                    return true;
                }).setMaxSupportedZoomRatio(maxZoom).build();
                mlScanner=BarcodeScanning.getClient(new BarcodeScannerOptions.Builder()
                    .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                    .enableAllPotentialBarcodes()
                    .setZoomSuggestionOptions(autoZoom)
                    .build());
                analysis.setAnalyzer(imageExecutor,this::inspectFrame);
            } catch(Exception e) {
                message.setText("Không mở được camera Android. Hãy thử lại.");
            }
        },ContextCompat.getMainExecutor(this));
    }

    @androidx.camera.core.ExperimentalGetImage
    private void inspectFrame(@NonNull ImageProxy proxy) {
        if(mlScanner==null || completed.get() || !busy.compareAndSet(false,true)) {proxy.close();return;}
        android.media.Image media=proxy.getImage();
        if(media==null){busy.set(false);proxy.close();return;}
        InputImage input=InputImage.fromMediaImage(media,proxy.getImageInfo().getRotationDegrees());
        mlScanner.process(input).addOnSuccessListener(codes->{
            for(Barcode code:codes) {
                String raw=code.getRawValue();
                if(raw!=null && raw.length()<4096 && raw.matches("^\\d{12}\\|.*")
                    && completed.compareAndSet(false,true)) {
                    Intent data=new Intent();data.putExtra(EXTRA_QR,raw);
                    setResult(Activity.RESULT_OK,data);finish();break;
                }
            }
        }).addOnFailureListener(error-> {
            // Do not log QR or personal data.
        }).addOnCompleteListener(task->{proxy.close();busy.set(false);});
    }

    private void toggleTorch(){
        if(camera==null || !camera.getCameraInfo().hasFlashUnit()) {
            message.setText("Camera không có đèn flash.");return;
        }
        torchEnabled=!torchEnabled;
        camera.getCameraControl().enableTorch(torchEnabled);
        torchButton.setText(torchEnabled?"Tắt đèn":"Bật đèn");
    }
    private void toggleZoom(){
        if(camera==null)return;
        zoomRatio=zoomRatio>1.2f?1f:2f;
        camera.getCameraControl().setZoomRatio(zoomRatio);
        zoomButton.setText(zoomRatio>1.2f?"Thu nhỏ 1×":"Phóng to 2×");
    }
    @Override protected void onDestroy(){
        if(provider!=null)provider.unbindAll();
        if(mlScanner!=null)mlScanner.close();
        if(imageExecutor!=null)imageExecutor.shutdown();
        super.onDestroy();
    }
}
