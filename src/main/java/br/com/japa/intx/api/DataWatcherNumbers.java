package br.com.japa.intx.api;

import br.com.japa.intx.core.IntXRuntime;
import br.com.japa.intx.numeric.NumberLimits;
import net.minecraft.entity.DataWatcher;
import java.math.BigInteger;
import java.util.List;

public final class DataWatcherNumbers {
    private DataWatcherNumbers() {
    }

    public static void addLong(DataWatcher watcher, int id, long value) {
        requireLongPatch();
        watcher.addObject(id, Long.valueOf(value));
    }

    public static void updateLong(DataWatcher watcher, int id, long value) {
        requireLongPatch();
        watcher.updateObject(id, Long.valueOf(value));
    }

    public static long getLong(DataWatcher watcher, int id) {
        requireLongPatch();
        Object value = find(watcher, id);
        if (!(value instanceof Long)) throw new IllegalArgumentException("Entry is not a Long");
        return ((Long) value).longValue();
    }

    public static void addBigInteger(DataWatcher watcher, int id, BigInteger value) {
        watcher.addObject(id, NumberLimits.validate(value).toString());
    }

    public static void updateBigInteger(DataWatcher watcher, int id, BigInteger value) {
        watcher.updateObject(id, NumberLimits.validate(value).toString());
    }

    public static BigInteger getBigInteger(DataWatcher watcher, int id) {
        Object value = find(watcher, id);
        if (!(value instanceof String)) throw new IllegalArgumentException("Entry is not a decimal String");
        return NumberLimits.parse((String) value);
    }

    private static Object find(DataWatcher watcher, int id) {
        if (watcher == null) throw new IllegalArgumentException("DataWatcher cannot be null");
        List<?> watched = watcher.getAllWatched();
        if (watched != null) {
            for (Object raw : watched) {
                DataWatcher.WatchableObject object = (DataWatcher.WatchableObject) raw;
                if (object.getDataValueId() == id) return object.getObject();
            }
        }
        throw new IllegalArgumentException("No DataWatcher entry exists for ID " + id);
    }

    private static void requireLongPatch() {
        if (!IntXRuntime.dataWatcherLongSupported) {
            throw new IllegalStateException("Long DataWatcher type unavailable: CoreMod patch did not apply");
        }
    }
}
