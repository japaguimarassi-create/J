package br.com.japa.intx.numeric;

import org.junit.Test;
import java.math.BigInteger;
import static org.junit.Assert.assertEquals;

public class NumberFormatterTest {
    @Test
    public void formatsThousands() {
        assertEquals("1.2K", NumberFormatter.compact(new BigInteger("1200")));
    }

    @Test
    public void formatsNegativeValues() {
        assertEquals("-1.2K", NumberFormatter.compact(new BigInteger("-1200")));
    }

    @Test
    public void formatsVeryLargeValues() {
        assertEquals("1.00e36", NumberFormatter.compact(
            new BigInteger("1000000000000000000000000000000000000")));
    }
}
