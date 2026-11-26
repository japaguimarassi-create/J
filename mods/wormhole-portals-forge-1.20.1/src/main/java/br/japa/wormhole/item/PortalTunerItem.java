package br.japa.wormhole.item;
import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.PortalEndpointEntity;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import java.util.ArrayList;
import java.util.List;
public final class PortalTunerItem extends Item {
    private static final String TARGET = "wormhole_tuner_target";
    public PortalTunerItem(Properties properties) { super(properties); }
    @Override public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand); if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel serverLevel) || !(player instanceof ServerPlayer serverPlayer)) return InteractionResultHolder.pass(stack);
        List<ResourceLocation> dimensions = new ArrayList<>();
        for (ServerLevel candidate : serverLevel.getServer().getAllLevels()) dimensions.add(candidate.dimension().location());
        if (dimensions.size() < 2) return InteractionResultHolder.fail(stack);
        String current = serverPlayer.getPersistentData().getString(TARGET);
        int index = -1; for (int i = 0; i < dimensions.size(); i++) if (dimensions.get(i).toString().equals(current)) index = i;
        ResourceLocation next = dimensions.get((index + 1 + dimensions.size()) % dimensions.size());
        if (next.equals(serverLevel.dimension().location())) next = dimensions.get((dimensions.indexOf(next) + 1) % dimensions.size());
        serverPlayer.getPersistentData().putString(TARGET, next.toString());
        serverPlayer.displayClientMessage(net.minecraft.network.chat.Component.literal("Destino selecionado: " + next), true);
        return InteractionResultHolder.consume(stack);
    }
    @Override public InteractionResult useOn(UseOnContext context) {
        if (context.getLevel().isClientSide) return InteractionResult.SUCCESS;
        if (!(context.getLevel() instanceof ServerLevel level) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        Vec3 at = Vec3.atCenterOf(context.getClickedPos());
        List<PortalEndpointEntity> nearby = BubblePortalFactory.findPortals(level, at, 12.0);
        PortalEndpointEntity portal = nearby.stream().min((a,b) -> Double.compare(a.position().distanceToSqr(at), b.position().distanceToSqr(at))).orElse(null);
        if (portal == null) { player.displayClientMessage(net.minecraft.network.chat.Component.literal("Nenhuma bolha próxima."), true); return InteractionResult.FAIL; }
        String id = portal.linkId();
        if (player.isShiftKeyDown()) {
            String target = player.getPersistentData().getString(TARGET);
            if (target.isBlank()) { BubblePortalFactory.removeLink(level.getServer(), id); player.displayClientMessage(net.minecraft.network.chat.Component.literal("Ligação removida."), true); return InteractionResult.CONSUME; }
            ResourceLocation destinationId = ResourceLocation.tryParse(target);
            ServerLevel destination = destinationId == null ? null : level.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, destinationId));
            if (destination == null) return InteractionResult.FAIL;
            Vec3 point = BubblePortalFactory.defaultDestination(level, destination, portal.position());
            BubblePortalFactory.retarget(level.getServer(), id, destination, point);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Portal redirecionado para " + target), true);
            return InteractionResult.CONSUME;
        }
        double next = nextRadius(portal.radius());
        BubblePortalFactory.resize(level.getServer(), id, next);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Raio do portal: " + next), true);
        return InteractionResult.CONSUME;
    }
    private static double nextRadius(double current) {
        double[] values = {1.5, 2.0, 2.5, 3.0, 4.0, 5.0};
        for (int i = 0; i < values.length; i++) if (Math.abs(values[i] - current) < 0.01) return values[(i + 1) % values.length];
        return 2.5;
    }
}