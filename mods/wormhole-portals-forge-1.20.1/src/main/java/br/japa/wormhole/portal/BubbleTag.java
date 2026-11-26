package br.japa.wormhole.portal;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;

import java.util.Locale;

public record BubbleTag(
    String linkId,
    String side,
    ResourceLocation sourceDimension,
    ResourceLocation destinationDimension,
    Vec3 center,
    Vec3 targetCenter,
    double radius,
    double activationRange,
    boolean border,
    boolean enabled
) {
    public static final String PREFIX = "wp1|";

    public String encode() {
        return String.format(Locale.ROOT,
            "wp1|%s|%s|%s|%s|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%s|%s",
            linkId, side, sourceDimension, destinationDimension,
            center.x, center.y, center.z,
            targetCenter.x, targetCenter.y, targetCenter.z,
            radius, activationRange, border, enabled
        );
    }

    public BubbleTag withRange(double value) {
        return new BubbleTag(linkId, side, sourceDimension, destinationDimension, center, targetCenter, radius, value, border, enabled);
    }

    public BubbleTag withEnabled(boolean value) {
        return new BubbleTag(linkId, side, sourceDimension, destinationDimension, center, targetCenter, radius, activationRange, border, value);
    }

    public static BubbleTag parse(String raw) {
        if (raw == null || !raw.startsWith(PREFIX)) return null;
        try {
            String[] p = raw.split("\\|", -1);
            if (p.length != 15) return null;
            ResourceLocation from = ResourceLocation.tryParse(p[3]);
            ResourceLocation to = ResourceLocation.tryParse(p[4]);
            if (from == null || to == null) return null;
            return new BubbleTag(
                p[1], p[2], from, to,
                new Vec3(Double.parseDouble(p[5]), Double.parseDouble(p[6]), Double.parseDouble(p[7])),
                new Vec3(Double.parseDouble(p[8]), Double.parseDouble(p[9]), Double.parseDouble(p[10])),
                Double.parseDouble(p[11]), Double.parseDouble(p[12]),
                Boolean.parseBoolean(p[13]), Boolean.parseBoolean(p[14])
            );
        } catch (RuntimeException ignored) {
            return null;
        }
    }
}
