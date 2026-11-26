package br.japa.wormhole.item;

import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.BubbleTag;
import net.minecraft.core.registries.Registries;
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
import qouteall.imm_ptl.core.portal.Portal;

import java.util.ArrayList;
import java.util.List;

public final class PortalTunerItem extends Item {
    private static final String TARGET = "wormhole_tuner_target";

    public PortalTunerItem(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel serverLevel) || !(player instanceof ServerPlayer serverPlayer)) return InteractionResultHolder.pass(stack);
        List<ResourceKey<Level>> dimensions = new ArrayList<>();
        for (ServerLevel candidate : serverLevel.getServer().getAllLevels()) dimensions.add(candidate.dimension());
        if (dimensions.size() < 2) return InteractionResultHolder.fail(stack);
        String current = serverPlayer.getPersistentData().getString(TARGET);
        int index = -1;
        for (int i = 0; i < dimensions.size(); i++) if (dimensions.get(i).location().toString().equals(current)) index = i;
        ResourceKey<Level> next = dimensions.get((index + 1 + dimensions.size()) % dimensions.size());
        if (next.equals(serverLevel.dimension())) next = dimensions.get((dimensions.indexOf(next) + 1) % dimensions.size());
        serverPlayer.getPersistentData().putString(TARGET, next.location().toString());
        serverPlayer.displayClientMessage(net.minecraft.network.chat.Component.literal("Destino selecionado no Tuner: " + next.location()), true);
        return InteractionResultHolder.consume(stack);
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        if (context.getLevel().isClientSide) return InteractionResult.SUCCESS;
        if (!(context.getLevel() instanceof ServerLevel level) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        Vec3 target = Vec3.atCenterOf(context.getClickedPos());
        List<Portal> portals = BubblePortalFactory.findPortals(level, target, 12.0);
        Portal closest = portals.stream().min((a, b) -> Double.compare(a.position().distanceToSqr(target), b.position().distanceToSqr(target))).orElse(null);
        if (closest == null) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Nenhuma bolha próxima."), true);
            return InteractionResult.FAIL;
        }
        BubbleTag portalTag = BubbleTag.parse(closest.portalTag);
        if (portalTag == null) return InteractionResult.FAIL;
        BubbleTag tag = BubblePortalFactory.findAnyTag(level.getServer(), portalTag.linkId());
        if (tag == null) return InteractionResult.FAIL;
        if (player.isShiftKeyDown()) {
            String targetDimension = player.getPersistentData().getString(TARGET);
            if (targetDimension.isBlank()) {
                BubblePortalFactory.removeLink(level.getServer(), tag.linkId());
                player.displayClientMessage(net.minecraft.network.chat.Component.literal("Ligação removida."), true);
                return InteractionResult.CONSUME;
            }
            ResourceLocation destinationId = ResourceLocation.tryParse(targetDimension);
            if (destinationId == null) return InteractionResult.FAIL;
            ServerLevel destination = level.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, destinationId));
            ServerLevel origin = level.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, tag.sourceDimension()));
            if (destination == null || origin == null) return InteractionResult.FAIL;
            Vec3 destinationPoint = BubblePortalFactory.defaultDestination(origin, destination, tag.center());
            BubblePortalFactory.retarget(level.getServer(), tag.linkId(), destination, destinationPoint);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Bolha redirecionada para " + targetDimension), true);
            return InteractionResult.CONSUME;
        }
        double radius = nextRadius(tag.radius());
        BubblePortalFactory.resize(level.getServer(), tag.linkId(), radius);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Raio da bolha alterado para " + radius + " blocos."), true);
        return InteractionResult.CONSUME;
    }

    private static double nextRadius(double current) {
        double[] values = {1.5, 2.0, 2.5, 3.0, 4.0, 5.0};
        for (int i = 0; i < values.length; i++) {
            if (Math.abs(values[i] - current) < 0.01) return values[(i + 1) % values.length];
        }
        return 2.5;
    }
}
