package com.japa.hypercode.core;

import java.util.Locale;

public final class LanguageProfile {
    private static final String[][] WORDS = {
        {"pt", "que", "não", "para", "com", "uma", "você", "como", "isso", "quero", "código", "criar"},
        {"en", "the", "and", "is", "are", "you", "with", "how", "what", "code", "create", "please"},
        {"es", "que", "no", "para", "con", "una", "como", "esto", "quiero", "código", "crear"},
        {"fr", "que", "pas", "pour", "avec", "une", "vous", "comment", "code", "créer", "cela"}
    };

    private LanguageProfile() {
    }

    public static String firstSentence(String text) {
        if (text == null) return "";
        String value = text.trim();
        if (value.isEmpty()) return "";
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '.' || c == '!' || c == '?' || c == '\n') {
                return value.substring(0, i + 1).toLowerCase(Locale.ROOT);
            }
        }
        return value.toLowerCase(Locale.ROOT);
    }

    public static String detect(String text) {
        String sentence = " " + firstSentence(text).replaceAll("[^\\p{L}\\p{N}]+", " ") + " ";
        int bestScore = 0;
        String best = "pt";
        for (String[] row : WORDS) {
            int score = 0;
            for (int i = 1; i < row.length; i++) {
                if (sentence.contains(" " + row[i] + " ")) score++;
            }
            if (score > bestScore) {
                bestScore = score;
                best = row[0];
            }
        }
        return best;
    }

    public static String label(String code) {
        switch (code) {
            case "en": return "English";
            case "es": return "Español";
            case "fr": return "Français";
            default: return "Português";
        }
    }
}
