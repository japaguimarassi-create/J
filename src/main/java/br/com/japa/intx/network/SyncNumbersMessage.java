package br.com.japa.intx.network;

import br.com.japa.intx.numeric.NumberLimits;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import io.netty.buffer.ByteBuf;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public final class SyncNumbersMessage implements IMessage {
    private static final int PROTOCOL = 1;
    private static final int MAX_ENTRIES = 512;
    private Map<String, BigInteger> values = new LinkedHashMap<String, BigInteger>();

    public SyncNumbersMessage() { }

    public SyncNumbersMessage(Map<String, BigInteger> source) {
        if (source != null) values.putAll(source);
    }

    public Map<String, BigInteger> getValues() {
        return Collections.unmodifiableMap(values);
    }

    @Override
    public void toBytes(ByteBuf buffer) {
        if (values.size() > MAX_ENTRIES) throw new IllegalArgumentException("Too many values");
        buffer.writeByte(PROTOCOL);
        buffer.writeShort(values.size());
        for (Map.Entry<String, BigInteger> entry : values.entrySet()) {
            writeString(buffer, NumberLimits.requireKey(entry.getKey()), 64);
            writeString(buffer, NumberLimits.validate(entry.getValue()).toString(), NumberLimits.MAX_WIRE_DIGITS + 1);
        }
    }

    @Override
    public void fromBytes(ByteBuf buffer) {
        int version = buffer.readUnsignedByte();
        if (version != PROTOCOL) throw new IllegalArgumentException("Unsupported IntX protocol " + version);
        int count = buffer.readUnsignedShort();
        if (count > MAX_ENTRIES) throw new IllegalArgumentException("Too many IntX entries");
        Map<String, BigInteger> decoded = new LinkedHashMap<String, BigInteger>();
        for (int i = 0; i < count; i++) {
            String key = readString(buffer, 64);
            String number = readString(buffer, NumberLimits.MAX_WIRE_DIGITS + 1);
            if (!NumberLimits.isValidKey(key) || decoded.containsKey(key)) {
                throw new IllegalArgumentException("Invalid or duplicate IntX key");
            }
            decoded.put(key, NumberLimits.parseWireValue(number));
        }
        values = decoded;
    }

    private static void writeString(ByteBuf buffer, String value, int maxBytes) {
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > maxBytes || bytes.length > 65535) {
            throw new IllegalArgumentException("IntX packet string exceeds its size limit");
        }
        buffer.writeShort(bytes.length);
        buffer.writeBytes(bytes);
    }

    private static String readString(ByteBuf buffer, int maxBytes) {
        int length = buffer.readUnsignedShort();
        if (length > maxBytes || buffer.readableBytes() < length) {
            throw new IllegalArgumentException("Invalid IntX packet string size");
        }
        byte[] bytes = new byte[length];
        buffer.readBytes(bytes);
        return new String(bytes, StandardCharsets.UTF_8);
    }
}
