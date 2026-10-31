package io.github.japaguimarassi.voxmobs.memory;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class MobMemorySavedData extends SavedData {
    private static final String DATA_NAME = "voxmobs_memory";
    private final Map<String, List<String>> conversations = new LinkedHashMap<>();

    public static MobMemorySavedData get(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(
                MobMemorySavedData::load, MobMemorySavedData::new, DATA_NAME);
    }

    public static MobMemorySavedData load(CompoundTag tag) {
        MobMemorySavedData data = new MobMemorySavedData();
        ListTag records = tag.getList("records", Tag.TAG_COMPOUND);
        for (Tag raw : records) {
            CompoundTag record = (CompoundTag) raw;
            ListTag lines = record.getList("lines", Tag.TAG_STRING);
            List<String> values = new ArrayList<>();
            for (Tag line : lines) {
                values.add(line.getAsString());
            }
            data.conversations.put(record.getString("key"), values);
        }
        return data;
    }

    public List<String> getHistory(UUID mobId, UUID playerId, int maxLines) {
        List<String> lines = conversations.getOrDefault(key(mobId, playerId), List.of());
        int start = Math.max(0, lines.size() - Math.max(0, maxLines));
        return new ArrayList<>(lines.subList(start, lines.size()));
    }

    public void add(UUID mobId, UUID playerId, String line, int maxLines) {
        String key = key(mobId, playerId);
        List<String> lines = conversations.computeIfAbsent(key, ignored -> new ArrayList<>());
        lines.add(line.length() > 500 ? line.substring(0, 500) : line);
        int limit = Math.max(2, maxLines);
        while (lines.size() > limit) {
            lines.remove(0);
        }
        setDirty();
    }

    public void forgetPlayer(UUID playerId) {
        String suffix = ":" + playerId;
        conversations.keySet().removeIf(key -> key.endsWith(suffix));
        setDirty();
    }

    @Override
    public CompoundTag save(CompoundTag tag) {
        ListTag records = new ListTag();
        conversations.forEach((key, lines) -> {
            CompoundTag record = new CompoundTag();
            record.putString("key", key);
            ListTag lineTags = new ListTag();
            for (String line : lines) {
                lineTags.add(StringTag.valueOf(line));
            }
            record.put("lines", lineTags);
            records.add(record);
        });
        tag.put("records", records);
        return tag;
    }

    private static String key(UUID mobId, UUID playerId) {
        return mobId + ":" + playerId;
    }
}
