package app.motionforge.cut;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
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
    private static final String PREFS = "motionforge_ai";
    private static final String DEFAULT_ENDPOINT = "http://127.0.0.1:11434";
    private static final String DEFAULT_MODEL = "gemma4:12b";

    private WebView webView;
    private NativeBridge nativeBridge;
    private ValueCallback<Uri[]> fileCallback;
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
                    view.removeJavascriptInterface("MotionForgeNative");
                    view.loadUrl(target);
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
        setContentView(webView);
        webView.loadUrl("file:///android_asset/web/video.html");
    }

    @Override
    @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_PICKER_REQUEST || fileCallback == null) return;
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
        fileCallback.onReceiveValue(results);
        fileCallback = null;
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
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
        aiExecutor.shutdownNow();
        super.onDestroy();
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
                result.put("model", "backend".equals(mode()) ? "MotionForge · 3 professores" : model());
                result.put("endpoint", endpoint());
                return result.toString();
            } catch (JSONException ex) {
                return "{\"mode\":\"ollama\",\"model\":\"gemma4:12b\",\"endpoint\":\"http://127.0.0.1:11434\"}";
            }
        }

        @JavascriptInterface
        public void configureAI() {
            runOnUiThread(MainActivity.this::showAISettings);
        }
    }

    private void showAISettings() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(18);
        layout.setPadding(pad, dp(6), pad, dp(4));

        TextView intro = new TextView(this);
        intro.setText("Conecte a Forge AI a um serviço local. Os modelos não vêm embutidos no APK; eles continuam no Ollama ou no servidor que você configurar.");
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
        backend.setText("Backend MotionForge · três professores");
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
        modes.setOnCheckedChangeListener((group, checkedId) -> {
            String current = endpointInput.getText().toString().trim();
            if (checkedId == 2 && (current.isEmpty() || current.endsWith(":11434"))) {
                endpointInput.setText(current.isEmpty() ? "http://127.0.0.1:8000" : current.replaceFirst(":11434$", ":8000"));
            } else if (checkedId == 1 && current.endsWith(":8000")) {
                endpointInput.setText(current.replaceFirst(":8000$", ":11434"));
            }
        });

        TextView modelLabel = new TextView(this);
        modelLabel.setText("Modelo Ollama (ignorado no modo de três professores)");
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
                        .putString("endpoint", url).putString("model", selectedModel).apply();
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
