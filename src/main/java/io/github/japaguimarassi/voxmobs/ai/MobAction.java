package io.github.japaguimarassi.voxmobs.ai;

import java.util.Locale;

public enum MobAction {
    NONE,
    FOLLOW,
    APPROACH,
    FLEE,
    LOOK,
    SIT,
    JUMP,
    STOP,
    PROTECT,
    PICKUP_ITEM,
    DROP_ITEM,
    SPAWN_MOB;

    public static MobAction safeParse(String value) {
        if (value == null || value.isBlank()) {
            return NONE;
        }
        try {
            return valueOf(value.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ignored) {
            return NONE;
        }
    }
}
