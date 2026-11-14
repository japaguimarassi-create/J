package br.com.japa.intx.core;

import net.minecraft.entity.DataWatcher;
import net.minecraft.network.PacketBuffer;

public final class LongDataWatcherHooks {
    private LongDataWatcherHooks() { }

    public static void writeLong(PacketBuffer buffer, DataWatcher.WatchableObject object) {
        Object value = object.getObject();
        if (!(value instanceof Long)) {
            throw new IllegalArgumentException("DataWatcher type 7 requires java.lang.Long");
        }
        buffer.writeLong(((Long) value).longValue());
    }

    public static DataWatcher.WatchableObject readLong(PacketBuffer buffer, int type, int id) {
        return new DataWatcher.WatchableObject(type, id, Long.valueOf(buffer.readLong()));
    }
}
