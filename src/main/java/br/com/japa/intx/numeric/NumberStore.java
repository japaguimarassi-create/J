package br.com.japa.intx.numeric;

import net.minecraft.nbt.NBTTagCompound;
import java.math.BigInteger;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

public final class NumberStore {
    private final Map<String, BigInteger> values = new LinkedHashMap<String, BigInteger>();

    public synchronized BigInteger get(String key) {
        NumberLimits.requireKey(key);
        BigInteger value = values.get(key);
        return value == null ? BigInteger.ZERO : value;
    }

    public synchronized boolean contains(String key) {
        NumberLimits.requireKey(key);
        return values.containsKey(key);
    }

    public synchronized void set(String key, BigInteger value) {
        NumberLimits.requireKey(key);
        NumberLimits.validate(value);
        if (!values.containsKey(key) && values.size() >= NumberLimits.getMaxEntries()) {
            throw new IllegalStateException("Player reached the configured numeric-entry limit");
        }
        values.put(key, value);
    }

    public synchronized BigInteger add(String key, BigInteger amount) {
        NumberLimits.validate(amount);
        BigInteger result = get(key).add(amount);
        NumberLimits.validate(result);
        set(key, result);
        return result;
    }

    public synchronized void remove(String key) {
        NumberLimits.requireKey(key);
        values.remove(key);
    }

    public synchronized Map<String, BigInteger> snapshot() {
        return Collections.unmodifiableMap(new LinkedHashMap<String, BigInteger>(values));
    }

    public synchronized void replace(Map<String, BigInteger> replacement) {
        values.clear();
        if (replacement == null) return;
        for (Map.Entry<String, BigInteger> entry : replacement.entrySet()) {
            if (values.size() >= NumberLimits.getMaxEntries()) break;
            try {
                set(entry.getKey(), entry.getValue());
            } catch (IllegalArgumentException ignored) {
            }
        }
    }

    public synchronized void copyFrom(NumberStore source) {
        replace(source == null ? null : source.snapshot());
    }

    public synchronized NBTTagCompound writeToNBT() {
        NBTTagCompound root = new NBTTagCompound();
        NBTTagCompound saved = new NBTTagCompound();
        for (Map.Entry<String, BigInteger> entry : values.entrySet()) {
            saved.setString(entry.getKey(), entry.getValue().toString());
        }
        root.setInteger("schema", 1);
        root.setTag("values", saved);
        return root;
    }

    public synchronized void readFromNBT(NBTTagCompound root) {
        values.clear();
        if (root == null || !root.hasKey("values", 10)) return;
        NBTTagCompound saved = root.getCompoundTag("values");
        Set<?> keys = saved.func_150296_c();
        for (Object raw : keys) {
            if (values.size() >= NumberLimits.getMaxEntries()) break;
            if (!(raw instanceof String)) continue;
            String key = (String) raw;
            try {
                if (NumberLimits.isValidKey(key)) set(key, NumberLimits.parse(saved.getString(key)));
            } catch (RuntimeException ignored) {
            }
        }
    }
}
