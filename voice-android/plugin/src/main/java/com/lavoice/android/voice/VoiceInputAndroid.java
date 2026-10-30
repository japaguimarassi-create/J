package com.lavoice.android.voice;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.speech.RecognizerIntent;

import org.godotengine.godot.Godot;
import org.godotengine.godot.plugin.GodotPlugin;
import org.godotengine.godot.plugin.SignalInfo;
import org.godotengine.godot.plugin.UsedByGodot;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;

public final class VoiceInputAndroid extends GodotPlugin {
    private static final int SPEECH_REQUEST_CODE = 45017;
    private static final String SIGNAL_RESULT = "speech_result";
    private static final String SIGNAL_ERROR = "speech_error";

    public VoiceInputAndroid(Godot godot) {
        super(godot);
    }

    @Override
    public String getPluginName() {
        return "VoiceInputAndroid";
    }

    @Override
    public Set<SignalInfo> getPluginSignals() {
        Set<SignalInfo> signals = new HashSet<>();
        signals.add(new SignalInfo(SIGNAL_RESULT, String.class));
        signals.add(new SignalInfo(SIGNAL_ERROR, Integer.class));
        return signals;
    }

    @UsedByGodot
    public void startRecognition() {
        runOnHostThread(() -> {
            Activity host = getActivity();
            if (host == null) {
                emitSignal(SIGNAL_ERROR, -1);
                return;
            }

            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR");
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "pt-BR");
            intent.putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Descreva a arma que deseja criar");

            try {
                host.startActivityForResult(intent, SPEECH_REQUEST_CODE);
            } catch (ActivityNotFoundException exception) {
                emitSignal(SIGNAL_ERROR, -2);
            }
        });
    }

    @Override
    public void onMainActivityResult(int requestCode, int resultCode, Intent data) {
        super.onMainActivityResult(requestCode, resultCode, data);
        if (requestCode != SPEECH_REQUEST_CODE) {
            return;
        }

        if (resultCode != Activity.RESULT_OK || data == null) {
            emitSignal(SIGNAL_ERROR, resultCode);
            return;
        }

        ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
        if (results == null || results.isEmpty() || results.get(0) == null || results.get(0).trim().isEmpty()) {
            emitSignal(SIGNAL_ERROR, -3);
            return;
        }

        emitSignal(SIGNAL_RESULT, results.get(0).trim());
    }
}
