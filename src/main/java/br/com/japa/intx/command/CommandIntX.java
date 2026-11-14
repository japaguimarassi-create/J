package br.com.japa.intx.command;

import br.com.japa.intx.api.IntXAPI;
import br.com.japa.intx.data.PlayerNumbers;
import br.com.japa.intx.numeric.NumberFormatter;
import br.com.japa.intx.numeric.NumberLimits;
import cpw.mods.fml.common.FMLCommonHandler;
import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;
import java.math.BigInteger;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class CommandIntX extends CommandBase {
    @Override public String getCommandName() { return "intx"; }
    @Override public String getCommandUsage(ICommandSender sender) {
        return "/intx <set|add|get|list|reset|debug>";
    }
    @Override public int getRequiredPermissionLevel() { return 2; }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (args.length == 0) {
            send(sender, getCommandUsage(sender));
            return;
        }
        String action = args[0].toLowerCase(Locale.ROOT);
        try {
            if ("debug".equals(action) && args.length == 1) {
                send(sender, "IntX active; maxDigits=" + NumberLimits.getMaxDigits()
                    + "; maxEntries=" + NumberLimits.getMaxEntries()
                    + "; side=" + FMLCommonHandler.instance().getSide());
                return;
            }
            if (("set".equals(action) || "add".equals(action)) && args.length == 4) {
                EntityPlayerMP target = findPlayer(args[1]);
                if (target == null) {
                    send(sender, "Player must be online: " + args[1]);
                    return;
                }
                NumberLimits.requireKey(args[2]);
                BigInteger value = NumberLimits.parse(args[3]);
                if ("set".equals(action)) IntXAPI.set(target, args[2], value);
                else value = IntXAPI.add(target, args[2], value);
                send(sender, target.getCommandSenderName() + " " + args[2] + " = "
                    + NumberFormatter.compact(value) + " (" + shortened(value) + ")");
                return;
            }
            if ("get".equals(action) && args.length == 3) {
                EntityPlayerMP target = findPlayer(args[1]);
                if (target == null) {
                    send(sender, "Player must be online: " + args[1]);
                    return;
                }
                PlayerNumbers stats = PlayerNumbers.get(target);
                if (!stats.contains(args[2])) {
                    send(sender, "No value stored for key " + args[2]);
                    return;
                }
                BigInteger value = stats.get(args[2]);
                send(sender, args[2] + " = " + NumberFormatter.compact(value)
                    + " (" + shortened(value) + ")");
                return;
            }
            if ("list".equals(action) && args.length == 2) {
                EntityPlayerMP target = findPlayer(args[1]);
                if (target == null) {
                    send(sender, "Player must be online: " + args[1]);
                    return;
                }
                Map<String, BigInteger> values = PlayerNumbers.get(target).snapshot();
                send(sender, target.getCommandSenderName() + " has " + values.size() + " IntX values.");
                int shown = 0;
                for (Map.Entry<String, BigInteger> entry : values.entrySet()) {
                    if (shown++ >= 12) {
                        send(sender, "Further values omitted.");
                        break;
                    }
                    send(sender, entry.getKey() + " = " + NumberFormatter.compact(entry.getValue()));
                }
                return;
            }
            if ("reset".equals(action) && args.length == 3) {
                EntityPlayerMP target = findPlayer(args[1]);
                if (target == null) {
                    send(sender, "Player must be online: " + args[1]);
                    return;
                }
                IntXAPI.remove(target, args[2]);
                send(sender, "Removed " + args[2] + " from " + target.getCommandSenderName());
                return;
            }
        } catch (IllegalArgumentException | IllegalStateException error) {
            send(sender, "IntX: " + error.getMessage());
            return;
        }
        send(sender, getCommandUsage(sender));
    }

    @Override
    public List addTabCompletionOptions(ICommandSender sender, String[] args) {
        if (args.length == 1) {
            return getListOfStringsMatchingLastWord(
                args, new String[] {"set", "add", "get", "list", "reset", "debug"}
            );
        }
        return null;
    }

    private static EntityPlayerMP findPlayer(String name) {
        return MinecraftServer.getServer().getConfigurationManager().getPlayerByUsername(name);
    }

    private static String shortened(BigInteger value) {
        String exact = value.toString();
        if (exact.length() <= 160) return exact;
        int digits = exact.charAt(0) == '-' ? exact.length() - 1 : exact.length();
        return exact.substring(0, 72) + "..." + exact.substring(exact.length() - 24)
            + " (" + digits + " digits)";
    }

    private static void send(ICommandSender sender, String message) {
        sender.addChatMessage(new ChatComponentText(message));
    }
}
