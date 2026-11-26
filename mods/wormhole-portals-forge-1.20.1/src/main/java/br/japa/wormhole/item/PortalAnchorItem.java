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
    public PortalAnchorItem(Properties properties) { super(properties); }
    @Override public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand); if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel serverLevel) || !(player instanceof ServerPlayer serverPlayer)) return InteractionResultHolder.pass(stack);
        List<ResourceLocation> dimensions = new ArrayList<>();
        for (ServerLevel candidate : serverLevel.getServer().getAllLevels()) if (!candidate.dimension().equals(serverLevel.dimension())) dimensions.add(candidate.dimension().location());
        if (dimensions.isEmpty()) return InteractionResultHolder.fail(stack);
        CompoundTag tag = stack.getOrCreateTag();
        ResourceLocation current = ResourceLocation.tryParse(tag.getString(TARGET));
        int index = dimensions.indexOf(current);
        ResourceLocation next = dimensions.get((index + 1 + dimensions.size()) % dimensions.size());
        tag.putString(TARGET, next.toString());
        serverPlayer.displayClientMessage(net.minecraft.network.chat.Component.literal("Destino da âncora: " + next), true);
        return InteractionResultHolder.consume(stack);
    }
    @Override public InteractionResult useOn(UseOnContext context) {
        if (context.getLevel().isClientSide) return InteractionResult.SUCCESS;
        if (!(context.getLevel() instanceof ServerLevel source) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        CompoundTag tag = context.getItemInHand().getTag();
        ResourceLocation targetId = tag == null ? null : ResourceLocation.tryParse(tag.getString(TARGET));
        ServerLevel destination = targetId == null ? null : source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, targetId));
        if (destination == null) {
            destination = source.dimension().equals(Level.NETHER) ? source.getServer().getLevel(Level.OVERWORLD) : source.getServer().getLevel(Level.NETHER);
        }
        if (destination == null || destination == source) { player.displayClientMessage(net.minecraft.network.chat.Component.literal("A dimensão de destino não está carregada."), true); return InteractionResult.FAIL; }
        Vec3 normal = Vec3.atLowerCornerOf(context.getClickedFace().getNormal());
        Vec3 center = Vec3.atCenterOf(context.getClickedPos()).add(normal.scale(0.55));
        Vec3 target = BubblePortalFactory.defaultDestination(source, destination, center);
        String id = BubblePortalFactory.createPair(source, center, destination, target, 2.25, 18.0, false);
        if (!player.getAbilities().instabuild) context.getItemInHand().shrink(1);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Bolha dimensional criada: " + id), true);
        return InteractionResult.CONSUME;
    }
}