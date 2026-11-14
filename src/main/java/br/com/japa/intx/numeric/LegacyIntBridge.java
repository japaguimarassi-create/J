package br.com.japa.intx.numeric;

import java.math.BigInteger;

public final class LegacyIntBridge {
    private static final BigInteger INT_MIN = BigInteger.valueOf(Integer.MIN_VALUE);
    private static final BigInteger INT_MAX = BigInteger.valueOf(Integer.MAX_VALUE);
    private static final BigInteger LONG_MIN = BigInteger.valueOf(Long.MIN_VALUE);
    private static final BigInteger LONG_MAX = BigInteger.valueOf(Long.MAX_VALUE);

    private LegacyIntBridge() {
    }

    public static int toIntClamped(BigInteger value) {
        if (value.compareTo(INT_MAX) > 0) return Integer.MAX_VALUE;
        if (value.compareTo(INT_MIN) < 0) return Integer.MIN_VALUE;
        return value.intValue();
    }

    public static long toLongClamped(BigInteger value) {
        if (value.compareTo(LONG_MAX) > 0) return Long.MAX_VALUE;
        if (value.compareTo(LONG_MIN) < 0) return Long.MIN_VALUE;
        return value.longValue();
    }

    public static boolean exceedsIntRange(BigInteger value) {
        return value.compareTo(INT_MIN) < 0 || value.compareTo(INT_MAX) > 0;
    }

    public static boolean exceedsLongRange(BigInteger value) {
        return value.compareTo(LONG_MIN) < 0 || value.compareTo(LONG_MAX) > 0;
    }
}
