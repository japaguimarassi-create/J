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
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognizerIntent;
import android.text.Editable;
import android.text.Html;
import android.text.TextWatcher;
import android.text.util.Linkify;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;
import android.webkit.WebSettings;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
    private static final String PREFS_KNOWLEDGE = "local_web_knowledge";
    private static final int VOICE_REQUEST = 712;
    private static final int MAX_WEB_BYTES = 1_200_000;
    private static final int MAX_RESULTS = 5;

    private final ArrayList<Conversation> conversations = new ArrayList<>();
    private final ExecutorService background = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
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

    private enum Icon { MENU, SPARKLE, NEW_CHAT, SEARCH, PLUS, MIC, WAVE, IMAGE, EDIT, CLOSE, HOME, WEB, PROJECT, LIBRARY, BRAIN }

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
        loadConversations();
        buildScreen();
    }

    @Override
    public void onBackPressed() {
        if (drawerLayer != null) {
            closeDrawer();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        background.shutdownNow();
        super.onDestroy();
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
        suggestions.addView(suggestionRow(Icon.WEB, "Pesquisar na web",
                "Pesquise na web: "));
        suggestions.addView(suggestionRow(Icon.PROJECT, "Criar projeto",
                "Crie um jogo de navegador chamado Neon Target."));
        suggestions.addView(suggestionRow(Icon.LIBRARY, "Base de conhecimento",
                "Mostre minha base de conhecimento local."));
        suggestions.addView(suggestionRow(Icon.BRAIN, "Modelo neural local",
                "Explique o estado do modelo neural da Deta."));
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
        ImageView brandIcon = new ImageView(this);
        brandIcon.setImageResource(R.drawable.ic_deta_foreground);
        brandIcon.setContentDescription("Símbolo da Deta");
        brand.addView(brandIcon, lp(28, 28));
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
        composer.setHint("Descreva sua ideia para a Deta");
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
        TextView privacyHint = text("Pesquisa web sem API de IA · histórico e projetos locais", 11, Color.rgb(120, 120, 126), false);
        privacyHint.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams hintParams = lp(-1, 19);
        margin(hintParams, 0, 5, 0, 0);
        outer.addView(privacyHint, hintParams);
        return outer;
    }

    private void showAttachmentOptions() {
        String[] options = {"Biblioteca local", "Imagem ou arquivo"};
        new AlertDialog.Builder(this).setTitle("Adicionar conteúdo")
                .setItems(options, (dialog, which) -> Toast.makeText(this,
                        which == 0 ? "A biblioteca local será integrada em uma próxima etapa."
                                : "O seletor de arquivos será integrado em uma próxima etapa.",
                        Toast.LENGTH_SHORT).show())
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
            Toast.makeText(this, "Escreva uma mensagem para começar.", Toast.LENGTH_SHORT).show();
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
        ChatMessage pending = new ChatMessage(false, "Analisando seu pedido...");
        conversation.messages.add(pending);
        long conversationId = conversation.id;
        composer.setText("");
        persistConversations();
        renderTranscript();
        if (drawerLayer != null) renderDrawerRows();
        InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(composer.getWindowToken(), 0);
        composer.clearFocus();
        transcriptScroll.post(() -> transcriptScroll.fullScroll(View.FOCUS_DOWN));
        background.execute(() -> {
            String answer;
            try {
                answer = processMessage(value);
            } catch (Exception exception) {
                answer = "Não consegui concluir esta tarefa: " + safeError(exception)
                        + "\n\nTente novamente ou use \"Pesquisar na web\" para consultar fontes públicas.";
            }
            String finalAnswer = answer;
            mainHandler.post(() -> {
                pending.text = finalAnswer;
                persistConversations();
                if (activeConversationId == conversationId) {
                    renderTranscript();
                    transcriptScroll.post(() -> transcriptScroll.fullScroll(View.FOCUS_DOWN));
                }
                if (drawerLayer != null) renderDrawerRows();
            });
        });
    }

    private String processMessage(String original) {
        String prompt = original == null ? "" : original.trim();
        String lower = prompt.toLowerCase(Locale.ROOT);
        if (prompt.isEmpty()) return "Escreva uma pergunta, peça uma pesquisa web ou solicite a criação de um projeto.";
        if (isGreeting(lower)) {
            return "Olá! Sou a Deta. Posso pesquisar páginas públicas, guardar fontes neste dispositivo e criar projetos iniciais de jogos, sites e protótipos sociais. Não uso API de IA hospedada; as respostas de pesquisa vêm das fontes encontradas.";
        }
        if (lower.equals("ajuda") || lower.contains("o que você consegue fazer") || lower.contains("o que voce consegue fazer")
                || lower.contains("suas funções") || lower.contains("suas funcoes") || lower.equals("help")) {
            return "O que já funciona nesta versão:\n\n1. Pesquisar na web pública e mostrar links das fontes.\n2. Ler uma página HTTPS e salvar um resumo na base local.\n3. Criar projetos iniciais de jogos, sites e protótipos sociais.\n4. Guardar conversas e resultados localmente.\n5. Pesquisar novamente na base de conhecimento sem internet.\n\nO modelo neural treinado ainda não está embutido neste APK; não vou fingir que textos fixos são inferência neural.";
        }
        if (isProjectRequest(lower)) return createProjectFromPrompt(prompt, lower);
        if (lower.contains("base de conhecimento") || lower.contains("minha memória") || lower.contains("minha memoria")
                || lower.contains("fontes salvas") || lower.contains("fontes salvas")) {
            return summarizeLocalKnowledge(lower);
        }
        if (lower.contains("modelo neural") || lower.contains("parâmetros") || lower.contains("parametros")
                || lower.contains("treinamento") || lower.contains("checkpoint")) {
            return "Estado do modelo na interface Android:\n\nO núcleo Python da Deta tem um modelo experimental de 400.000 parâmetros dividido em cinco grupos. Este APK ainda não carrega o checkpoint PyTorch para inferência local, por isso não posso alegar que o modelo neural está respondendo aqui. A interface já pode pesquisar na web e criar projetos usando ferramentas locais, sem chave de API de IA.";
        }
        Matcher urlMatcher = Pattern.compile("https://[^\\s]+", Pattern.CASE_INSENSITIVE).matcher(prompt);
        if (urlMatcher.find() && (lower.startsWith("https://") || lower.contains("leia ") || lower.contains("resuma ") || lower.contains("abra "))) {
            return readPublicPage(urlMatcher.group().replaceAll("[),.;]+$", ""));
        }
        String query = prompt.replaceFirst("(?i)^(pesquise na web|pesquisar na web|buscar na web|pesquise|pesquisar|procure na internet|buscar na internet)\\s*[:,-]?\\s*", "").trim();
        if (query.isEmpty()) query = prompt;
        return searchPublicWeb(query);
    }

    private boolean isGreeting(String lower) {
        return lower.matches("^(oi|olá|ola|olá deta|ola deta|bom dia|boa tarde|boa noite|obrigado|obrigada|valeu)[!.? ]*$");
    }

    private boolean isProjectRequest(String lower) {
        boolean action = lower.matches("(?s)^(crie|criar|gere|gerar|desenvolva|construa|monte|montar|faca|faça|faz|create|build|generate|novo projeto)\\b.*");
        boolean subject = lower.contains("jogo") || lower.contains("game") || lower.contains("aplicativo")
                || lower.contains(" aplicativo") || lower.contains(" app") || lower.contains("site")
                || lower.contains("página") || lower.contains("pagina") || lower.contains("rede social")
                || lower.contains("projeto");
        return action && subject;
    }

    private String createProjectFromPrompt(String prompt, String lower) {
        String kind = lower.contains("rede social") || lower.contains("social") ? "social"
                : lower.contains("jogo") || lower.contains("game") ? "game" : "site";
        Matcher named = Pattern.compile("(?i)(?:chamado|chamada|nomeado|nomeada|com nome)\\s+(.+)$").matcher(prompt);
        String name;
        if (named.find()) {
            name = named.group(1).trim();
        } else {
            name = prompt.replaceFirst("(?i)^(crie|criar|gere|gerar|desenvolva|construa|monte|montar|faca|faça|faz|create|build|generate|novo projeto)\\s*", "")
                    .replaceFirst("(?i)^(um|uma|o|a|meu|minha)\\s+", "").trim();
            name = name.replaceFirst("(?i)^(jogo|game|aplicativo|app|site|página|pagina|projeto|rede social)\\s+(de|do|da|para|sobre)\\s+", "");
        }
        name = name.replaceAll("[^\\p{L}\\p{N} _.-]", "").trim();
        if (name.length() > 48) name = name.substring(0, 48).trim();
        if (name.isEmpty() || name.matches("(?i)(jogo|app|site|projeto|aplicativo)")) name = kind.equals("game") ? "Jogo Deta" : kind.equals("social") ? "Comunidade Deta" : "Projeto Deta";
        String slug = name.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", "-").replaceAll("^-|-$", "");
        if (slug.isEmpty()) slug = "projeto-deta";
        File rootDir = new File(getFilesDir(), "projects");
        File projectDir = new File(rootDir, slug);
        if (projectDir.exists()) projectDir = new File(rootDir, slug + "-" + (System.currentTimeMillis() % 1_000_000L));
        if (!projectDir.mkdirs()) throw new IllegalStateException("Não foi possível criar a pasta do projeto.");
        String html = buildProjectHtml(kind, name, prompt);
        try {
            writeUtf8(new File(projectDir, "index.html"), html);
            writeUtf8(new File(projectDir, "README.txt"),
                    "Projeto criado pela Deta. Tipo: " + kind + "\nNome: " + name + "\nCriado localmente, sem API de IA.\n");
        } catch (IOException exception) {
            throw new IllegalStateException("Falha ao gravar os arquivos do projeto.", exception);
        }
        return "Projeto criado com arquivos reais neste dispositivo.\n\nNome: " + name
                + "\nTipo: " + (kind.equals("game") ? "jogo de navegador" : kind.equals("social") ? "protótipo social local" : "site/aplicativo web")
                + "\nArquivos: index.html e README.txt\nPasta interna: " + projectDir.getAbsolutePath()
                + "\n\nAbra o menu Deta → Biblioteca para executar a prévia. Os arquivos ficam no armazenamento privado do app; não é um APK ainda.";
    }

    private String buildProjectHtml(String kind, String name, String brief) {
        String title = escapeHtml(name);
        String description = escapeHtml(brief);
        String style = "body{margin:0;background:#090b16;color:#f2f4ff;font-family:system-ui,sans-serif;padding:22px}main{max-width:760px;margin:auto}section{background:#171b2c;border:1px solid #2d3658;border-radius:18px;padding:18px;margin:14px 0}h1{font-size:clamp(25px,6vw,40px)}p{line-height:1.55;color:#bfc8e8}button{background:#aaa4ff;border:0;border-radius:12px;padding:12px 16px;font-weight:700;color:#090b16}input,textarea{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #374262;background:#0d1020;color:white;margin:8px 0}button{cursor:pointer}";
        if (kind.equals("game")) {
            return "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>" + title
                    + "</title><style>" + style + "#target{width:100%;min-height:190px;font-size:24px;background:linear-gradient(135deg,#5c66ff,#61d9ff)}strong{font-size:28px}</style></head><body><main><section><small>JOGO CRIADO PELA DETA</small><h1>"
                    + title + "</h1><p>" + description + "</p><p>Toque no alvo o máximo que conseguir.</p><p>Pontos: <strong id='score'>0</strong></p><button id='target'>TOQUE AQUI</button><p id='message'>Pronto para começar.</p></section></main><script>let score=0;const target=document.getElementById('target');target.addEventListener('click',()=>{score++;document.getElementById('score').textContent=score;target.textContent=['BOM!','MAIS UMA!','CONTINUE!','INCRÍVEL!'][score%4];document.getElementById('message').textContent='Pontuação atualizada: '+score;});</script></body></html>";
        }
        if (kind.equals("social")) {
            return "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>" + title
                    + "</title><style>" + style + ".post{white-space:pre-wrap}</style></head><body><main><section><small>COMUNIDADE LOCAL</small><h1>"
                    + title + "</h1><p>" + description + "</p><form id='form'><textarea id='input' placeholder='Compartilhe uma ideia' required></textarea><button>Publicar</button></form></section><section><h2>Publicações</h2><div id='feed'></div></section></main><script>const form=document.getElementById('form'),input=document.getElementById('input'),feed=document.getElementById('feed'),key='deta-social-" + escapeJs(name) + "';let posts=[];try{posts=JSON.parse(localStorage.getItem(key)||'[]')}catch(e){}function render(){feed.replaceChildren();posts.forEach((post,index)=>{const row=document.createElement('section');row.className='post';const text=document.createElement('p');text.textContent=post;const del=document.createElement('button');del.textContent='Excluir';del.onclick=()=>{posts.splice(index,1);save()};row.append(text,del);feed.append(row)})}function save(){localStorage.setItem(key,JSON.stringify(posts));render()}form.addEventListener('submit',e=>{e.preventDefault();if(input.value.trim()){posts.unshift(input.value.trim());input.value='';save()}});render();</script></body></html>";
        }
        return "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>" + title
                + "</title><style>" + style + "</style></head><body><main><section><small>PROJETO DETA</small><h1>" + title
                + "</h1><p>" + description + "</p><label for='idea'>Experimente a interface</label><input id='idea' placeholder='Digite alguma coisa'><button id='run'>Executar ação</button><p id='output'>Seu projeto está funcionando.</p></section></main><script>document.getElementById('run').addEventListener('click',()=>{document.getElementById('output').textContent='Resultado: '+document.getElementById('idea').value;});</script></body></html>";
    }

    private String escapeHtml(String value) {
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&#39;");
    }

    private String escapeJs(String value) {
        return value.replace("\\\\", "\\\\\\\\").replace("'", "\\\\'").replace("\\n", " ");
    }

    private void writeUtf8(File file, String value) throws IOException {
        try (FileOutputStream stream = new FileOutputStream(file)) {
            stream.write(value.getBytes(StandardCharsets.UTF_8));
            stream.flush();
        }
    }

    private String searchPublicWeb(String query) {
        String cleaned = query == null ? "" : query.trim();
        if (cleaned.isEmpty()) return "Digite o assunto que deseja pesquisar.";
        try {
            String endpoint = "https://html.duckduckgo.com/html/?q=" + URLEncoder.encode(cleaned, "UTF-8");
            String page = fetchPublicHttps(endpoint);
            ArrayList<JSONObject> results = extractSearchResults(page);
            if (results.isEmpty()) return "A pesquisa não devolveu resultados legíveis para \"" + cleaned
                    + "\". O site de busca pode estar temporariamente indisponível ou ter alterado o HTML. Tente uma frase mais específica.";
            saveKnowledge(results);
            StringBuilder answer = new StringBuilder("Pesquisa na web: ").append(cleaned).append("\n\n");
            for (int index = 0; index < results.size(); index++) {
                JSONObject item = results.get(index);
                answer.append(index + 1).append(". ").append(item.optString("title", "Fonte pública")).append("\n")
                        .append(item.optString("snippet", "Sem resumo disponível.")).append("\n")
                        .append(item.optString("url", "")).append("\n\n");
                if (answer.length() > 5200) break;
            }
            answer.append("As informações acima são trechos do buscador, não uma validação independente. Abra as fontes para confirmar detalhes.");
            return answer.toString();
        } catch (Exception exception) {
            return "Não consegui acessar a pesquisa pública agora: " + safeError(exception)
                    + "\n\nA Deta não usa chave de API de IA, mas precisa de internet para pesquisar. Tente novamente ou envie uma página HTTPS pública.";
        }
    }

    private String readPublicPage(String address) {
        try {
            String page = fetchPublicHttps(address);
            String title = "Página pública";
            Matcher titleMatcher = Pattern.compile("(?is)<title[^>]*>(.*?)</title>").matcher(page);
            if (titleMatcher.find()) title = htmlToText(titleMatcher.group(1)).trim();
            String body = htmlToText(page);
            if (body.length() > 4000) body = body.substring(0, 4000) + "...";
            JSONObject item = new JSONObject();
            item.put("title", title.isEmpty() ? address : title);
            item.put("url", address);
            item.put("snippet", body.substring(0, Math.min(body.length(), 1200)));
            ArrayList<JSONObject> records = new ArrayList<>();
            records.add(item);
            saveKnowledge(records);
            return "Página consultada e adicionada à base local.\n\n" + title + "\n" + address + "\n\n" + body;
        } catch (Exception exception) {
            return "Não consegui ler esta página: " + safeError(exception)
                    + "\nUse um endereço HTTPS público que permita acesso sem login.";
        }
    }

    private String fetchPublicHttps(String requested) throws IOException {
        String current = requested;
        for (int redirects = 0; redirects <= 4; redirects++) {
            validatePublicUrl(current);
            URL url = new URL(current);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(12000);
            connection.setReadTimeout(15000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestMethod("GET");
            connection.setRequestProperty("User-Agent", "Deta-Android/0.3 public-web-research");
            connection.setRequestProperty("Accept", "text/html,text/plain,application/xhtml+xml");
            int status = connection.getResponseCode();
            if (status >= 300 && status < 400) {
                String location = connection.getHeaderField("Location");
                connection.disconnect();
                if (location == null || redirects == 4) throw new IOException("Redirecionamento web excessivo ou sem destino.");
                current = new URL(url, location).toString();
                continue;
            }
            if (status < 200 || status >= 300) {
                connection.disconnect();
                throw new IOException("O site respondeu HTTP " + status + ".");
            }
            String contentType = connection.getContentType();
            if (contentType != null && !(contentType.contains("text/html") || contentType.contains("text/plain")
                    || contentType.contains("application/xhtml+xml"))) {
                connection.disconnect();
                throw new IOException("Formato de página não suportado: " + contentType);
            }
            try (InputStream stream = connection.getInputStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int total = 0;
                int count;
                while ((count = stream.read(buffer)) != -1) {
                    total += count;
                    if (total > MAX_WEB_BYTES) throw new IOException("A página ultrapassa o limite de leitura de 1,2 MB.");
                    output.write(buffer, 0, count);
                }
                return output.toString(StandardCharsets.UTF_8.name());
            } finally {
                connection.disconnect();
            }
        }
        throw new IOException("Não foi possível seguir o endereço web.");
    }

    private void validatePublicUrl(String address) throws IOException {
        Uri uri = Uri.parse(address);
        String scheme = uri.getScheme();
        String host = uri.getHost();
        if (!"https".equalsIgnoreCase(scheme) || host == null || host.isEmpty() || uri.getUserInfo() != null
                || (uri.getPort() != -1 && uri.getPort() != 443)) {
            throw new IOException("Aceito apenas páginas HTTPS públicas, sem usuário ou senha no endereço.");
        }
        String lowerHost = host.toLowerCase(Locale.ROOT);
        if (lowerHost.equals("localhost") || lowerHost.endsWith(".localhost") || lowerHost.endsWith(".local")
                || lowerHost.endsWith(".internal") || lowerHost.equals("metadata.google.internal")) {
            throw new IOException("Endereços locais e internos não são permitidos.");
        }
        try {
            for (InetAddress addressResult : InetAddress.getAllByName(host)) {
                if (addressResult.isAnyLocalAddress() || addressResult.isLoopbackAddress()
                        || addressResult.isLinkLocalAddress() || addressResult.isSiteLocalAddress()
                        || addressResult.isMulticastAddress()) {
                    throw new IOException("O endereço resolve para uma rede privada ou não pública.");
                }
            }
        } catch (SecurityException exception) {
            throw new IOException("A verificação do endereço falhou.", exception);
        }
    }

    private ArrayList<JSONObject> extractSearchResults(String source) throws JSONException {
        ArrayList<JSONObject> results = new ArrayList<>();
        ArrayList<String> snippets = new ArrayList<>();
        Pattern anchorPattern = Pattern.compile("(?is)<a\\b([^>]*)>(.*?)</a>");
        Matcher anchorMatcher = anchorPattern.matcher(source);
        Pattern classPattern = Pattern.compile("(?is)\\bclass\\s*=\\s*['\"]([^'\"]*)['\"]");
        Pattern hrefPattern = Pattern.compile("(?is)\\bhref\\s*=\\s*['\"]([^'\"]+)['\"]");
        while (anchorMatcher.find()) {
            String attributes = anchorMatcher.group(1);
            String body = anchorMatcher.group(2);
            Matcher classMatcher = classPattern.matcher(attributes);
            if (!classMatcher.find()) continue;
            String classes = classMatcher.group(1);
            if (classes.contains("result__snippet") || classes.contains("result-snippet")) {
                String snippet = htmlToText(body).trim();
                if (!snippet.isEmpty()) snippets.add(snippet);
                continue;
            }
            if (!classes.contains("result__a") && !classes.contains("result-link")) continue;
            Matcher hrefMatcher = hrefPattern.matcher(attributes);
            if (!hrefMatcher.find()) continue;
            String destination = decodeSearchDestination(hrefMatcher.group(1));
            try {
                validatePublicUrl(destination);
            } catch (Exception ignored) {
                continue;
            }
            String title = htmlToText(body).trim();
            if (title.isEmpty()) continue;
            boolean duplicate = false;
            for (JSONObject item : results) {
                if (destination.equals(item.optString("url"))) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) continue;
            JSONObject item = new JSONObject();
            item.put("title", title);
            item.put("url", destination);
            item.put("snippet", "");
            results.add(item);
            if (results.size() >= MAX_RESULTS) break;
        }
        for (int index = 0; index < results.size() && index < snippets.size(); index++) {
            results.get(index).put("snippet", snippets.get(index));
        }
        return results;
    }

    private String decodeSearchDestination(String value) throws IOException {
        String href = value.replace("&amp;", "&");
        if (href.startsWith("//")) href = "https:" + href;
        if (href.startsWith("/")) href = "https://html.duckduckgo.com" + href;
        Uri uri = Uri.parse(href);
        String host = uri.getHost();
        if (host != null && (host.equals("duckduckgo.com") || host.endsWith(".duckduckgo.com"))) {
            String destination = uri.getQueryParameter("uddg");
            if (destination != null && !destination.isEmpty()) href = destination;
        }
        return href;
    }

    private String htmlToText(String source) {
        String withoutScripts = source.replaceAll("(?is)<script\\b[^>]*>.*?</script>", " ")
                .replaceAll("(?is)<style\\b[^>]*>.*?</style>", " ")
                .replaceAll("(?is)<noscript\\b[^>]*>.*?</noscript>", " ")
                .replaceAll("(?is)<(br|/p|/div|/li|/h[1-6])\\b[^>]*>", "\n")
                .replaceAll("(?is)<[^>]+>", " ");
        CharSequence textValue;
        if (android.os.Build.VERSION.SDK_INT >= 24) {
            textValue = Html.fromHtml(withoutScripts, Html.FROM_HTML_MODE_LEGACY);
        } else {
            textValue = Html.fromHtml(withoutScripts);
        }
        return textValue.toString().replace('\u00a0', ' ').replaceAll("[ \\t\\r\\f]+", " ")
                .replaceAll("\\n{3,}", "\n\n").trim();
    }

    private void saveKnowledge(ArrayList<JSONObject> incoming) {
        String stored = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(PREFS_KNOWLEDGE, "[]");
        JSONArray current;
        try {
            current = new JSONArray(stored);
        } catch (JSONException exception) {
            current = new JSONArray();
        }
        for (JSONObject fresh : incoming) {
            String url = fresh.optString("url", "");
            if (url.isEmpty()) continue;
            JSONArray updated = new JSONArray();
            try {
                for (int index = 0; index < current.length(); index++) {
                    JSONObject item = current.getJSONObject(index);
                    if (!url.equals(item.optString("url", ""))) updated.put(item);
                }
                updated.put(fresh);
                current = updated;
            } catch (JSONException ignored) { }
        }
        JSONArray bounded = new JSONArray();
        int start = Math.max(0, current.length() - 200);
        try {
            for (int index = start; index < current.length(); index++) bounded.put(current.getJSONObject(index));
        } catch (JSONException ignored) { }
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit().putString(PREFS_KNOWLEDGE, bounded.toString()).apply();
    }

    private String summarizeLocalKnowledge(String lower) {
        JSONArray knowledge;
        try {
            knowledge = new JSONArray(getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(PREFS_KNOWLEDGE, "[]"));
        } catch (JSONException exception) {
            return "A base de conhecimento local ainda está vazia.";
        }
        if (knowledge.length() == 0) {
            return "A base de conhecimento local está vazia. Envie \"Pesquise na web: assunto\" ou um endereço HTTPS para guardar fontes neste dispositivo.";
        }
        StringBuilder output = new StringBuilder("Base de conhecimento local: ").append(knowledge.length()).append(" fonte(s).\n\n");
        int shown = 0;
        for (int index = knowledge.length() - 1; index >= 0 && shown < 8; index--) {
            JSONObject item = knowledge.optJSONObject(index);
            if (item == null) continue;
            String title = item.optString("title", "Fonte pública");
            String snippet = item.optString("snippet", "");
            if (!lower.contains("base de conhecimento") && !lower.contains("minha memória") && !lower.contains("minha memoria")
                    && !title.toLowerCase(Locale.ROOT).contains(lower) && !snippet.toLowerCase(Locale.ROOT).contains(lower)) {
                continue;
            }
            output.append("• ").append(title).append("\n").append(item.optString("url", "")).append("\n")
                    .append(snippet).append("\n\n");
            shown++;
        }
        if (shown == 0) output.append("Nenhuma fonte corresponde à consulta. Tente uma pesquisa web primeiro.");
        return output.toString();
    }

    private String safeError(Exception exception) {
        String value = exception.getMessage();
        if (value == null || value.trim().isEmpty()) value = exception.getClass().getSimpleName();
        if (value.length() > 220) value = value.substring(0, 217) + "...";
        return value.replace('\n', ' ').replace('\r', ' ');
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
                response.setTextIsSelectable(true);
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
        header.addView(text("Deta", 25, WHITE, true), new LinearLayout.LayoutParams(0, dp(48), 1f));
        header.addView(iconButton(Icon.SEARCH, 46, SURFACE_LIGHT, WHITE, "Buscar conversas", this::toggleSearch), lp(46, 46));
        panel.addView(header, lp(-1, 50));

        drawerSearch = new EditText(this);
        drawerSearch.setSingleLine(true);
        drawerSearch.setVisibility(View.VISIBLE);
        drawerSearch.setTextSize(15);
        drawerSearch.setTextColor(WHITE);
        drawerSearch.setHintTextColor(MUTED);
        drawerSearch.setHint("Buscar projetos ou conversas");
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

        LinearLayout.LayoutParams navParams = lp(-1, 46);
        margin(navParams, 0, 12, 0, 0);
        panel.addView(drawerActionRow(Icon.HOME, "Início", this::startNewConversation), navParams);
        LinearLayout.LayoutParams nav2 = lp(-1, 46);
        margin(nav2, 0, 6, 0, 0);
        panel.addView(drawerActionRow(Icon.PROJECT, "Novo projeto", this::showCreateProjectDialog), nav2);
        LinearLayout.LayoutParams nav3 = lp(-1, 46);
        margin(nav3, 0, 6, 0, 0);
        panel.addView(drawerActionRow(Icon.LIBRARY, "Biblioteca", this::openLibrary), nav3);
        LinearLayout.LayoutParams nav4 = lp(-1, 46);
        margin(nav4, 0, 6, 0, 0);
        panel.addView(drawerActionRow(Icon.WEB, "Pesquisar na web", this::focusWebSearch), nav4);
        LinearLayout.LayoutParams nav5 = lp(-1, 46);
        margin(nav5, 0, 6, 0, 0);
        panel.addView(drawerActionRow(Icon.BRAIN, "Modelo neural", this::showModelStatus), nav5);

        View separator = new View(this);
        separator.setBackgroundColor(OUTLINE);
        LinearLayout.LayoutParams separatorParams = lp(-1, 1);
        margin(separatorParams, 0, 17, 0, 13);
        panel.addView(separator, separatorParams);
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

    private LinearLayout drawerActionRow(Icon icon, String title, Runnable action) {
        LinearLayout row = horizontal();
        row.setPadding(dp(13), 0, dp(13), 0);
        row.setMinimumHeight(dp(46));
        row.setBackground(rounded(SURFACE_LIGHT, 14, 0));
        row.setClickable(true);
        row.setFocusable(true);
        row.addView(new IconView(this, icon, ACCENT), lp(23, 23));
        TextView titleView = text(title, 15, WHITE, false);
        LinearLayout.LayoutParams titleParams = lp(-1, -1);
        margin(titleParams, 13, 0, 0, 0);
        row.addView(titleView, titleParams);
        row.setOnClickListener(view -> {
            closeDrawer();
            action.run();
        });
        return row;
    }

    private void toggleSearch() {
        searchOpen = true;
        if (drawerSearch != null) {
            drawerSearch.requestFocus();
            showKeyboard(drawerSearch);
        }
    }

    private void focusWebSearch() {
        composer.setText("Pesquise na web: ");
        composer.setSelection(composer.length());
        composer.requestFocus();
        showKeyboard(composer);
    }

    private void showCreateProjectDialog() {
        String[] kinds = {"Jogo de navegador", "Aplicativo social local", "Site ou ferramenta web"};
        new AlertDialog.Builder(this).setTitle("Novo projeto").setItems(kinds, (dialog, which) -> {
            String kind = which == 0 ? "game" : which == 1 ? "social" : "site";
            showProjectNameDialog(kind);
        }).setNegativeButton("Cancelar", null).show();
    }

    private void showProjectNameDialog(String kind) {
        EditText nameInput = new EditText(this);
        nameInput.setSingleLine(true);
        nameInput.setTextSize(16);
        nameInput.setTextColor(WHITE);
        nameInput.setHintTextColor(MUTED);
        nameInput.setHint(kind.equals("game") ? "Nome do jogo" : kind.equals("social") ? "Nome da comunidade" : "Nome do site");
        nameInput.setPadding(dp(14), dp(12), dp(14), dp(12));
        nameInput.setBackground(rounded(SURFACE_LIGHT, 14, OUTLINE));
        LinearLayout body = vertical();
        body.setPadding(dp(20), dp(8), dp(20), dp(4));
        body.addView(nameInput, lp(-1, 52));
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("Criar projeto")
                .setView(body)
                .setPositiveButton("Criar", (ignored, which) -> {
                    String name = nameInput.getText().toString().trim();
                    if (name.isEmpty()) name = kind.equals("game") ? "Jogo Deta" : kind.equals("social") ? "Comunidade Deta" : "Projeto Deta";
                    String request = "Crie " + (kind.equals("game") ? "um jogo" : kind.equals("social") ? "uma rede social" : "um site")
                            + " chamado " + name;
                    String result;
                    try {
                        result = createProjectFromPrompt(request, request.toLowerCase(Locale.ROOT));
                    } catch (Exception exception) {
                        result = "Falha ao criar o projeto: " + safeError(exception);
                    }
                    new AlertDialog.Builder(this).setTitle("Deta").setMessage(result)
                            .setPositiveButton("Abrir biblioteca", (d, w) -> openLibrary())
                            .setNegativeButton("Fechar", null).show();
                }).setNegativeButton("Cancelar", null).create();
        dialog.show();
        showKeyboard(nameInput);
    }

    private File projectsDirectory() {
        File directory = new File(getFilesDir(), "projects");
        if (!directory.exists()) directory.mkdirs();
        return directory;
    }

    private void openLibrary() {
        File[] directories = projectsDirectory().listFiles(File::isDirectory);
        if (directories == null || directories.length == 0) {
            new AlertDialog.Builder(this).setTitle("Biblioteca").setMessage("Ainda não há projetos. Use Novo projeto ou peça à Deta para criar um jogo, site ou protótipo social.")
                    .setPositiveButton("Criar projeto", (dialog, which) -> showCreateProjectDialog())
                    .setNegativeButton("Fechar", null).show();
            return;
        }
        java.util.Arrays.sort(directories, Comparator.comparingLong(File::lastModified).reversed());
        String[] names = new String[directories.length];
        for (int index = 0; index < directories.length; index++) names[index] = directories[index].getName().replace('-', ' ');
        new AlertDialog.Builder(this).setTitle("Biblioteca de projetos").setItems(names, (dialog, which) -> openProjectPreview(directories[which]))
                .setNegativeButton("Fechar", null).show();
    }

    private void openProjectPreview(File directory) {
        File page = new File(directory, "index.html");
        if (!page.isFile()) {
            Toast.makeText(this, "O projeto não contém index.html.", Toast.LENGTH_SHORT).show();
            return;
        }
        WebView webView = new WebView(this);
        webView.setBackgroundColor(BLACK);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(false);
        webView.loadUrl(Uri.fromFile(page).toString());
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle(directory.getName().replace('-', ' '))
                .setView(webView).setPositiveButton("Fechar", null)
                .setNeutralButton("Compartilhar HTML", (d, which) -> {
                    try {
                        String html = readUtf8(page);
                        Intent share = new Intent(Intent.ACTION_SEND);
                        share.setType("text/html");
                        share.putExtra(Intent.EXTRA_SUBJECT, directory.getName() + " — Deta");
                        share.putExtra(Intent.EXTRA_TEXT, html);
                        startActivity(Intent.createChooser(share, "Compartilhar projeto HTML"));
                    } catch (IOException exception) {
                        Toast.makeText(this, "Não foi possível ler o arquivo do projeto.", Toast.LENGTH_SHORT).show();
                    }
                }).create();
        dialog.show();
        if (dialog.getWindow() != null) dialog.getWindow().setLayout(Math.min(dp(380), getResources().getDisplayMetrics().widthPixels - dp(24)), dp(560));
    }

    private void showModelStatus() {
        String message = "Modelo experimental Deta: 400.000 parâmetros, divididos em cinco grupos no núcleo Python.\n\n"
                + "Este APK não embute um runtime compatível com o checkpoint PyTorch. A pesquisa web e a criação local de projetos funcionam sem uma API de IA; inferência neural dentro do Android exige conversão e validação adicionais.";
        new AlertDialog.Builder(this).setTitle("Modelo neural local").setMessage(message)
                .setPositiveButton("Entendi", null).show();
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
        int conversationCount = 0;
        for (Conversation conversation : sorted) {
            if (!query.isEmpty() && !conversation.title.toLowerCase(Locale.ROOT).contains(query)) continue;
            conversationCount++;
            visibleCount++;
            LinearLayout row = horizontal();
            row.setPadding(dp(11), dp(10), dp(11), dp(10));
            row.setMinimumHeight(dp(46));
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
        if (conversationCount == 0 && query.isEmpty()) {
            TextView empty = text("Suas conversas aparecerão aqui quando você começar.", 14, MUTED, false);
            empty.setPadding(dp(11), dp(8), dp(11), dp(14));
            drawerRows.addView(empty, lp(-1, -2));
        }

        File[] projects = projectsDirectory().listFiles(File::isDirectory);
        ArrayList<File> matchingProjects = new ArrayList<>();
        if (projects != null) {
            for (File project : projects) {
                String displayName = project.getName().replace('-', ' ');
                if (query.isEmpty() || displayName.toLowerCase(Locale.ROOT).contains(query)) matchingProjects.add(project);
            }
        }
        Collections.sort(matchingProjects, Comparator.comparingLong(File::lastModified).reversed());
        if (!matchingProjects.isEmpty()) {
            TextView sectionTitle = text("Projetos", 15, WHITE, true);
            LinearLayout.LayoutParams sectionParams = lp(-1, 31);
            margin(sectionParams, 0, 10, 0, 2);
            drawerRows.addView(sectionTitle, sectionParams);
            for (File project : matchingProjects) {
                visibleCount++;
                LinearLayout row = horizontal();
                row.setPadding(dp(11), dp(10), dp(11), dp(10));
                row.setMinimumHeight(dp(46));
                row.setBackgroundResource(android.R.drawable.list_selector_background);
                row.setClickable(true);
                row.setFocusable(true);
                row.addView(new IconView(this, Icon.PROJECT, ACCENT), lp(20, 20));
                TextView title = text(project.getName().replace('-', ' '), 15, Color.rgb(223, 223, 227), false);
                title.setSingleLine(true);
                title.setEllipsize(android.text.TextUtils.TruncateAt.END);
                LinearLayout.LayoutParams titleParams = lp(-1, -2);
                margin(titleParams, 10, 0, 0, 0);
                row.addView(title, titleParams);
                row.setOnClickListener(view -> {
                    closeDrawer();
                    openProjectPreview(project);
                });
                LinearLayout.LayoutParams rowParams = lp(-1, -2);
                margin(rowParams, 0, 2, 0, 2);
                drawerRows.addView(row, rowParams);
            }
        }
        if (visibleCount == 0) {
            TextView empty = text(query.isEmpty() ? "Nenhuma conversa ou projeto ainda." : "Nenhum resultado.", 14, MUTED, false);
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
                case HOME:
                    path(canvas, 3, 11, 12, 3, 21, 11);
                    path(canvas, 5, 10, 5, 21, 19, 21, 19, 10);
                    break;
                case WEB:
                    canvas.drawCircle(12, 12, 9, paint);
                    canvas.drawOval(new RectF(7, 3, 17, 21), paint);
                    line(canvas, 3, 12, 21, 12);
                    line(canvas, 5, 7, 19, 7);
                    line(canvas, 5, 17, 19, 17);
                    break;
                case PROJECT:
                    line(canvas, 12, 3, 12, 21);
                    line(canvas, 3, 12, 21, 12);
                    break;
                case LIBRARY:
                    canvas.drawRect(new RectF(3, 3, 21, 21), paint);
                    line(canvas, 9, 3, 9, 21);
                    line(canvas, 15, 3, 15, 21);
                    line(canvas, 3, 9, 21, 9);
                    line(canvas, 3, 15, 21, 15);
                    break;
                case BRAIN:
                    canvas.drawArc(new RectF(3, 3, 12, 20), 105, 250, false, paint);
                    canvas.drawArc(new RectF(12, 3, 21, 20), 185, 250, false, paint);
                    line(canvas, 12, 4, 12, 21);
                    path(canvas, 7, 7, 9, 10, 6, 13);
                    path(canvas, 17, 7, 15, 10, 18, 13);
                    break;
            }
            canvas.restoreToCount(saved);
        }
    }
}
