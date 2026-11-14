package br.com.japa.intx.config;

import br.com.japa.intx.numeric.NumberLimits;
import net.minecraftforge.common.config.Configuration;
import java.io.File;

public final class IntXConfig {
    public static int maxDigits = 4096;
    public static int maxEntries = 128;
    public static boolean showHud = false;

    private IntXConfig() {
    }

    public static void load(File file) {
        Configuration config = new Configuration(file);
        try {
            config.load();
            maxDigits = config.getInt("maximumDigits", "limits", 4096, 1, 16384,
                "Maximum decimal digits accepted for each player value.");
            maxEntries = config.getInt("maximumEntriesPerPlayer", "limits", 128, 1, 512,
                "Maximum distinct numeric keys per player.");
            showHud = config.getBoolean("showHud", "client", false,
                "Display synchronized IntX values in the upper-left HUD.");
        } finally {
            if (config.hasChanged()) {
                config.save();
            }
        }
        NumberLimits.configure(maxDigits, maxEntries);
    }
}
