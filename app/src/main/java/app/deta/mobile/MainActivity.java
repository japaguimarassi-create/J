package app.deta.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.method.LinkMovementMethod;
import android.text.util.Linkify;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int PANEL = Color.rgb(30, 30, 31);
    private static final int SURFACE = Color.rgb(45, 45, 47);
    private static final int SURFACE_LIGHT = Color.rgb(58, 58, 60);
    private static final int OUTLINE = Color.rgb(70, 70, 73);
    private static final int WHITE = Color.rgb(245, 245, 247);
    private static final int MUTED = Color.rgb(171, 171, 178);
    private static final int ACCENT = Color.rgb(184, 171, 255);
    private static final int BLUE = Color.rgb(55, 101, 246);
    private static final String PREFS_NAME = "deta_local_ui";
    private static final String PREFS_CONVERSATIONS = "conversations";
    private static final int VOICE_REQUEST = 712;

    private final ArrayList<Conversation> conversations = new ArrayList<>();
    private FrameLayout root;
    private FrameLayout drawerLayer;
    private ScrollView transcriptScroll;
    private LinearLayout transcript;
    private LinearLayout suggestions;
    private LinearLayout drawerRows;
    private EditText composer;
    private EditText drawerSearch;
    private long activeConversationId = -1L;
    private boolean searchOpen;

    private enum Icon { MENU, SPARKLE, NEW_CHAT, SEARCH, PLUS, MIC, WAVE, IMAGE, EDIT, CLOSE }

    private static final class ChatMessage {
        final boolean fromUser;
        String text;
        ChatMessage(boolean fromUser, String text) {
            this.fromUser = fromUser;
            this.text = text;
        }
    }

    private static final class Conversation {
        final long id;
        String title;
        final ArrayList<ChatMessage> messages = new ArrayList<>();
        Conversation(long id, String title) {
            this.id = id;
            this.title = title;
        }
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Window window = getWindow();
        window.setStatusBarColor(BLACK);
        window.setNavigationBarColor(Color.rgb(9, 9, 9));
        window.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        window.getDecorView().setSystemUiVisibility(0);
        if (android.os.Build.VERSION.SDK_INT >= 29) window.setNavigationBarContrastEnforced(false);
        try {
            loadConversations();
            buildScreen();
        } catch (RuntimeException exception) {
            getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit().putString("last_startup_error", exception.getClass().getName() + ": " + String.valueOf(exception.getMessage())).apply();
            showStartupRecovery(exception);
        }
    }

    private void showStartupRecovery(RuntimeException exception) {
        LinearLayout recovery = vertical();
        recovery.setBackgroundColor(BLACK);
        recovery.setPadding(dp(24), dp(32), dp(24), dp(24));
        recovery.addView(text("Deta — recuperação", 24, WHITE, true), lp(-1, 48));
        TextView message = text("A interface principal encontrou um erro ao iniciar. Os dados locais foram preservados. Tente abrir novamente.", 16, MUTED, false);
        message.setGravity(Gravity.TOP);
        LinearLayout.LayoutParams messageParams = lp(-1, -2);
        margin(messageParams, 0, 12, 0, 20);
        recovery.addView(message, messageParams);
        TextView detail = text(exception.getClass().getSimpleName() + ": " + String.valueOf(exception.getMessage()), 12, MUTED, false);
        detail.setGravity(Gravity.TOP);
        recovery.addView(detail, lp(-1, -2));
        TextView retry = text("Tentar novamente", 16, BLACK, true);
        retry.setGravity(Gravity.CENTER);
        retry.setBackground(rounded(ACCENT, 24, 0));
        retry.setClickable(true);
        retry.setFocusable(true);
        LinearLayout.LayoutParams retryParams = lp(-1, 52);
        margin(retryParams, 0, 28, 0, 0);
        recovery.addView(retry, retryParams);
        retry.setOnClickListener(view -> {
            try { buildScreen(); }
            catch (RuntimeException next) { showStartupRecovery(next); }
        });
        setContentView(recovery);
    }
    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private LinearLayout.LayoutParams lp(int width, int height) {
        return new LinearLayout.LayoutParams(width < 0 ? width : dp(width), height < 0 ? height : dp(height));
    }

    private void margin(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) {
        params.setMargins(dp(left), dp(top), dp(right), dp(bottom));
    }

    private GradientDrawable rounded(int fill, int radius, int stroke) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(radius));
        if (stroke != 0) drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private TextView text(String value, float size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setTypeface(Typeface.create("sans-serif", bold ? Typeface.BOLD : Typeface.NORMAL));
        view.setGravity(Gravity.CENTER_VERTICAL);
        view.setIncludeFontPadding(false);
        return view;
    }

    private LinearLayout vertical() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.VERTICAL);
        return view;
    }

    private LinearLayout horizontal() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.HORIZONTAL);
        view.setGravity(Gravity.CENTER_VERTICAL);
        return view;
    }

    private FrameLayout iconButton(Icon icon, int size, int fill, int color, String description, Runnable action) {
        FrameLayout button = new FrameLayout(this);
        button.setBackground(rounded(fill, size / 2, fill == SURFACE ? OUTLINE : 0));
        button.setContentDescription(description);
        button.setClickable(true);
        button.setFocusable(true);
        button.addView(new IconView(this, icon, color),
                new FrameLayout.LayoutParams(dp(24), dp(24), Gravity.CENTER));
        button.setOnClickListener(view -> action.run());
        return button;
    }

    private void buildScreen() {
        root = new FrameLayout(this);
        root.setBackgroundColor(BLACK);

        LinearLayout page = vertical();
        page.setBackgroundColor(BLACK);
        root.addView(page, new FrameLayout.LayoutParams(-1, -1));
        page.addView(buildTopBar(), lp(-1, 72));

        transcriptScroll = new ScrollView(this);
        transcriptScroll.setFillViewport(true);
        transcriptScroll.setClipToPadding(false);
        transcriptScroll.setVerticalScrollBarEnabled(false);
        transcript = vertical();
        transcript.setPadding(dp(18), dp(18), dp(18), dp(20));
        transcriptScroll.addView(transcript, new ScrollView.LayoutParams(-1, -2));
        page.addView(transcriptScroll, new LinearLayout.LayoutParams(-1, 0, 1f));

        suggestions = vertical();
        suggestions.setPadding(dp(25), dp(2), dp(22), dp(7));
        suggestions.addView(suggestionRow(Icon.IMAGE, "Criar uma imagem ou visual",
                "Ajude-me a planejar um visual original."));
        suggestions.addView(suggestionRow(Icon.EDIT, "Escrever ou editar",
                "Ajude-me a escrever ou revisar um texto."));
        page.addView(suggestions, lp(-1, -2));
        page.addView(buildComposer(), lp(-1, -2));
        setContentView(root);
        renderTranscript();
    }

    private View buildTopBar() {
        LinearLayout bar = horizontal();
        bar.setPadding(dp(16), dp(7), dp(16), dp(7));
        bar.addView(iconButton(Icon.MENU, 48, SURFACE_LIGHT, WHITE, "Abrir conversas", this::openDrawer), lp(48, 48));

        LinearLayout brand = horizontal();
        brand.setPadding(dp(15), 0, dp(19), 0);
        brand.setBackground(rounded(SURFACE, 28, OUTLINE));
        brand.addView(new IconView(this, Icon.SPARKLE, ACCENT), lp(23, 23));
        TextView title = text("Deta", 19, ACCENT, true);
        LinearLayout.LayoutParams titleParams = lp(-2, -1);
        margin(titleParams, 8, 0, 0, 0);
        brand.addView(title, titleParams);
        LinearLayout.LayoutParams brandParams = lp(-2, 48);
        margin(brandParams, 12, 0, 0, 0);
        bar.addView(brand, brandParams);
        bar.addView(new Space(this), new LinearLayout.LayoutParams(0, 1, 1f));
        bar.addView(iconButton(Icon.NEW_CHAT, 48, SURFACE_LIGHT, WHITE, "Nova conversa", this::startNewConversation), lp(48, 48));
        return bar;
    }

    private View suggestionRow(Icon icon, String title, String prompt) {
        LinearLayout row = horizontal();
        row.setPadding(dp(1), dp(10), dp(4), dp(10));
        row.setMinimumHeight(dp(50));
        row.setBackgroundResource(android.R.drawable.list_selector_background);
        row.setClickable(true);
        row.setFocusable(true);
        row.addView(new IconView(this, icon, Color.rgb(205, 205, 210)), lp(26, 26));
        TextView titleView = text(title, 16, Color.rgb(218, 218, 222), false);
        LinearLayout.LayoutParams titleParams = lp(-1, -2);
        margin(titleParams, 18, 0, 0, 0);
        row.addView(titleView, titleParams);
        row.setOnClickListener(view -> {
            composer.setText(prompt);
            composer.setSelection(composer.length());
            composer.requestFocus();
            showKeyboard(composer);
        });
        return row;
    }

    private View buildComposer() {
        LinearLayout outer = vertical();
        outer.setPadding(dp(18), dp(2), dp(18), dp(12));

        LinearLayout box = horizontal();
        box.setPadding(dp(7), dp(7), dp(7), dp(7));
        box.setBackground(rounded(SURFACE, 28, OUTLINE));

        box.addView(iconButton(Icon.PLUS, 42, SURFACE, WHITE, "Mais opções", this::showAttachmentOptions), lp(42, 42));

        composer = new EditText(this);
        composer.setSingleLine(false);
        composer.setMinLines(1);
        composer.setMaxLines(4);
        composer.setTextSize(17);
        composer.setTextColor(WHITE);
        composer.setHintTextColor(MUTED);
        composer.setHint("Mensagem para Deta");
        composer.setPadding(dp(7), dp(7), dp(5), dp(7));
        composer.setBackgroundColor(Color.TRANSPARENT);
        composer.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        composer.setImeOptions(EditorInfo.IME_ACTION_SEND | EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        composer.setOnEditorActionListener((view, actionId, event) -> {
            boolean enterPressed = event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER
                    && event.getAction() == KeyEvent.ACTION_DOWN;
            if (actionId == EditorInfo.IME_ACTION_SEND || enterPressed) {
                sendMessage();
                return true;
            }
            return false;
        });
        box.addView(composer, new LinearLayout.LayoutParams(0, -2, 1f));
        box.addView(iconButton(Icon.MIC, 40, SURFACE, WHITE, "Ditado por voz", this::startVoiceInput), lp(40, 42));
        box.addView(iconButton(Icon.WAVE, 42, Color.WHITE, BLACK, "Enviar mensagem", this::sendMessage), lp(42, 42));

        outer.addView(box, lp(-1, -2));
        TextView privacyHint = text("As conversas ficam salvas neste dispositivo.", 11, Color.rgb(120, 120, 126), false);
        privacyHint.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams hintParams = lp(-1, 19);
        margin(hintParams, 0, 5, 0, 0);
        outer.addView(privacyHint, hintParams);
        return outer;
    }

    private void showAttachmentOptions() {
        String[] options = {"Pesquisar na web", "Ajuda e funções", "Limpar mensagem", "Nova conversa"};
        new AlertDialog.Builder(this).setTitle("Ações da Deta")
                .setItems(options, (dialog, which) -> {
                    if (which == 0) {
                        composer.setText("Pesquisar na web: ");
                        composer.setSelection(composer.length());
                        composer.requestFocus();
                        showKeyboard(composer);
                    } else if (which == 1) {
                        composer.setText("/ajuda");
                        composer.setSelection(composer.length());
                    } else if (which == 2) {
                        composer.setText("");
                        composer.requestFocus();
                    } else {
                        startNewConversation();
                    }
                })
                .setNegativeButton("Fechar", null).show();
    }

    private void startVoiceInput() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Fale sua mensagem");
        try {
            startActivityForResult(intent, VOICE_REQUEST);
        } catch (Exception exception) {
            Toast.makeText(this, "Ditado por voz não está disponível neste dispositivo.", Toast.LENGTH_LONG).show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != VOICE_REQUEST || resultCode != RESULT_OK || data == null) return;
        ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
        if (results != null && !results.isEmpty() && results.get(0) != null) {
            composer.setText(results.get(0));
            composer.setSelection(composer.length());
        }
    }

    private void showKeyboard(EditText field) {
        field.postDelayed(() -> {
            InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (manager != null) manager.showSoftInput(field, InputMethodManager.SHOW_IMPLICIT);
        }, 160);
    }

    private Conversation activeConversation() {
        for (Conversation conversation : conversations) {
            if (conversation.id == activeConversationId) return conversation;
        }
        return null;
    }

    private Conversation findConversation(long id) {
        for (Conversation conversation : conversations) {
            if (conversation.id == id) return conversation;
        }
        return null;
    }

    private long nextConversationId() {
        long id = System.currentTimeMillis();
        while (findConversation(id) != null) id++;
        return id;
    }

    private void startNewConversation() {
        activeConversationId = -1L;
        closeDrawer();
        composer.setText("");
        composer.clearFocus();
        renderTranscript();
    }

    private void sendMessage() {
        String value = composer.getText().toString().trim();
        if (value.isEmpty()) {
            Toast.makeText(this, "Escreva uma pergunta ou consulta.", Toast.LENGTH_SHORT).show();
            return;
        }
        Conversation conversation = activeConversation();
        if (conversation == null) {
            conversation = new Conversation(nextConversationId(), "Nova conversa");
            conversations.add(0, conversation);
            activeConversationId = conversation.id;
        }
        if (conversation.messages.isEmpty()) conversation.title = createTitle(value);
        conversation.messages.add(new ChatMessage(true, value));
        ChatMessage response = new ChatMessage(false, "Consultando a web pública...");
        conversation.messages.add(response);
        Conversation responseConversation = conversation;
        composer.setText("");
        persistConversations();
        renderTranscript();
        if (drawerLayer != null) renderDrawerRows();
        InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(composer.getWindowToken(), 0);
        composer.clearFocus();
        transcriptScroll.post(() -> transcriptScroll.fullScroll(View.FOCUS_DOWN));

        Thread worker = new Thread(() -> {
            String answer = WebSearch.answer(value);
            runOnUiThread(() -> {
                response.text = answer;
                persistConversations();
                if (activeConversationId == responseConversation.id) {
                    renderTranscript();
                    transcriptScroll.post(() -> transcriptScroll.fullScroll(View.FOCUS_DOWN));
                }
                if (drawerLayer != null) renderDrawerRows();
            });
        }, "deta-public-web-search");
        worker.setDaemon(true);
        worker.start();
    }

    private String createTitle(String value) {
        String result = value.replaceAll("\\s+", " ").trim();
        if (result.length() > 34) result = result.substring(0, 31).trim() + "...";
        return result.isEmpty() ? "Nova conversa" : result;
    }

    private void renderTranscript() {
        if (transcript == null) return;
        transcript.removeAllViews();
        Conversation conversation = activeConversation();
        boolean hasMessages = conversation != null && !conversation.messages.isEmpty();
        suggestions.setVisibility(hasMessages ? View.GONE : View.VISIBLE);
        if (!hasMessages) return;

        for (ChatMessage message : conversation.messages) {
            LinearLayout row = horizontal();
            row.setGravity(message.fromUser ? Gravity.RIGHT : Gravity.LEFT);
            LinearLayout.LayoutParams rowParams = lp(-1, -2);
            margin(rowParams, 0, 8, 0, 8);
            if (message.fromUser) {
                TextView bubble = text(message.text, 16, WHITE, false);
                bubble.setMaxWidth((int) (getResources().getDisplayMetrics().widthPixels * 0.78f));
                bubble.setPadding(dp(15), dp(12), dp(15), dp(12));
                bubble.setBackground(rounded(Color.rgb(48, 48, 50), 22, 0));
                row.addView(bubble, new LinearLayout.LayoutParams(-2, -2));
            } else {
                LinearLayout.LayoutParams iconParams = lp(25, 25);
                margin(iconParams, 1, 5, 10, 0);
                row.addView(new IconView(this, Icon.SPARKLE, ACCENT), iconParams);
                TextView response = text(message.text, 15, Color.rgb(222, 222, 226), false);
                response.setGravity(Gravity.TOP);
                response.setLineSpacing(dp(3), 1f);
                response.setAutoLinkMask(Linkify.WEB_URLS);
                response.setLinkTextColor(ACCENT);
                response.setMovementMethod(LinkMovementMethod.getInstance());
                row.addView(response, new LinearLayout.LayoutParams(0, -2, 1f));
            }
            transcript.addView(row, rowParams);
        }
    }

    private void openDrawer() {
        if (drawerLayer != null) root.removeView(drawerLayer);
        drawerLayer = new FrameLayout(this);
        drawerLayer.setBackgroundColor(0x99000000);
        drawerLayer.setClickable(true);
        drawerLayer.setOnClickListener(view -> closeDrawer());

        LinearLayout panel = vertical();
        panel.setBackgroundColor(PANEL);
        panel.setElevation(dp(14));
        panel.setPadding(dp(22), dp(26), dp(18), dp(14));
        panel.setOnClickListener(view -> { });

        LinearLayout header = horizontal();
        header.addView(text("Conversas", 25, WHITE, true), new LinearLayout.LayoutParams(0, dp(48), 1f));
        header.addView(iconButton(Icon.SEARCH, 46, SURFACE_LIGHT, WHITE, "Buscar conversas", this::toggleSearch), lp(46, 46));
        panel.addView(header, lp(-1, 50));

        drawerSearch = new EditText(this);
        drawerSearch.setSingleLine(true);
        drawerSearch.setVisibility(searchOpen ? View.VISIBLE : View.GONE);
        drawerSearch.setTextSize(15);
        drawerSearch.setTextColor(WHITE);
        drawerSearch.setHintTextColor(MUTED);
        drawerSearch.setHint("Buscar conversas");
        drawerSearch.setBackground(rounded(SURFACE_LIGHT, 16, 0));
        drawerSearch.setPadding(dp(12), 0, dp(12), 0);
        drawerSearch.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        drawerSearch.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) { }
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { renderDrawerRows(); }
            @Override public void afterTextChanged(Editable s) { }
        });
        LinearLayout.LayoutParams searchParams = lp(-1, 46);
        margin(searchParams, 0, 12, 0, 0);
        panel.addView(drawerSearch, searchParams);

        LinearLayout newConversation = horizontal();
        newConversation.setPadding(dp(14), 0, dp(14), 0);
        newConversation.setBackground(rounded(BLUE, 20, 0));
        newConversation.addView(new IconView(this, Icon.NEW_CHAT, Color.WHITE), lp(22, 22));
        TextView newLabel = text("Nova conversa", 15, Color.WHITE, true);
        LinearLayout.LayoutParams newTextParams = lp(-1, -1);
        margin(newTextParams, 11, 0, 0, 0);
        newConversation.addView(newLabel, newTextParams);
        newConversation.setClickable(true);
        newConversation.setFocusable(true);
        newConversation.setOnClickListener(view -> startNewConversation());
        LinearLayout.LayoutParams newParams = lp(-1, 48);
        margin(newParams, 0, 19, 0, 23);
        panel.addView(newConversation, newParams);

        panel.addView(text("Recentes", 16, WHITE, true), lp(-1, 30));
        ScrollView rowsScroll = new ScrollView(this);
        rowsScroll.setVerticalScrollBarEnabled(false);
        drawerRows = vertical();
        drawerRows.setPadding(0, dp(6), 0, dp(8));
        rowsScroll.addView(drawerRows, new ScrollView.LayoutParams(-1, -2));
        panel.addView(rowsScroll, new LinearLayout.LayoutParams(-1, 0, 1f));

        LinearLayout footer = horizontal();
        View avatar = new View(this);
        avatar.setBackground(rounded(Color.rgb(46, 116, 169), 24, 0));
        FrameLayout avatarFrame = new FrameLayout(this);
        avatarFrame.addView(avatar, new FrameLayout.LayoutParams(dp(42), dp(42), Gravity.CENTER));
        TextView avatarLetter = text("D", 18, Color.WHITE, true);
        avatarLetter.setGravity(Gravity.CENTER);
        avatarFrame.addView(avatarLetter, new FrameLayout.LayoutParams(-1, -1));
        footer.addView(avatarFrame, lp(42, 42));
        LinearLayout footerText = vertical();
        footerText.addView(text("Deta", 14, WHITE, true), lp(-1, 21));
        footerText.addView(text("Interface local", 12, MUTED, false), lp(-1, 18));
        LinearLayout.LayoutParams footerTextParams = lp(-1, -2);
        margin(footerTextParams, 12, 0, 0, 0);
        footer.addView(footerText, footerTextParams);
        panel.addView(footer, lp(-1, 58));

        int panelWidth = Math.min(dp(340), getResources().getDisplayMetrics().widthPixels - dp(58));
        drawerLayer.addView(panel, new FrameLayout.LayoutParams(Math.max(dp(260), panelWidth), -1, Gravity.START));
        root.addView(drawerLayer, new FrameLayout.LayoutParams(-1, -1));
        renderDrawerRows();
        if (searchOpen) {
            drawerSearch.requestFocus();
            showKeyboard(drawerSearch);
        }
    }

    private void toggleSearch() {
        searchOpen = !searchOpen;
        closeDrawer();
        openDrawer();
    }

    private void closeDrawer() {
        if (drawerLayer != null && root != null) root.removeView(drawerLayer);
        drawerLayer = null;
        drawerRows = null;
        drawerSearch = null;
    }

    private void renderDrawerRows() {
        if (drawerRows == null) return;
        drawerRows.removeAllViews();
        ArrayList<Conversation> sorted = new ArrayList<>(conversations);
        Collections.sort(sorted, Comparator.comparingLong((Conversation item) -> item.id).reversed());
        String query = drawerSearch == null ? "" : drawerSearch.getText().toString().trim().toLowerCase(Locale.ROOT);
        int visibleCount = 0;
        for (Conversation conversation : sorted) {
            if (!query.isEmpty() && !conversation.title.toLowerCase(Locale.ROOT).contains(query)) continue;
            visibleCount++;
            LinearLayout row = horizontal();
            row.setPadding(dp(11), dp(10), dp(11), dp(10));
            row.setMinimumHeight(dp(48));
            row.setBackgroundResource(android.R.drawable.list_selector_background);
            row.setClickable(true);
            row.setFocusable(true);
            TextView title = text(conversation.title, 15,
                    conversation.id == activeConversationId ? Color.WHITE : Color.rgb(223, 223, 227), false);
            title.setSingleLine(true);
            title.setEllipsize(android.text.TextUtils.TruncateAt.END);
            row.addView(title, new LinearLayout.LayoutParams(0, -2, 1f));
            row.setOnClickListener(view -> {
                activeConversationId = conversation.id;
                closeDrawer();
                renderTranscript();
            });
            LinearLayout.LayoutParams rowParams = lp(-1, -2);
            margin(rowParams, 0, 2, 0, 2);
            drawerRows.addView(row, rowParams);
        }
        if (visibleCount == 0) {
            TextView empty = text(query.isEmpty() ? "Nenhuma conversa ainda." : "Nenhum resultado.", 14, MUTED, false);
            empty.setPadding(dp(11), dp(14), dp(11), dp(14));
            drawerRows.addView(empty, lp(-1, -2));
        }
    }

    private void persistConversations() {
        JSONArray array = new JSONArray();
        for (Conversation conversation : conversations) {
            JSONObject object = new JSONObject();
            try {
                object.put("id", conversation.id);
                object.put("title", conversation.title);
                JSONArray messages = new JSONArray();
                for (ChatMessage message : conversation.messages) {
                    JSONObject item = new JSONObject();
                    item.put("user", message.fromUser);
                    item.put("text", message.text);
                    messages.put(item);
                }
                object.put("messages", messages);
                array.put(object);
            } catch (JSONException ignored) { }
        }
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
                .putString(PREFS_CONVERSATIONS, array.toString()).apply();
    }

    private void loadConversations() {
        String saved = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(PREFS_CONVERSATIONS, "[]");
        try {
            JSONArray array = new JSONArray(saved);
            for (int index = 0; index < array.length(); index++) {
                JSONObject object = array.getJSONObject(index);
                Conversation conversation = new Conversation(object.getLong("id"), object.optString("title", "Nova conversa"));
                JSONArray messages = object.optJSONArray("messages");
                if (messages != null) {
                    for (int messageIndex = 0; messageIndex < messages.length(); messageIndex++) {
                        JSONObject item = messages.getJSONObject(messageIndex);
                        conversation.messages.add(new ChatMessage(item.optBoolean("user", false), item.optString("text", "")));
                    }
                }
                if (!conversation.messages.isEmpty()) conversations.add(conversation);
            }
        } catch (JSONException ignored) {
            conversations.clear();
        }
    }

    private final class IconView extends View {
        private final Icon icon;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        IconView(Context context, Icon icon, int color) {
            super(context);
            this.icon = icon;
            paint.setColor(color);
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(2.0f);
            paint.setStrokeCap(Paint.Cap.ROUND);
            paint.setStrokeJoin(Paint.Join.ROUND);
            setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        }

        private void line(Canvas c, float x1, float y1, float x2, float y2) { c.drawLine(x1, y1, x2, y2, paint); }

        private void path(Canvas c, float... points) {
            Path path = new Path();
            path.moveTo(points[0], points[1]);
            for (int i = 2; i < points.length; i += 2) path.lineTo(points[i], points[i + 1]);
            c.drawPath(path, paint);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float size = Math.min(getWidth(), getHeight());
            if (size <= 0) return;
            int saved = canvas.save();
            canvas.translate((getWidth() - size) / 2f, (getHeight() - size) / 2f);
            canvas.scale(size / 24f, size / 24f);
            switch (icon) {
                case MENU:
                    line(canvas, 4, 6, 20, 6); line(canvas, 4, 12, 16, 12); line(canvas, 4, 18, 20, 18); break;
                case SPARKLE:
                    path(canvas, 12, 2.8f, 14.5f, 9.5f, 21.2f, 12, 14.5f, 14.5f, 12, 21.2f, 9.5f, 14.5f, 2.8f, 12, 9.5f, 9.5f, 12); break;
                case NEW_CHAT:
                    canvas.drawRoundRect(new RectF(3.5f, 4.5f, 18.5f, 17.5f), 4, 4, paint);
                    path(canvas, 7, 17.5f, 6, 21, 11, 17.5f);
                    line(canvas, 16.5f, 14, 22, 14); line(canvas, 19.25f, 11.25f, 19.25f, 16.75f); break;
                case SEARCH:
                    canvas.drawCircle(10.5f, 10.5f, 6.5f, paint); line(canvas, 15.5f, 15.5f, 21, 21); break;
                case PLUS:
                    line(canvas, 12, 4, 12, 20); line(canvas, 4, 12, 20, 12); break;
                case MIC:
                    canvas.drawRoundRect(new RectF(8.5f, 3, 15.5f, 15), 3.5f, 3.5f, paint);
                    canvas.drawArc(new RectF(5.5f, 7, 18.5f, 18.5f), 0, 180, false, paint);
                    line(canvas, 12, 18.5f, 12, 21); line(canvas, 8.5f, 21, 15.5f, 21); break;
                case WAVE:
                    paint.setStyle(Paint.Style.FILL);
                    canvas.drawRoundRect(new RectF(4, 9, 6.5f, 15), 1.2f, 1.2f, paint);
                    canvas.drawRoundRect(new RectF(8, 5.5f, 10.5f, 18.5f), 1.2f, 1.2f, paint);
                    canvas.drawRoundRect(new RectF(12, 3, 14.5f, 21), 1.2f, 1.2f, paint);
                    canvas.drawRoundRect(new RectF(16, 7, 18.5f, 17), 1.2f, 1.2f, paint);
                    canvas.drawRoundRect(new RectF(20, 10, 22, 14), 1.0f, 1.0f, paint);
                    paint.setStyle(Paint.Style.STROKE); break;
                case IMAGE:
                    canvas.drawRoundRect(new RectF(3, 4, 21, 20), 2.5f, 2.5f, paint);
                    canvas.drawCircle(8.2f, 9, 1.7f, paint);
                    path(canvas, 4, 17.5f, 9.5f, 12.5f, 13, 15.2f, 16, 12.5f, 20, 17.1f); break;
                case EDIT:
                    path(canvas, 4, 17.8f, 3, 21, 6.4f, 20, 19.5f, 6.8f, 17.2f, 4.5f, 4, 17.8f);
                    line(canvas, 15.6f, 6.1f, 17.9f, 8.4f); break;
                case CLOSE:
                    line(canvas, 6, 6, 18, 18); line(canvas, 18, 6, 6, 18); break;
            }
            canvas.restoreToCount(saved);
        }
    }
}
