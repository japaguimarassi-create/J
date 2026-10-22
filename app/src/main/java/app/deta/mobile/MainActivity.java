package app.deta.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentResolver;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(8, 9, 13);
    private static final int PANEL = Color.rgb(25, 26, 31);
    private static final int FIELD = Color.rgb(39, 40, 46);
    private static final int BORDER = Color.rgb(57, 58, 66);
    private static final int FG = Color.rgb(244, 244, 247);
    private static final int MUTED = Color.rgb(164, 166, 177);
    private static final int ACCENT = Color.rgb(186, 174, 255);
    private static final int CYAN = Color.rgb(73, 217, 245);
    private static final String PREFS = "deta_creator_v2";
    private static final String HISTORY_KEY = "history";
    private static final String ACTIVE_KEY = "active";
    private static final int SAVE_REQUEST = 742;
    private static final int MAX_CONVERSATIONS = 24;
    private static final int MAX_MESSAGES = 40;

    private final ArrayList<Conversation> history = new ArrayList<>();
    private final ExecutorService generationExecutor = Executors.newSingleThreadExecutor();
    private DetaLocalModel localModel;
    private FrameLayout root;
    private LinearLayout transcript;
    private ScrollView transcriptScroll;
    private EditText composer;
    private FrameLayout drawerOverlay;
    private LinearLayout drawerList;
    private EditText drawerSearch;
    private long activeId = -1L;
    private DetaProjectFactory.Project pendingProject;
    private boolean searchOpen;

    private static final class Message {
        final boolean fromUser;
        String text;
        String projectPrompt;
        String neuralDraft;
        DetaProjectFactory.Project project;

        Message(boolean fromUser, String text) {
            this.fromUser = fromUser;
            this.text = text;
        }
    }

    private static final class Conversation {
        final long id;
        String title;
        long updatedAt;
        final ArrayList<Message> messages = new ArrayList<>();

        Conversation(long id, String title) {
            this.id = id;
            this.title = title;
            this.updatedAt = id;
        }
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Window window = getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(BG);
        window.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        try {
            loadHistory();
            activeId = state == null
                    ? getSharedPreferences(PREFS, MODE_PRIVATE).getLong(ACTIVE_KEY, -1L)
                    : state.getLong(ACTIVE_KEY, -1L);
            if (activeConversation() == null) activeId = -1L;
            buildInterface();
        } catch (RuntimeException exception) {
            showRecovery(exception);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        state.putLong(ACTIVE_KEY, activeId);
        super.onSaveInstanceState(state);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isFinishing()) generationExecutor.shutdownNow();
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

    private void margins(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) {
        params.setMargins(dp(left), dp(top), dp(right), dp(bottom));
    }

    private GradientDrawable shape(int fill, int radius, int stroke) {
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
        view.setIncludeFontPadding(false);
        view.setGravity(Gravity.CENTER_VERTICAL);
        return view;
    }

    private LinearLayout column() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.VERTICAL);
        return view;
    }

    private LinearLayout row() {
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.HORIZONTAL);
        view.setGravity(Gravity.CENTER_VERTICAL);
        return view;
    }

    private TextView button(String glyph, String description, int fill, int color, Runnable action) {
        TextView view = text(glyph, 22, color, false);
        view.setGravity(Gravity.CENTER);
        view.setContentDescription(description);
        view.setBackground(shape(fill, 23, fill == FIELD ? BORDER : 0));
        view.setClickable(true);
        view.setFocusable(true);
        view.setOnClickListener(ignored -> action.run());
        return view;
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
        transcriptScroll.setClipToPadding(false);
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
        bar.addView(button("☰", "Abrir conversas", FIELD, FG, this::openDrawer), lp(46, 46));

        LinearLayout brand = row();
        brand.setPadding(dp(12), 0, dp(17), 0);
        brand.setBackground(shape(PANEL, 24, BORDER));
        TextView logo = text("D", 21, ACCENT, true);
        logo.setGravity(Gravity.CENTER);
        logo.setBackground(shape(Color.rgb(43, 39, 64), 10, 0));
        brand.addView(logo, lp(30, 30));
        TextView title = text("Deta", 18, FG, true);
        LinearLayout.LayoutParams titleParams = lp(-2, -1);
        margins(titleParams, 9, 0, 0, 0);
        brand.addView(title, titleParams);
        LinearLayout.LayoutParams brandParams = lp(-2, 46);
        margins(brandParams, 10, 0, 0, 0);
        bar.addView(brand, brandParams);
        bar.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        bar.addView(button("+", "Nova criação", FIELD, FG, this::startNewConversation), lp(46, 46));
        return bar;
    }

    private View buildComposer() {
        LinearLayout wrapper = column();
        wrapper.setPadding(dp(16), dp(3), dp(16), dp(10));
        LinearLayout field = row();
        field.setPadding(dp(8), dp(7), dp(7), dp(7));
        field.setBackground(shape(FIELD, 26, BORDER));

        TextView add = button("+", "Sugestões de criação", FIELD, FG, this::showCreationOptions);
        add.setBackgroundColor(Color.TRANSPARENT);
        field.addView(add, lp(40, 42));

        composer = new EditText(this);
        composer.setSingleLine(false);
        composer.setMinLines(1);
        composer.setMaxLines(4);
        composer.setTextSize(16);
        composer.setTextColor(FG);
        composer.setHintTextColor(MUTED);
        composer.setHint("Descreva o app ou jogo que quer criar");
        composer.setPadding(dp(8), dp(7), dp(5), dp(7));
        composer.setBackgroundColor(Color.TRANSPARENT);
        composer.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        composer.setImeOptions(EditorInfo.IME_ACTION_SEND | EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        composer.setOnEditorActionListener((view, actionId, event) -> {
            boolean enter = event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER
                    && event.getAction() == KeyEvent.ACTION_DOWN;
            if (actionId == EditorInfo.IME_ACTION_SEND || enter) {
                createFromPrompt();
                return true;
            }
            return false;
        });
        field.addView(composer, new LinearLayout.LayoutParams(0, -2, 1f));
        TextView send = button("↑", "Criar projeto", ACCENT, BG, this::createFromPrompt);
        field.addView(send, lp(42, 42));
        wrapper.addView(field, lp(-1, -2));

        TextView note = text("Modelo neural local · 400 mil parâmetros · sem API de IA", 10, Color.rgb(127, 129, 143), false);
        note.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams noteParams = lp(-1, 18);
        margins(noteParams, 0, 4, 0, 0);
        wrapper.addView(note, noteParams);
        return wrapper;
    }

    private void showCreationOptions() {
        String[] options = {"Criar um jogo", "Criar um app social", "Criar um app utilitário", "Ver informações do modelo"};
        new AlertDialog.Builder(this).setTitle("Criar com a Deta")
                .setItems(options, (dialog, which) -> {
                    if (which == 0) composer.setText("Crie um jogo de reflexos chamado Neon Arena com pontuação e recorde.");
                    else if (which == 1) composer.setText("Crie uma rede social chamada Comunidade Deta com publicações, curtidas e comentários.");
                    else if (which == 2) composer.setText("Crie um app de tarefas chamado Minha Rotina com adicionar, concluir e excluir.");
                    else showModelInfo();
                    if (which < 3) {
                        composer.setSelection(composer.length());
                        composer.requestFocus();
                        showKeyboard(composer);
                    }
                }).setNegativeButton("Fechar", null).show();
    }

    private void showModelInfo() {
        new AlertDialog.Builder(this).setTitle("Modelo Deta local")
                .setMessage("Checkpoint original DetaFiveGroupModel. 400.000 parâmetros em cinco grupos de 80.000. O modelo funciona localmente, sem API de IA hospedada. É um modelo byte-level experimental; por isso, o aplicativo combina a inferência neural com um gerador estruturado que cria projetos jogáveis, sociais e utilitários.")
                .setPositiveButton("Entendi", null).show();
    }

    private void showRecovery(RuntimeException exception) {
        LinearLayout recovery = column();
        recovery.setPadding(dp(24), dp(32), dp(24), dp(24));
        recovery.setBackgroundColor(BG);
        recovery.addView(text("Deta — recuperação", 24, FG, true), lp(-1, 48));
        TextView body = text("A tela encontrou um erro ao iniciar. Os projetos e conversas salvos não foram apagados.", 16, MUTED, false);
        body.setGravity(Gravity.TOP);
        LinearLayout.LayoutParams bodyParams = lp(-1, -2);
        margins(bodyParams, 0, 12, 0, 16);
        recovery.addView(body, bodyParams);
        TextView detail = text(exception.getClass().getSimpleName() + ": " + String.valueOf(exception.getMessage()), 12, MUTED, false);
        detail.setGravity(Gravity.TOP);
        recovery.addView(detail, lp(-1, -2));
        TextView retry = text("Tentar novamente", 16, BG, true);
        retry.setGravity(Gravity.CENTER);
        retry.setBackground(shape(ACCENT, 24, 0));
        retry.setClickable(true);
        LinearLayout.LayoutParams retryParams = lp(-1, 52);
        margins(retryParams, 0, 25, 0, 0);
        recovery.addView(retry, retryParams);
        retry.setOnClickListener(view -> {
            try {
                loadHistory();
                buildInterface();
            } catch (RuntimeException retryError) {
                showRecovery(retryError);
            }
        });
        setContentView(recovery);
    }

    private Conversation activeConversation() {
        for (Conversation conversation : history) if (conversation.id == activeId) return conversation;
        return null;
    }

    private Conversation createConversation() {
        long id = Math.max(System.currentTimeMillis(), history.stream().mapToLong(c -> c.id).max().orElse(0L) + 1L);
        Conversation conversation = new Conversation(id, "Nova criação");
        history.add(0, conversation);
        activeId = id;
        return conversation;
    }

    private void startNewConversation() {
        activeId = -1L;
        closeDrawer();
        if (composer != null) {
            composer.setText("");
            composer.clearFocus();
        }
        saveHistory();
        renderConversation();
    }

    private void createFromPrompt() {
        String prompt = composer.getText().toString().trim();
        if (prompt.isEmpty()) {
            Toast.makeText(this, "Descreva o app ou jogo que quer construir.", Toast.LENGTH_SHORT).show();
            return;
        }
        if (prompt.length() > 3000) {
            Toast.makeText(this, "O pedido deve ter até 3.000 caracteres.", Toast.LENGTH_LONG).show();
            return;
        }
        Conversation conversation = activeConversation();
        if (conversation == null) conversation = createConversation();
        if (conversation.messages.isEmpty()) conversation.title = makeTitle(prompt);
        conversation.updatedAt = System.currentTimeMillis();

        Message userMessage = new Message(true, prompt);
        Message assistantMessage = new Message(false, "Montando o projeto e carregando o modelo neural local…");
        conversation.messages.add(userMessage);
        conversation.messages.add(assistantMessage);
        composer.setText("");
        closeDrawer();
        saveHistory();
        renderConversation();
        hideKeyboard();

        long conversationId = conversation.id;
        generationExecutor.execute(() -> {
            DetaProjectFactory.Project project = null;
            String neuralDraft = "";
            String modelStatus;
            try {
                DetaLocalModel model = getLocalModel();
                neuralDraft = model.generate(prompt, 112, 0.82f, 18, System.nanoTime());
                modelStatus = "Inferência local concluída com o checkpoint de 400.000 parâmetros.";
            } catch (Exception exception) {
                modelStatus = "O modelo neural não pôde ser carregado: " + exception.getClass().getSimpleName()
                        + ". O gerador de projetos continuará disponível.";
            }
            String response;
            try {
                project = DetaProjectFactory.create(prompt);
                response = "Projeto preparado: " + project.title + "\n"
                        + "Tipo: " + project.kind + "\n"
                        + project.summary + "\n\n"
                        + "Arquivos incluídos: " + project.fileList() + "\n\n"
                        + modelStatus + "\n\n"
                        + "O construtor estruturado cria os arquivos executáveis; o rascunho neural é experimental e não foi inserido automaticamente no código final.";
            } catch (Exception exception) {
                response = "Não consegui montar o projeto: " + exception.getMessage();
            }
            DetaProjectFactory.Project finalProject = project;
            String finalDraft = neuralDraft;
            String finalResponse = response;
            runOnUiThread(() -> {
                Conversation targetConversation = findConversation(conversationId);
                if (targetConversation == null) return;
                int index = targetConversation.messages.indexOf(assistantMessage);
                if (index < 0) return;
                assistantMessage.text = finalResponse;
                assistantMessage.neuralDraft = finalDraft;
                if (finalProject != null) {
                    assistantMessage.projectPrompt = prompt;
                    assistantMessage.project = finalProject;
                    pendingProject = finalProject;
                }
                targetConversation.updatedAt = System.currentTimeMillis();
                moveToTop(targetConversation);
                saveHistory();
                if (activeId == conversationId) {
                    renderConversation();
                    transcriptScroll.post(() -> transcriptScroll.fullScroll(View.FOCUS_DOWN));
                }
                if (drawerOverlay != null) renderHistoryList();
            });
        });
    }

    private DetaLocalModel getLocalModel() throws IOException {
        if (localModel != null) return localModel;
        synchronized (this) {
            if (localModel == null) localModel = DetaLocalModel.fromAssets(getAssets());
            return localModel;
        }
    }

    private Conversation findConversation(long id) {
        for (Conversation conversation : history) if (conversation.id == id) return conversation;
        return null;
    }

    private String makeTitle(String prompt) {
        String value = prompt.replaceAll("\\s+", " ").trim();
        if (value.length() > 38) value = value.substring(0, 35).trim() + "...";
        return value.isEmpty() ? "Nova criação" : value;
    }

    private void moveToTop(Conversation conversation) {
        history.remove(conversation);
        history.add(0, conversation);
    }

    private void hideKeyboard() {
        if (composer == null) return;
        InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(composer.getWindowToken(), 0);
        composer.clearFocus();
    }

    private void renderConversation() {
        if (transcript == null) return;
        transcript.removeAllViews();
        Conversation conversation = activeConversation();
        if (conversation == null || conversation.messages.isEmpty()) {
            renderWelcome();
            return;
        }
        for (Message message : conversation.messages) {
            addMessageBubble(message);
        }
    }

    private void renderWelcome() {
        LinearLayout welcome = column();
        welcome.setGravity(Gravity.CENTER_HORIZONTAL);
        welcome.setPadding(dp(4), dp(36), dp(4), dp(18));
        TextView icon = text("D", 34, ACCENT, true);
        icon.setGravity(Gravity.CENTER);
        icon.setBackground(shape(Color.rgb(37, 34, 55), 22, BORDER));
        welcome.addView(icon, lp(68, 68));

        TextView heading = text("O que vamos criar?", 26, FG, true);
        heading.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams headingParams = lp(-1, -2);
        margins(headingParams, 0, 20, 0, 0);
        welcome.addView(heading, headingParams);

        TextView body = text("Descreva o app ou jogo. A Deta usa seu modelo neural local e transforma o pedido em arquivos de projeto.", 15, MUTED, false);
        body.setGravity(Gravity.CENTER);
        body.setLineSpacing(dp(4), 1f);
        LinearLayout.LayoutParams bodyParams = lp(-1, -2);
        margins(bodyParams, 8, 11, 8, 22);
        welcome.addView(body, bodyParams);
        welcome.addView(chip("Criar jogo", "Crie um jogo de reflexos chamado Neon Arena com pontuação e recorde."), lp(-1, 48));
        welcome.addView(chip("Criar app social", "Crie uma rede social chamada Comunidade Deta com publicações, curtidas e comentários."), lp(-1, 48));
        welcome.addView(chip("Criar app utilitário", "Crie um app de tarefas chamado Minha Rotina com adicionar, concluir e excluir."), lp(-1, 48));
        TextView info = text("400.000 parâmetros · 5 grupos · processamento local", 11, Color.rgb(113, 116, 130), false);
        info.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams infoParams = lp(-1, 24);
        margins(infoParams, 0, 18, 0, 0);
        welcome.addView(info, infoParams);
        transcript.addView(welcome, lp(-1, -2));
    }

    private TextView chip(String label, String prompt) {
        TextView chip = text(label, 14, FG, true);
        chip.setGravity(Gravity.CENTER);
        chip.setBackground(shape(PANEL, 16, BORDER));
        chip.setClickable(true);
        chip.setFocusable(true);
        LinearLayout.LayoutParams params = lp(-1, 46);
        margins(params, 0, 5, 0, 5);
        chip.setOnClickListener(view -> {
            composer.setText(prompt);
            composer.setSelection(composer.length());
            composer.requestFocus();
            showKeyboard(composer);
        });
        return chip;
    }

    private void addMessageBubble(Message message) {
        LinearLayout wrapper = column();
        LinearLayout row = row();
        row.setGravity(message.fromUser ? Gravity.RIGHT : Gravity.LEFT);
        LinearLayout.LayoutParams rowParams = lp(-1, -2);
        margins(rowParams, 0, 7, 0, 7);

        if (!message.fromUser) {
            TextView mark = text("D", 15, ACCENT, true);
            mark.setGravity(Gravity.CENTER);
            mark.setBackground(shape(Color.rgb(37, 34, 55), 13, 0));
            LinearLayout.LayoutParams markParams = lp(28, 28);
            margins(markParams, 0, 0, 8, 0);
            row.addView(mark, markParams);
        }

        TextView bubble = text(message.text, 15, FG, false);
        bubble.setGravity(Gravity.TOP);
        bubble.setLineSpacing(dp(3), 1f);
        bubble.setPadding(dp(14), dp(12), dp(14), dp(12));
        bubble.setBackground(shape(message.fromUser ? Color.rgb(40, 41, 48) : PANEL, 19, message.fromUser ? 0 : BORDER));
        bubble.setMaxWidth((int) (getResources().getDisplayMetrics().widthPixels * (message.fromUser ? 0.82f : 0.88f)));
        row.addView(bubble, new LinearLayout.LayoutParams(-2, -2));
        wrapper.addView(row, rowParams);

        if (!message.fromUser && message.project != null) {
            LinearLayout actions = row();
            LinearLayout.LayoutParams actionsParams = lp(-1, 43);
            margins(actionsParams, 36, 0, 0, 4);
            actions.addView(actionButton("Pré-visualizar", () -> showProjectPreview(message.project)), new LinearLayout.LayoutParams(0, dp(38), 1f));
            View spacer = new View(this);
            actions.addView(spacer, lp(8, 1));
            actions.addView(actionButton("Exportar ZIP", () -> exportProject(message.project)), new LinearLayout.LayoutParams(0, dp(38), 1f));
            wrapper.addView(actions, actionsParams);
        }

        if (!message.fromUser && message.neuralDraft != null && !message.neuralDraft.isEmpty()) {
            TextView draftAction = text("Ver rascunho neural local", 12, CYAN, true);
            draftAction.setPadding(dp(36), dp(8), dp(8), dp(8));
            draftAction.setClickable(true);
            draftAction.setOnClickListener(view -> showNeuralDraft(message.neuralDraft));
            wrapper.addView(draftAction, lp(-1, 35));
        }
        transcript.addView(wrapper, lp(-1, -2));
    }

    private TextView actionButton(String label, Runnable action) {
        TextView button = text(label, 13, FG, true);
        button.setGravity(Gravity.CENTER);
        button.setBackground(shape(FIELD, 13, BORDER));
        button.setClickable(true);
        button.setFocusable(true);
        button.setOnClickListener(view -> action.run());
        return button;
    }

    private void showNeuralDraft(String draft) {
        ScrollView scroll = new ScrollView(this);
        TextView content = text(draft, 13, FG, false);
        content.setGravity(Gravity.TOP);
        content.setTextIsSelectable(true);
        content.setPadding(dp(14), dp(14), dp(14), dp(14));
        scroll.addView(content);
        new AlertDialog.Builder(this).setTitle("Rascunho do modelo Deta")
                .setView(scroll)
                .setPositiveButton("Copiar", (dialog, which) -> copyText("Rascunho Deta", draft))
                .setNegativeButton("Fechar", null).show();
    }

    private void copyText(String label, String value) {
        ClipboardManager manager = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (manager != null) {
            manager.setPrimaryClip(ClipData.newPlainText(label, value));
            Toast.makeText(this, "Copiado.", Toast.LENGTH_SHORT).show();
        }
    }

    private void showProjectPreview(DetaProjectFactory.Project project) {
        if (project == null) return;
        WebView webView = new WebView(this);
        webView.setBackgroundColor(BG);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        webView.setWebChromeClient(new WebChromeClient());
        webView.loadDataWithBaseURL(null, project.previewHtml(), "text/html", "UTF-8", null);
        int height = Math.min(getResources().getDisplayMetrics().heightPixels - dp(120), dp(620));
        new AlertDialog.Builder(this).setTitle(project.title)
                .setView(webView, dp(320), Math.max(dp(300), height))
                .setPositiveButton("Exportar ZIP", (dialog, which) -> exportProject(project))
                .setNegativeButton("Fechar", null).show();
    }

    private void exportProject(DetaProjectFactory.Project project) {
        if (project == null) return;
        pendingProject = project;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/zip");
        intent.putExtra(Intent.EXTRA_TITLE, slug(project.title) + ".zip");
        try {
            startActivityForResult(intent, SAVE_REQUEST);
        } catch (RuntimeException exception) {
            Toast.makeText(this, "Não foi possível abrir o seletor de arquivos.", Toast.LENGTH_LONG).show();
        }
    }

    private String slug(String value) {
        String result = java.text.Normalizer.normalize(value.toLowerCase(Locale.ROOT), java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "").replaceAll("[^a-z0-9]+", "-").replaceAll("^-|-$", "");
        return result.isEmpty() ? "deta-project" : result;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != SAVE_REQUEST || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        DetaProjectFactory.Project project = pendingProject;
        if (project == null) return;
        Uri uri = data.getData();
        try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
            if (output == null) throw new IOException("The selected destination could not be opened.");
            output.write(project.zip);
            output.flush();
            Toast.makeText(this, "Projeto exportado: " + project.title + ".zip", Toast.LENGTH_LONG).show();
        } catch (IOException exception) {
            Toast.makeText(this, "Falha ao salvar o projeto: " + exception.getMessage(), Toast.LENGTH_LONG).show();
        } finally {
            pendingProject = null;
        }
    }

    private void openDrawer() {
        if (drawerOverlay != null) return;
        drawerOverlay = new FrameLayout(this);
        View dim = new View(this);
        dim.setBackgroundColor(0xAA000000);
        dim.setOnClickListener(view -> closeDrawer());
        drawerOverlay.addView(dim, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout panel = column();
        panel.setBackgroundColor(PANEL);
        panel.setPadding(dp(20), dp(26), dp(16), dp(14));
        panel.setElevation(dp(12));
        panel.setOnClickListener(view -> {});

        LinearLayout titleRow = row();
        titleRow.addView(text("Conversas", 24, FG, true), new LinearLayout.LayoutParams(0, dp(46), 1f));
        titleRow.addView(button("×", "Fechar menu", FIELD, FG, this::closeDrawer), lp(42, 42));
        panel.addView(titleRow, lp(-1, 46));

        drawerSearch = new EditText(this);
        drawerSearch.setSingleLine(true);
        drawerSearch.setTextSize(15);
        drawerSearch.setTextColor(FG);
        drawerSearch.setHintTextColor(MUTED);
        drawerSearch.setHint("Buscar no histórico");
        drawerSearch.setPadding(dp(12), 0, dp(12), 0);
        drawerSearch.setBackground(shape(FIELD, 14, BORDER));
        LinearLayout.LayoutParams searchParams = lp(-1, 46);
        margins(searchParams, 0, 12, 0, 0);
        panel.addView(drawerSearch, searchParams);
        drawerSearch.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { renderHistoryList(); }
            @Override public void afterTextChanged(Editable s) {}
        });

        TextView newChat = actionButton("＋   Nova criação", this::startNewConversation);
        LinearLayout.LayoutParams newParams = lp(-1, 48);
        margins(newParams, 0, 16, 0, 20);
        panel.addView(newChat, newParams);
        panel.addView(text("Recentes", 15, MUTED, true), lp(-1, 28));

        ScrollView rowsScroll = new ScrollView(this);
        rowsScroll.setVerticalScrollBarEnabled(false);
        drawerList = column();
        rowsScroll.addView(drawerList, new ScrollView.LayoutParams(-1, -2));
        panel.addView(rowsScroll, new LinearLayout.LayoutParams(-1, 0, 1f));

        panel.addView(text("Deta · modelo local de criação", 12, MUTED, false), lp(-1, 38));
        int width = Math.min(dp(340), getResources().getDisplayMetrics().widthPixels - dp(52));
        drawerOverlay.addView(panel, new FrameLayout.LayoutParams(Math.max(dp(260), width), -1, Gravity.START));
        root.addView(drawerOverlay, new FrameLayout.LayoutParams(-1, -1));
        renderHistoryList();
        if (searchOpen) {
            drawerSearch.requestFocus();
            showKeyboard(drawerSearch);
        }
    }

    private void showKeyboard(EditText field) {
        field.postDelayed(() -> {
            InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (manager != null) manager.showSoftInput(field, InputMethodManager.SHOW_IMPLICIT);
        }, 150);
    }

    private void closeDrawer() {
        if (drawerOverlay != null) root.removeView(drawerOverlay);
        drawerOverlay = null;
        drawerList = null;
        drawerSearch = null;
    }

    private void renderHistoryList() {
        if (drawerList == null) return;
        drawerList.removeAllViews();
        ArrayList<Conversation> sorted = new ArrayList<>(history);
        Collections.sort(sorted, Comparator.comparingLong((Conversation item) -> item.updatedAt).reversed());
        String query = drawerSearch == null ? "" : drawerSearch.getText().toString().trim().toLowerCase(Locale.ROOT);
        int count = 0;
        for (Conversation conversation : sorted) {
            if (!query.isEmpty() && !conversation.title.toLowerCase(Locale.ROOT).contains(query)) continue;
            count++;
            TextView item = text(conversation.title, 14, conversation.id == activeId ? FG : MUTED, false);
            item.setSingleLine(true);
            item.setEllipsize(android.text.TextUtils.TruncateAt.END);
            item.setPadding(dp(10), dp(12), dp(10), dp(12));
            item.setBackground(shape(conversation.id == activeId ? Color.rgb(42, 42, 51) : PANEL, 12, 0));
            item.setClickable(true);
            item.setOnClickListener(view -> {
                activeId = conversation.id;
                closeDrawer();
                saveHistory();
                renderConversation();
            });
            item.setOnLongClickListener(view -> {
                new AlertDialog.Builder(this).setTitle("Apagar conversa?")
                        .setMessage(conversation.title)
                        .setNegativeButton("Cancelar", null)
                        .setPositiveButton("Apagar", (dialog, which) -> {
                            history.remove(conversation);
                            if (activeId == conversation.id) activeId = -1L;
                            saveHistory();
                            renderHistoryList();
                            renderConversation();
                        }).show();
                return true;
            });
            LinearLayout.LayoutParams itemParams = lp(-1, 44);
            margins(itemParams, 0, 2, 0, 2);
            drawerList.addView(item, itemParams);
        }
        if (count == 0) {
            TextView empty = text(query.isEmpty() ? "Nenhuma conversa ainda." : "Nenhum resultado.", 13, MUTED, false);
            drawerList.addView(empty, lp(-1, 42));
        }
    }

    private void saveHistory() {
        trimHistory();
        JSONArray array = new JSONArray();
        for (Conversation conversation : history) {
            JSONObject item = new JSONObject();
            try {
                item.put("id", conversation.id);
                item.put("title", conversation.title);
                item.put("updatedAt", conversation.updatedAt);
                JSONArray messages = new JSONArray();
                int start = Math.max(0, conversation.messages.size() - MAX_MESSAGES);
                for (int index = start; index < conversation.messages.size(); index++) {
                    Message message = conversation.messages.get(index);
                    JSONObject object = new JSONObject();
                    object.put("user", message.fromUser);
                    object.put("text", trimText(message.text, 2500));
                    if (message.projectPrompt != null) object.put("projectPrompt", trimText(message.projectPrompt, 3000));
                    if (message.neuralDraft != null) object.put("neuralDraft", trimText(message.neuralDraft, 300));
                    messages.put(object);
                }
                item.put("messages", messages);
                array.put(item);
            } catch (JSONException ignored) {
            }
        }
        String serialized = array.toString();
        while (serialized.length() > 600_000 && array.length() > 0) {
            array.remove(array.length() - 1);
            serialized = array.toString();
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(HISTORY_KEY, serialized)
                .putLong(ACTIVE_KEY, activeId)
                .apply();
    }

    private String trimText(String value, int limit) {
        if (value == null || value.length() <= limit) return value == null ? "" : value;
        return value.substring(0, limit);
    }

    private void trimHistory() {
        for (Conversation conversation : history) {
            while (conversation.messages.size() > MAX_MESSAGES) conversation.messages.remove(0);
        }
        while (history.size() > MAX_CONVERSATIONS) {
            Conversation removed = history.remove(history.size() - 1);
            if (removed.id == activeId) activeId = -1L;
        }
    }

    private void loadHistory() {
        String saved = getSharedPreferences(PREFS, MODE_PRIVATE).getString(HISTORY_KEY, "[]");
        try {
            JSONArray array = new JSONArray(saved);
            for (int index = 0; index < Math.min(array.length(), MAX_CONVERSATIONS); index++) {
                JSONObject object = array.optJSONObject(index);
                if (object == null) continue;
                long id = object.optLong("id", -1L);
                if (id < 0) continue;
                Conversation conversation = new Conversation(id, object.optString("title", "Nova criação"));
                conversation.updatedAt = object.optLong("updatedAt", id);
                JSONArray messages = object.optJSONArray("messages");
                if (messages != null) {
                    for (int messageIndex = 0; messageIndex < messages.length() && messageIndex < MAX_MESSAGES; messageIndex++) {
                        JSONObject source = messages.optJSONObject(messageIndex);
                        if (source == null) continue;
                        Message message = new Message(source.optBoolean("user", false), source.optString("text", ""));
                        message.neuralDraft = source.optString("neuralDraft", null);
                        message.projectPrompt = source.optString("projectPrompt", null);
                        if (!message.fromUser && message.projectPrompt != null) {
                            try {
                                message.project = DetaProjectFactory.create(message.projectPrompt);
                            } catch (Exception ignored) {
                                message.project = null;
                            }
                        }
                        conversation.messages.add(message);
                    }
                }
                history.add(conversation);
            }
        } catch (JSONException | RuntimeException ignored) {
            history.clear();
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove(HISTORY_KEY).remove(ACTIVE_KEY).apply();
        }
    }
}
