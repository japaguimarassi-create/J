package io.github.japaguimarassi.voxmobs.command;

import io.github.japaguimarassi.voxmobs.ai.ConversationService;
import io.github.japaguimarassi.voxmobs.memory.MobMemorySavedData;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.RegisterCommandsEvent;
import com.mojang.brigadier.arguments.StringArgumentType;

public final class CommandHandler {
    private CommandHandler() {
    }

    public static void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("voxmobs")
                .then(Commands.literal("status").executes(context -> {
                    context.getSource().sendSuccess(() -> Component.literal("VoxMobs ativo: cérebro local de 100.000 parâmetros, memória e voz offline."), false);
                    return 1;
                }))
                .then(Commands.literal("brain").executes(context -> {
                    context.getSource().sendSuccess(() -> Component.literal(ConversationService.brainStatus()), false);
                    return 1;
                }))
                .then(Commands.literal("teach").requires(source -> source.hasPermission(2))
                        .then(Commands.argument("action", StringArgumentType.word())
                                .then(Commands.argument("phrase", StringArgumentType.greedyString()).executes(context -> {
                                    String action = StringArgumentType.getString(context, "action");
                                    String phrase = StringArgumentType.getString(context, "phrase");
                                    boolean queued = ConversationService.teachAction(action, phrase);
                                    context.getSource().sendSuccess(() -> Component.literal(queued
                                            ? "VoxMobs: exemplo recebido; o cérebro está aprendendo localmente."
                                            : "VoxMobs: ação/frase inválida ou cérebro ainda inicializando."), false);
                                    return queued ? 1 : 0;
                                }))))
                .then(Commands.literal("forget").executes(context -> {
                    if (context.getSource().getEntity() instanceof ServerPlayer player) {
                        MobMemorySavedData.get(context.getSource().getServer()).forgetPlayer(player.getUUID());
                        context.getSource().sendSuccess(() -> Component.literal("VoxMobs: memórias das suas conversas foram apagadas deste mundo."), false);
                        return 1;
                    }
                    return 0;
                })));
    }
}
