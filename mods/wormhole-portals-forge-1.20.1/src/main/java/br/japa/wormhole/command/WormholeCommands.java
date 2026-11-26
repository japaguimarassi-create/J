package br.japa.wormhole.command;
import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.PortalEndpointEntity;
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
import java.util.HashSet;
import java.util.Set;
public final class WormholeCommands {
    private WormholeCommands() {}
    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("wormhole").requires(s -> s.hasPermission(2))
            .then(Commands.literal("place").executes(c -> placeDefault(c.getSource())).then(Commands.argument("dimension", ResourceLocationArgument.id()).executes(c -> place(c.getSource(), ResourceLocationArgument.getId(c, "dimension")))))
            .then(Commands.literal("list").executes(c -> list(c.getSource())))
            .then(Commands.literal("info").then(Commands.argument("id", StringArgumentType.word()).executes(c -> info(c.getSource(), StringArgumentType.getString(c, "id")))))
            .then(Commands.literal("remove").then(Commands.argument("id", StringArgumentType.word()).executes(c -> remove(c.getSource(), StringArgumentType.getString(c, "id")))))
            .then(Commands.literal("size").then(Commands.argument("radius", DoubleArgumentType.doubleArg(1, 8)).then(Commands.argument("id", StringArgumentType.word()).executes(c -> size(c.getSource(), DoubleArgumentType.getDouble(c, "radius"), StringArgumentType.getString(c, "id"))))))
            .then(Commands.literal("range").then(Commands.argument("blocks", DoubleArgumentType.doubleArg(2, 128)).then(Commands.argument("id", StringArgumentType.word()).executes(c -> range(c.getSource(), DoubleArgumentType.getDouble(c, "blocks"), StringArgumentType.getString(c, "id"))))))
            .then(Commands.literal("target").then(Commands.argument("dimension", ResourceLocationArgument.id()).then(Commands.argument("id", StringArgumentType.word()).executes(c -> target(c.getSource(), ResourceLocationArgument.getId(c, "dimension"), StringArgumentType.getString(c, "id"))))))
            .then(Commands.literal("link").then(Commands.argument("id", StringArgumentType.word()).executes(c -> toggle(c.getSource(), StringArgumentType.getString(c, "id"), true))))
            .then(Commands.literal("unlink").then(Commands.argument("id", StringArgumentType.word()).executes(c -> toggle(c.getSource(), StringArgumentType.getString(c, "id"), false))))
            .then(Commands.literal("rule").then(Commands.literal("auto").then(Commands.argument("id", StringArgumentType.word()).executes(c -> ruleAuto(c.getSource(), StringArgumentType.getString(c, "id")))))
                .then(Commands.literal("identity").then(Commands.argument("id", StringArgumentType.word()).executes(c -> ruleIdentity(c.getSource(), StringArgumentType.getString(c, "id")))))
                .then(Commands.literal("end").then(Commands.argument("id", StringArgumentType.word()).executes(c -> target(c.getSource(), Level.END.location(), StringArgumentType.getString(c, "id")))))
                .then(Commands.literal("fixed").then(Commands.argument("x", DoubleArgumentType.doubleArg()).then(Commands.argument("y", DoubleArgumentType.doubleArg()).then(Commands.argument("z", DoubleArgumentType.doubleArg()).then(Commands.argument("id", StringArgumentType.word()).executes(c -> fixed(c.getSource(), DoubleArgumentType.getDouble(c, "x"), DoubleArgumentType.getDouble(c, "y"), DoubleArgumentType.getDouble(c, "z"), StringArgumentType.getString(c, "id"))))))))));
    }
    private static int placeDefault(CommandSourceStack source) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        ResourceLocation destination = player.level().dimension().equals(Level.NETHER) ? Level.OVERWORLD.location() : Level.NETHER.location();
        return place(source, destination);
    }
    private static int place(CommandSourceStack source, ResourceLocation dimension) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel destination = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, dimension));
        if (destination == null) { source.sendFailure(Component.literal("Dimensão não carregada: " + dimension)); return 0; }
        ServerLevel origin = player.serverLevel();
        Vec3 center = player.position().add(player.getLookAngle().scale(6.0));
        Vec3 target = BubblePortalFactory.defaultDestination(origin, destination, center);
        String id = BubblePortalFactory.createPair(origin, center, destination, target, 2.25, 18.0, true);
        source.sendSuccess(() -> Component.literal("Bolha criada: " + id), true); return 1;
    }
    private static int list(CommandSourceStack source) {
        Set<String> ids = new HashSet<>();
        for (ServerLevel level : source.getServer().getAllLevels()) for (net.minecraft.world.entity.Entity e : level.getAllEntities()) if (e instanceof PortalEndpointEntity p) ids.add(p.linkId());
        source.sendSuccess(() -> Component.literal(ids.isEmpty() ? "Nenhuma bolha carregada." : "Ligações: " + String.join(", ", ids)), false); return ids.size();
    }
    private static int info(CommandSourceStack source, String id) {
        PortalEndpointEntity p = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (p == null) { source.sendFailure(Component.literal("Bolha não encontrada: " + id)); return 0; }
        source.sendSuccess(() -> Component.literal("Link " + id + " | origem " + p.level().dimension().location() + " | destino " + p.destinationId() + " | raio " + p.radius() + " | alcance " + p.activationRange() + " | aberta " + p.isOpen()), false); return 1;
    }
    private static int remove(CommandSourceStack source, String id) {
        if (id.equalsIgnoreCase("all")) {
            Set<String> ids = new HashSet<>();
            for (ServerLevel level : source.getServer().getAllLevels()) for (net.minecraft.world.entity.Entity e : level.getAllEntities()) if (e instanceof PortalEndpointEntity p) ids.add(p.linkId());
            for (String link : ids) BubblePortalFactory.removeLink(source.getServer(), link);
            source.sendSuccess(() -> Component.literal("Removidas " + ids.size() + " ligações."), true); return ids.size();
        }
        BubblePortalFactory.removeLink(source.getServer(), id); source.sendSuccess(() -> Component.literal("Ligação removida: " + id), true); return 1;
    }
    private static int size(CommandSourceStack source, double radius, String id) {
        if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) { source.sendFailure(Component.literal("Portal não encontrado")); return 0; }
        BubblePortalFactory.resize(source.getServer(), id, radius); source.sendSuccess(() -> Component.literal("Raio atualizado: " + radius), true); return 1;
    }
    private static int range(CommandSourceStack source, double range, String id) {
        if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) { source.sendFailure(Component.literal("Portal não encontrado")); return 0; }
        BubblePortalFactory.setRange(source.getServer(), id, range); source.sendSuccess(() -> Component.literal("Alcance atualizado: " + range), true); return 1;
    }
    private static int target(CommandSourceStack source, ResourceLocation dimension, String id) {
        ServerLevel destination = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, dimension));
        PortalEndpointEntity p = BubblePortalFactory.findAnyTag(source.getServer(), id);
        if (destination == null || p == null) { source.sendFailure(Component.literal("Dimensão ou portal não encontrado")); return 0; }
        ServerLevel origin = (ServerLevel)p.level(); Vec3 point = BubblePortalFactory.defaultDestination(origin, destination, p.position());
        BubblePortalFactory.retarget(source.getServer(), id, destination, point); source.sendSuccess(() -> Component.literal("Destino alterado: " + dimension), true); return 1;
    }
    private static int toggle(CommandSourceStack source, String id, boolean enabled) {
        if (BubblePortalFactory.findAnyTag(source.getServer(), id) == null) { source.sendFailure(Component.literal("Portal não encontrado")); return 0; }
        BubblePortalFactory.setEnabled(source.getServer(), id, enabled); source.sendSuccess(() -> Component.literal(enabled ? "Ligação ativada." : "Ligação desativada."), true); return 1;
    }
    private static int ruleAuto(CommandSourceStack source, String id) {
        PortalEndpointEntity p = BubblePortalFactory.findAnyTag(source.getServer(), id); if (p == null) return 0;
        ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, p.destinationId()); ServerLevel destination = source.getServer().getLevel(key);
        if (destination == null) return 0; return target(source, destination.dimension().location(), id);
    }
    private static int ruleIdentity(CommandSourceStack source, String id) {
        PortalEndpointEntity p = BubblePortalFactory.findAnyTag(source.getServer(), id); if (p == null) return 0;
        ServerLevel origin = (ServerLevel)p.level(); BubblePortalFactory.retarget(source.getServer(), id, origin, p.position().add(128, 0, 0));
        source.sendSuccess(() -> Component.literal("Ligação na mesma dimensão criada."), true); return 1;
    }
    private static int fixed(CommandSourceStack source, double x, double y, double z, String id) {
        PortalEndpointEntity p = BubblePortalFactory.findAnyTag(source.getServer(), id); if (p == null) return 0;
        ServerLevel destination = source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, p.destinationId())); if (destination == null) return 0;
        BubblePortalFactory.retarget(source.getServer(), id, destination, new Vec3(x, y, z));
        source.sendSuccess(() -> Component.literal("Destino fixo aplicado."), true); return 1;
    }
}