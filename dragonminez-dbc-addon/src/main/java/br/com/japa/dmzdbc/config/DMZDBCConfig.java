package br.com.japa.dmzdbc.config;

import java.io.File;
import net.minecraftforge.common.config.Configuration;

public final class DMZDBCConfig {
    public static int MAX_ENERGY = 100;
    public static int ENERGY_COST = 30;
    public static int ACTIVE_TICKS = 160;
    public static int COOLDOWN_TICKS = 600;
    public static int REGEN_INTERVAL_TICKS = 20;
    public static float DODGE_CHANCE = 0.20F;

    private DMZDBCConfig() {
    }

    public static void load(File file) {
        Configuration config = new Configuration(file);
        config.load();

        MAX_ENERGY = config.getInt("maxEnergy", "divine", 100, 1, 1000, "Maximum Divine Energy.");
        ENERGY_COST = config.getInt("energyCost", "divine", 30, 1, 1000, "Energy cost to activate Divine Instinct.");
        ACTIVE_TICKS = config.getInt("activeTicks", "divine", 160, 20, 12000, "Ability duration in ticks.");
        COOLDOWN_TICKS = config.getInt("cooldownTicks", "divine", 600, 20, 24000, "Ability cooldown in ticks.");
        REGEN_INTERVAL_TICKS = config.getInt("regenIntervalTicks", "divine", 20, 1, 1200, "Ticks per point of energy regenerated.");
        DODGE_CHANCE = config.getInt("dodgeChancePercent", "divine", 20, 0, 100, "Chance to evade direct incoming damage while active.") / 100.0F;

        if (config.hasChanged()) {
            config.save();
        }
    }
}
