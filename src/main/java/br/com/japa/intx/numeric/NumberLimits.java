package br.com.japa.intx.numeric;

import java.math.BigInteger;

public final class NumberLimits {
    public static final int MAX_KEY_LENGTH = 64;
    public static final int MAX_WIRE_DIGITS = 16384;
    private static volatile int maxDigits = 4096;
    private static volatile int maxEntries = 128;

    private NumberLimits() {
    }

    public static void configure(int digits, int entries) {
        if (digits < 1 || digits > MAX_WIRE_DIGITS) {
            throw new IllegalArgumentException("maxDigits must be between 1 and " + MAX_WIRE_DIGITS);
        }
        if (entries < 1 || entries > 512) {
            throw new IllegalArgumentException("maxEntries must be between 1 and 512");
        }
        maxDigits = digits;
        maxEntries = entries;
    }

    public static int getMaxDigits() { return maxDigits; }
    public static int getMaxEntries() { return maxEntries; }

    public static boolean isValidKey(String key) {
        if (key == null || key.length() < 1 || key.length() > MAX_KEY_LENGTH) return false;
        for (int i = 0; i < key.length(); i++) {
            char c = key.charAt(i);
            if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.')) return false;
        }
        return true;
    }

    public static String requireKey(String key) {
        if (!isValidKey(key)) {
            throw new IllegalArgumentException("Invalid key: use 1-64 letters, digits, _, -, or .");
        }
        return key;
    }

    public static BigInteger parse(String raw) {
        if (raw == null) throw new IllegalArgumentException("Missing numeric value");
        String value = raw.trim();
        int sign = value.startsWith("-") || value.startsWith("+") ? 1 : 0;
        int digits = value.length() - sign;
        if (digits < 1) throw new IllegalArgumentException("Invalid integer");
        if (digits > maxDigits) {
            throw new IllegalArgumentException("Value exceeds the configured " + maxDigits + " digit limit");
        }
        validateDecimal(value, sign);
        return validate(new BigInteger(value));
    }

    public static BigInteger parseWireValue(String raw) {
        if (raw == null) throw new IllegalArgumentException("Missing network value");
        int sign = raw.startsWith("-") || raw.startsWith("+") ? 1 : 0;
        int digits = raw.length() - sign;
        if (digits < 1 || digits > MAX_WIRE_DIGITS) {
            throw new IllegalArgumentException("Invalid network value length");
        }
        validateDecimal(raw, sign);
        return new BigInteger(raw);
    }

    public static BigInteger validate(BigInteger value) {
        if (value == null) throw new IllegalArgumentException("Numeric value cannot be null");
        int digits = value.signum() == 0 ? 1 : value.abs().toString().length();
        if (digits > maxDigits) {
            throw new IllegalArgumentException("Value exceeds the configured " + maxDigits + " digit limit");
        }
        return value;
    }

    private static void validateDecimal(String value, int offset) {
        for (int i = offset; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c < '0' || c > '9') {
                throw new IllegalArgumentException("Only base-10 integers are accepted");
            }
        }
    }
}
