package app.motionforge.cut;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int FILE_PICKER_REQUEST = 7412;
    private static final int BROWSER_FILE_PICKER_REQUEST = 7413;
    private static final String PREFS = "motionforge_ai";
    private static final String DEFAULT_ENDPOINT = "http://127.0.0.1:11434";
    private static final String DEFAULT_MODEL = "gemma4:12b";

    private WebView webView;
    private WebView browserView;
    private NativeBridge nativeBridge;
    private ValueCallback<Uri[]> fileCallback;
    private ValueCallback<Uri[]> browserFileCallback;
    private LinearLayout rootLayout;
    private LinearLayout browserToolbar;
    private HorizontalScrollView browserShortcuts;
    private EditText browserAddress;
    private Button editorTab;
    private Button browserTab;
    private boolean browserVisible = false;
    private final ExecutorService aiExecutor = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(9, 12, 18));
        getWindow().setNavigationBarColor(Color.rgb(9, 12, 18));
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(9, 12, 18));
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        nativeBridge = new NativeBridge();
        webView.addJavascriptInterface(nativeBridge, "MotionForgeNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme();
                String target = uri.toString();
                if ("file".equalsIgnoreCase(scheme) && target.startsWith("file:///android_asset/web/")) {
                    view.loadUrl(target);
                    return true;
                }
                if ("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme)) {
                    showBrowser(target, false);
                    return true;
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (url != null && url.startsWith("file:///android_asset/web/")) {
                    view.addJavascriptInterface(nativeBridge, "MotionForgeNative");
                    view.evaluateJavascript("if(window.refreshNativeAIStatus)window.refreshNativeAIStatus();", null);
                } else {
                    view.removeJavascriptInterface("MotionForgeNative");
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{
                        "image/*", "video/*", "audio/*", "application/zip",
                        "application/x-zip-compressed", "application/octet-stream"
                });
                try {
                    startActivityForResult(intent, FILE_PICKER_REQUEST);
                    return true;
                } catch (Exception error) {
                    fileCallback = null;
                    return false;
                }
            }
        });
        createInternalBrowser();
        buildRootLayout();
        webView.loadUrl("file:///android_asset/web/video.html");
    }

    @Override
    @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        boolean editorPicker = requestCode == FILE_PICKER_REQUEST;
        boolean browserPicker = requestCode == BROWSER_FILE_PICKER_REQUEST;
        if (!editorPicker && !browserPicker) return;
        ValueCallback<Uri[]> callback = editorPicker ? fileCallback : browserFileCallback;
        if (callback == null) return;
        Uri[] results = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                results = new Uri[count];
                for (int i = 0; i < count; i++) results[i] = data.getClipData().getItemAt(i).getUri();
            } else if (data.getData() != null) {
                results = new Uri[]{data.getData()};
            }
        }
        callback.onReceiveValue(results);
        if (editorPicker) fileCallback = null;
        else browserFileCallback = null;
    }

    @Override
    public void onBackPressed() {
        if (browserVisible) {
            if (browserView != null && browserView.canGoBack()) browserView.goBack();
            else showEditor();
        } else if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.removeJavascriptInterface("MotionForgeNative");
            webView.destroy();
            webView = null;
        }
        if (browserView != null) {
            browserView.destroy();
            browserView = null;
        }
        aiExecutor.shutdownNow();
        super.onDestroy();
    }

    private void createInternalBrowser() {
        browserView = new WebView(this);
        browserView.setBackgroundColor(Color.rgb(9, 12, 18));
        WebSettings settings = browserView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);
        settings.setSupportMultipleWindows(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(browserView, true);
        browserView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (browserFileCallback != null) browserFileCallback.onReceiveValue(null);
                browserFileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, false);
                try {
                    startActivityForResult(intent, BROWSER_FILE_PICKER_REQUEST);
                    return true;
                } catch (Exception error) {
                    browserFileCallback = null;
                    return false;
                }
            }
        });
        browserView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme();
                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) return false;
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                if (browserAddress != null && url != null) browserAddress.setText(url);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (browserAddress != null && url != null) browserAddress.setText(url);
            }
        });
    }

    private Button makeToolbarButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(12);
        button.setTextColor(Color.WHITE);
        button.setMinHeight(dp(36));
        button.setMinWidth(dp(42));
        button.setPadding(dp(5), 0, dp(5), 0);
        button.setBackgroundColor(Color.rgb(35, 43, 57));
        return button;
    }

    private void buildRootLayout() {
        rootLayout = new LinearLayout(this);
        rootLayout.setOrientation(LinearLayout.VERTICAL);
        rootLayout.setBackgroundColor(Color.rgb(9, 12, 18));

        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setPadding(dp(5), dp(3), dp(5), dp(3));
        tabs.setBackgroundColor(Color.rgb(14, 19, 28));
        editorTab = makeToolbarButton("Editor");
        browserTab = makeToolbarButton("Navegador IA");
        tabs.addView(editorTab, new LinearLayout.LayoutParams(0, dp(42), 1));
        tabs.addView(browserTab, new LinearLayout.LayoutParams(0, dp(42), 1));
        editorTab.setOnClickListener(v -> showEditor());
        browserTab.setOnClickListener(v -> showBrowser(browserView.getUrl() == null ? "https://chatgpt.com/" : browserView.getUrl(), false));
        rootLayout.addView(tabs, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)));

        browserToolbar = new LinearLayout(this);
        browserToolbar.setGravity(Gravity.CENTER_VERTICAL);
        browserToolbar.setPadding(dp(4), dp(3), dp(4), dp(3));
        browserToolbar.setBackgroundColor(Color.rgb(14, 19, 28));
        Button back = makeToolbarButton("‹");
        Button forward = makeToolbarButton("›");
        Button reload = makeToolbarButton("↻");
        Button go = makeToolbarButton("Ir");
        browserAddress = new EditText(this);
        browserAddress.setSingleLine(true);
        browserAddress.setTextSize(12);
        browserAddress.setTextColor(Color.WHITE);
        browserAddress.setHintTextColor(Color.GRAY);
        browserAddress.setHint("https://chatgpt.com");
        browserAddress.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        browserAddress.setImeOptions(EditorInfo.IME_ACTION_GO);
        browserAddress.setPadding(dp(7), 0, dp(7), 0);
        browserAddress.setSelectAllOnFocus(false);
        back.setOnClickListener(v -> { if (browserView.canGoBack()) browserView.goBack(); });
        forward.setOnClickListener(v -> { if (browserView.canGoForward()) browserView.goForward(); });
        reload.setOnClickListener(v -> { if (browserView.getUrl() != null) browserView.reload(); });
        go.setOnClickListener(v -> navigateBrowser());
        browserAddress.setOnEditorActionListener((view, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_GO || actionId == EditorInfo.IME_ACTION_DONE) {
                navigateBrowser();
                return true;
            }
            return false;
        });
        browserToolbar.addView(back, new LinearLayout.LayoutParams(dp(38), dp(40)));
        browserToolbar.addView(forward, new LinearLayout.LayoutParams(dp(38), dp(40)));
        browserToolbar.addView(reload, new LinearLayout.LayoutParams(dp(38), dp(40)));
        browserToolbar.addView(browserAddress, new LinearLayout.LayoutParams(0, dp(40), 1));
        browserToolbar.addView(go, new LinearLayout.LayoutParams(dp(40), dp(40)));
        browserToolbar.setVisibility(View.GONE);
        rootLayout.addView(browserToolbar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));

        HorizontalScrollView shortcutScroll = new HorizontalScrollView(this);
        shortcutScroll.setHorizontalScrollBarEnabled(false);
        shortcutScroll.setFillViewport(false);
        LinearLayout shortcuts = new LinearLayout(this);
        shortcuts.setOrientation(LinearLayout.HORIZONTAL);
        shortcuts.setPadding(dp(4), dp(2), dp(4), dp(2));
        addShortcut(shortcuts, "ChatGPT", "https://chatgpt.com/");
        addShortcut(shortcuts, "Gemini", "https://gemini.google.com/");
        addShortcut(shortcuts, "Claude", "https://claude.ai/");
        addShortcut(shortcuts, "Copilot", "https://copilot.microsoft.com/");
        addShortcut(shortcuts, "HuggingChat", "https://huggingface.co/chat/");
        shortcutScroll.addView(shortcuts);
        browserShortcuts = shortcutScroll;
        browserShortcuts.setVisibility(View.GONE);
        rootLayout.addView(browserShortcuts, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(42)));

        FrameLayout content = new FrameLayout(this);
        content.addView(webView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        FrameLayout.LayoutParams browserParams = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        content.addView(browserView, browserParams);
        browserView.setVisibility(View.GONE);
        rootLayout.addView(content, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(rootLayout);
        updateTabColors();
    }

    private void addShortcut(LinearLayout row, String label, String url) {
        Button button = makeToolbarButton(label);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(36));
        params.setMargins(dp(3), 0, dp(3), 0);
        button.setOnClickListener(v -> showBrowser(url, false));
        row.addView(button, params);
    }

    private void updateTabColors() {
        if (editorTab == null || browserTab == null) return;
        editorTab.setBackgroundColor(browserVisible ? Color.rgb(35, 43, 57) : Color.rgb(22, 115, 180));
        browserTab.setBackgroundColor(browserVisible ? Color.rgb(22, 115, 180) : Color.rgb(35, 43, 57));
    }

    private void showEditor() {
        browserVisible = false;
        if (browserView != null) browserView.setVisibility(View.GONE);
        if (webView != null) {
            webView.setVisibility(View.VISIBLE);
            webView.evaluateJavascript("window.refreshNativeAIStatus&&window.refreshNativeAIStatus()", null);
        }
        if (browserToolbar != null) browserToolbar.setVisibility(View.GONE);
        if (browserShortcuts != null) browserShortcuts.setVisibility(View.GONE);
        updateTabColors();
    }

    private void showBrowser(String url, boolean unused) {
        String target = url == null || url.trim().isEmpty() ? "https://chatgpt.com/" : url.trim();
        if (!target.startsWith("https://") && !target.startsWith("http://")) target = "https://" + target;
        browserVisible = true;
        if (webView != null) webView.setVisibility(View.GONE);
        if (browserView != null) {
            browserView.setVisibility(View.VISIBLE);
            String current = browserView.getUrl();
            if (!target.equals(current)) browserView.loadUrl(target);
        }
        if (browserToolbar != null) browserToolbar.setVisibility(View.VISIBLE);
        if (browserShortcuts != null) browserShortcuts.setVisibility(View.VISIBLE);
        if (browserAddress != null) browserAddress.setText(target);
        updateTabColors();
    }

    private void navigateBrowser() {
        if (browserAddress == null) return;
        String target = browserAddress.getText().toString().trim();
        if (target.isEmpty()) return;
        if (!(target.startsWith("https://") || target.startsWith("http://"))) {
            if (target.contains(" ") || !target.contains(".")) target = "https://www.google.com/search?q=" + Uri.encode(target);
            else target = "https://" + target;
        }
        if (!target.startsWith("https://") && !target.startsWith("http://")) {
            android.widget.Toast.makeText(this, "Use um endereço HTTPS ou HTTP.", android.widget.Toast.LENGTH_SHORT).show();
            return;
        }
        browserAddress.setText(target);
        browserView.loadUrl(target);
        View current = getCurrentFocus();
        if (current != null) {
            InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (imm != null) imm.hideSoftInputFromWindow(current.getWindowToken(), 0);
            current.clearFocus();
        }
    }

    private String mode() {
        return prefs.getString("mode", "ollama");
    }

    private String endpoint() {
        return trimSlash(prefs.getString("endpoint", DEFAULT_ENDPOINT));
    }

    private String model() {
        return prefs.getString("model", DEFAULT_MODEL);
    }

    private String backendKey() {
        return prefs.getString("backend_key", "");
    }

    private static String trimSlash(String value) {
        String result = value == null ? "" : value.trim();
        while (result.endsWith("/")) result = result.substring(0, result.length() - 1);
        return result;
    }

    private static JSONObject readJson(HttpURLConnection connection) throws IOException, JSONException {
        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream();
        String body = readAll(stream);
        JSONObject json = new JSONObject(body);
        if (status < 200 || status >= 300) {
            String message = json.optString("error", body);
            throw new IOException("HTTP " + status + ": " + message);
        }
        return json;
    }

    private static String readAll(InputStream stream) throws IOException {
        if (stream == null) return "";
        try (InputStream in = stream; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
                if (out.size() > 12 * 1024 * 1024) throw new IOException("Resposta da IA excedeu 12 MB.");
            }
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }

    private JSONObject postJson(String urlText, JSONObject request) throws IOException, JSONException {
        HttpURLConnection connection = null;
        try {
            URL url = new URL(urlText);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(12000);
            connection.setReadTimeout(600000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("Accept", "application/json");
            String accessKey = backendKey();
            if ("backend".equals(mode()) && !accessKey.isEmpty()) {
                connection.setRequestProperty("Authorization", "Bearer " + accessKey);
            }
            byte[] bytes = request.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(bytes);
            }
            return readJson(connection);
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private JSONObject callAI(JSONObject input) throws Exception {
        if ("backend".equals(mode())) {
            JSONObject response = postJson(endpoint() + "/api/brainstorm", input);
            response.put("mode", response.optString("mode", "teachers"));
            return response;
        }

        String prompt = input.optString("prompt", "");
        String source = input.optString("source", "");
        String notes = input.optString("reference_notes", "");
        String combined = "Você é a Forge AI dentro do MotionForge Cut. Responda em português com um plano de edição executável, sem alegar operações que não fez.\n\nPEDIDO:\n"
                + prompt + "\n\nCONTEXTO DO PROJETO:\n" + source + "\n\nNOTAS E TRANSCRIÇÕES:\n" + notes
                + "\n\nQuando sugerir montagem, inclua uma seção PLANO JSON com uma lista de clipes que use os nomes e durações informados.";
        JSONObject userMessage = new JSONObject();
        userMessage.put("role", "user");
        userMessage.put("content", combined);
        JSONArray images = input.optJSONArray("reference_images");
        if (images != null && images.length() > 0) {
            JSONArray safeImages = new JSONArray();
            for (int i = 0; i < Math.min(4, images.length()); i++) {
                String image = images.optString(i, "");
                if (image.length() > 250000 || image.isEmpty()) continue;
                safeImages.put(image);
            }
            if (safeImages.length() > 0) userMessage.put("images", safeImages);
        }
        JSONArray messages = new JSONArray();
        JSONObject systemMessage = new JSONObject();
        systemMessage.put("role", "system");
        systemMessage.put("content", "Você é um editor de vídeo e assistente multimodal. Use as imagens recebidas como referência visual, sem inventar fatos sobre o áudio. Responda de forma prática, explique o plano e inclua o bloco PLANO JSON quando for possível.");
        messages.put(systemMessage);
        messages.put(userMessage);
        JSONObject request = new JSONObject();
        request.put("model", model());
        request.put("stream", false);
        request.put("messages", messages);
        JSONObject response = postJson(endpoint() + "/api/chat", request);
        JSONObject message = response.optJSONObject("message");
        String content = message == null ? "" : message.optString("content", "");
        if (content.trim().isEmpty()) throw new IOException("O modelo retornou uma resposta vazia.");
        JSONObject result = new JSONObject();
        result.put("response", content);
        result.put("mode", "ollama");
        result.put("model", model());
        result.put("visual_reference_count", images == null ? 0 : Math.min(4, images.length()));
        result.put("reference_notes_included", !notes.trim().isEmpty());
        return result;
    }

    private void sendResult(String callbackId, JSONObject result, String error) {
        if (webView == null) return;
        String resultJson = result == null ? "{}" : result.toString();
        String script = "window.__nativeAIResult(" + JSONObject.quote(callbackId) + ","
                + JSONObject.quote(resultJson) + ","
                + (error == null ? "null" : JSONObject.quote(error)) + ");";
        webView.evaluateJavascript(script, null);
    }

    private final class NativeBridge {
        @JavascriptInterface
        public void brainstorm(String payload, String callbackId) {
            aiExecutor.execute(() -> {
                JSONObject result = null;
                String error = null;
                try {
                    JSONObject request = new JSONObject(payload);
                    result = callAI(request);
                } catch (Exception ex) {
                    error = ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage();
                    if (error.contains("CLEARTEXT communication")) {
                        error += " Ative HTTP permitido para endpoint local ou use HTTPS.";
                    } else if (error.contains("Failed to connect") || error.contains("Connection refused")) {
                        error += " Configure o endereço do Ollama ou do backend MotionForge em Configurar IA local.";
                    }
                }
                JSONObject finalResult = result;
                String finalError = error;
                runOnUiThread(() -> sendResult(callbackId, finalResult, finalError));
            });
        }

        @JavascriptInterface
        public String aiStatus() {
            try {
                JSONObject result = new JSONObject();
                result.put("mode", mode());
                result.put("model", "backend".equals(mode()) ? "MotionForge backend" : model());
                result.put("endpoint", endpoint());
                return result.toString();
            } catch (JSONException ex) {
                return "{\"mode\":\"ollama\",\"model\":\"gemma4:12b\",\"endpoint\":\"http://127.0.0.1:11434\"}";
            }
        }

        @JavascriptInterface
        public void openAIBrowser(String prompt) {
            String safePrompt = prompt == null ? "" : prompt.trim();
            if (safePrompt.length() > 16000) safePrompt = safePrompt.substring(0, 16000);
            Intent intent = new Intent(MainActivity.this, AIBrowserActivity.class);
            intent.putExtra(AIBrowserActivity.EXTRA_PROMPT, safePrompt);
            runOnUiThread(() -> startActivity(intent));
        }

        @JavascriptInterface
        public void configureAI() {
            runOnUiThread(MainActivity.this::showAISettings);
        }

        @JavascriptInterface
        public void openAIBrowserWithPrompt(String prompt) {
            String safePrompt = prompt == null ? "" : prompt.trim();
            if (safePrompt.length() > 20000) safePrompt = safePrompt.substring(0, 20000);
            String finalPrompt = safePrompt;
            runOnUiThread(() -> {
                if (!finalPrompt.isEmpty()) {
                    ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                    if (clipboard != null) clipboard.setPrimaryClip(ClipData.newPlainText("MotionForge AI prompt", finalPrompt));
                }
                showBrowser("https://chatgpt.com/", false);
                if (!finalPrompt.isEmpty()) {
                    android.widget.Toast.makeText(MainActivity.this, "Pedido copiado. Cole no chat da IA. Para trazer a resposta, copie-a e toque em Importar resposta no Editor.", android.widget.Toast.LENGTH_LONG).show();
                }
            });
        }

        @JavascriptInterface
        public String readClipboardText() {
            try {
                ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                if (clipboard == null || !clipboard.hasPrimaryClip()) return "";
                ClipData clip = clipboard.getPrimaryClip();
                if (clip == null || clip.getItemCount() == 0) return "";
                CharSequence text = clip.getItemAt(0).coerceToText(MainActivity.this);
                String value = text == null ? "" : text.toString();
                return value.length() > 50000 ? value.substring(0, 50000) : value;
            } catch (Exception ex) {
                return "";
            }
        }
    }

    private void showAISettings() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(18);
        layout.setPadding(pad, dp(6), pad, dp(4));

        TextView intro = new TextView(this);
        intro.setText("Conecte a Forge AI a um Ollama local ou a um backend MotionForge remoto. No modo remoto, o backend pode encaminhar pedidos ao GitHub Models; as credenciais ficam no servidor, não no APK.");
        intro.setTextSize(13);
        intro.setTextColor(Color.LTGRAY);
        intro.setPadding(0, 0, 0, dp(12));
        layout.addView(intro);

        RadioGroup modes = new RadioGroup(this);
        modes.setOrientation(RadioGroup.VERTICAL);
        RadioButton ollama = new RadioButton(this);
        ollama.setText("Ollama direto · um modelo multimodal");
        ollama.setTextColor(Color.WHITE);
        ollama.setId(1);
        RadioButton backend = new RadioButton(this);
        backend.setText("Backend MotionForge · local/remoto");
        backend.setTextColor(Color.WHITE);
        backend.setId(2);
        modes.addView(ollama);
        modes.addView(backend);
        modes.check("backend".equals(mode()) ? 2 : 1);
        layout.addView(modes);

        TextView endpointLabel = new TextView(this);
        endpointLabel.setText("Endereço base do serviço (sem /api)");
        endpointLabel.setTextColor(Color.WHITE);
        endpointLabel.setPadding(0, dp(10), 0, dp(5));
        layout.addView(endpointLabel);
        EditText endpointInput = new EditText(this);
        endpointInput.setSingleLine(true);
        endpointInput.setText(endpoint());
        endpointInput.setHint("http://127.0.0.1:11434");
        endpointInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        layout.addView(endpointInput);

        TextView keyLabel = new TextView(this);
        keyLabel.setText("Chave de acesso do backend remoto (opcional no servidor local)");
        keyLabel.setTextColor(Color.WHITE);
        keyLabel.setPadding(0, dp(10), 0, dp(5));
        layout.addView(keyLabel);
        EditText backendKeyInput = new EditText(this);
        backendKeyInput.setSingleLine(true);
        backendKeyInput.setText(backendKey());
        backendKeyInput.setHint("Chave definida no servidor remoto");
        backendKeyInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        layout.addView(backendKeyInput);

        modes.setOnCheckedChangeListener((group, checkedId) -> {
            String current = endpointInput.getText().toString().trim();
            if (checkedId == 2 && (current.isEmpty() || current.endsWith(":11434"))) {
                endpointInput.setText(current.isEmpty() ? "http://127.0.0.1:8000" : current.replaceFirst(":11434$", ":8000"));
            } else if (checkedId == 1 && current.endsWith(":8000")) {
                endpointInput.setText(current.replaceFirst(":8000$", ":11434"));
            }
        });

        TextView modelLabel = new TextView(this);
        modelLabel.setText("Modelo Ollama (usado somente no modo Ollama direto)");
        modelLabel.setTextColor(Color.WHITE);
        modelLabel.setPadding(0, dp(10), 0, dp(5));
        layout.addView(modelLabel);
        EditText modelInput = new EditText(this);
        modelInput.setSingleLine(true);
        modelInput.setText(model());
        modelInput.setHint("gemma4:12b");
        modelInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT);
        layout.addView(modelInput);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(layout);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Forge AI · conexão local")
                .setView(scroll)
                .setNegativeButton("Cancelar", null)
                .setNeutralButton("Testar conexão", null)
                .setPositiveButton("Salvar", null)
                .create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                String url = trimSlash(endpointInput.getText().toString());
                String selectedModel = modelInput.getText().toString().trim();
                if (!(url.startsWith("http://") || url.startsWith("https://")) || url.length() > 300) {
                    endpointInput.setError("Use um endereço HTTP ou HTTPS válido.");
                    return;
                }
                if (selectedModel.isEmpty()) {
                    modelInput.setError("Informe o nome do modelo.");
                    return;
                }
                prefs.edit().putString("mode", modes.getCheckedRadioButtonId() == 2 ? "backend" : "ollama")
                        .putString("endpoint", url).putString("model", selectedModel)
                        .putString("backend_key", backendKeyInput.getText().toString().trim()).apply();
                if (webView != null) webView.evaluateJavascript("window.refreshNativeAIStatus&&window.refreshNativeAIStatus()", null);
                dialog.dismiss();
            });
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                String url = trimSlash(endpointInput.getText().toString());
                boolean isBackend = modes.getCheckedRadioButtonId() == 2;
                aiExecutor.execute(() -> {
                    String status;
                    try {
                        HttpURLConnection c = (HttpURLConnection) new URL(url + (isBackend ? "/api/status" : "/api/tags")).openConnection();
                        c.setConnectTimeout(5000);
                        c.setReadTimeout(5000);
                        String accessKey = backendKeyInput.getText().toString().trim();
                        if (isBackend && !accessKey.isEmpty()) c.setRequestProperty("Authorization", "Bearer " + accessKey);
                        int code = c.getResponseCode();
                        String body = readAll(code >= 200 && code < 300 ? c.getInputStream() : c.getErrorStream());
                        if (code < 200 || code >= 300) throw new IOException("HTTP " + code);
                        status = "Conexão OK. Serviço respondeu a " + (isBackend ? "/api/status" : "/api/tags") + ".";
                        c.disconnect();
                    } catch (Exception ex) {
                        status = "Não conectou: " + (ex.getMessage() == null ? "erro desconhecido" : ex.getMessage());
                    }
                    String finalStatus = status;
                    runOnUiThread(() -> new AlertDialog.Builder(MainActivity.this)
                            .setTitle("Teste da conexão")
                            .setMessage(finalStatus)
                            .setPositiveButton("OK", null)
                            .show());
                });
            });
        });
        dialog.show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
