package com.lokivolt.setup;

import android.app.backup.BackupAgentHelper;
import android.app.backup.SharedPreferencesBackupHelper;

public final class LokivoltBackupAgent extends BackupAgentHelper {
    private static final String PREFS = "lokivolt_roles";

    @Override
    public void onCreate() {
        addHelper("roles", new SharedPreferencesBackupHelper(this, PREFS));
    }
}
