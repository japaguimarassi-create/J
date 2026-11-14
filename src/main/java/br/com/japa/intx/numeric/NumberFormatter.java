package br.com.japa.intx.numeric;

import java.math.BigInteger;

public final class NumberFormatter {
    private static final String[] SUFFIXES = {
        "", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"
    };

    private NumberFormatter() {
    }

    public static String compact(BigInteger value) {
        if (value == null || value.signum() == 0) return "0";
        boolean negative = value.signum() < 0;
        String digits = value.abs().toString();
        if (digits.length() <= 3) return (negative ? "-" : "") + digits;
        int group = (digits.length() - 1) / 3;
        if (group < SUFFIXES.length) {
            BigInteger scaled = value.abs().multiply(BigInteger.TEN)
                .divide(BigInteger.TEN.pow(group * 3));
            return (negative ? "-" : "") + scaled.divide(BigInteger.TEN) + "."
                + scaled.remainder(BigInteger.TEN) + SUFFIXES[group];
        }
        String fraction = digits.substring(1, Math.min(3, digits.length()));
        while (fraction.length() < 2) fraction += "0";
        return (negative ? "-" : "") + digits.charAt(0) + "." + fraction
            + "e" + (digits.length() - 1);
    }
}
