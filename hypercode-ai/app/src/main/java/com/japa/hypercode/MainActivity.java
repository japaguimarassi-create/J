package com.japa.hypercode;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.content.SharedPreferences;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.japa.hypercode.core.LanguageProfile;
import com.japa.hypercode.core.StarterAssistant;

public class MainActivity extends Activity {
    private final int bg = Color.rgb(10, 14, 25);
    private final int panel = Color.rgb(19, 27, 45);
    private final int accent = Color.rgb(78, 160, 255);
    private LinearLayout transcript;
    private ScrollView scroll;
    private EditText composer;
    private SharedPreferences preferences;
    private String conversationLanguage;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("hypercode", MODE_PRIVATE);
        conversationLanguage = preferences.getString("conversation_language", null);
        buildScreen();
        appendMessage("HyperCode", "Interface HyperCode. As sete redes recebem a mesma pergunta, comunicam seus estados em dez etapas e enviam uma representação coletiva ao núcleo final.\n\nCheckpoint-alvo ainda não treinado nem integrado ao aplicativo. O chat não deve ser confundido com o modelo neural final.", false);
    }

    private void buildScreen() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(12), dp(16), dp(10));
        root.setBackgroundColor(bg);

        TextView title = text("HYPERCODE AI", 22, Color.WHITE, true);
        root.addView(title);
        TextView subtitle = text("SEVEN-NETWORK MUTUAL INTELLIGENCE", 10, Color.rgb(137, 159, 193), true);
        subtitle.setLetterSpacing(0.12f);
        root.addView(subtitle);

        LinearLayout status = new LinearLayout(this);
        status.setOrientation(LinearLayout.VERTICAL);
        status.setPadding(dp(12), dp(10), dp(12), dp(10));
        status.setBackground(round(panel, 14));
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(-1, -2);
        statusParams.topMargin = dp(14);
        root.addView(status, statusParams);
        status.addView(text("MUTUAL CORE  •  TRAINING REQUIRED", 11, accent, true));
        status.addView(text("7 redes universais: 10 × 256  |  Núcleo: 20 × 1.792", 11, Color.WHITE, false));
        status.addView(text("Mesmo contexto • comunicação mútua • uma resposta coletiva", 10, Color.rgb(255, 194, 112), false));

        TextView experts = text("REDES UNIVERSAIS", 10, Color.rgb(137, 159, 193), true);
        LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(-1, -2);
        ep.topMargin = dp(12);
        root.addView(experts, ep);

        String[] names = {"NETWORK 01", "NETWORK 02", "NETWORK 03", "NETWORK 04", "NETWORK 05", "NETWORK 06", "NETWORK 07"};
        LinearLayout grid = new LinearLayout(this);
        grid.setOrientation(LinearLayout.VERTICAL);
        for (int i = 0; i < names.length; i += 2) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.addView(expertCard(names[i]), new LinearLayout.LayoutParams(0, dp(38), 1));
            if (i + 1 < names.length) {
                View gap = new View(this);
                row.addView(gap, new LinearLayout.LayoutParams(dp(8), 1));
                row.addView(expertCard(names[i + 1]), new LinearLayout.LayoutParams(0, dp(38), 1));
            }
            LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(-1, -2);
            rp.topMargin = dp(5);
            grid.addView(row, rp);
        }
        root.addView(grid);

        scroll = new ScrollView(this);
        transcript = new LinearLayout(this);
        transcript.setOrientation(LinearLayout.VERTICAL);
        transcript.setPadding(0, dp(8), 0, dp(8));
        scroll.addView(transcript);
        LinearLayout.LayoutParams chatParams = new LinearLayout.LayoutParams(-1, 0, 1);
        chatParams.topMargin = dp(8);
        chatParams.bottomMargin = dp(8);
        root.addView(scroll, chatParams);

        LinearLayout inputRow = new LinearLayout(this);
        inputRow.setOrientation(LinearLayout.HORIZONTAL);
        composer = new EditText(this);
        composer.setSingleLine(false);
        composer.setMinLines(1);
        composer.setMaxLines(4);
        composer.setTextColor(Color.WHITE);
        composer.setHintTextColor(Color.rgb(119, 137, 165));
        composer.setHint("Pergunte sobre código...");
        composer.setPadding(dp(13), dp(8), dp(13), dp(8));
        composer.setBackground(round(panel, 14));
        composer.setImeOptions(EditorInfo.IME_ACTION_SEND);
        inputRow.addView(composer, new LinearLayout.LayoutParams(0, -2, 1));
        Button send = new Button(this);
        send.setText("ENVIAR");
        send.setTextColor(Color.WHITE);
        send.setAllCaps(false);
        send.setBackground(round(accent, 14));
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(dp(88), dp(50));
        sendParams.leftMargin = dp(8);
        inputRow.addView(send, sendParams);
        root.addView(inputRow);

        send.setOnClickListener(v -> sendMessage());
        composer.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                sendMessage();
                return true;
            }
            return false;
        });
        setContentView(root);
    }

    private TextView expertCard(String name) {
        TextView card = text(name + "  ·  10×256", 10, Color.WHITE, true);
        card.setGravity(Gravity.CENTER);
        card.setBackground(round(panel, 10));
        return card;
    }

    private void sendMessage() {
        String message = composer.getText().toString().trim();
        if (message.isEmpty()) return;
        if (conversationLanguage == null) {
            conversationLanguage = LanguageProfile.detect(message);
            preferences.edit().putString("conversation_language", conversationLanguage).apply();
        }
        appendMessage("Você", message, true);
        composer.setText("");
        appendMessage("HyperCode", StarterAssistant.reply(message, conversationLanguage), false);
    }

    private void appendMessage(String speaker, String body, boolean user) {
        LinearLayout bubble = new LinearLayout(this);
        bubble.setOrientation(LinearLayout.VERTICAL);
        bubble.setPadding(dp(12), dp(10), dp(12), dp(10));
        bubble.setBackground(round(user ? Color.rgb(26, 53, 84) : panel, 14));
        TextView name = text(speaker.toUpperCase(), 10, user ? Color.rgb(156, 205, 255) : accent, true);
        TextView content = text(body, 13, Color.rgb(235, 241, 250), false);
        content.setTextIsSelectable(true);
        bubble.addView(name);
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(-1, -2);
        cp.topMargin = dp(5);
        bubble.addView(content, cp);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, -2);
        bp.topMargin = dp(7);
        transcript.addView(bubble, bp);
        scroll.post(() -> scroll.fullScroll(View.FOCUS_DOWN));
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private GradientDrawable round(int color, int radius) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radius));
        return drawable;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
