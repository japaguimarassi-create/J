package io.github.japaguimarassi.voxmobs.client;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.TargetDataLine;
import javax.sound.sampled.AudioSystem;
import java.io.ByteArrayOutputStream;

public final class MicrophoneCapture {
    private static final float CAPTURE_RATE = 44100.0F;
    private final AudioFormat format = new AudioFormat(CAPTURE_RATE, 16, 1, true, false);
    private final ByteArrayOutputStream captured = new ByteArrayOutputStream();
    private volatile boolean running;
    private TargetDataLine line;
    private Thread reader;

    public void start() throws Exception {
        DataLine.Info info = new DataLine.Info(TargetDataLine.class, format);
        line = (TargetDataLine) AudioSystem.getLine(info);
        line.open(format, 8192);
        line.start();
        running = true;
        reader = new Thread(this::readLoop, "VoxMobs-Microphone");
        reader.setDaemon(true);
        try {
            reader.start();
        } catch (RuntimeException exception) {
            running = false;
            line.stop();
            line.close();
            line = null;
            reader = null;
            throw exception;
        }
    }

    public byte[] stopAs16kMono() {
        running = false;
        if (line != null) {
            try {
                line.stop();
            } catch (RuntimeException ignored) {
            }
            try {
                line.close();
            } catch (RuntimeException ignored) {
            }
        }
        if (reader != null) {
            try {
                reader.join(1200L);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
            }
        }
        byte[] recording;
        synchronized (captured) {
            recording = captured.toByteArray();
        }
        return resample(recording, (int) CAPTURE_RATE, 16000);
    }

    private void readLoop() {
        byte[] buffer = new byte[4096];
        while (running && line != null) {
            int count;
            try {
                count = line.read(buffer, 0, buffer.length);
            } catch (IllegalStateException exception) {
                break;
            }
            if (count > 0) {
                synchronized (captured) {
                    if (captured.size() < 44100 * 2 * 20) {
                        captured.write(buffer, 0, count);
                    }
                }
            } else if (count < 0) {
                break;
            }
        }
    }

    private static byte[] resample(byte[] input, int inputRate, int outputRate) {
        int inputSamples = input.length / 2;
        if (inputSamples == 0) {
            return new byte[0];
        }
        int outputSamples = (int) Math.floor(inputSamples * (outputRate / (double) inputRate));
        byte[] output = new byte[outputSamples * 2];
        for (int i = 0; i < outputSamples; i++) {
            double sourcePosition = i * (inputRate / (double) outputRate);
            int left = Math.min(inputSamples - 1, (int) sourcePosition);
            int right = Math.min(inputSamples - 1, left + 1);
            double fraction = sourcePosition - left;
            short a = readShort(input, left * 2);
            short b = readShort(input, right * 2);
            short value = (short) Math.round(a + (b - a) * fraction);
            output[i * 2] = (byte) (value & 0xFF);
            output[i * 2 + 1] = (byte) ((value >> 8) & 0xFF);
        }
        return output;
    }

    private static short readShort(byte[] data, int offset) {
        return (short) ((data[offset] & 0xFF) | (data[offset + 1] << 8));
    }
}
