package br.japa.wormhole.item;
import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.PortalCarvingData;
import net.minecraft.core.Direction;
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
    private static final String MODE = "wormhole_anchor_mode";
    private static final String[] MODES = {"bubble", "floor", "ceiling", "wall"};
    public PortalAnchorItem(Properties properties) { super(properties); }
    @Override public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand); if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel serverLevel) || !(player instanceof ServerPlayer serverPlayer)) return InteractionResultHolder.pass(stack);
        CompoundTag tag = stack.getOrCreateTag();
        if (player.isShiftKeyDown()) {
            String current = tag.getString(MODE); int index = 0;
            for (int i = 0; i < MODES.length; i++) if (MODES[i].equals(current)) index = i;
            String next = MODES[(index + 1) % MODES.length]; tag.putString(MODE, next);
            serverPlayer.displayClientMessage(net.minecraft.network.chat.Component.literal("Modo Anchor: " + next.toUpperCase(java.util.Locale.ROOT)), true);
            return InteractionResultHolder.consume(stack);
        }
        List<ResourceLocation> dimensions = new ArrayList<>();
        for (ServerLevel candidate : serverLevel.getServer().getAllLevels()) if (!candidate.dimension().equals(serverLevel.dimension())) dimensions.add(candidate.dimension().location());
        if (dimensions.isEmpty()) return InteractionResultHolder.fail(stack);
        ResourceLocation current = ResourceLocation.tryParse(tag.getString(TARGET)); int index = dimensions.indexOf(current);
        ResourceLocation next = dimensions.get((index + 1 + dimensions.size()) % dimensions.size()); tag.putString(TARGET, next.toString());
        serverPlayer.displayClientMessage(net.minecraft.network.chat.Component.literal("Destino da âncora: " + next), true);
        return InteractionResultHolder.consume(stack);
    }
    @Override public InteractionResult useOn(UseOnContext context) {
        if (context.getLevel().isClientSide) return InteractionResult.SUCCESS;
        if (!(context.getLevel() instanceof ServerLevel source) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        CompoundTag tag = context.getItemInHand().getTag();
        ResourceLocation targetId = tag == null ? null : ResourceLocation.tryParse(tag.getString(TARGET));
        ServerLevel destination = targetId == null ? null : source.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, targetId));
        if (destination == null) destination = source.dimension().equals(Level.NETHER) ? source.getServer().getLevel(Level.OVERWORLD) : source.getServer().getLevel(Level.NETHER);
        if (destination == null || destination == source) { player.displayClientMessage(net.minecraft.network.chat.Component.literal("A dimensão de destino não está carregada."), true); return InteractionResult.FAIL; }
        String mode = tag == null || tag.getString(MODE).isBlank() ? "bubble" : tag.getString(MODE);
        Direction normal = context.getClickedFace();
        if (mode.equals("floor")) normal = Direction.UP;
        if (mode.equals("ceiling")) normal = Direction.DOWN;
        Vec3 center = Vec3.atCenterOf(context.getClickedPos()).add(Vec3.atLowerCornerOf(normal.getNormal()).scale(0.55));
        Vec3 target = BubblePortalFactory.defaultDestination(source, destination, center);
        String id = BubblePortalFactory.createPair(source, center, destination, target, 2.25, 18.0, false);
        PortalCarvingData data = PortalCarvingData.get(source.getServer());
        data.carveSurface(source, id, new PortalCarvingData.Vec3Center(center.x, center.y, center.z), normal, mode, 2.25);
        data.carveSurface(destination, id, new PortalCarvingData.Vec3Center(target.x, target.y, target.z), normal, mode, 2.25);
        if (!player.getAbilities().instabuild) context.getItemInHand().shrink(1);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Bolha dimensional criada: " + id + " | modo: " + mode), true);
        return InteractionResult.CONSUME;
    }
}