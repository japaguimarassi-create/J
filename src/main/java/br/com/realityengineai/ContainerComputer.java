package br.com.realityengineai;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.inventory.Container;
import net.minecraft.util.ChatComponentText;

public final class ContainerComputer extends Container {
    private final RealityEngineAI.TileEntityComputer tile;

    public ContainerComputer(EntityPlayer owner, RealityEngineAI.TileEntityComputer tile) {
        this.tile = tile;
    }

    @Override
    public boolean canInteractWith(EntityPlayer player) {
        return tile != null && !tile.isInvalid() && player.worldObj == tile.getWorldObj()
            && player.getDistanceSq(tile.xCoord + 0.5D, tile.yCoord + 0.5D, tile.zCoord + 0.5D) <= 64.0D;
    }

    @Override
    public boolean enchantItem(EntityPlayer player, int buttonId) {
        if (player == null || player.worldObj.isRemote) {
            return false;
        }
        if (buttonId == 0) {
            ModKnowledgeBase.sendInstalledMods(player);
        } else if (buttonId == 1) {
            ModKnowledgeBase.sendRegistrySummary(player);
        } else if (buttonId == 2) {
            player.addChatMessage(new ChatComponentText("Computador Reality: consulta registros reais do Forge e executa ações no servidor."));
            LocalKnowledge.sendRelevantNotes(player, "Forge texture computer blocks dimension entity mods");
        } else if (buttonId == 3) {
            String description = tile.getDescription();
            player.addChatMessage(new ChatComponentText("Projeto atual: " + (description.isEmpty() ? "sem descrição salva" : description)));
        }
        return true;
    }
}
