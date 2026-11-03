package io.github.japaguimarassi.voxmobs.entity;

import io.github.japaguimarassi.voxmobs.ai.ConversationService;
import io.github.japaguimarassi.voxmobs.network.MobReplyPacket;
import io.github.japaguimarassi.voxmobs.network.NetworkHandler;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.animation.AnimationController;
import software.bernie.geckolib.animation.AnimationState;
import software.bernie.geckolib.animation.PlayState;
import software.bernie.geckolib.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

import java.util.List;

public final class TalkingVillagerEntity extends Villager implements GeoEntity {
    private static final EntityDataAccessor<Boolean> TALKING =
            SynchedEntityData.defineId(TalkingVillagerEntity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> TALK_EMOTION =
            SynchedEntityData.defineId(TalkingVillagerEntity.class, EntityDataSerializers.INT);
    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("animation.voxmobs.villager.idle");
    private static final RawAnimation WALKING = RawAnimation.begin().thenLoop("animation.voxmobs.villager.walking");
    private static final RawAnimation TALKING = RawAnimation.begin().thenLoop("animation.voxmobs.villager.talking");
    private static final RawAnimation TALKING_HAPPY = RawAnimation.begin().thenLoop("animation.voxmobs.villager.talking_happy");
    private static final RawAnimation TALKING_ANGRY = RawAnimation.begin().thenLoop("animation.voxmobs.villager.talking_angry");
    private static final RawAnimation TALKING_SAD = RawAnimation.begin().thenLoop("animation.voxmobs.villager.talking_sad");

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private long talkUntilTick;
    private long nextAmbientTalkTick;
    private long pendingAmbientAt;
    private String pendingAmbientLine = "";

    public TalkingVillagerEntity(EntityType<? extends Villager> type, Level level) {
        super(type, level);
        this.nextAmbientTalkTick = level.getGameTime() + 400L + getRandom().nextInt(900);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(TALKING, false);
        entityData.define(TALK_EMOTION, 0);
    }

    @Override
    public void registerControllers(software.bernie.geckolib.animation.AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "dialogue", 4, this::animationPredicate));
    }

    private PlayState animationPredicate(AnimationState<TalkingVillagerEntity> state) {
        if (isTalking()) {
            state.setAnimation(switch (entityData.get(TALK_EMOTION)) {
                case 1 -> TALKING_HAPPY;
                case 2 -> TALKING_ANGRY;
                case 3 -> TALKING_SAD;
                default -> TALKING;
            });
        } else if (state.isMoving()) {
            state.setAnimation(WALKING);
        } else {
            state.setAnimation(IDLE);
        }
        return PlayState.CONTINUE;
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    public boolean isTalking() {
        return entityData.get(TALKING);
    }

    public void beginTalking(String emotion, int durationTicks) {
        if (level().isClientSide) {
            return;
        }
        entityData.set(TALK_EMOTION, emotionIndex(emotion));
        entityData.set(TALKING, true);
        talkUntilTick = level().getGameTime() + Math.max(12, Math.min(240, durationTicks));
    }

    private void stopTalking() {
        entityData.set(TALKING, false);
        entityData.set(TALK_EMOTION, 0);
        talkUntilTick = 0L;
    }

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel serverLevel)) {
            return;
        }
        long now = serverLevel.getGameTime();
        if (isTalking() && now >= talkUntilTick) {
            stopTalking();
        }
        if (!pendingAmbientLine.isEmpty() && now >= pendingAmbientAt && !isTalking()) {
            String line = pendingAmbientLine;
            pendingAmbientLine = "";
            publishAmbientLine(serverLevel, line, "feliz");
        }
        if (now >= nextAmbientTalkTick && !isTalking() && serverLevel.getNearestPlayer(this, 10.0D) != null) {
            nextAmbientTalkTick = now + 500L + getRandom().nextInt(900);
            startAmbientConversation(serverLevel, now);
        }
    }

    private void startAmbientConversation(ServerLevel serverLevel, long now) {
        if (getRandom().nextInt(8) != 0) {
            return;
        }
        AABB searchArea = getBoundingBox().inflate(7.0D, 3.0D, 7.0D);
        List<TalkingVillagerEntity> candidates = serverLevel.getEntitiesOfClass(
                TalkingVillagerEntity.class,
                searchArea,
                other -> other != this && other.getId() > getId()
                        && !other.isTalking() && other.pendingAmbientLine.isEmpty());
        if (candidates.isEmpty()) {
            return;
        }
        TalkingVillagerEntity partner = candidates.get(getRandom().nextInt(candidates.size()));
        String[] openings = {
                "Você viu como o tempo mudou hoje?",
                "A vila está movimentada. Parece que teremos visitas.",
                "Estou pensando em organizar melhor a plantação.",
                "Você ouviu aquele barulho perto da floresta?",
                "Hoje é um bom dia para fazer alguns negócios."
        };
        String[] answers = {
                "Também percebi! É melhor ficarmos atentos.",
                "Concordo. Talvez apareça algum viajante interessante.",
                "Boa ideia. Posso ajudar depois do meu turno.",
                "Ouvi sim. Espero que não seja nenhum zumbi.",
                "Tomara que tragam bons itens para trocar."
        };
        String first = openings[getRandom().nextInt(openings.length)];
        String second = answers[getRandom().nextInt(answers.length)];
        int duration = speechDurationTicks(first);
        publishAmbientLine(serverLevel, first, "curioso");
        partner.pendingAmbientLine = second;
        partner.pendingAmbientAt = now + duration + 8L;
        partner.nextAmbientTalkTick = partner.pendingAmbientAt + 240L;
    }

    private void publishAmbientLine(ServerLevel serverLevel, String line, String emotion) {
        int duration = speechDurationTicks(line);
        beginTalking(emotion, duration);
        String entityType = net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE
                .getKey(getType()).toString();
        NetworkHandler.sendReplyToTracking(this, new MobReplyPacket(
                line, entityType, getUUID(), getName().getString(), emotion));
        for (ServerPlayer listener : serverLevel.players()) {
            if (listener.distanceToSqr(this) <= 18.0D * 18.0D) {
                listener.sendSystemMessage(net.minecraft.network.chat.Component.literal(
                        getName().getString() + ": " + line));
            }
        }
    }

    private static int speechDurationTicks(String line) {
        int characters = line.codePointCount(0, line.length());
        return Math.max(28, Math.min(220, characters * 2 + 14));
    }

    private static int emotionIndex(String emotion) {
        if (emotion == null) {
            return 0;
        }
        return switch (emotion.toLowerCase(java.util.Locale.ROOT)) {
            case "feliz", "animado", "happy", "excited", "animada" -> 1;
            case "bravo", "raiva", "angry", "irritado" -> 2;
            case "triste", "sad", "cansado" -> 3;
            default -> 0;
        };
    }

    @Override
    public InteractionResult mobInteract(Player player, InteractionHand hand) {
        if (player.isShiftKeyDown() && hand == InteractionHand.MAIN_HAND
                && player.getItemInHand(hand).isEmpty()) {
            if (!level().isClientSide && player instanceof ServerPlayer serverPlayer) {
                ConversationService.handle(serverPlayer, getId(), "Oi! Como você está?");
            }
            return InteractionResult.sidedSuccess(level().isClientSide);
        }
        return super.mobInteract(player, hand);
    }
}
