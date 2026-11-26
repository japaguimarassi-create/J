package br.japa.wormhole.item;

import br.japa.wormhole.portal.BubblePortalFactory;
import net.minecraft.nbt.CompoundTag;
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
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

public final class PortalGunItem extends Item {
    private static final String PENDING = "wormhole_gun_pending";
    private static final String ACTIVE = "wormhole_gun_active";
    private static final String RADIUS = "wormhole_gun_radius";

    public PortalGunItem(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if (level.isClientSide) return InteractionResultHolder.success(stack);
        if (!(level instanceof ServerLevel serverLevel) || !(player instanceof ServerPlayer serverPlayer)) {
            return InteractionResultHolder.pass(stack);
        }
        if (!player.getAbilities().instabuild) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("A Portal Gun só funciona no modo Criativo."), true);
            return InteractionResultHolder.fail(stack);
        }
        CompoundTag data = player.getPersistentData();
        if (player.isShiftKeyDown()) {
            double next = nextRadius(data.getDouble(RADIUS));
            data.putDouble(RADIUS, next);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Tamanho da bolha: " + next + " blocos."), true);
            return InteractionResultHolder.consume(stack);
        }
        HitResult hit = player.pick(96.0, 0.0F, false);
        if (hit.getType() == HitResult.Type.MISS) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Aponte para uma superfície para abrir o portal."), true);
            return InteractionResultHolder.fail(stack);
        }
        Vec3 point = hit.getLocation();
        if (hit instanceof BlockHitResult blockHit) {
            point = point.add(Vec3.atLowerCornerOf(blockHit.getDirection().getNormal()).scale(0.55));
        }
        return place(serverLevel, serverPlayer, point, stack);
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        if (context.getLevel().isClientSide) return InteractionResult.SUCCESS;
        if (!(context.getLevel() instanceof ServerLevel level) || !(context.getPlayer() instanceof ServerPlayer player)) return InteractionResult.PASS;
        if (!player.getAbilities().instabuild) return InteractionResult.FAIL;
        Vec3 point = Vec3.atCenterOf(context.getClickedPos()).add(
            Vec3.atLowerCornerOf(context.getClickedFace().getNormal()).scale(0.55));
        place(level, player, point, context.getItemInHand());
        return InteractionResult.CONSUME;
    }

    private InteractionResultHolder<ItemStack> place(ServerLevel level, ServerPlayer player, Vec3 point, ItemStack stack) {
        CompoundTag data = player.getPersistentData();
        if (data.contains(ACTIVE)) {
            BubblePortalFactory.removeLink(level.getServer(), data.getString(ACTIVE));
            data.remove(ACTIVE);
        }
        if (!data.getBoolean(PENDING)) {
            data.putBoolean(PENDING, true);
            data.putString(PENDING + "_dimension", level.dimension().location().toString());
            data.putDouble(PENDING + "_x", point.x);
            data.putDouble(PENDING + "_y", point.y);
            data.putDouble(PENDING + "_z", point.z);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Primeira abertura marcada. Escolha a segunda superfície."), true);
            return InteractionResultHolder.consume(stack);
        }
        String dimension = data.getString(PENDING + "_dimension");
        if (!dimension.equals(level.dimension().location().toString())) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("A segunda abertura precisa estar na mesma dimensão."), true);
            return InteractionResultHolder.fail(stack);
        }
        Vec3 first = new Vec3(data.getDouble(PENDING + "_x"), data.getDouble(PENDING + "_y"), data.getDouble(PENDING + "_z"));
        double radius = data.contains(RADIUS) ? data.getDouble(RADIUS) : 2.0;
        String id = BubblePortalFactory.createPair(level, first, level, point, radius, 18.0, true);
        data.putString(ACTIVE, id);
        clearPending(data);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Duas bolhas conectadas. O próximo disparo reinicia a ligação."), true);
        return InteractionResultHolder.consume(stack);
    }

    private static double nextRadius(double current) {
        double[] values = {1.5, 2.0, 2.5, 3.0, 4.0, 5.0};
        for (int i = 0; i < values.length; i++) {
            if (Math.abs(values[i] - current) < 0.01) return values[(i + 1) % values.length];
        }
        return 2.5;
    }

    private static void clearPending(CompoundTag data) {
        data.remove(PENDING);
        data.remove(PENDING + "_dimension");
        data.remove(PENDING + "_x");
        data.remove(PENDING + "_y");
        data.remove(PENDING + "_z");
    }
}
