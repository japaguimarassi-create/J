package br.com.realityengineai;

import java.util.Locale;
import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;

public final class BotCommand extends CommandBase {
    @Override
    public String getCommandName() { return "bot"; }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/bot [crie <prompt>|pesquisar <assunto>|status|parar|remover|recarregar|modulos|ajuda]";
    }

    @Override
    public int getRequiredPermissionLevel() { return 0; }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (!(sender instanceof EntityPlayer)) {
            sender.addChatMessage(new ChatComponentText("Reality Engine Bot: use o comando dentro de um mundo por um jogador."));
            return;
        }
        EntityPlayer player = (EntityPlayer) sender;
        if (args.length == 0 || "spawn".equalsIgnoreCase(args[0]) || "gerar".equalsIgnoreCase(args[0])) {
            EntityRealityBot bot = BotPromptEngine.INSTANCE.spawnBot(player);
            player.addChatMessage(new ChatComponentText(bot == null ? "Reality Engine Bot: não foi possível gerar o bot." :
                "Reality Engine Bot pronto e seguindo você. Use /bot crie <prompt>."));
            return;
        }
        String action = args[0].toLowerCase(Locale.ROOT);
        if ("crie".equals(action) || "criar".equals(action)) {
            if (args.length < 2) {
                player.addChatMessage(new ChatComponentText("Uso: /bot crie <prompt>. Exemplo: /bot crie um mapa do zero raio 24"));
                return;
            }
            EntityRealityBot bot = BotPromptEngine.INSTANCE.findOwnedBot(player);
            if (bot == null) bot = BotPromptEngine.INSTANCE.spawnBot(player);
            if (bot == null) {
                player.addChatMessage(new ChatComponentText("Reality Engine Bot: não foi possível gerar um bot."));
                return;
            }
            BotPromptEngine.INSTANCE.submit(player, bot, join(args, 1));
            return;
        }
        if ("pesquisar".equals(action) || "pesquisa".equals(action) || "research".equals(action) || "estudar".equals(action)) {
            if (args.length < 2) player.addChatMessage(new ChatComponentText("Uso: /bot pesquisar <assunto>."));
            else OnlineResearchEngine.INSTANCE.research(player, join(args, 1));
            return;
        }
        if ("status".equals(action)) {
            EntityRealityBot bot = BotPromptEngine.INSTANCE.findOwnedBot(player);
            player.addChatMessage(new ChatComponentText("Bot=" + (bot == null ? "ausente" : "ativo")
                + "; tarefas=" + BotPromptEngine.INSTANCE.getActiveJobCount() + "; módulos=" + BotPromptEngine.INSTANCE.getModuleCount()
                + "; operações/tick=" + BotPromptEngine.INSTANCE.getOperationsPerTick() + "."));
            return;
        }
        if ("parar".equals(action) || "stop".equals(action) || "cancelar".equals(action)) {
            player.addChatMessage(new ChatComponentText("Reality Engine Bot: tarefas canceladas=" + BotPromptEngine.INSTANCE.cancelOwnedJobs(player.getCommandSenderName()) + "."));
            return;
        }
        if ("remover".equals(action) || "despawn".equals(action) || "kill".equals(action)) {
            int jobs = BotPromptEngine.INSTANCE.cancelOwnedJobs(player.getCommandSenderName());
            int bots = BotPromptEngine.INSTANCE.removeOwnedBots(player);
            player.addChatMessage(new ChatComponentText("Reality Engine Bot: bots removidos=" + bots + ", tarefas canceladas=" + jobs + "."));
            return;
        }
        if ("recarregar".equals(action) || "reload".equals(action)) {
            boolean modules = BotPromptEngine.INSTANCE.reloadModules();
            boolean rules = RuntimeConfigurationEngine.INSTANCE.reload();
            player.addChatMessage(new ChatComponentText("Bot: módulos=" + modules + " (" + BotPromptEngine.INSTANCE.getModuleCount() + "), regras=" + rules + "."));
            return;
        }
        if ("modulos".equals(action) || "módulos".equals(action) || "modules".equals(action)) {
            player.addChatMessage(new ChatComponentText("Bot: " + BotPromptEngine.INSTANCE.getModuleCount()
                + " módulos ativos. Edite/crie JSON em config/realityengineai/modules/ e use /bot recarregar."));
            return;
        }
        if ("ajuda".equals(action) || "help".equals(action)) {
            player.addChatMessage(new ChatComponentText("/bot | /bot crie <prompt> | /bot pesquisar <assunto> | /bot status | /bot parar | /bot remover | /bot recarregar | /bot modulos"));
            player.addChatMessage(new ChatComponentText("Exemplos: /bot crie um mapa do zero raio 24; /bot crie um castelo de pedra; /bot crie uma cidade; /bot crie um módulo chamado garagem 15x9x7"));
            return;
        }
        player.addChatMessage(new ChatComponentText("Uso: " + getCommandUsage(sender) + ". Use /bot ajuda."));
    }

    private static String join(String[] args, int start) {
        StringBuilder value = new StringBuilder();
        for (int i = start; i < args.length; i++) {
            if (value.length() > 0) value.append(' ');
            value.append(args[i]);
        }
        return value.toString().trim();
    }
}
