package app.motionforge.cut;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class AIBrowserActivity extends Activity {
    public static final String EXTRA_PROMPT = "motionforge.browser.prompt";
    private static final int FILE_PICKER_REQUEST = 9152;
    private static final int BG = Color.rgb(9, 12, 18);
    private static final int PANEL = Color.rgb(19, 25, 36);
    private static final int TEXT = Color.rgb(235, 241, 250);
    private static final int MUTED = Color.rgb(151, 165, 185);

    private WebView webView;
    private EditText addressInput;
    private EditText promptInput;
    private TextView pageStatus;
    private View promptPanel;
    private ValueCallback<Uri[]> fileCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        root.setPadding(dp(8), dp(6), dp(8), dp(4));

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        Button back = button("‹ Editor", true);
        back.setOnClickListener(v -> finish());
        header.addView(back, new LinearLayout.LayoutParams(dp(94), dp(44)));
        TextView title = new TextView(this);
        title.setText("Navegador de IAs");
        title.setTextColor(TEXT);
        title.setTextSize(18);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        title.setPadding(dp(10), 0, 0, 0);
        header.addView(title, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        root.addView(header);

        HorizontalScrollView providersScroller = new HorizontalScrollView(this);
        providersScroller.setHorizontalScrollBarEnabled(false);
        LinearLayout providers = new LinearLayout(this);
        providers.setOrientation(LinearLayout.HORIZONTAL);
        addProvider(providers, "ChatGPT", "https://chatgpt.com/");
        addProvider(providers, "Gemini", "https://gemini.google.com/");
        addProvider(providers, "Claude", "https://claude.ai/");
        addProvider(providers, "Copilot", "https://copilot.microsoft.com/");
        addProvider(providers, "Perplexity", "https://www.perplexity.ai/");
        providersScroller.addView(providers);
        root.addView(providersScroller, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(48)));

        LinearLayout addressRow = new LinearLayout(this);
        addressRow.setOrientation(LinearLayout.HORIZONTAL);
        addressInput = new EditText(this);
        addressInput.setSingleLine(true);
        addressInput.setTextSize(14);
        addressInput.setTextColor(TEXT);
        addressInput.setHintTextColor(MUTED);
        addressInput.setHint("https://…");
        addressInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        addressInput.setPadding(dp(10), 0, dp(10), 0);
        addressInput.setBackgroundColor(PANEL);
        addressRow.addView(addressInput, new LinearLayout.LayoutParams(0, dp(44), 1));
        Button go = button("Abrir", false);
        go.setOnClickListener(v -> loadAddress(addressInput.getText().toString()));
        addressRow.addView(go, new LinearLayout.LayoutParams(dp(75), dp(44)));
        root.addView(addressRow);

        LinearLayout tools = new LinearLayout(this);
        tools.setOrientation(LinearLayout.HORIZONTAL);
        Button promptToggle = button("Pedido do editor ▾", true);
        promptToggle.setOnClickListener(v -> {
            boolean show = promptPanel.getVisibility() != View.VISIBLE;
            promptPanel.setVisibility(show ? View.VISIBLE : View.GONE);
            promptToggle.setText(show ? "Ocultar pedido ▴" : "Pedido do editor ▾");
        });
        tools.addView(promptToggle, new LinearLayout.LayoutParams(0, dp(42), 1));
        Button external = button("Abrir no Chrome", true);
        external.setOnClickListener(v -> openExternal(addressInput.getText().toString()));
        tools.addView(external, new LinearLayout.LayoutParams(0, dp(42), 1));
        root.addView(tools);

        LinearLayout promptCard = new LinearLayout(this);
        promptCard.setOrientation(LinearLayout.VERTICAL);
        promptCard.setBackgroundColor(PANEL);
        promptCard.setPadding(dp(8), dp(6), dp(8), dp(6));
        promptInput = new EditText(this);
        promptInput.setTextColor(TEXT);
        promptInput.setHintTextColor(MUTED);
        promptInput.setTextSize(13);
        promptInput.setGravity(Gravity.TOP | Gravity.START);
        promptInput.setMinLines(3);
        promptInput.setMaxLines(6);
        promptInput.setHint("O pedido criado no editor aparecerá aqui.");
        promptInput.setText(getIntent().getStringExtra(EXTRA_PROMPT) == null
                ? "" : getIntent().getStringExtra(EXTRA_PROMPT));
        promptCard.addView(promptInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(110)));
        Button copyPrompt = button("Copiar pedido", false);
        copyPrompt.setOnClickListener(v -> copyPrompt());
        promptCard.addView(copyPrompt, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(40)));
        promptPanel = promptCard;
        promptPanel.setVisibility(View.GONE);
        root.addView(promptPanel);

        pageStatus = new TextView(this);
        pageStatus.setText("Escolha uma IA acima. É necessária conexão com a internet.");
        pageStatus.setTextColor(MUTED);
        pageStatus.setTextSize(11);
        pageStatus.setPadding(dp(4), dp(5), dp(4), dp(5));
        root.addView(pageStatus);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.WHITE);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);
        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(webView, true);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme();
                if ("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme)) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (Exception ignored) {
                    Toast.makeText(AIBrowserActivity.this, "Não foi possível abrir este link.", Toast.LENGTH_SHORT).show();
                }
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                addressInput.setText(url == null ? "" : url);
                pageStatus.setText("Carregando site de IA…");
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                addressInput.setText(url == null ? "" : url);
                pageStatus.setText("Página carregada. Caso o login falhe, use Abrir no Chrome.");
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try {
                    startActivityForResult(intent, FILE_PICKER_REQUEST);
                    return true;
                } catch (Exception ex) {
                    fileCallback = null;
                    return false;
                }
            }

            @Override
            public void onProgressChanged(WebView view, int progress) {
                if (progress < 100) pageStatus.setText("Carregando… " + progress + "%");
            }
        });
        root.addView(webView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(root);
        webView.loadUrl("https://chatgpt.com/");
    }

    private void addProvider(LinearLayout row, String label, String url) {
        Button item = button(label, false);
        item.setOnClickListener(v -> loadAddress(url));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(40));
        lp.setMargins(dp(2), dp(2), dp(4), dp(2));
        row.addView(item, lp);
    }

    private Button button(String label, boolean secondary) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(12);
        button.setAllCaps(false);
        button.setTextColor(TEXT);
        button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(secondary ? PANEL : Color.rgb(34, 91, 178)));
        button.setPadding(dp(5), 0, dp(5), 0);
        return button;
    }

    private void loadAddress(String value) {
        String input = value == null ? "" : value.trim();
        if (input.isEmpty()) return;
        if (!input.matches("(?i)^https?://.*")) input = "https://" + input;
        Uri uri = Uri.parse(input);
        String scheme = uri.getScheme();
        if (scheme == null || !("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme))
                || uri.getHost() == null) {
            addressInput.setError("Informe um endereço HTTP ou HTTPS válido.");
            return;
        }
        addressInput.setText(uri.toString());
        webView.loadUrl(uri.toString());
    }

    private void openExternal(String value) {
        String input = value == null ? "" : value.trim();
        if (input.isEmpty()) input = "https://chatgpt.com/";
        if (!input.matches("(?i)^https?://.*")) input = "https://" + input;
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(input)));
        } catch (Exception ex) {
            Toast.makeText(this, "Nenhum navegador disponível.", Toast.LENGTH_LONG).show();
        }
    }

    private void copyPrompt() {
        String text = promptInput.getText().toString().trim();
        if (text.isEmpty()) {
            Toast.makeText(this, "Não há pedido para copiar.", Toast.LENGTH_SHORT).show();
            return;
        }
        ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("MotionForge AI prompt", text));
        Toast.makeText(this, "Pedido copiado. Cole-o na conversa da IA.", Toast.LENGTH_LONG).show();
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
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (fileCallback != null) {
            fileCallback.onReceiveValue(null);
            fileCallback = null;
        }
        if (webView != null) {
            webView.stopLoading();
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
