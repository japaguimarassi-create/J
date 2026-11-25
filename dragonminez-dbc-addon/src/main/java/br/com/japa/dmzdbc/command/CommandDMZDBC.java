package br.com.japa.dmzdbc.command;

import br.com.japa.dmzdbc.DMZDBC;
import br.com.japa.dmzdbc.compat.DbcCompatibility;
import br.com.japa.dmzdbc.player.DMZDBCData;
import net.minecraft.command.CommandBase;
import net.minecraft.command.CommandException;
import net.minecraft.command.ICommandSender;
import net.minecraft.command.WrongUsageException;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;

public class CommandDMZDBC extends CommandBase {
    @Override
    public String getCommandName() {
        return "dmzdbc";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/dmzdbc status | /dmzdbc admin unlock <player> | /dmzdbc admin reset <player>";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 0;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (args.length == 0 || "status".equalsIgnoreCase(args[0])) {
            if (!(sender instanceof EntityPlayer)) {
                sender.addChatMessage(new ChatComponentText("Run this command as a player."));
                return;
            }

            EntityPlayer player = (EntityPlayer) sender;
            DMZDBCData data = DMZDBCData.get(player);
            sender.addChatMessage(new ChatComponentText("§6[DMZ-DBC] §fAngel Lineage: " + (data.isAngelUnlocked() ? "§aAwakened" : "§cLocked")));
            sender.addChatMessage(new ChatComponentText("§6[DMZ-DBC] §fDivine Energy: " + data.getDivineEnergy()));
            sender.addChatMessage(new ChatComponentText("§6[DMZ-DBC] §fInstinct: " + (data.isActive() ? "§aActive" : "§7Inactive") + " | Cooldown: " + (data.getCooldownTicks() / 20) + "s"));
            sender.addChatMessage(new ChatComponentText("§6[DMZ-DBC] §fDBC/JRMCore detected: " + (DbcCompatibility.isPresent() ? "§aYes" : "§cNo")));
            return;
        }

        if ("admin".equalsIgnoreCase(args[0]) && args.length == 3) {
            if (!sender.canCommandSenderUseCommand(2, getCommandName())) {
                throw new CommandException("You do not have permission to use this command.");
            }

            EntityPlayer target = getPlayer(sender, args[2]);
            DMZDBCData data = DMZDBCData.get(target);

            if ("unlock".equalsIgnoreCase(args[1])) {
                data.unlockAngel();
                target.addChatMessage(new ChatComponentText("§bAn administrator awakened your Angel Lineage."));
                DMZDBC.sync(target);
            } else if ("reset".equalsIgnoreCase(args[1])) {
                data.reset();
                target.addChatMessage(new ChatComponentText("§cYour DMZ-DBC progression was reset by an administrator."));
                DMZDBC.sync(target);
            } else {
                throw new WrongUsageException(getCommandUsage(sender));
            }
            return;
        }

        throw new WrongUsageException(getCommandUsage(sender));
    }
}
