package br.japa.wormhole.command;

import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.BubbleTag;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.ResourceLocationArgument;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import qouteall.imm_ptl.core.portal.Portal;

import java.util.HashSet;
import java.util.Set;

public final class WormholeCommands {
    private WormholeCommands() {}

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("wormhole")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("place")
                .executes(context -> placeDefault(context.getSource()))
                .then(Commands.argument("dimension", ResourceLocationArgument.id())
                    .executes(context -> place(context.getSource(), ResourceLocationArgument.getId(context, "dimension")))))
            .then(Commands.literal("list").executes(context -> list(context.getSource())))
            .then(Commands.literal("info")
                .then(Commands.argument("id", StringArgumentType.word())
                    .executes(context -> info(context.getSource(), StringArgumentType.getString(context, "id")))))
            .then(Commands.literal("remove")
                .then(Commands.argument("id", StringArgumentType.word())
                    .executes(context -> remove(context.getSource(), StringArgumentType.getString(context, "id")))))
            .then(Commands.literal("size")
                .then(Commands.argument("radius", DoubleArgumentType.doubleArg(1.0, 8.0))
                    .then(Commands.argument("id", StringArgumentType.word())
                        .executes(context -> resize(context.getSource(), DoubleArgumentType.getDouble(context, "radius"), StringArgumentType.getString(context, "id"))))))
            .then(Commands.literal("range")
                .then(Commands.argument("blocks", DoubleArgumentType.doubleArg(2.0, 128.0))
                    .then(Commands.argument("id", StringArgumentType.word())
                        .executes(context -> setRange(context.getSource(), DoubleArgumentType.getDouble(context, "blocks"), StringArgumentType.getString(context, "id"))))))
            .then(Commands.literal("target")
                .then(Commands.argument("dimension", ResourceLocationArgument.id())
                    .then(Commands.argument("id", StringArgumentType.word())
                        .executes(context -> target(context.getSource(), ResourceLocationArgument.getId(context, "dimension"), StringArgumentType.getString(context, "id"))))))
            .then(Commands.literal("link")
                .then(Commands.argument("id", StringArgumentType.word())
                    .executes(context -> enabled(context.getSource(), StringArgumentType.getString(context, "id"), true))))
            .then(Commands.literal("unlink")
                .then(Commands.argument("id", StringArgumentType.word())
                    .executes(context -> enabled(context.getSource(), StringArgumentType.getString(context, "id"), false))))
            .then(Commands.literal("rule")
                .then(Commands.literal("auto")
                    .then(Commands.argument("id", StringArgumentType.word())
                        .executes(context -> ruleAuto(context.getSource(), StringArgumentType.getString(context, "id")))))
                .then(Commands.literal("identity")
                    .then(Commands.argument("id", StringArgumentType.word())
                        .executes(context -> ruleIdentity(context.getSource(), StringArgumentType.getString(context, "id")))))
                .then(Commands.literal("end")
                    .then(Commands.argument("id", StringArgumentType.word())
                        .executes(context -> target(context.getSource(), Level.END.location(), StringArgumentType.getString(context, "id")))))
                .then(Commands.literal("scale")
                    .then(Commands.argument("factor", DoubleArgumentType.doubleArg(0.25, 4.0))
                        .then(Commands.argument("id", StringArgumentType.word())
                            .executes(context -> scale(context.getSource(), DoubleArgumentType.getDouble(context, "factor"), StringArgumentType.getString(context, "id"))))))
                .then(Commands.literal("fixed")
                    .then(Commands.argument("x", DoubleArgumentType.doubleArg())
                        .then(Commands.argument("y", DoubleArgumentType.doubleArg())
                            .then(Commands.argument("z", DoubleArgumentType.doubleArg())
                                .then(Commands.argument("id", StringArgumentType.word())
                                    .executes(context -> fixed(context.getSource(),
                                        DoubleArgumentType.getDouble(context, "x"),
                                        DoubleArgumentType.getDouble(context, "y"),
                                        DoubleArgumentType.getDouble(context, "z"),
                                        StringArgumentType.getString(context, "id"))))))))));
    }

    private static int placeDefault(CommandSourceStack source) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        ResourceLocation destination = player.level().dimension().equals(Level.NETHER) ? Level.OVERWORLD.location() : Level.NETHER.location();
        return place(source, destination);
    }

    private static int place(CommandSourceStack source, ResourceLocation dimension) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, dimension);
        ServerLevel destination = source.getServer().getLevel(key);
        if (destination == null) {
            source.sendFailure(Component.literal("Dimensão não encontrada: " + dimension));
            return 0;
        }
        ServerLevel origin = player.serverLevel();
        Vec3 center = player.position().add(player.getLookAngle().scale(5.0));
        Vec3 target = BubblePortalFactory.defaultDestination(origin, destination, center);
        String id = BubblePortalFactory.createPair(origin, center, destination, target, 2.25, 18.0, false);
        source.sendSuccess(() -> Component.literal("Bolha criada: " + id), true);
        return 1;
    }

    private static int list(CommandSourceStack source) {
        Set<String> ids = new HashSet<>();
        for (ServerLevel level : source.getServer().getAllLevels()) {
            for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
                if (!(entity instanceof Portal portal)) continue;
                BubbleTag tag = BubbleTag.parse(portal.portalTag);
                if (tag != null) ids.add(tag.linkId());
            }
        }
        if (ids.isEmpty()) source.sendSuccess(() -> Component.literal("Nenhuma bolha carregada."), false);
        else source.sendSuccess(() -> Component.literal("Bolhas carregadas (" + ids.size() + "): " + String.join(", ", ids)), false);
        return ids.size();
    }

    private static int info(CommandSourceStack source, String id) {
        BubbleTag tag = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (tag == null) {
            source.sendFailure(Component.literal("Bolha não encontrada: " + id));
            return 0;
        }
        source.sendSuccess(() -> Component.literal("Link " + id + " | " + tag.sourceDimension() + " -> " + tag.destinationDimension()
            + " | centro " + tag.center() + " -> " + tag.targetCenter() + " | raio " + tag.radius()
            + " | alcance " + tag.activationRange() + " | habilitado " + tag.enabled()), false);
        return 1;
    }

    private static int remove(CommandSourceStack source, String id) {
        if (id.equalsIgnoreCase("all")) {
            Set<String> ids = new HashSet<>();
            for (ServerLevel level : source.getServer().getAllLevels()) {
                for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
                    if (!(entity instanceof Portal portal)) continue;
                    BubbleTag tag = BubbleTag.parse(portal.portalTag);
                    if (tag != null) ids.add(tag.linkId());
                }
            }
            for (String link : ids) BubblePortalFactory.removeLink(source.getServer(), link);
            source.sendSuccess(() -> Component.literal("Removidas " + ids.size() + " ligações."), true);
            return ids.size();
        }
        BubblePortalFactory.removeLink(source.getServer(), id);
        source.sendSuccess(() -> Component.literal("Ligação removida: " + id), true);
        return 1;
    }

    private static int resize(CommandSourceStack source, double radius, String id) {
        try {
            if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) throw new IllegalArgumentException("Bolha não encontrada");
            BubblePortalFactory.resize(source.getServer(), id, radius);
            source.sendSuccess(() -> Component.literal("Raio atualizado para " + radius + "."), true);
            return 1;
        } catch (RuntimeException exception) {
            source.sendFailure(Component.literal(exception.getMessage()));
            return 0;
        }
    }

    private static int setRange(CommandSourceStack source, double range, String id) {
        try {
            if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) throw new IllegalArgumentException("Bolha não encontrada");
            BubblePortalFactory.setRange(source.getServer(), id, range);
            source.sendSuccess(() -> Component.literal("Alcance de ativação atualizado para " + range + "."), true);
            return 1;
        } catch (RuntimeException exception) {
            source.sendFailure(Component.literal(exception.getMessage()));
            return 0;
        }
    }

    private static int target(CommandSourceStack source, ResourceLocation dimension, String id) {
        ServerLevel destination = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, dimension));
        if (destination == null) {
            source.sendFailure(Component.literal("Dimensão não encontrada: " + dimension));
            return 0;
        }
        BubbleTag tag = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (tag == null) {
            source.sendFailure(Component.literal("Bolha não encontrada: " + id));
            return 0;
        }
        ServerLevel origin = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, tag.sourceDimension()));
        if (origin == null) return 0;
        Vec3 target = BubblePortalFactory.defaultDestination(origin, destination, tag.center());
        BubblePortalFactory.retarget(source.getServer(), id, destination, target);
        source.sendSuccess(() -> Component.literal("Destino alterado para " + dimension + "."), true);
        return 1;
    }

    private static int enabled(CommandSourceStack source, String id, boolean enabled) {
        if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) {
            source.sendFailure(Component.literal("Bolha não encontrada: " + id));
            return 0;
        }
        BubblePortalFactory.setEnabled(source.getServer(), id, enabled);
        source.sendSuccess(() -> Component.literal(enabled ? "Bolha ativada." : "Bolha desativada."), true);
        return 1;
    }

    private static int scale(CommandSourceStack source, double factor, String id) {
        try {
            if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) throw new IllegalArgumentException("Bolha não encontrada");
            BubblePortalFactory.setScale(source.getServer(), id, factor);
            source.sendSuccess(() -> Component.literal("Escala dimensional definida: " + factor), true);
            return 1;
        } catch (RuntimeException exception) {
            source.sendFailure(Component.literal(exception.getMessage()));
            return 0;
        }
    }

    private static int ruleAuto(CommandSourceStack source, String id) {
        BubbleTag tag = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (tag == null) return 0;
        ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, tag.destinationDimension());
        ServerLevel destination = source.getServer().getLevel(key);
        ServerLevel origin = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, tag.sourceDimension()));
        if (destination == null || origin == null) return 0;
        Vec3 target = BubblePortalFactory.defaultDestination(origin, destination, tag.center());
        BubblePortalFactory.retarget(source.getServer(), id, destination, target);
        source.sendSuccess(() -> Component.literal("Regra automática aplicada."), true);
        return 1;
    }

    private static int ruleIdentity(CommandSourceStack source, String id) {
        BubbleTag tag = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (tag == null) return 0;
        ServerLevel origin = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, tag.sourceDimension()));
        if (origin == null) return 0;
        Vec3 target = tag.center().add(128.0, 0.0, 0.0);
        BubblePortalFactory.retarget(source.getServer(), id, origin, target);
        source.sendSuccess(() -> Component.literal("Regra identity aplicada: ligação na mesma dimensão."), true);
        return 1;
    }

    private static int fixed(CommandSourceStack source, double x, double y, double z, String id) {
        BubbleTag tag = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (tag == null) return 0;
        ServerLevel destination = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, tag.destinationDimension()));
        if (destination == null) return 0;
        BubblePortalFactory.retarget(source.getServer(), id, destination, new Vec3(x, y, z));
        source.sendSuccess(() -> Component.literal("Destino fixo aplicado."), true);
        return 1;
    }
}
