package app.deta.mobile;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final int BLACK = Color.rgb(0, 0, 0);
    private static final int PANEL = Color.rgb(25, 25, 27);
    private static final int SURFACE = Color.rgb(43, 43, 46);
    private static final int SURFACE_LIGHT = Color.rgb(58, 58, 62);
    private static final int WHITE = Color.rgb(245, 245, 247);
    private static final int MUTED = Color.rgb(163, 163, 170);
    private static final int ACCENT = Color.rgb(169, 181, 255);

    private FrameLayout root;
    private FrameLayout drawerLayer;
    private LinearLayout feed;
    private LinearLayout welcome;
    private EditText composer;
    private ScrollView conversationScroll;
    private boolean conversationStarted;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BLACK);
        getWindow().setNavigationBarColor(BLACK);
        getWindow().getDecorView().setSystemUiVisibility(0);
        buildScreen();
    }

    private void buildScreen() {
        root = new FrameLayout(this);
        root.setBackgroundColor(BLACK);

        LinearLayout main = new LinearLayout(this);
        main.setOrientation(LinearLayout.VERTICAL);
        main.setBackgroundColor(BLACK);
        root.addView(main, new FrameLayout.LayoutParams(-1, -1));

        main.addView(createTopBar(), new LinearLayout.LayoutParams(-1, dp(76)));

        FrameLayout content = new FrameLayout(this);
        LinearLayout.LayoutParams contentParams = new LinearLayout.LayoutParams(-1, 0, 1f);
        contentParams.bottomMargin = dp(4);
        main.addView(content, contentParams);

        conversationScroll = new ScrollView(this);
        conversationScroll.setFillViewport(true);
        conversationScroll.setClipToPadding(false);
        conversationScroll.setVerticalScrollBarEnabled(false);
        feed = new LinearLayout(this);
        feed.setOrientation(LinearLayout.VERTICAL);
        feed.setPadding(dp(18), dp(18), dp(18), dp(18));
        conversationScroll.addView(feed, new ScrollView.LayoutParams(-1, -2));
        content.addView(conversationScroll, new FrameLayout.LayoutParams(-1, -1));

        welcome = createWelcome();
        FrameLayout.LayoutParams welcomeParams = new FrameLayout.LayoutParams(-1, -2, Gravity.CENTER);
        welcomeParams.leftMargin = dp(20);
        welcomeParams.rightMargin = dp(20);
        content.addView(welcome, welcomeParams);

        main.addView(createComposer(), new LinearLayout.LayoutParams(-1, -2));

        drawerLayer = createDrawer();
        drawerLayer.setVisibility(View.GONE);
        root.addView(drawerLayer, new FrameLayout.LayoutParams(-1, -1));

        setContentView(root);
        refreshConversationState();
    }

    private View createTopBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(18), dp(8), dp(18), dp(8));

        TextView menu = circleButton("☰", "Abrir menu");
        bar.addView(menu, new LinearLayout.LayoutParams(dp(48), dp(48)));
        menu.setOnClickListener(v -> toggleDrawer(true));

        TextView brand = text("✦  Deta", 19, WHITE, true);
        brand.setGravity(Gravity.CENTER);
        brand.setBackground(rounded(SURFACE, 48));
        LinearLayout.LayoutParams brandParams = new LinearLayout.LayoutParams(0, dp(48), 1f);
        brandParams.setMargins(dp(12), 0, dp(12), 0);
        bar.addView(brand, brandParams);

        TextView newChat = circleButton("＋", "Nova conversa");
        bar.addView(newChat, new LinearLayout.LayoutParams(dp(48), dp(48)));
        newChat.setOnClickListener(v -> clearConversation());

        return bar;
    }

    private LinearLayout createWelcome() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setGravity(Gravity.CENTER_HORIZONTAL);
        panel.setPadding(dp(8), dp(14), dp(8), dp(14));

        TextView mark = text("✦", 36, ACCENT, true);
        mark.setGravity(Gravity.CENTER);
        mark.setBackground(rounded(PANEL, 26));
        LinearLayout.LayoutParams markParams = new LinearLayout.LayoutParams(dp(68), dp(68));
        markParams.bottomMargin = dp(22);
        panel.addView(mark, markParams);

        TextView title = text("O que vamos criar?", 27, WHITE, true);
        title.setGravity(Gravity.CENTER);
        panel.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView subtitle = text("Transforme sua ideia em um projeto.", 15, MUTED, false);
        subtitle.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams subtitleParams = new LinearLayout.LayoutParams(-1, -2);
        subtitleParams.topMargin = dp(10);
        subtitleParams.bottomMargin = dp(26);
        panel.addView(subtitle, subtitleParams);

        panel.addView(suggestion("◇", "Criar um jogo", "Planejar mecânicas, fases e sistemas"), new LinearLayout.LayoutParams(-1, -2));
        panel.addView(suggestion("▦", "Aplicativo social", "Perfis, conversas e comunidades"), new LinearLayout.LayoutParams(-1, -2));
        panel.addView(suggestion("⌘", "Revisar código", "Encontrar falhas e propor correções"), new LinearLayout.LayoutParams(-1, -2));

        TextView note = text("A interface está pronta; a geração automática será conectada em uma próxima etapa.", 12, MUTED, false);
        note.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams noteParams = new LinearLayout.LayoutParams(-1, -2);
        noteParams.topMargin = dp(18);
        panel.addView(note, noteParams);
        return panel;
    }

    private View suggestion(String symbol, String titleText, String detailText) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(dp(14), dp(12), dp(12), dp(12));
        card.setBackground(rounded(PANEL, 18));
        LinearLayout.LayoutParams outer = new LinearLayout.LayoutParams(-1, -2);
        outer.setMargins(0, dp(5), 0, dp(5));
        card.setLayoutParams(outer);

        TextView icon = text(symbol, 21, ACCENT, true);
        icon.setGravity(Gravity.CENTER);
        card.addView(icon, new LinearLayout.LayoutParams(dp(34), dp(34)));

        LinearLayout labels = new LinearLayout(this);
        labels.setOrientation(LinearLayout.VERTICAL);
        labels.setPadding(dp(10), 0, 0, 0);
        card.addView(labels, new LinearLayout.LayoutParams(0, -2, 1f));
        labels.addView(text(titleText, 15, WHITE, true));
        TextView detail = text(detailText, 12, MUTED, false);
        LinearLayout.LayoutParams detailParams = new LinearLayout.LayoutParams(-1, -2);
        detailParams.topMargin = dp(3);
        labels.addView(detail, detailParams);

        TextView arrow = text("›", 24, MUTED, false);
        card.addView(arrow);

        card.setClickable(true);
        card.setFocusable(true);
        card.setOnClickListener(v -> {
            composer.setText(titleText + ": ");
            composer.setSelection(composer.length());
            composer.requestFocus();
            android.view.inputmethod.InputMethodManager imm =
                (android.view.inputmethod.InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (imm != null) imm.showSoftInput(composer, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT);
        });
        return card;
    }

    private View createComposer() {
        LinearLayout wrapper = new LinearLayout(this);
        wrapper.setOrientation(LinearLayout.VERTICAL);
        wrapper.setPadding(dp(16), dp(8), dp(16), dp(12));

        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.HORIZONTAL);
        box.setGravity(Gravity.CENTER_VERTICAL);
        box.setPadding(dp(8), dp(7), dp(8), dp(7));
        box.setBackground(rounded(SURFACE, 34));
        wrapper.addView(box, new LinearLayout.LayoutParams(-1, -2));

        TextView attach = text("＋", 28, WHITE, false);
        attach.setGravity(Gravity.CENTER);
        box.addView(attach, new LinearLayout.LayoutParams(dp(42), dp(44)));
        attach.setOnClickListener(v -> Toast.makeText(this, "Anexos serão adicionados em uma próxima versão.", Toast.LENGTH_SHORT).show());

        composer = new EditText(this);
        composer.setTextColor(WHITE);
        composer.setHintTextColor(MUTED);
        composer.setHint("Descreva sua ideia para a Deta");
        composer.setTextSize(16);
        composer.setPadding(dp(6), dp(5), dp(6), dp(5));
        composer.setBackgroundColor(Color.TRANSPARENT);
        composer.setMinLines(1);
        composer.setMaxLines(4);
        composer.setSingleLine(false);
        composer.setInputType(android.text.InputType.TYPE_CLASS_TEXT
            | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
            | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        composer.setImeOptions(EditorInfo.IME_ACTION_SEND);
        box.addView(composer, new LinearLayout.LayoutParams(0, -2, 1f));
        composer.setOnEditorActionListener((view, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                sendPrompt();
                return true;
            }
            return false;
        });

        TextView send = circleButton("↑", "Enviar mensagem");
        send.setTextSize(24);
        send.setTextColor(BLACK);
        send.setBackground(rounded(ACCENT, 30));
        box.addView(send, new LinearLayout.LayoutParams(dp(43), dp(43)));
        send.setOnClickListener(v -> sendPrompt());

        TextView footnote = text("As mensagens desta versão ficam apenas nesta sessão.", 11, MUTED, false);
        footnote.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams footParams = new LinearLayout.LayoutParams(-1, -2);
        footParams.topMargin = dp(7);
        wrapper.addView(footnote, footParams);

        return wrapper;
    }

    private FrameLayout createDrawer() {
        FrameLayout layer = new FrameLayout(this);
        layer.setBackgroundColor(0x99000000);
        layer.setClickable(true);
        layer.setOnClickListener(v -> toggleDrawer(false));

        LinearLayout drawer = new LinearLayout(this);
        drawer.setOrientation(LinearLayout.VERTICAL);
        drawer.setPadding(dp(20), dp(30), dp(16), dp(18));
        drawer.setBackgroundColor(PANEL);
        FrameLayout.LayoutParams drawerParams = new FrameLayout.LayoutParams(dp(310), -1, Gravity.START);
        layer.addView(drawer, drawerParams);
        drawer.setOnClickListener(v -> { });

        LinearLayout titleRow = new LinearLayout(this);
        titleRow.setOrientation(LinearLayout.HORIZONTAL);
        titleRow.setGravity(Gravity.CENTER_VERTICAL);
        drawer.addView(titleRow, new LinearLayout.LayoutParams(-1, dp(54)));
        TextView title = text("Deta", 25, WHITE, true);
        titleRow.addView(title, new LinearLayout.LayoutParams(0, -2, 1f));
        TextView close = circleButton("×", "Fechar menu");
        titleRow.addView(close, new LinearLayout.LayoutParams(dp(42), dp(42)));
        close.setOnClickListener(v -> toggleDrawer(false));

        EditText search = new EditText(this);
        search.setSingleLine(true);
        search.setTextSize(15);
        search.setTextColor(WHITE);
        search.setHintTextColor(MUTED);
        search.setHint("⌕  Buscar projetos");
        search.setPadding(dp(14), 0, dp(14), 0);
        search.setBackground(rounded(SURFACE, 15));
        LinearLayout.LayoutParams searchParams = new LinearLayout.LayoutParams(-1, dp(48));
        searchParams.topMargin = dp(20);
        searchParams.bottomMargin = dp(22);
        drawer.addView(search, searchParams);

        addDrawerItem(drawer, "⌂", "Início", () -> toggleDrawer(false));
        addDrawerItem(drawer, "＋", "Novo projeto", () -> {
            toggleDrawer(false);
            composer.setText("Novo projeto: ");
            composer.setSelection(composer.length());
            composer.requestFocus();
        });
        addDrawerItem(drawer, "▦", "Biblioteca", () -> {
            toggleDrawer(false);
            Toast.makeText(this, "A biblioteca será integrada em uma próxima versão.", Toast.LENGTH_SHORT).show();
        });

        View divider = new View(this);
        divider.setBackgroundColor(SURFACE_LIGHT);
        LinearLayout.LayoutParams dividerParams = new LinearLayout.LayoutParams(-1, dp(1));
        dividerParams.setMargins(0, dp(24), 0, dp(24));
        drawer.addView(divider, dividerParams);

        drawer.addView(text("Recentes", 16, WHITE, true));
        TextView empty = text("Suas conversas aparecerão aqui quando você começar.", 14, MUTED, false);
        empty.setGravity(Gravity.START);
        LinearLayout.LayoutParams emptyParams = new LinearLayout.LayoutParams(-1, -2);
        emptyParams.topMargin = dp(12);
        drawer.addView(empty, emptyParams);

        View spacer = new View(this);
        drawer.addView(spacer, new LinearLayout.LayoutParams(1, 0, 1f));

        TextView footer = text("DETA  ·  ESPAÇO DE CRIAÇÃO", 11, MUTED, true);
        footer.setGravity(Gravity.CENTER_VERTICAL);
        drawer.addView(footer, new LinearLayout.LayoutParams(-1, dp(36)));
        return layer;
    }

    private void addDrawerItem(LinearLayout drawer, String symbol, String label, Runnable action) {
        LinearLayout item = new LinearLayout(this);
        item.setOrientation(LinearLayout.HORIZONTAL);
        item.setGravity(Gravity.CENTER_VERTICAL);
        item.setPadding(dp(10), 0, dp(10), 0);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(48));
        params.bottomMargin = dp(4);
        drawer.addView(item, params);

        TextView icon = text(symbol, 21, ACCENT, false);
        icon.setGravity(Gravity.CENTER);
        item.addView(icon, new LinearLayout.LayoutParams(dp(36), dp(42)));
        TextView labelView = text(label, 16, WHITE, false);
        LinearLayout.LayoutParams labelParams = new LinearLayout.LayoutParams(-1, -2);
        labelParams.leftMargin = dp(8);
        item.addView(labelView, labelParams);
        item.setBackground(rounded(SURFACE, 14));
        item.setClickable(true);
        item.setFocusable(true);
        item.setOnClickListener(v -> action.run());
    }

    private void sendPrompt() {
        String message = composer.getText().toString().trim();
        if (message.isEmpty()) {
            Toast.makeText(this, "Escreva uma ideia primeiro.", Toast.LENGTH_SHORT).show();
            return;
        }

        if (!conversationStarted) {
            conversationStarted = true;
            welcome.setVisibility(View.GONE);
        }

        LinearLayout userBlock = new LinearLayout(this);
        userBlock.setOrientation(LinearLayout.VERTICAL);
        userBlock.setGravity(Gravity.END);
        LinearLayout.LayoutParams userBlockParams = new LinearLayout.LayoutParams(-1, -2);
        userBlockParams.bottomMargin = dp(18);
        feed.addView(userBlock, userBlockParams);

        TextView userLabel = text("Você", 12, MUTED, true);
        userBlock.addView(userLabel);
        TextView bubble = text(message, 16, WHITE, false);
        bubble.setPadding(dp(15), dp(12), dp(15), dp(12));
        bubble.setBackground(rounded(SURFACE, 20));
        LinearLayout.LayoutParams bubbleParams = new LinearLayout.LayoutParams(-2, -2);
        bubbleParams.topMargin = dp(5);
        bubble.setMaxWidth(getResources().getDisplayMetrics().widthPixels - dp(76));
        userBlock.addView(bubble, bubbleParams);

        LinearLayout answerBlock = new LinearLayout(this);
        answerBlock.setOrientation(LinearLayout.VERTICAL);
        answerBlock.setGravity(Gravity.START);
        LinearLayout.LayoutParams answerParams = new LinearLayout.LayoutParams(-1, -2);
        answerParams.bottomMargin = dp(20);
        feed.addView(answerBlock, answerParams);
        TextView assistantLabel = text("✦ Deta", 13, ACCENT, true);
        answerBlock.addView(assistantLabel);
        TextView answer = text(
            "Recebi sua ideia. Esta versão já inclui a interface e o núcleo experimental, mas a geração automática de projetos ainda não está conectada ao aplicativo.",
            15, WHITE, false
        );
        answer.setPadding(dp(2), dp(8), dp(2), dp(4));
        answerBlock.addView(answer);

        composer.setText("");
        conversationScroll.post(() -> conversationScroll.fullScroll(View.FOCUS_DOWN));
    }

    private void refreshConversationState() {
        welcome.setVisibility(conversationStarted ? View.GONE : View.VISIBLE);
    }

    private void clearConversation() {
        feed.removeAllViews();
        conversationStarted = false;
        composer.setText("");
        refreshConversationState();
        toggleDrawer(false);
    }

    private void toggleDrawer(boolean open) {
        drawerLayer.setVisibility(open ? View.VISIBLE : View.GONE);
    }

    private TextView circleButton(String label, String description) {
        TextView view = text(label, 21, WHITE, true);
        view.setGravity(Gravity.CENTER);
        view.setBackground(rounded(SURFACE, 50));
        view.setContentDescription(description);
        view.setClickable(true);
        view.setFocusable(true);
        return view;
    }

    private TextView text(String value, int sp, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        view.setGravity(Gravity.CENTER_VERTICAL);
        view.setIncludeFontPadding(true);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private GradientDrawable rounded(int color, int radiusDp) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radiusDp));
        return shape;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
