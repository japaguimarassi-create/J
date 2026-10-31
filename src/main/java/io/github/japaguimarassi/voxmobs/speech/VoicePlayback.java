package io.github.japaguimarassi.voxmobs.speech;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.SourceDataLine;
import javax.sound.sampled.AudioSystem;

public final class VoicePlayback {
    private VoicePlayback() {
    }

    public static void play(byte[] pcm, double volume) {
        if (pcm == null || pcm.length == 0 || volume <= 0.0D) {
            return;
        }
        AudioFormat format = new AudioFormat(FormantTtsEngine.SAMPLE_RATE, 16, 1, true, false);
        SourceDataLine line = null;
        try {
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, format);
            line = (SourceDataLine) AudioSystem.getLine(info);
            line.open(format, Math.min(pcm.length, FormantTtsEngine.SAMPLE_RATE * 2));
            line.start();
            byte[] adjusted = applyVolume(pcm, volume);
            int offset = 0;
            while (offset < adjusted.length) {
                int written = line.write(adjusted, offset, Math.min(4096, adjusted.length - offset));
                if (written <= 0) {
                    break;
                }
                offset += written;
            }
            line.drain();
        } catch (Exception ignored) {
        } finally {
            if (line != null) {
                line.stop();
                line.close();
            }
        }
    }

    private static byte[] applyVolume(byte[] input, double volume) {
        double gain = Math.max(0.0D, Math.min(1.0D, volume));
        byte[] output = new byte[input.length];
        for (int i = 0; i + 1 < input.length; i += 2) {
            int value = (short) ((input[i] & 0xFF) | (input[i + 1] << 8));
            int scaled = (int) Math.round(value * gain);
            scaled = Math.max(Short.MIN_VALUE, Math.min(Short.MAX_VALUE, scaled));
            output[i] = (byte) (scaled & 0xFF);
            output[i + 1] = (byte) ((scaled >> 8) & 0xFF);
        }
        return output;
    }
}
