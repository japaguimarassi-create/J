package com.enturma.mod;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.RegisterCommandsEvent;

public final class EnturmaCommands {
    private EnturmaCommands() {}

    public static void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("enturma")
            .then(Commands.literal("status").executes(context -> {
                context.getSource().sendSuccess(() -> Component.literal("Enturma AI: " + (EnturmaConfig.ENABLED.get() ? "ligado" : "desligado") + "; todos os mobs=" + MobSettings.allMobsEnabled() + "; IDs=" + MobSettings.idsCsv()), false);
                return 1;
            }))
            .then(Commands.literal("reload").requires(source -> source.hasPermission(2)).executes(context -> {
                MobSettings.reload();
                context.getSource().sendSuccess(() -> Component.literal("Configuração de criaturas do Enturma recarregada."), true);
                return 1;
            }))
            .then(Commands.literal("talk").then(Commands.argument("mensagem", StringArgumentType.greedyString()).executes(context -> {
                ServerPlayer player = context.getSource().getPlayerOrException();
                return MobConversationHandler.forceTalk(player, StringArgumentType.getString(context, "mensagem"));
            })))
        );
    }
}
