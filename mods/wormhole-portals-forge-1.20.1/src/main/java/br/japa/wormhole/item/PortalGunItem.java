package br.japa.wormhole.item;
import br.japa.wormhole.WormholePortals;
import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.PortalOrbEntity;
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
public final class PortalGunItem extends Item {
    private static final String PENDING = "wormhole_gun_pending";
    private static final String ACTIVE = "wormhole_gun_active";
    private static final String PENDING_DIM = "wormhole_gun_dimension";
    private static final String PENDING_X = "wormhole_gun_x";
    private static final String PENDING_Y = "wormhole_gun_y";
    private static final String PENDING_Z = "wormhole_gun_z";
    private static final String RADIUS = "PortalRadius";
    public PortalGunItem(Properties properties) { super(properties); }
    public static double getRadius(ItemStack stack) {
        CompoundTag tag = stack.getTag();
        return tag == null || !tag.contains(RADIUS) ? 2.0 : Math.max(1.0, Math.min(8.0, tag.getDouble(RADIUS)));
    }
    public static void adjustRadius(ItemStack stack, double delta) {
        double next = Math.max(1.0, Math.min(8.0, getRadius(stack) + delta));
        stack.getOrCreateTag().putDouble(RADIUS, next);
    }
    @Override public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel server) || !(player instanceof ServerPlayer serverPlayer)) return InteractionResultHolder.pass(stack);
        if (!player.getAbilities().instabuild) { player.displayClientMessage(net.minecraft.network.chat.Component.literal("A Portal Gun só funciona no modo Criativo."), true); return InteractionResultHolder.fail(stack); }
        if (player.isShiftKeyDown()) {
            double[] sizes = {1.5, 2.0, 2.5, 3.0, 4.0, 5.0}; double current = getRadius(stack); double next = 2.5;
            for (int i = 0; i < sizes.length; i++) if (Math.abs(sizes[i] - current) < 0.01) next = sizes[(i + 1) % sizes.length];
            stack.getOrCreateTag().putDouble(RADIUS, next);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Raio da abertura: " + next + " blocos."), true);
            return InteractionResultHolder.consume(stack);
        }
        shootOrb(server, serverPlayer);
        return InteractionResultHolder.consume(stack);
    }
    @Override public InteractionResult useOn(UseOnContext context) {
        if (context.getLevel().isClientSide) return InteractionResult.SUCCESS;
        if (!(context.getLevel() instanceof ServerLevel level) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        if (!player.getAbilities().instabuild) return InteractionResult.FAIL;
        shootOrb(level, player);
        return InteractionResult.CONSUME;
    }
    private static void shootOrb(ServerLevel level, ServerPlayer player) {
        CompoundTag data = player.getPersistentData();
        if (!data.getBoolean(PENDING) && data.contains(ACTIVE)) {
            BubblePortalFactory.removeLink(level.getServer(), data.getString(ACTIVE));
            data.remove(ACTIVE);
        }
        PortalOrbEntity orb = new PortalOrbEntity(WormholePortals.PORTAL_ORB.get(), level);
        orb.setOwner(player);
        orb.setPos(player.getX(), player.getEyeY() - 0.08, player.getZ());
        Vec3 look = player.getLookAngle();
        orb.shoot(look.x, look.y, look.z, 1.85F, 0.0F);
        level.addFreshEntity(orb);
    }
    public static void onOrbImpact(ServerPlayer player, ServerLevel currentWorld, Vec3 point) {
        CompoundTag data = player.getPersistentData();
        if (!data.getBoolean(PENDING)) {
            data.putBoolean(PENDING, true);
            data.putString(PENDING_DIM, currentWorld.dimension().location().toString());
            data.putDouble(PENDING_X, point.x); data.putDouble(PENDING_Y, point.y); data.putDouble(PENDING_Z, point.z);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Primeira abertura marcada. Dispare a segunda esfera em outro local."), true);
            return;
        }
        ResourceLocation sourceId = ResourceLocation.tryParse(data.getString(PENDING_DIM));
        ServerLevel sourceWorld = sourceId == null ? null : currentWorld.getServer().getLevel(ResourceKey.create(Registries.DIMENSION, sourceId));
        if (sourceWorld == null) { clearPending(data); player.displayClientMessage(net.minecraft.network.chat.Component.literal("A primeira dimensão não está disponível. Tente novamente."), true); return; }
        Vec3 first = new Vec3(data.getDouble(PENDING_X), data.getDouble(PENDING_Y), data.getDouble(PENDING_Z));
        ItemStack gun = player.getMainHandItem().is(WormholePortals.PORTAL_GUN.get()) ? player.getMainHandItem() : player.getOffhandItem();
        double radius = getRadius(gun);
        String id = BubblePortalFactory.createPair(sourceWorld, first, currentWorld, point, radius, 18.0, true);
        data.putString(ACTIVE, id);
        clearPending(data);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Portal duplo conectado. O próximo disparo inicia uma nova ligação."), true);
    }
    private static void clearPending(CompoundTag data) {
        data.remove(PENDING); data.remove(PENDING_DIM); data.remove(PENDING_X); data.remove(PENDING_Y); data.remove(PENDING_Z);
    }
}