package br.com.japa.intx.numeric;

import org.junit.Before;
import org.junit.Test;
import java.math.BigInteger;
import static org.junit.Assert.*;

public class NumberLimitsTest {
    @Before
    public void reset() { NumberLimits.configure(4096, 128); }

    @Test
    public void parsesValuesBeyondIntAndLong() {
        BigInteger value = NumberLimits.parse("922337203685477580812345678901234567890");
        assertEquals("922337203685477580812345678901234567890", value.toString());
    }

    @Test
    public void preservesNegativeValues() {
        assertEquals("-214748364812345678901",
            NumberLimits.parse("-214748364812345678901").toString());
    }

    @Test
    public void rejectsConfiguredDigitOverflow() {
        NumberLimits.configure(4, 12);
        try {
            NumberLimits.parse("12345");
            fail("Expected digit limit rejection");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("digit limit"));
        }
    }

    @Test
    public void validatesKeys() {
        assertTrue(NumberLimits.isValidKey("ki.power_2"));
        assertFalse(NumberLimits.isValidKey("ki power"));
        assertFalse(NumberLimits.isValidKey(""));
    }
}
