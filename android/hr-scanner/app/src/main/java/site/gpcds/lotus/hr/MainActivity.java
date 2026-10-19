package site.gpcds.lotus.hr;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import androidx.activity.ComponentActivity;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.util.Collections;
import org.json.JSONObject;

/**
 * Trusted, same-origin HR shell. Raw identity data is returned only to the
 * loaded Lotus HR form, never persisted in Android storage or placed in a URL.
 */
public class MainActivity extends ComponentActivity {
    private static final String ORIGIN = "https://lotus.gpcds.site";
    private static final String START_URL = ORIGIN + "/hr-mobile";
    private WebView webView;
    private boolean nativeBridgeEnabled;
    private ActivityResultLauncher<Intent> scannerLauncher;

    private boolean trustedUrl(String url) {
        try {
            Uri uri = Uri.parse(url);
            return "https".equals(uri.getScheme()) && "lotus.gpcds.site".equals(uri.getHost())
                && (uri.getPort() == -1 || uri.getPort() == 443);
        } catch (Exception ignored) { return false; }
    }

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        scannerLauncher = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(), result -> {
                if (webView == null || !trustedUrl(webView.getUrl())) return;
                if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null) {
                    webView.evaluateJavascript(
                        "window.dispatchEvent(new CustomEvent('lotus:cccd-native-cancel'))", null);
                    return;
                }
                String raw = result.getData().getStringExtra(ScannerActivity.EXTRA_QR);
                if (raw == null || raw.length() > 4096) return;
                // JSON encoding prevents an untrusted QR payload from executing script.
                String js = "window.dispatchEvent(new CustomEvent('lotus:cccd-native-result',{detail:{raw:"
                    + JSONObject.quote(raw) + "}}))";
                webView.evaluateJavascript(js, null);
            }
        );
        webView = new WebView(this);
        webView.setBackgroundColor(Color.WHITE);
        setContentView(webView, new FrameLayout.LayoutParams(-1,-1));
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        webView.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView,false);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                if (trustedUrl(url)) return false;
                // All other links go to Android browser, without native bridge access.
                if ("https".equals(request.getUrl().getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW,request.getUrl())); }
                    catch (Exception ignored) {}
                }
                return true;
            }
        });
        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            WebViewCompat.addWebMessageListener(webView,"LotusCccdNative",
                Collections.singleton(ORIGIN),(view,message,sourceOrigin,isMainFrame,replyProxy)-> {
                    if (!isMainFrame || !ORIGIN.equals(sourceOrigin.toString())
                        || !trustedUrl(view.getUrl()) || !"scan".equals(message.getData())) return;
                    runOnUiThread(()-> scannerLauncher.launch(new Intent(this,ScannerActivity.class)));
                });
            nativeBridgeEnabled = true;
        } else {
            Toast.makeText(this,"Cập nhật Android System WebView để dùng quét nhanh",Toast.LENGTH_LONG).show();
        }
        webView.loadUrl(START_URL);
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
    @Override public void onDestroy() {
        if (webView != null) { webView.destroy(); webView=null; }
        super.onDestroy();
    }
}
