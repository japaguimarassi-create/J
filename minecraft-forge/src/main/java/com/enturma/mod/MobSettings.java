package com.enturma.mod;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraftforge.fml.loading.FMLPaths;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

public final class MobSettings {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Pattern RESOURCE_ID = Pattern.compile("[a-z0-9_.-]+:[a-z0-9/._-]+");
    private static final Path FILE = FMLPaths.CONFIGDIR.get().resolve("enturma-mobs.json");
    private static volatile boolean allMobs = false;
    private static volatile Set<String> entityIds = new LinkedHashSet<>(List.of("minecraft:villager", "minecraft:wandering_trader", "minecraft:iron_golem"));

    private static final class SettingsFile {
        boolean allMobs;
        List<String> entityIds = new ArrayList<>();
    }

    private MobSettings() {}

    public static synchronized void reload() {
        try {
            if (!Files.exists(FILE)) {
                save(allMobs, String.join(",", entityIds));
                return;
            }
            SettingsFile loaded = GSON.fromJson(Files.readString(FILE, StandardCharsets.UTF_8), SettingsFile.class);
            if (loaded == null) return;
            allMobs = loaded.allMobs;
            Set<String> next = new LinkedHashSet<>();
            if (loaded.entityIds != null) {
                for (String id : loaded.entityIds) {
                    String clean = id == null ? "" : id.trim().toLowerCase(Locale.ROOT);
                    if (RESOURCE_ID.matcher(clean).matches()) next.add(clean);
                }
            }
            entityIds = next;
        } catch (Exception ignored) {
        }
    }

    public static synchronized void save(boolean enableAll, String csv) {
        Set<String> next = new LinkedHashSet<>();
        if (csv != null) {
            for (String raw : csv.split(",")) {
                String id = raw.trim().toLowerCase(Locale.ROOT);
                if (RESOURCE_ID.matcher(id).matches()) next.add(id);
            }
        }
        allMobs = enableAll;
        entityIds = next;
        try {
            Files.createDirectories(FILE.getParent());
            SettingsFile data = new SettingsFile();
            data.allMobs = allMobs;
            data.entityIds = new ArrayList<>(entityIds);
            Files.writeString(FILE, GSON.toJson(data), StandardCharsets.UTF_8);
        } catch (IOException exception) {
            throw new IllegalStateException("Não foi possível salvar config/enturma-mobs.json", exception);
        }
    }

    public static boolean allows(Entity entity) {
        if (!(entity instanceof Mob) || entity instanceof net.minecraft.world.entity.player.Player) return false;
        if (allMobs) return true;
        String id = BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString();
        return entityIds.contains(id);
    }

    public static boolean allMobsEnabled() { return allMobs; }
    public static synchronized String idsCsv() { return String.join(", ", entityIds); }
}
