package com.japa.hypercode;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.japa.hypercode.core.LanguageProfile;
import com.japa.hypercode.core.StarterAssistant;

import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int BG = Color.rgb(7, 12, 22);
    private static final int SURFACE = Color.rgb(16, 25, 41);
    private static final int SURFACE_2 = Color.rgb(21, 33, 53);
    private static final int BORDER = Color.rgb(37, 54, 78);
    private static final int TEXT = Color.rgb(239, 245, 255);
    private static final int MUTED = Color.rgb(139, 158, 186);
    private static final int BLUE = Color.rgb(93, 169, 255);
    private static final int CYAN = Color.rgb(106, 220, 226);
    private static final int GREEN = Color.rgb(91, 213, 166);
    private static final int AMBER = Color.rgb(255, 190, 108);

    private final ArrayList<ChatMessage> messages = new ArrayList<>();
    private SharedPreferences preferences;
    private String conversationLanguage;
    private String selectedLanguage = "auto";
    private int selectedTab = 0;

    private LinearLayout root;
    private FrameLayout contentHost;
    private LinearLayout composerPanel;
    private LinearLayout transcript;
    private ScrollView chatScroll;
    private EditText composer;
    private TextView sendButton;
    private final TextView[] navItems = new TextView[3];

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("hypercode", MODE_PRIVATE);
        conversationLanguage = preferences.getString("conversation_language", null);
        selectedLanguage = preferences.getString("selected_language", "auto");
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(0);
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);

        messages.add(new ChatMessage(
            "HYPERCODE",
            "Interface de desenvolvimento pronta. As sete redes universais, a comunicação mútua e o núcleo coletivo estão documentados no projeto, mas os pesos PyTorch ainda não estão integrados a este APK. As respostas desta versão são avisos de estado, não inferência neural.",
            false
        ));
        buildShell();
        showTab(0);
    }

    private void buildShell() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackground(new GradientDrawable(
            GradientDrawable.Orientation.TOP_BOTTOM,
            new int[]{Color.rgb(10, 19, 34), BG, BG}
        ));
        root.setPadding(dp(18), dp(10), dp(18), dp(8));

        root.addView(buildHeader(), new LinearLayout.LayoutParams(-1, -2));

        contentHost = new FrameLayout(this);
        LinearLayout.LayoutParams contentParams = new LinearLayout.LayoutParams(-1, 0, 1);
        contentParams.topMargin = dp(12);
        root.addView(contentHost, contentParams);

        composerPanel = buildComposer();
        root.addView(composerPanel, new LinearLayout.LayoutParams(-1, -2));
        root.addView(buildBottomNavigation(), new LinearLayout.LayoutParams(-1, dp(62)));

        setContentView(root);
    }

    private View buildHeader() {
        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setOrientation(LinearLayout.HORIZONTAL);

        TextView mark = text("H", 21, Color.WHITE, true);
        mark.setGravity(Gravity.CENTER);
        mark.setBackground(gradient(BLUE, CYAN, 15));
        header.addView(mark, new LinearLayout.LayoutParams(dp(44), dp(44)));

        LinearLayout identity = new LinearLayout(this);
        identity.setOrientation(LinearLayout.VERTICAL);
        identity.setPadding(dp(11), 0, 0, 0);
        TextView title = text("HYPERCODE", 17, TEXT, true);
        title.setLetterSpacing(0.08f);
        identity.addView(title);
        TextView subtitle = text("UNIVERSAL INTELLIGENCE", 9, MUTED, true);
        subtitle.setLetterSpacing(0.12f);
        LinearLayout.LayoutParams subParams = new LinearLayout.LayoutParams(-2, -2);
        subParams.topMargin = dp(3);
        identity.addView(subtitle, subParams);
        header.addView(identity, new LinearLayout.LayoutParams(0, -2, 1));

        TextView status = text("DEV", 10, CYAN, true);
        status.setGravity(Gravity.CENTER);
        status.setPadding(dp(11), dp(7), dp(11), dp(7));
        status.setBackground(outline(SURFACE_2, CYAN, 30));
        status.setContentDescription("Build de desenvolvimento");
        header.addView(status);

        TextView menu = text("⋮", 24, TEXT, true);
        menu.setGravity(Gravity.CENTER);
        menu.setBackground(rippleShape(SURFACE_2, 14));
        menu.setOnClickListener(this::showMenu);
        LinearLayout.LayoutParams menuParams = new LinearLayout.LayoutParams(dp(42), dp(42));
        menuParams.leftMargin = dp(7);
        header.addView(menu, menuParams);
        return header;
    }

    private void showMenu(View anchor) {
        PopupMenu popup = new PopupMenu(this, anchor);
        popup.getMenu().add("Nova conversa").setOnMenuItemClickListener(item -> {
            clearConversation();
            return true;
        });
        popup.getMenu().add("Arquitetura").setOnMenuItemClickListener(item -> {
            showTab(1);
            return true;
        });
        popup.getMenu().add("Sobre o HyperCode").setOnMenuItemClickListener(item -> {
            showTab(2);
            return true;
        });
        popup.show();
    }

    private LinearLayout buildComposer() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(11), dp(10), dp(11), dp(9));
        panel.setBackground(outline(SURFACE, BORDER, 18));

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.BOTTOM);

        composer = new EditText(this);
        composer.setTextColor(TEXT);
        composer.setHintTextColor(MUTED);
        composer.setHint("Pergunte sobre arquitetura ou código...");
        composer.setTextSize(14);
        composer.setPadding(dp(12), dp(10), dp(12), dp(10));
        composer.setMinLines(1);
        composer.setMaxLines(4);
        composer.setSingleLine(false);
        composer.setBackground(round(Color.TRANSPARENT, 12));
        composer.setInputType(
            android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE
                | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        );
        composer.setImeOptions(EditorInfo.IME_ACTION_SEND | EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        row.addView(composer, new LinearLayout.LayoutParams(0, -2, 1));

        sendButton = text("↑", 25, Color.WHITE, true);
        sendButton.setGravity(Gravity.CENTER);
        sendButton.setBackground(gradient(BLUE, Color.rgb(62, 127, 226), 14));
        sendButton.setContentDescription("Enviar mensagem");
        sendButton.setOnClickListener(v -> sendMessage());
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(dp(48), dp(48));
        sendParams.leftMargin = dp(8);
        row.addView(sendButton, sendParams);
        panel.addView(row);

        TextView note = text("MODO DE DESENVOLVIMENTO  ·  ENGINE NEURAL NÃO CONECTADA", 9, MUTED, true);
        note.setLetterSpacing(0.035f);
        LinearLayout.LayoutParams noteParams = new LinearLayout.LayoutParams(-1, -2);
        noteParams.topMargin = dp(6);
        panel.addView(note, noteParams);

        composer.addTextChangedListener(new android.text.TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                boolean active = s != null && s.toString().trim().length() > 0;
                sendButton.setAlpha(active ? 1.0f : 0.55f);
            }

            @Override
            public void afterTextChanged(android.text.Editable s) {
            }
        });

        composer.setOnEditorActionListener((view, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                sendMessage();
                return true;
            }
            return false;
        });
        return panel;
    }

    private View buildBottomNavigation() {
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(0, dp(7), 0, 0);

        String[] labels = {"CHAT", "ARQUITETURA", "AJUSTES"};
        for (int i = 0; i < labels.length; i++) {
            final int tab = i;
            TextView item = text(labels[i], 10, MUTED, true);
            item.setGravity(Gravity.CENTER);
            item.setBackground(round(Color.TRANSPARENT, 13));
            item.setOnClickListener(v -> showTab(tab));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(46), 1);
            if (i > 0) params.leftMargin = dp(5);
            nav.addView(item, params);
            navItems[i] = item;
        }
        return nav;
    }

    private void showTab(int tab) {
        selectedTab = tab;
        contentHost.removeAllViews();
        for (int i = 0; i < navItems.length; i++) {
            boolean selected = i == tab;
            navItems[i].setTextColor(selected ? TEXT : MUTED);
            navItems[i].setBackground(selected ? outline(SURFACE_2, BORDER, 13) : round(Color.TRANSPARENT, 13));
        }

        if (tab == 0) {
            composerPanel.setVisibility(View.VISIBLE);
            contentHost.addView(buildChatPage(), new FrameLayout.LayoutParams(-1, -1));
        } else {
            composerPanel.setVisibility(View.GONE);
            View page = tab == 1 ? buildArchitecturePage() : buildSettingsPage();
            contentHost.addView(page, new FrameLayout.LayoutParams(-1, -1));
            hideKeyboard();
        }
    }

    private View buildChatPage() {
        chatScroll = new ScrollView(this);
        chatScroll.setFillViewport(false);
        chatScroll.setClipToPadding(false);
        chatScroll.setVerticalScrollBarEnabled(false);

        LinearLayout page = pageColumn();
        page.addView(buildChatHero());
        page.addView(buildEngineNotice(), topSpace(11));
        page.addView(buildQuickPrompts(), topSpace(14));
        page.addView(buildNetworkOverview(), topSpace(14));

        TextView conversationTitle = sectionTitle("CONVERSA");
        page.addView(conversationTitle, topSpace(18));

        transcript = new LinearLayout(this);
        transcript.setOrientation(LinearLayout.VERTICAL);
        page.addView(transcript, topSpace(5));
        for (ChatMessage message : messages) addMessageBubble(message);

        chatScroll.addView(page);
        chatScroll.post(() -> chatScroll.fullScroll(View.FOCUS_DOWN));
        return chatScroll;
    }

    private View buildChatHero() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(17), dp(18), dp(17), dp(17));
        card.setBackground(new GradientDrawable(
            GradientDrawable.Orientation.TL_BR,
            new int[]{Color.rgb(21, 47, 78), Color.rgb(16, 30, 50), Color.rgb(17, 27, 44)}
        ));
        GradientDrawable shape = (GradientDrawable) card.getBackground();
        shape.setCornerRadius(dp(20));
        shape.setStroke(dp(1), Color.rgb(48, 82, 119));

        TextView eyebrow = text("HYPER-INTER  /  COLLECTIVE CORE", 9, CYAN, true);
        eyebrow.setLetterSpacing(0.09f);
        card.addView(eyebrow);

        TextView heading = text("Sete redes.\nUma inteligência coletiva.", 25, TEXT, true);
        heading.setLineSpacing(dp(1), 1.02f);
        LinearLayout.LayoutParams headingParams = new LinearLayout.LayoutParams(-1, -2);
        headingParams.topMargin = dp(11);
        card.addView(heading, headingParams);

        TextView description = text(
            "Uma arquitetura universal com comunicação mútua e síntese no núcleo central.",
            12, Color.rgb(183, 202, 227), false
        );
        description.setLineSpacing(dp(3), 1.0f);
        LinearLayout.LayoutParams descriptionParams = new LinearLayout.LayoutParams(-1, -2);
        descriptionParams.topMargin = dp(9);
        card.addView(description, descriptionParams);

        LinearLayout metrics = new LinearLayout(this);
        metrics.setOrientation(LinearLayout.HORIZONTAL);
        metrics.addView(metric("07", "REDES"), new LinearLayout.LayoutParams(0, -2, 1));
        metrics.addView(metric("10", "ETAPAS"), new LinearLayout.LayoutParams(0, -2, 1));
        metrics.addView(metric("01", "SAÍDA"), new LinearLayout.LayoutParams(0, -2, 1));
        LinearLayout.LayoutParams metricsParams = new LinearLayout.LayoutParams(-1, -2);
        metricsParams.topMargin = dp(17);
        card.addView(metrics, metricsParams);
        return card;
    }

    private View metric(String value, String caption) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        TextView number = text(value, 20, TEXT, true);
        box.addView(number);
        TextView label = text(caption, 9, MUTED, true);
        label.setLetterSpacing(0.08f);
        LinearLayout.LayoutParams labelParams = new LinearLayout.LayoutParams(-2, -2);
        labelParams.topMargin = dp(2);
        box.addView(label, labelParams);
        return box;
    }

    private View buildEngineNotice() {
        LinearLayout notice = new LinearLayout(this);
        notice.setOrientation(LinearLayout.HORIZONTAL);
        notice.setGravity(Gravity.CENTER_VERTICAL);
        notice.setPadding(dp(13), dp(12), dp(13), dp(12));
        notice.setBackground(outline(Color.rgb(42, 32, 24), Color.rgb(102, 73, 43), 15));

        View dot = new View(this);
        dot.setBackground(round(AMBER, 20));
        notice.addView(dot, new LinearLayout.LayoutParams(dp(8), dp(8)));

        LinearLayout labels = new LinearLayout(this);
        labels.setOrientation(LinearLayout.VERTICAL);
        labels.setPadding(dp(10), 0, 0, 0);
        labels.addView(text("ENGINE NEURAL NÃO CONECTADA", 10, AMBER, true));
        TextView detail = text(
            "Este APK ainda não carrega os checkpoints. O chat não simula respostas do modelo.",
            11, Color.rgb(222, 203, 181), false
        );
        detail.setLineSpacing(dp(2), 1.0f);
        LinearLayout.LayoutParams detailParams = new LinearLayout.LayoutParams(-1, -2);
        detailParams.topMargin = dp(4);
        labels.addView(detail, detailParams);
        notice.addView(labels, new LinearLayout.LayoutParams(0, -2, 1));
        return notice;
    }

    private View buildQuickPrompts() {
        LinearLayout block = new LinearLayout(this);
        block.setOrientation(LinearLayout.VERTICAL);
        block.addView(sectionTitle("COMECE POR AQUI"));
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        String[] prompts = {"Arquitetura", "Treinamento", "Código"};
        String[] questions = {
            "Explique a arquitetura das sete redes.",
            "Quais são as etapas do treinamento?",
            "Como estruturar um projeto de código?"
        };
        for (int i = 0; i < prompts.length; i++) {
            final String prompt = questions[i];
            TextView chip = text(prompts[i], 10, Color.rgb(201, 218, 240), true);
            chip.setGravity(Gravity.CENTER);
            chip.setPadding(dp(10), dp(10), dp(10), dp(10));
            chip.setBackground(outline(SURFACE_2, BORDER, 30));
            chip.setOnClickListener(v -> {
                composer.setText(prompt);
                composer.setSelection(composer.getText().length());
                composer.requestFocus();
                ((InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE))
                    .showSoftInput(composer, InputMethodManager.SHOW_IMPLICIT);
            });
            LinearLayout.LayoutParams chipParams = new LinearLayout.LayoutParams(0, dp(38), 1);
            if (i > 0) chipParams.leftMargin = dp(6);
            row.addView(chip, chipParams);
        }
        LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(-1, -2);
        rowParams.topMargin = dp(8);
        block.addView(row, rowParams);
        return block;
    }

    private View buildNetworkOverview() {
        LinearLayout card = cardColumn();
        LinearLayout heading = new LinearLayout(this);
        heading.setOrientation(LinearLayout.HORIZONTAL);
        heading.setGravity(Gravity.CENTER_VERTICAL);
        heading.addView(text("REDE INTERCONECTADA", 10, TEXT, true),
            new LinearLayout.LayoutParams(0, -2, 1));
        heading.addView(text("7 NÓS", 9, CYAN, true));
        card.addView(heading);

        TextView explanation = text(
            "Todos os ramos são universais e recebem o mesmo contexto.",
            11, MUTED, false
        );
        LinearLayout.LayoutParams explanationParams = new LinearLayout.LayoutParams(-1, -2);
        explanationParams.topMargin = dp(5);
        card.addView(explanation, explanationParams);

        LinearLayout grid = new LinearLayout(this);
        grid.setOrientation(LinearLayout.VERTICAL);
        for (int i = 0; i < 7; i += 2) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.addView(networkTile(i + 1), new LinearLayout.LayoutParams(0, dp(51), 1));
            if (i + 1 < 7) {
                View gap = new View(this);
                row.addView(gap, new LinearLayout.LayoutParams(dp(7), 1));
                row.addView(networkTile(i + 2), new LinearLayout.LayoutParams(0, dp(51), 1));
            } else {
                row.addView(new View(this), new LinearLayout.LayoutParams(0, dp(51), 1));
            }
            LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(-1, -2);
            rowParams.topMargin = dp(7);
            grid.addView(row, rowParams);
        }
        LinearLayout.LayoutParams gridParams = new LinearLayout.LayoutParams(-1, -2);
        gridParams.topMargin = dp(11);
        card.addView(grid, gridParams);
        return card;
    }

    private View networkTile(int number) {
        LinearLayout tile = new LinearLayout(this);
        tile.setOrientation(LinearLayout.VERTICAL);
        tile.setGravity(Gravity.CENTER_VERTICAL);
        tile.setPadding(dp(10), dp(7), dp(8), dp(7));
        tile.setBackground(outline(Color.rgb(19, 31, 49), BORDER, 11));

        LinearLayout line = new LinearLayout(this);
        line.setGravity(Gravity.CENTER_VERTICAL);
        TextView id = text(String.format(Locale.ROOT, "N%02d", number), 11, BLUE, true);
        line.addView(id, new LinearLayout.LayoutParams(dp(34), -2));
        TextView state = text("UNIVERSAL", 8, Color.rgb(188, 207, 231), true);
        line.addView(state);
        tile.addView(line);

        TextView info = text("10 camadas · 256", 9, MUTED, false);
        LinearLayout.LayoutParams infoParams = new LinearLayout.LayoutParams(-1, -2);
        infoParams.topMargin = dp(3);
        tile.addView(info, infoParams);
        return tile;
    }

    private View buildArchitecturePage() {
        ScrollView scroll = new ScrollView(this);
        scroll.setVerticalScrollBarEnabled(false);
        LinearLayout page = pageColumn();

        page.addView(pageHeading("Arquitetura", "Visão estrutural da hiper-rede universal."));
        page.addView(buildEngineNotice(), topSpace(12));
        page.addView(buildNetworkOverview(), topSpace(14));

        LinearLayout communication = cardColumn();
        communication.addView(sectionTitle("CAMADA DE COMUNICAÇÃO"));
        communication.addView(text("10 etapas de troca de informação", 16, TEXT, true), topSpace(7));
        communication.addView(text(
            "Em cada etapa, os sete estados participam de atenção mútua. Nenhum ramo é reservado a uma linguagem específica.",
            12, MUTED, false
        ), topSpace(6));
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        for (int i = 0; i < 10; i++) {
            View segment = new View(this);
            segment.setBackground(round(i < 10 ? BLUE : BORDER, 5));
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, dp(6), 1);
            if (i > 0) p.leftMargin = dp(4);
            bar.addView(segment, p);
        }
        communication.addView(bar, topSpace(14));
        page.addView(communication, topSpace(12));

        LinearLayout core = cardColumn();
        core.addView(text("NÚCLEO COLETIVO", 10, CYAN, true));
        core.addView(text("20 × 1.792", 26, TEXT, true), topSpace(6));
        core.addView(text(
            "Recebe a concatenação das sete representações e produz a saída coletiva única.",
            12, MUTED, false
        ), topSpace(5));
        TextView pending = text("PESOS NÃO INTEGRADOS AO APK", 9, AMBER, true);
        pending.setGravity(Gravity.CENTER);
        pending.setPadding(dp(10), dp(8), dp(10), dp(8));
        pending.setBackground(outline(Color.rgb(42, 32, 24), Color.rgb(102, 73, 43), 10));
        core.addView(pending, topSpace(12));
        page.addView(core, topSpace(12));

        LinearLayout pipeline = cardColumn();
        pipeline.addView(sectionTitle("PIPELINE DE TREINAMENTO"));
        String[][] steps = {
            {"01", "Rede-base universal", "Fundação"},
            {"02", "Sete ramos universais", "Treino individual"},
            {"03", "Núcleo central", "Fusão"},
            {"04", "Comunicação mútua", "Integração"},
            {"05", "Ajuste conjunto", "Refinamento"},
            {"06", "SFT e benchmark", "Avaliação"}
        };
        for (int i = 0; i < steps.length; i++) {
            pipeline.addView(pipelineRow(steps[i][0], steps[i][1], steps[i][2]));
            if (i < steps.length - 1) pipeline.addView(separator());
        }
        page.addView(pipeline, topSpace(12));

        TextView footer = text(
            "A visualização descreve a arquitetura planejada. O APK atual ainda não executa os checkpoints PyTorch.",
            10, MUTED, false
        );
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(dp(10), dp(14), dp(10), dp(18));
        page.addView(footer);
        scroll.addView(page);
        return scroll;
    }

    private View pipelineRow(String number, String title, String subtitle) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, dp(10), 0, dp(10));
        TextView index = text(number, 11, BLUE, true);
        index.setGravity(Gravity.CENTER);
        index.setBackground(outline(Color.rgb(19, 38, 60), BORDER, 9));
        row.addView(index, new LinearLayout.LayoutParams(dp(37), dp(37)));

        LinearLayout labels = new LinearLayout(this);
        labels.setOrientation(LinearLayout.VERTICAL);
        labels.setPadding(dp(11), 0, 0, 0);
        labels.addView(text(title, 12, TEXT, true));
        labels.addView(text(subtitle, 10, MUTED, false), topSpace(3));
        row.addView(labels, new LinearLayout.LayoutParams(0, -2, 1));
        row.addView(text("PLANEJADO", 8, AMBER, true));
        return row;
    }

    private View buildSettingsPage() {
        ScrollView scroll = new ScrollView(this);
        scroll.setVerticalScrollBarEnabled(false);
        LinearLayout page = pageColumn();

        page.addView(pageHeading("Ajustes", "Preferências da interface e informações do build."));

        LinearLayout language = cardColumn();
        language.addView(sectionTitle("IDIOMA DA CONVERSA"));
        language.addView(text("Selecione um idioma ou mantenha a detecção automática.", 11, MUTED, false), topSpace(6));
        String[][] options = {
            {"auto", "Automático"},
            {"pt", "Português"},
            {"en", "English"},
            {"es", "Español"},
            {"fr", "Français"}
        };
        for (String[] option : options) {
            TextView item = text(
                (selectedLanguage.equals(option[0]) ? "●  " : "○  ") + option[1],
                12,
                selectedLanguage.equals(option[0]) ? CYAN : TEXT,
                true
            );
            item.setPadding(dp(12), dp(11), dp(12), dp(11));
            item.setBackground(outline(
                selectedLanguage.equals(option[0]) ? Color.rgb(18, 43, 60) : Color.rgb(19, 29, 46),
                selectedLanguage.equals(option[0]) ? CYAN : BORDER,
                11
            ));
            item.setOnClickListener(v -> {
                selectedLanguage = option[0];
                preferences.edit().putString("selected_language", selectedLanguage).apply();
                if (!"auto".equals(selectedLanguage)) {
                    conversationLanguage = selectedLanguage;
                    preferences.edit().putString("conversation_language", selectedLanguage).apply();
                } else {
                    conversationLanguage = null;
                    preferences.edit().remove("conversation_language").apply();
                }
                showTab(2);
            });
            language.addView(item, topSpace(7));
        }
        page.addView(language, topSpace(13));

        LinearLayout app = cardColumn();
        app.addView(sectionTitle("ESTADO DO APLICATIVO"));
        addInfoRow(app, "Interface", "Desenvolvimento");
        addInfoRow(app, "Inferência neural", "Não conectada");
        addInfoRow(app, "Checkpoint Android", "Não integrado");
        addInfoRow(app, "Arquitetura", "7 redes + núcleo");
        page.addView(app, topSpace(12));

        LinearLayout actions = cardColumn();
        actions.addView(sectionTitle("CONVERSA"));
        TextView clear = actionButton("Limpar histórico", false);
        clear.setOnClickListener(v -> clearConversation());
        actions.addView(clear, topSpace(9));
        page.addView(actions, topSpace(12));

        TextView disclaimer = text(
            "O HyperCode Android é uma interface de desenvolvimento. Esta versão não executa o modelo treinado nem envia suas mensagens a um servidor.",
            10, MUTED, false
        );
        disclaimer.setLineSpacing(dp(3), 1.0f);
        disclaimer.setPadding(dp(4), dp(15), dp(4), dp(20));
        page.addView(disclaimer);

        scroll.addView(page);
        return scroll;
    }

    private void addInfoRow(LinearLayout parent, String key, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, dp(9), 0, dp(9));
        row.addView(text(key, 11, MUTED, false), new LinearLayout.LayoutParams(0, -2, 1));
        row.addView(text(value, 11, TEXT, true));
        parent.addView(row);
        parent.addView(separator());
    }

    private TextView actionButton(String label, boolean primary) {
        TextView button = text(label, 12, primary ? Color.WHITE : Color.rgb(225, 235, 248), true);
        button.setGravity(Gravity.CENTER);
        button.setPadding(dp(14), dp(12), dp(14), dp(12));
        button.setBackground(primary ? gradient(BLUE, Color.rgb(59, 125, 220), 12)
            : outline(SURFACE_2, BORDER, 12));
        return button;
    }

    private View pageHeading(String heading, String subheading) {
        LinearLayout block = new LinearLayout(this);
        block.setOrientation(LinearLayout.VERTICAL);
        block.addView(text(heading, 25, TEXT, true));
        block.addView(text(subheading, 12, MUTED, false), topSpace(5));
        return block;
    }

    private LinearLayout pageColumn() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(0, dp(2), 0, dp(14));
        return page;
    }

    private LinearLayout cardColumn() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(14), dp(14), dp(14));
        card.setBackground(outline(SURFACE, BORDER, 16));
        return card;
    }

    private TextView sectionTitle(String label) {
        TextView view = text(label, 9, MUTED, true);
        view.setLetterSpacing(0.12f);
        return view;
    }

    private View separator() {
        View line = new View(this);
        line.setBackgroundColor(BORDER);
        line.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(1)));
        return line;
    }

    private LinearLayout.LayoutParams topSpace(int value) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.topMargin = dp(value);
        return params;
    }

    private void addMessageBubble(ChatMessage message) {
        LinearLayout bubble = new LinearLayout(this);
        bubble.setOrientation(LinearLayout.VERTICAL);
        bubble.setPadding(dp(13), dp(11), dp(13), dp(11));
        bubble.setBackground(outline(
            message.user ? Color.rgb(22, 49, 78) : SURFACE_2,
            message.user ? Color.rgb(43, 91, 137) : BORDER,
            15
        ));

        TextView speaker = text(
            message.speaker.toUpperCase(Locale.ROOT),
            9,
            message.user ? Color.rgb(157, 207, 255) : CYAN,
            true
        );
        speaker.setLetterSpacing(0.08f);
        bubble.addView(speaker);

        TextView body = text(message.body, 13, TEXT, false);
        body.setTextIsSelectable(true);
        body.setLineSpacing(dp(3), 1.0f);
        bubble.addView(body, topSpace(6));
        bubble.setOnLongClickListener(v -> {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText("HyperCode", message.body));
            Toast.makeText(this, "Mensagem copiada", Toast.LENGTH_SHORT).show();
            return true;
        });

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.topMargin = dp(7);
        if (message.user) {
            params.leftMargin = dp(28);
        } else {
            params.rightMargin = dp(12);
        }
        transcript.addView(bubble, params);
    }

    private void sendMessage() {
        String value = composer.getText().toString().trim();
        if (value.isEmpty()) return;
        if (value.length() > 4000) {
            Toast.makeText(this, "Limite de 4.000 caracteres por mensagem.", Toast.LENGTH_SHORT).show();
            return;
        }

        String language = selectedLanguage;
        if ("auto".equals(language)) {
            if (conversationLanguage == null) conversationLanguage = LanguageProfile.detect(value);
            language = conversationLanguage;
        } else {
            conversationLanguage = language;
        }
        preferences.edit().putString("conversation_language", language).apply();

        messages.add(new ChatMessage("Você", value, true));
        messages.add(new ChatMessage("HYPERCODE · DEV", StarterAssistant.reply(value, language), false));
        composer.setText("");
        hideKeyboard();
        if (selectedTab == 0) {
            showTab(0);
        }
    }

    private void clearConversation() {
        messages.clear();
        messages.add(new ChatMessage(
            "HYPERCODE",
            "Nova conversa iniciada. Esta versão continua em modo de desenvolvimento e não possui inferência neural conectada.",
            false
        ));
        if (composer != null) composer.setText("");
        showTab(0);
    }

    private void hideKeyboard() {
        if (composer == null) return;
        InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        manager.hideSoftInputFromWindow(composer.getWindowToken(), 0);
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setIncludeFontPadding(true);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private GradientDrawable round(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private GradientDrawable outline(int fill, int stroke, int radius) {
        GradientDrawable shape = round(fill, radius);
        shape.setStroke(dp(1), stroke);
        return shape;
    }

    private GradientDrawable gradient(int first, int second, int radius) {
        GradientDrawable shape = new GradientDrawable(
            GradientDrawable.Orientation.LEFT_RIGHT,
            new int[]{first, second}
        );
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private GradientDrawable rippleShape(int color, int radius) {
        return outline(color, BORDER, radius);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class ChatMessage {
        final String speaker;
        final String body;
        final boolean user;

        ChatMessage(String speaker, String body, boolean user) {
            this.speaker = speaker;
            this.body = body;
            this.user = user;
        }
    }
}
