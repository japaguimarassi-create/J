package io.github.japaguimarassi.voxmobs.speech;

import java.io.ByteArrayOutputStream;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class FormantTtsEngine {
    public static final int SAMPLE_RATE = 22050;
    private static final double TWO_PI = Math.PI * 2.0D;

    private FormantTtsEngine() {
    }

    public static byte[] synthesize(String input, VoiceProfile profile) {
        String text = normalize(input);
        if (text.isBlank()) {
            return new byte[0];
        }
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        List<String> words = splitWords(text);
        for (int i = 0; i < words.size(); i++) {
            String word = words.get(i);
            synthesizeWord(output, word, profile);
            appendSilence(output, word.endsWith(".") || word.endsWith("?") || word.endsWith("!") ? 150 : 65);
            if (output.size() > SAMPLE_RATE * 2 * 24) {
                break;
            }
        }
        return output.toByteArray();
    }

    private static String normalize(String text) {
        if (text == null) {
            return "";
        }
        String value = Normalizer.normalize(text.trim().toLowerCase(Locale.ROOT), Normalizer.Form.NFC);
        return value.replaceAll("[^\\p{L}0-9.,!?;:' -]", " ").replaceAll("\\s+", " ").trim();
    }

    private static List<String> splitWords(String text) {
        List<String> result = new ArrayList<>();
        for (String part : text.split("\\s+")) {
            if (!part.isBlank()) {
                result.add(part);
            }
        }
        return result;
    }

    private static void synthesizeWord(ByteArrayOutputStream output, String word, VoiceProfile profile) {
        StringBuilder normalized = new StringBuilder();
        for (int i = 0; i < word.length(); i++) {
            char c = word.charAt(i);
            if (Character.isLetter(c)) {
                normalized.append(c);
            }
        }
        String value = normalized.toString();
        if (value.isEmpty()) {
            return;
        }
        int index = 0;
        while (index < value.length()) {
            String pair = index + 1 < value.length() ? value.substring(index, index + 2) : "";
            if (pair.equals("ch")) {
                renderNoise(output, 0.075D, profile, 0.7D);
                index += 2;
                continue;
            }
            if (pair.equals("lh") || pair.equals("nh")) {
                renderNasal(output, profile, pair.equals("nh") ? 0.058D : 0.064D);
                index += 2;
                continue;
            }
            if (pair.equals("rr") || pair.equals("ss")) {
                if (pair.equals("ss")) {
                    renderNoise(output, 0.065D, profile, 0.8D);
                } else {
                    renderVoiced(output, profile.pitch() * 1.1D, 0.045D, profile.brightness());
                }
                index += 2;
                continue;
            }
            char c = value.charAt(index++);
            switch (c) {
                case 'a', 'á', 'à', 'â', 'ã' -> renderVowel(output, profile, 800.0D, 1200.0D, 2550.0D, c == 'ã' ? 0.22D : profile.nasal());
                case 'e', 'é', 'ê' -> renderVowel(output, profile, 520.0D, 1850.0D, 2650.0D, profile.nasal());
                case 'i', 'í' -> renderVowel(output, profile, 320.0D, 2200.0D, 3000.0D, profile.nasal());
                case 'o', 'ó', 'ô', 'õ' -> renderVowel(output, profile, 500.0D, 950.0D, 2500.0D, c == 'õ' ? 0.24D : profile.nasal());
                case 'u', 'ú' -> renderVowel(output, profile, 350.0D, 850.0D, 2200.0D, profile.nasal());
                case 'm', 'n' -> renderNasal(output, profile, 0.065D);
                case 's', 'f', 'x' -> renderNoise(output, 0.055D, profile, c == 's' ? 1.0D : 0.72D);
                case 'r' -> renderVoiced(output, profile.pitch() * 1.06D, 0.045D, profile.brightness());
                case 'l' -> renderVoiced(output, profile.pitch(), 0.05D, profile.brightness() * 0.9D);
                case 'b', 'd', 'g', 'v', 'z', 'j' -> renderVoiced(output, profile.pitch() * 1.12D, 0.045D, profile.brightness());
                case 'p', 't', 'k', 'q', 'c' -> renderStop(output, profile);
                case 'h' -> {
                }
                case 'w' -> renderVowel(output, profile, 350.0D, 850.0D, 2200.0D, profile.nasal());
                case 'y' -> renderVowel(output, profile, 320.0D, 2200.0D, 3000.0D, profile.nasal());
                default -> renderVowel(output, profile, 520.0D, 1400.0D, 2500.0D, profile.nasal());
            }
            if (index < value.length() && isVowel(value.charAt(index))) {
                appendSilence(output, 7);
            }
        }
    }

    private static boolean isVowel(char c) {
        return "aeiouáàâãéêíóôõú".indexOf(c) >= 0;
    }

    private static void renderVowel(ByteArrayOutputStream output, VoiceProfile profile,
                                    double f1, double f2, double f3, double nasal) {
        int count = Math.max(1, (int) (SAMPLE_RATE * 0.095D / profile.speed()));
        byte[] samples = new byte[count * 2];
        double fundamental = profile.pitch();
        double bandwidth = 150.0D;
        for (int i = 0; i < count; i++) {
            double t = i / (double) SAMPLE_RATE;
            double envelope = Math.min(1.0D, i / 280.0D) * Math.min(1.0D, (count - i) / 320.0D);
            double sample = 0.0D;
            for (int harmonic = 1; harmonic <= 34; harmonic++) {
                double hz = fundamental * harmonic;
                double resonance = gaussian(hz, f1 * profile.formantScale(), bandwidth)
                        + 0.82D * gaussian(hz, f2 * profile.formantScale(), bandwidth * 1.45D)
                        + 0.48D * gaussian(hz, f3 * profile.formantScale(), bandwidth * 1.9D)
                        + nasal * 0.25D * gaussian(hz, 1000.0D, 280.0D);
                sample += Math.sin(TWO_PI * hz * t) * resonance / harmonic;
            }
            double raspNoise = Math.sin(TWO_PI * (71.0D + profile.seed() % 53L) * t) * profile.rasp() * 0.035D;
            sample = (sample + raspNoise) * envelope * profile.brightness() * 0.68D;
            putSample(samples, i, sample);
        }
        output.writeBytes(samples);
    }

    private static void renderNasal(ByteArrayOutputStream output, VoiceProfile profile, double seconds) {
        int count = Math.max(1, (int) (SAMPLE_RATE * seconds / profile.speed()));
        byte[] samples = new byte[count * 2];
        for (int i = 0; i < count; i++) {
            double t = i / (double) SAMPLE_RATE;
            double envelope = Math.min(1.0D, i / 160.0D) * Math.min(1.0D, (count - i) / 210.0D);
            double tone = Math.sin(TWO_PI * profile.pitch() * t) * 0.55D
                    + Math.sin(TWO_PI * profile.pitch() * 2.0D * t) * 0.24D
                    + Math.sin(TWO_PI * profile.pitch() * 3.0D * t) * 0.1D;
            putSample(samples, i, tone * envelope * profile.brightness() * 0.5D);
        }
        output.writeBytes(samples);
    }

    private static void renderVoiced(ByteArrayOutputStream output, double pitch, double seconds, double brightness) {
        int count = Math.max(1, (int) (SAMPLE_RATE * seconds));
        byte[] samples = new byte[count * 2];
        for (int i = 0; i < count; i++) {
            double t = i / (double) SAMPLE_RATE;
            double envelope = Math.min(1.0D, i / 100.0D) * Math.min(1.0D, (count - i) / 130.0D);
            double tone = Math.sin(TWO_PI * pitch * t) * 0.6D
                    + Math.sin(TWO_PI * pitch * 2.0D * t) * 0.2D
                    + Math.sin(TWO_PI * pitch * 3.0D * t) * 0.1D;
            putSample(samples, i, tone * envelope * brightness * 0.36D);
        }
        output.writeBytes(samples);
    }

    private static void renderNoise(ByteArrayOutputStream output, double seconds, VoiceProfile profile, double gain) {
        int count = Math.max(1, (int) (SAMPLE_RATE * seconds / profile.speed()));
        byte[] samples = new byte[count * 2];
        long seed = Double.doubleToLongBits(profile.pitch() * seconds * gain);
        for (int i = 0; i < count; i++) {
            seed ^= seed << 13;
            seed ^= seed >>> 7;
            seed ^= seed << 17;
            double noise = ((seed & 0xFFFFL) / 32767.5D) - 1.0D;
            double envelope = Math.min(1.0D, i / 120.0D) * Math.min(1.0D, (count - i) / 180.0D);
            putSample(samples, i, noise * envelope * gain * 0.19D);
        }
        output.writeBytes(samples);
    }

    private static void renderStop(ByteArrayOutputStream output, VoiceProfile profile) {
        renderNoise(output, 0.018D, profile, 0.8D);
        appendSilence(output, 12);
    }

    private static void appendSilence(ByteArrayOutputStream output, int millis) {
        int frames = Math.max(0, SAMPLE_RATE * millis / 1000);
        output.writeBytes(new byte[frames * 2]);
    }

    private static double gaussian(double value, double center, double width) {
        double delta = (value - center) / width;
        return Math.exp(-0.5D * delta * delta);
    }

    private static void putSample(byte[] output, int sampleIndex, double value) {
        int clamped = (int) Math.round(Math.max(-1.0D, Math.min(1.0D, value)) * 27000.0D);
        output[sampleIndex * 2] = (byte) (clamped & 0xFF);
        output[sampleIndex * 2 + 1] = (byte) ((clamped >> 8) & 0xFF);
    }
}
