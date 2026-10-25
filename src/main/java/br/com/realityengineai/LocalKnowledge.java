package br.com.realityengineai;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;

public final class LocalKnowledge {
    private static final String[] RESOURCES = {
        "/assets/realityengineai/knowledge/forge_1710.txt",
        "/assets/realityengineai/knowledge/minecraft_1710.txt",
        "/assets/realityengineai/knowledge/mod_compatibility.txt"
    };
    private static final Pattern WORDS = Pattern.compile("[a-z0-9]+");

    private LocalKnowledge() {
    }

    public static void sendRelevantNotes(EntityPlayer player, String query) {
        List<Note> notes = new ArrayList<Note>();
        Set<String> queryWords = words(query);
        for (String resource : RESOURCES) {
            InputStream stream = LocalKnowledge.class.getResourceAsStream(resource);
            if (stream == null) {
                continue;
            }
            BufferedReader reader = null;
            try {
                reader = new BufferedReader(new InputStreamReader(stream, "UTF-8"));
                String line;
                while ((line = reader.readLine()) != null) {
                    String cleaned = line.trim();
                    if (cleaned.isEmpty() || cleaned.startsWith("#") || cleaned.endsWith(":")) {
                        continue;
                    }
                    int score = 0;
                    Set<String> lineWords = words(cleaned);
                    for (String word : queryWords) {
                        if (lineWords.contains(word)) {
                            score++;
                        }
                    }
                    if (score > 0) {
                        notes.add(new Note(cleaned, score));
                    }
                }
            } catch (IOException exception) {
                RealityEngineAI.LOG.warn("Could not read local knowledge resource " + resource, exception);
            } finally {
                if (reader != null) {
                    try {
                        reader.close();
                    } catch (IOException ignored) {
                    }
                } else {
                    try {
                        stream.close();
                    } catch (IOException ignored) {
                    }
                }
            }
        }
        Collections.sort(notes, new Comparator<Note>() {
            @Override
            public int compare(Note left, Note right) {
                return right.score - left.score;
            }
        });
        player.addChatMessage(new ChatComponentText("Base de conhecimento offline:"));
        int sent = 0;
        Set<String> unique = new HashSet<String>();
        for (Note note : notes) {
            if (unique.add(note.text)) {
                player.addChatMessage(new ChatComponentText("- " + note.text));
                sent++;
                if (sent >= 5) {
                    break;
                }
            }
        }
        if (sent == 0) {
            player.addChatMessage(new ChatComponentText("A base contém referências de Forge 1.7.10, texturas, registries e dimensões; faça uma pergunta mais específica."));
        }
        player.addChatMessage(new ChatComponentText("As notas offline não equivalem a uma IA geral nem a uma integração automática com todos os mods."));
    }

    private static Set<String> words(String text) {
        String normalized = java.text.Normalizer.normalize(text == null ? "" : text.toLowerCase(Locale.ROOT), java.text.Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        Matcher matcher = WORDS.matcher(normalized);
        Set<String> result = new HashSet<String>();
        while (matcher.find()) {
            String word = matcher.group();
            if (word.length() > 2) {
                result.add(word);
            }
        }
        return result;
    }

    private static final class Note {
        private final String text;
        private final int score;

        private Note(String text, int score) {
            this.text = text;
            this.score = score;
        }
    }
}
