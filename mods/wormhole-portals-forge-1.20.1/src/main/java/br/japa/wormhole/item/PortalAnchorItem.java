package br.japa.wormhole.item;

import br.japa.wormhole.portal.BubblePortalFactory;
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

public final class PortalAnchorItem extends Item {
    private static final String TARGET = "wormhole_anchor_target";

    public PortalAnchorItem(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel serverLevel) || !(player instanceof ServerPlayer serverPlayer)) return InteractionResultHolder.pass(stack);
        List<ResourceLocation> dimensions = new ArrayList<>();
        for (ServerLevel candidate : serverLevel.getServer().getAllLevels()) dimensions.add(candidate.dimension().location());
        if (dimensions.size() < 2) return InteractionResultHolder.fail(stack);
        CompoundTag tag = stack.getOrCreateTag();
        ResourceLocation current = ResourceLocation.tryParse(tag.getString(TARGET));
        int index = dimensions.indexOf(current);
        ResourceLocation next = dimensions.get((index + 1 + dimensions.size()) % dimensions.size());
        if (next.equals(serverLevel.dimension().location())) next = dimensions.get((dimensions.indexOf(next) + 1) % dimensions.size());
        tag.putString(TARGET, next.toString());
        serverPlayer.displayClientMessage(net.minecraft.network.chat.Component.literal("Destino do Anchor: " + next), true);
        return InteractionResultHolder.consume(stack);
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Level level = context.getLevel();
        if (level.isClientSide) return InteractionResult.SUCCESS;
        if (!(level instanceof ServerLevel source) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        CompoundTag itemTag = context.getItemInHand().getTag();
        ResourceLocation targetId = itemTag == null ? null : ResourceLocation.tryParse(itemTag.getString(TARGET));
        ServerLevel destination = targetId == null ? null : source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, targetId));
        if (destination == null || destination == source) {
            destination = source.dimension().equals(Level.NETHER)
                ? source.getServer().getLevel(Level.OVERWORLD)
                : source.getServer().getLevel(Level.NETHER);
        }
        if (destination == null) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("A dimensão de destino não está disponível."), true);
            return InteractionResult.FAIL;
        }
        Vec3 face = Vec3.atLowerCornerOf(context.getClickedFace().getNormal());
        Vec3 center = Vec3.atCenterOf(context.getClickedPos()).add(face.scale(0.53));
        Vec3 target = BubblePortalFactory.defaultDestination(source, destination, center);
        BubblePortalFactory.createPair(source, center, destination, target, 2.25, 18.0, false);
        if (!player.getAbilities().instabuild) context.getItemInHand().shrink(1);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Bolha dimensional posicionada: " + destination.dimension().location()), true);
        return InteractionResult.CONSUME;
    }
}
