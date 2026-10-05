package com.lokivolt.setup;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final String PREFS = "lokivolt_roles";
    private static final String EMAIL_1 = "email_1";
    private static final String EMAIL_2 = "email_2";

    private EditText securityEmail;
    private EditText restoreEmail;
    private TextView status;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        buildUi();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 60, 48, 48);
        root.setGravity(Gravity.CENTER_HORIZONTAL);

        TextView title = new TextView(this);
        title.setText("LOKIVOLT");
        title.setTextSize(34);
        title.setGravity(Gravity.CENTER);
        root.addView(title, full());

        TextView subtitle = new TextView(this);
        subtitle.setText("Reset, verify, restore");
        subtitle.setTextSize(18);
        subtitle.setGravity(Gravity.CENTER);
        root.addView(subtitle, full());

        securityEmail = field("Security Account · EMAIL 1");
        restoreEmail = field("Restore Account · EMAIL 2");
        root.addView(securityEmail, full());
        root.addView(restoreEmail, full());

        Button save = button("Save account roles");
        save.setOnClickListener(v -> saveRoles());
        root.addView(save, full());

        Button backup = button("Open backup settings");
        backup.setOnClickListener(v -> openSettings(Settings.ACTION_SETTINGS));
        root.addView(backup, full());

        Button passwords = button("Open password manager");
        passwords.setOnClickListener(v -> {
            Intent i = new Intent(Intent.ACTION_VIEW);
            i.setData(android.net.Uri.parse("https://passwords.google.com/"));
            startActivity(i);
        });
        root.addView(passwords, full());

        Button reset = button("Open factory reset settings");
        reset.setOnClickListener(v -> openSettings(Settings.ACTION_PRIVACY_SETTINGS));
        root.addView(reset, full());

        status = new TextView(this);
        status.setTextSize(15);
        status.setPadding(0, 30, 0, 0);
        root.addView(status, full());

        loadRoles();
        setContentView(root);
    }

    private EditText field(String hint) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setSingleLine(true);
        e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        e.setPadding(0, 28, 0, 18);
        return e;
    }

    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        return b;
    }

    private LinearLayout.LayoutParams full() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
    }

    private void saveRoles() {
        String e1 = securityEmail.getText().toString().trim().toLowerCase();
        String e2 = restoreEmail.getText().toString().trim().toLowerCase();
        if (!validEmail(e1) || !validEmail(e2)) {
            Toast.makeText(this, "Enter two valid email addresses", Toast.LENGTH_LONG).show();
            return;
        }
        if (e1.equals(e2)) {
            Toast.makeText(this, "EMAIL 1 and EMAIL 2 must be different", Toast.LENGTH_LONG).show();
            return;
        }
        prefs.edit().putString(EMAIL_1, e1).putString(EMAIL_2, e2).apply();
        status.setText("Saved: EMAIL 1 security · EMAIL 2 restore");
        Toast.makeText(this, "Lokivolt account roles saved", Toast.LENGTH_SHORT).show();
    }

    private void loadRoles() {
        String e1 = prefs.getString(EMAIL_1, "");
        String e2 = prefs.getString(EMAIL_2, "");
        securityEmail.setText(e1);
        restoreEmail.setText(e2);
        status.setText(e1.isEmpty() || e2.isEmpty()
                ? "Set both accounts before a reset"
                : "EMAIL 1 security · EMAIL 2 restore");
    }

    private boolean validEmail(String value) {
        return value.contains("@") && value.indexOf('@') > 0 && value.indexOf('@') < value.length() - 1;
    }

    private void openSettings(String action) {
        try {
            startActivity(new Intent(action));
        } catch (Exception e) {
            startActivity(new Intent(Settings.ACTION_SETTINGS));
        }
    }
}
