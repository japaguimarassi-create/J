package io.github.japaguimarassi.voxmobs.ai;

import io.github.japaguimarassi.voxmobs.action.ActionExecutor;
import io.github.japaguimarassi.voxmobs.config.VoxMobsConfig;
import io.github.japaguimarassi.voxmobs.entity.TalkingVillagerEntity;
import io.github.japaguimarassi.voxmobs.memory.MobMemorySavedData;
import io.github.japaguimarassi.voxmobs.network.MobReplyPacket;
import io.github.japaguimarassi.voxmobs.network.NetworkHandler;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.Level;
import net.minecraftforge.fml.loading.FMLPaths;
import net.minecraftforge.event.server.ServerStoppingEvent;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

public final class ConversationService {
    private static final Map<UUID, ArrayDeque<Long>> REQUEST_TIMES = new ConcurrentHashMap<>();
    private static final ExecutorService BRAIN_EXECUTOR = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "VoxMobs-LocalBrain");
        thread.setDaemon(true);
        return thread;
    });
    private static final AtomicBoolean INITIALIZING = new AtomicBoolean();
    private static volatile CognitiveCore100k brain;
    private static volatile String brainError = "";

    private ConversationService() {
    }

    public static void initialize() {
        if (!INITIALIZING.compareAndSet(false, true)) {
            return;
        }
        BRAIN_EXECUTOR.execute(() -> {
            try {
                brain = CognitiveCore100k.loadOrTrain(brainPath());
            } catch (Exception exception) {
                brainError = exception.getMessage() == null ? exception.getClass().getSimpleName() : exception.getMessage();
            }
        });
    }

    public static String brainStatus() {
        CognitiveCore100k current = brain;
        if (current == null) {
            return brainError.isBlank() ? "Cérebro local inicializando ou treinando o corpus inicial." : "Falha ao iniciar o cérebro: " + brainError;
        }
        return "Cérebro VoxMobs ativo: " + current.parameterCount() + " parâmetros; corpus: "
                + CoreTrainingCorpus.examples().size() + " exemplos; temperaturas de treino 0,55–1,28; "
                + current.trainingSteps() + " atualizações; ações confirmadas: " + current.successfulActions()
                + "; ações rejeitadas/revisadas: " + current.rejectedActions() + ".";
    }

    public static boolean teachAction(String actionName, String phrase) {
        MobAction action = MobAction.safeParse(actionName);
        if (action == MobAction.NONE || phrase == null || phrase.isBlank() || phrase.length() > 240) {
            return false;
        }
        CognitiveCore100k current = brain;
        if (current == null) {
            return false;
        }
        BRAIN_EXECUTOR.execute(() -> {
            try {
                current.learnFromTeaching(phrase, "minecraft:generic", action);
                current.save(brainPath());
            } catch (Exception exception) {
                brainError = "falha ao ensinar o cérebro: " + exception.getMessage();
            }
        });
        return true;
    }

    public static void saveBrain(ServerStoppingEvent event) {
        CognitiveCore100k current = brain;
        if (current == null) {
            return;
        }
        try {
            current.save(brainPath());
        } catch (IOException exception) {
            brainError = "não foi possível salvar o aprendizado: " + exception.getMessage();
        }
    }

    public static void handle(ServerPlayer player, int entityId, String rawMessage) {
        if (rawMessage == null || rawMessage.isBlank() || rawMessage.length() > 240) {
            return;
        }
        Level level = player.level();
        Entity entity = level.getEntity(entityId);
        if (!(entity instanceof Mob mob) || mob.isRemoved() || !mob.isAlive()) {
            player.sendSystemMessage(Component.literal("VoxMobs: não encontrei esse mob."));
            return;
        }
        double range = VoxMobsConfig.COMMON_VALUES.conversationRange.get();
        if (mob.distanceToSqr(player) > range * range || mob.level() != player.level()) {
            player.sendSystemMessage(Component.literal("VoxMobs: chegue mais perto do mob para conversar."));
            return;
        }
        if (!allowRequest(player)) {
            player.sendSystemMessage(Component.literal("VoxMobs: limite de conversas atingido. Aguarde um pouco."));
            return;
        }
        MinecraftServer server = player.getServer();
        if (server == null) {
            return;
        }
        String message = rawMessage.trim();
        String entityType = String.valueOf(BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()));
        MobMemorySavedData memory = MobMemorySavedData.get(server);
        List<String> history = memory.getHistory(mob.getUUID(), player.getUUID(), VoxMobsConfig.COMMON_VALUES.memoryLines.get());

        CognitiveCore100k currentBrain = brain;
        CognitivePrediction cognition = currentBrain == null ? null : currentBrain.predict(message, entityType);
        String memoryLabel = cognition != null && cognition.memoryConfidence() >= 0.30F
                && cognition.memory() > 0
                ? CognitivePrediction.MEMORY_TYPES[cognition.memory()] : "recent_conversation";
        memory.add(mob.getUUID(), player.getUUID(), "Jogador [" + memoryLabel + "]: " + message,
                VoxMobsConfig.COMMON_VALUES.memoryLines.get());
        AiReply reply = OfflineBrain.answer(mob, player, message, history, cognition);
        String learnedEmotion = emotionFrom(cognition);
        if (learnedEmotion != null) {
            reply = new AiReply(reply.reply(), reply.action(), learnedEmotion, reply.argument());
        }
        deliver(server, player, mob, reply, message, entityType);
    }

    private static String emotionFrom(CognitivePrediction cognition) {
        if (cognition == null) {
            return null;
        }
        if (cognition.voiceConfidence() >= 0.30F) {
            return CognitivePrediction.VOICE_EMOTIONS[cognition.voiceEmotion()];
        }
        if (cognition.reactionConfidence() < 0.30F) {
            return null;
        }
        return switch (cognition.reaction()) {
            case 1 -> "curioso";
            case 2 -> "feliz";
            case 3 -> "medo";
            case 4, 9 -> "alerta";
            case 5, 12 -> "serio";
            case 6 -> "sussurro";
            case 7, 13 -> "calmo";
            case 8 -> "triste";
            case 10, 15 -> "animado";
            case 11 -> "confuso";
            case 14 -> "cansado";
            default -> "neutro";
        };
    }

    private static void deliver(MinecraftServer server, ServerPlayer player, Mob mob, AiReply reply,
                                String input, String entityType) {
        boolean allowed = reply.action() != MobAction.SPAWN_MOB || VoxMobsConfig.COMMON_VALUES.allowMobSpawning.get();
        boolean actionExecuted = reply.action() == MobAction.NONE
                || (allowed && ActionExecutor.execute(mob, player, reply.action(), reply.argument()));
        AiReply delivered = actionExecuted ? reply : new AiReply(
                actionFailure(reply.action()), MobAction.NONE, "confuso");

        if (reply.action() != MobAction.NONE) {
            CognitiveCore100k currentBrain = brain;
            if (currentBrain != null && VoxMobsConfig.COMMON_VALUES.enableOnlineLearning.get()) {
                currentBrain.learnFromOutcome(input, entityType, reply.action(), actionExecuted);
                if (currentBrain.trainingSteps() % 8L == 0L) {
                    BRAIN_EXECUTOR.execute(() -> {
                        try {
                            currentBrain.save(brainPath());
                        } catch (IOException exception) {
                            brainError = "não foi possível salvar o aprendizado: " + exception.getMessage();
                        }
                    });
                }
            }
        }

        String name = mob.getName().getString();
        MobReplyPacket packet = new MobReplyPacket(delivered.reply(), entityType,
                mob.getUUID(), name, delivered.emotion());
        if (mob instanceof TalkingVillagerEntity villager && mob.level() instanceof ServerLevel serverLevel) {
            int speechTicks = Math.max(28, Math.min(220,
                    delivered.reply().codePointCount(0, delivered.reply().length()) * 2 + 14));
            villager.beginTalking(delivered.emotion(), speechTicks);
            NetworkHandler.sendReplyToTracking(mob, packet);
            for (ServerPlayer listener : serverLevel.players()) {
                if (listener.distanceToSqr(mob) <= 18.0D * 18.0D) {
                    listener.sendSystemMessage(Component.literal(name + ": " + delivered.reply()));
                }
            }
        } else {
            player.sendSystemMessage(Component.literal(name + ": " + delivered.reply()));
            NetworkHandler.sendReply(player, packet);
        }
        MobMemorySavedData.get(server).add(mob.getUUID(), player.getUUID(),
                name + ": " + delivered.reply(), VoxMobsConfig.COMMON_VALUES.memoryLines.get());
    }

    private static String actionFailure(MobAction action) {
        return switch (action) {
            case PICKUP_ITEM -> "Não encontrei um item próximo que eu possa pegar.";
            case DROP_ITEM -> "Não estou segurando nenhum item para soltar.";
            case SPAWN_MOB -> "Não consegui criar essa criatura. Confira o ID, o espaço livre e o limite de criaturas.";
            case SIT -> "Não posso sentar sob suas ordens. Essa ação exige um animal domesticado e seu dono.";
            default -> "Não consigo executar isso nesta situação.";
        };
    }

    private static Path brainPath() {
        return FMLPaths.CONFIGDIR.get().resolve("voxmobs").resolve("brain-100k.dat");
    }

    private static boolean allowRequest(ServerPlayer player) {
        long now = System.currentTimeMillis();
        ArrayDeque<Long> times = REQUEST_TIMES.computeIfAbsent(player.getUUID(), ignored -> new ArrayDeque<>());
        synchronized (times) {
            while (!times.isEmpty() && now - times.peekFirst() > 60_000L) {
                times.removeFirst();
            }
            if (times.size() >= VoxMobsConfig.COMMON_VALUES.requestsPerMinute.get()) {
                return false;
            }
            times.addLast(now);
            return true;
        }
    }
}
