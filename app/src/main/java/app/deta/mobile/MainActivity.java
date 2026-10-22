package app.deta.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
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
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(8, 9, 13);
    private static final int PANEL = Color.rgb(25, 26, 31);
    private static final int FIELD = Color.rgb(39, 40, 46);
    private static final int BORDER = Color.rgb(57, 58, 66);
    private static final int FG = Color.rgb(244, 244, 247);
    private static final int MUTED = Color.rgb(164, 166, 177);
    private static final int ACCENT = Color.rgb(186, 174, 255);
    private static final String PREFS = "deta_rebuilt_base";
    private static final String HISTORY_KEY = "history";
    private static final String ACTIVE_KEY = "active_conversation";
    private static final int MAX_CONVERSATIONS = 80;
    private static final int MAX_MESSAGES = 120;

    private final ArrayList<Conversation> history = new ArrayList<>();
    private FrameLayout root;
    private LinearLayout transcript;
    private ScrollView transcriptScroll;
    private EditText composer;
    private FrameLayout drawerOverlay;
    private LinearLayout drawerList;
    private EditText drawerSearch;
    private long activeId = -1L;

    private static final class Conversation {
        final long id;
        String title;
        final ArrayList<String> messages = new ArrayList<>();
        Conversation(long id, String title) {
            this.id = id;
            this.title = title;
        }
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Window window = getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(BG);
        window.setSoftInputMode(Window.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        loadHistory();
        if (state != null) activeId = state.getLong(ACTIVE_KEY, -1L);
        buildInterface();
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        state.putLong(ACTIVE_KEY, activeId);
        super.onSaveInstanceState(state);
    }

    @Override
    public void onBackPressed() {
        if (drawerOverlay != null) closeDrawer();
        else super.onBackPressed();
    }

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private LinearLayout.LayoutParams lp(int width, int height) {
        return new LinearLayout.LayoutParams(width < 0 ? width : dp(width), height < 0 ? height : dp(height));
    }

    private void margins(LinearLayout.LayoutParams p, int left, int top, int right, int bottom) {
        p.setMargins(dp(left), dp(top), dp(right), dp(bottom));
    }

    private GradientDrawable shape(int fill, int radius, int stroke) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(dp(radius));
        if (stroke != 0) d.setStroke(dp(1), stroke);
        return d;
    }

    private TextView text(String value, float size, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(value);
        v.setTextSize(size);
        v.setTextColor(color);
        v.setTypeface(Typeface.create("sans-serif", bold ? Typeface.BOLD : Typeface.NORMAL));
        v.setIncludeFontPadding(false);
        v.setGravity(Gravity.CENTER_VERTICAL);
        return v;
    }

    private LinearLayout column() {
        LinearLayout v = new LinearLayout(this);
        v.setOrientation(LinearLayout.VERTICAL);
        return v;
    }

    private LinearLayout row() {
        LinearLayout v = new LinearLayout(this);
        v.setOrientation(LinearLayout.HORIZONTAL);
        v.setGravity(Gravity.CENTER_VERTICAL);
        return v;
    }

    private TextView button(String glyph, String description, int fill, int color, Runnable click) {
        TextView v = text(glyph, 22, color, false);
        v.setGravity(Gravity.CENTER);
        v.setContentDescription(description);
        v.setBackground(shape(fill, 23, fill == FIELD ? BORDER : 0));
        v.setClickable(true);
        v.setFocusable(true);
        v.setOnClickListener(view -> click.run());
        return v;
    }

    private void buildInterface() {
        root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        LinearLayout page = column();
        page.setBackgroundColor(BG);
        root.addView(page, new FrameLayout.LayoutParams(-1, -1));
        page.addView(buildToolbar(), lp(-1, 68));

        transcriptScroll = new ScrollView(this);
        transcriptScroll.setFillViewport(true);
        transcriptScroll.setVerticalScrollBarEnabled(false);
        transcript = column();
        transcript.setPadding(dp(18), dp(18), dp(18), dp(22));
        transcriptScroll.addView(transcript, new ScrollView.LayoutParams(-1, -2));
        page.addView(transcriptScroll, new LinearLayout.LayoutParams(-1, 0, 1f));
        page.addView(buildComposer(), lp(-1, -2));
        setContentView(root);
        renderConversation();
    }

    private View buildToolbar() {
        LinearLayout bar = row();
        bar.setPadding(dp(16), dp(8), dp(16), dp(8));
        bar.addView(button("☰", "Abrir menu", FIELD, FG, this::openDrawer), lp(46, 46));

        LinearLayout brand = row();
        brand.setPadding(dp(12), 0, dp(17), 0);
        brand.setBackground(shape(PANEL, 24, BORDER));
        TextView logo = text("D", 21, ACCENT, true);
        logo.setGravity(Gravity.CENTER);
        logo.setBackground(shape(Color.rgb(43, 39, 64), 10, 0));
        brand.addView(logo, lp(30, 30));
        TextView title = text("Deta", 18, FG, true);
        LinearLayout.LayoutParams tp = lp(-2, -1);
        margins(tp, 9, 0, 0, 0);
        brand.addView(title, tp);
        LinearLayout.LayoutParams bp = lp(-2, 46);
        margins(bp, 10, 0, 0, 0);
        bar.addView(brand, bp);
        bar.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        bar.addView(button("+", "Nova conversa", FIELD, FG, this::startNewConversation), lp(46, 46));
        return bar;
    }

    private View buildComposer() {
        LinearLayout wrapper = column();
        wrapper.setPadding(dp(16), dp(3), dp(16), dp(12));
        LinearLayout field = row();
        field.setPadding(dp(7), dp(7), dp(7), dp(7));
        field.setBackground(shape(PANEL, 27, BORDER));

        TextView options = button("+", "Mais opções", PANEL, FG, this::showOptions);
        field.addView(options, lp(42, 42));
        composer = new EditText(this);
        composer.setHint("Escreva uma mensagem ou nota");
        composer.setTextColor(FG);
        composer.setHintTextColor(MUTED);
        composer.setTextSize(16);
        composer.setMinLines(1);
        composer.setMaxLines(4);
        composer.setPadding(dp(9), dp(8), dp(5), dp(8));
        composer.setBackgroundColor(Color.TRANSPARENT);
        composer.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        composer.setImeOptions(EditorInfo.IME_ACTION_SEND | EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        composer.setOnEditorActionListener((view, actionId, event) -> {
            boolean enter = event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER
                    && event.getAction() == KeyEvent.ACTION_DOWN;
            if (actionId == EditorInfo.IME_ACTION_SEND || enter) {
                saveMessage();
                return true;
            }
            return false;
        });
        field.addView(composer, new LinearLayout.LayoutParams(0, -2, 1f));
        field.addView(button("↑", "Enviar mensagem", ACCENT, BG, this::saveMessage), lp(42, 42));
        wrapper.addView(field, lp(-1, -2));
        TextView footer = text("Base local · sem IA · sem internet", 11, MUTED, false);
        footer.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams fp = lp(-1, 22);
        margins(fp, 0, 4, 0, 0);
        wrapper.addView(footer, fp);
        return wrapper;
    }

    private Conversation findConversation(long id) {
        for (Conversation c : history) if (c.id == id) return c;
        return null;
    }

    private Conversation activeConversation() {
        return findConversation(activeId);
    }

    private long uniqueId() {
        long id = System.currentTimeMillis();
        while (findConversation(id) != null) id++;
        return id;
    }

    private void startNewConversation() {
        closeDrawer();
        activeId = uniqueId();
        history.add(0, new Conversation(activeId, "Nova conversa"));
        trimHistory();
        saveHistory();
        composer.setText("");
        composer.clearFocus();
        renderConversation();
    }

    private void saveMessage() {
        String value = composer.getText().toString().trim();
        if (value.isEmpty()) {
            Toast.makeText(this, "Escreva algo antes de salvar.", Toast.LENGTH_SHORT).show();
            return;
        }
        Conversation c = activeConversation();
        if (c == null) {
            c = new Conversation(uniqueId(), "Nova conversa");
            history.add(0, c);
            activeId = c.id;
        }
        if (c.messages.isEmpty()) c.title = makeTitle(value);
        c.messages.add(value);
        if (c.messages.size() > MAX_MESSAGES) c.messages.remove(0);
        moveToTop(c);
        trimHistory();
        saveHistory();
        composer.setText("");
        InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(composer.getWindowToken(), 0);
        composer.clearFocus();
        renderConversation();
        if (drawerList != null) renderHistoryList();
        transcriptScroll.post(() -> transcriptScroll.fullScroll(View.FOCUS_DOWN));
        Toast.makeText(this, "Mensagem salva neste dispositivo.", Toast.LENGTH_SHORT).show();
    }

    private String makeTitle(String value) {
        String title = value.replaceAll("\\s+", " ").trim();
        if (title.length() > 38) title = title.substring(0, 35).trim() + "...";
        return title.isEmpty() ? "Nova conversa" : title;
    }

    private void moveToTop(Conversation c) {
        history.remove(c);
        history.add(0, c);
    }

    private void trimHistory() {
        while (history.size() > MAX_CONVERSATIONS) {
            Conversation removed = history.remove(history.size() - 1);
            if (removed.id == activeId) activeId = -1L;
        }
    }

    private void renderConversation() {
        if (transcript == null) return;
        transcript.removeAllViews();
        Conversation c = activeConversation();
        if (c == null || c.messages.isEmpty()) {
            transcript.setGravity(Gravity.CENTER);
            LinearLayout intro = column();
            intro.setGravity(Gravity.CENTER_HORIZONTAL);
            TextView logo = text("D", 34, ACCENT, true);
            logo.setGravity(Gravity.CENTER);
            logo.setBackground(shape(Color.rgb(43, 39, 64), 23, 0));
            intro.addView(logo, lp(68, 68));
            TextView heading = text("Deta — base local", 23, FG, true);
            heading.setGravity(Gravity.CENTER);
            LinearLayout.LayoutParams hp = lp(-1, -2);
            margins(hp, 0, 22, 0, 0);
            intro.addView(heading, hp);
            TextView detail = text(
                    "A interface foi refeita do zero.\nAs mensagens ficam neste aparelho.\nNão há IA ou internet nesta versão.",
                    14, MUTED, false);
            detail.setGravity(Gravity.CENTER);
            detail.setLineSpacing(dp(5), 1f);
            LinearLayout.LayoutParams dp = lp(-1, -2);
            margins(dp, 0, 10, 0, 0);
            intro.addView(detail, dp);
            TextView historyAction = text("Abrir conversas", 14, FG, true);
            historyAction.setGravity(Gravity.CENTER);
            historyAction.setBackground(shape(FIELD, 20, BORDER));
            historyAction.setPadding(this.dp(18), 0, this.dp(18), 0);
            historyAction.setClickable(true);
            historyAction.setFocusable(true);
            historyAction.setContentDescription("Abrir conversas recentes");
            historyAction.setOnClickListener(view -> openDrawer());
            LinearLayout.LayoutParams ap = lp(-2, 44);
            margins(ap, 0, 22, 0, 0);
            intro.addView(historyAction, ap);
            transcript.addView(intro, lp(-1, -2));
            return;
        }

        transcript.setGravity(Gravity.TOP);
        for (String message : c.messages) {
            LinearLayout bubbleRow = row();
            bubbleRow.setGravity(Gravity.RIGHT);
            LinearLayout.LayoutParams rp = lp(-1, -2);
            margins(rp, 0, 6, 0, 6);
            TextView bubble = text(message, 16, FG, false);
            bubble.setMaxWidth((int) (getResources().getDisplayMetrics().widthPixels * 0.82f));
            bubble.setPadding(dp(15), dp(12), dp(15), dp(12));
            bubble.setBackground(shape(Color.rgb(47, 47, 56), 20, 0));
            bubble.setTextIsSelectable(true);
            bubbleRow.addView(bubble, new LinearLayout.LayoutParams(-2, -2));
            transcript.addView(bubbleRow, rp);
        }
    }

    private void showOptions() {
        ArrayList<String> values = new ArrayList<>();
        values.add("Nova conversa");
        if (activeConversation() != null) values.add("Apagar conversa atual");
        values.add("Sobre esta base");
        String[] labels = values.toArray(new String[0]);
        new AlertDialog.Builder(this).setTitle("Menu da Deta").setItems(labels, (dialog, index) -> {
            String chosen = labels[index];
            if (chosen.equals("Nova conversa")) startNewConversation();
            else if (chosen.equals("Apagar conversa atual")) confirmDelete(activeConversation());
            else new AlertDialog.Builder(this)
                    .setTitle("Deta 1.1 — base local")
                    .setMessage("Esta versão contém somente interface e histórico local. IA, rede e APIs foram removidas.")
                    .setPositiveButton("Fechar", null).show();
        }).setNegativeButton("Fechar", null).show();
    }

    private void confirmDelete(Conversation c) {
        if (c == null) return;
        new AlertDialog.Builder(this).setTitle("Apagar conversa?")
                .setMessage("A conversa será removida deste dispositivo.")
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Apagar", (dialog, which) -> {
                    history.remove(c);
                    activeId = -1L;
                    saveHistory();
                    renderConversation();
                    if (drawerList != null) renderHistoryList();
                }).show();
    }

    private void openDrawer() {
        closeDrawer();
        drawerOverlay = new FrameLayout(this);
        drawerOverlay.setBackgroundColor(0x99000000);
        drawerOverlay.setClickable(true);
        drawerOverlay.setOnClickListener(view -> closeDrawer());
        LinearLayout panel = column();
        panel.setBackgroundColor(PANEL);
        panel.setPadding(dp(18), dp(23), dp(16), dp(14));
        panel.setElevation(dp(12));
        panel.setOnClickListener(view -> {});

        LinearLayout header = row();
        header.addView(text("Conversas", 23, FG, true), new LinearLayout.LayoutParams(0, dp(46), 1f));
        header.addView(button("×", "Fechar menu", FIELD, FG, this::closeDrawer), lp(42, 42));
        panel.addView(header, lp(-1, 48));

        TextView create = text("+   Nova conversa", 15, BG, true);
        create.setPadding(dp(14), 0, dp(14), 0);
        create.setBackground(shape(ACCENT, 17, 0));
        create.setClickable(true);
        create.setFocusable(true);
        create.setContentDescription("Criar conversa");
        create.setOnClickListener(view -> startNewConversation());
        LinearLayout.LayoutParams cp = lp(-1, 48);
        margins(cp, 0, 18, 0, 17);
        panel.addView(create, cp);

        drawerSearch = new EditText(this);
        drawerSearch.setHint("Buscar conversas");
        drawerSearch.setTextColor(FG);
        drawerSearch.setHintTextColor(MUTED);
        drawerSearch.setSingleLine(true);
        drawerSearch.setTextSize(15);
        drawerSearch.setPadding(dp(12), 0, dp(12), 0);
        drawerSearch.setBackground(shape(FIELD, 14, BORDER));
        drawerSearch.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        LinearLayout.LayoutParams sp = lp(-1, 46);
        margins(sp, 0, 0, 0, 20);
        panel.addView(drawerSearch, sp);
        panel.addView(text("Recentes", 14, MUTED, true), lp(-1, 26));

        ScrollView listScroll = new ScrollView(this);
        listScroll.setVerticalScrollBarEnabled(false);
        drawerList = column();
        drawerList.setPadding(0, dp(5), 0, dp(8));
        listScroll.addView(drawerList, new ScrollView.LayoutParams(-1, -2));
        panel.addView(listScroll, new LinearLayout.LayoutParams(-1, 0, 1f));
        LinearLayout.LayoutParams fp = lp(-1, 34);
        margins(fp, 0, 10, 0, 0);
        panel.addView(text("Base local · sem IA", 12, MUTED, false), fp);

        int width = getResources().getDisplayMetrics().widthPixels;
        int panelWidth = Math.max(dp(240), Math.min(dp(330), width - dp(40)));
        drawerOverlay.addView(panel, new FrameLayout.LayoutParams(panelWidth, -1, Gravity.START));
        root.addView(drawerOverlay, new FrameLayout.LayoutParams(-1, -1));
        drawerSearch.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { renderHistoryList(); }
            @Override public void afterTextChanged(Editable s) {}
        });
        renderHistoryList();
    }

    private void closeDrawer() {
        if (drawerOverlay != null && root != null) root.removeView(drawerOverlay);
        drawerOverlay = null;
        drawerList = null;
        drawerSearch = null;
    }

    private void renderHistoryList() {
        if (drawerList == null) return;
        drawerList.removeAllViews();
        String query = drawerSearch == null ? "" : drawerSearch.getText().toString().trim().toLowerCase(Locale.ROOT);
        int count = 0;
        for (Conversation c : new ArrayList<>(history)) {
            String title = c.title == null ? "Nova conversa" : c.title;
            if (!query.isEmpty() && !title.toLowerCase(Locale.ROOT).contains(query)) continue;
            count++;
            TextView item = text(title, 15, c.id == activeId ? FG : MUTED, false);
            item.setPadding(dp(12), dp(10), dp(12), dp(10));
            item.setSingleLine(true);
            item.setEllipsize(android.text.TextUtils.TruncateAt.END);
            item.setBackgroundResource(android.R.drawable.list_selector_background);
            item.setClickable(true);
            item.setFocusable(true);
            item.setContentDescription("Abrir conversa: " + title);
            LinearLayout.LayoutParams ip = lp(-1, 46);
            margins(ip, 0, 2, 0, 2);
            drawerList.addView(item, ip);
            item.setOnClickListener(view -> {
                activeId = c.id;
                closeDrawer();
                renderConversation();
            });
            item.setOnLongClickListener(view -> {
                new AlertDialog.Builder(this).setTitle("Apagar conversa?")
                        .setMessage(title).setNegativeButton("Cancelar", null)
                        .setPositiveButton("Apagar", (dialog, which) -> {
                            history.remove(c);
                            if (activeId == c.id) activeId = -1L;
                            saveHistory();
                            renderHistoryList();
                            renderConversation();
                        }).show();
                return true;
            });
        }
        if (count == 0) {
            TextView empty = text(query.isEmpty() ? "Nenhuma conversa salva." : "Nenhum resultado.", 14, MUTED, false);
            empty.setPadding(dp(10), dp(12), dp(10), dp(12));
            drawerList.addView(empty, lp(-1, -2));
        }
    }

    private void loadHistory() {
        history.clear();
        String raw = getSharedPreferences(PREFS, MODE_PRIVATE).getString(HISTORY_KEY, "[]");
        try {
            JSONArray array = new JSONArray(raw);
            for (int i = 0; i < array.length() && i < MAX_CONVERSATIONS; i++) {
                JSONObject object = array.optJSONObject(i);
                if (object == null) continue;
                long id = object.optLong("id", -1L);
                if (id < 0) continue;
                Conversation c = new Conversation(id, object.optString("title", "Nova conversa"));
                JSONArray messages = object.optJSONArray("messages");
                if (messages != null) {
                    for (int j = 0; j < messages.length() && j < MAX_MESSAGES; j++) {
                        String value = messages.optString(j, "");
                        if (!value.trim().isEmpty()) c.messages.add(value);
                    }
                }
                history.add(c);
            }
        } catch (JSONException ignored) {
            history.clear();
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove(HISTORY_KEY).apply();
        }
    }

    private void saveHistory() {
        JSONArray array = new JSONArray();
        for (Conversation c : history) {
            JSONObject object = new JSONObject();
            try {
                object.put("id", c.id);
                object.put("title", c.title);
                JSONArray messages = new JSONArray();
                for (String message : c.messages) messages.put(message);
                object.put("messages", messages);
                array.put(object);
            } catch (JSONException ignored) {
            }
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(HISTORY_KEY, array.toString()).apply();
    }
}
