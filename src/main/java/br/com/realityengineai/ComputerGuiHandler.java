package br.com.realityengineai;

import cpw.mods.fml.common.network.IGuiHandler;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;

public final class ComputerGuiHandler implements IGuiHandler {
    @Override
    public Object getServerGuiElement(int id, EntityPlayer player, World world, int x, int y, int z) {
        if (id != RealityEngineAI.GUI_COMPUTER) {
            return null;
        }
        TileEntity tile = world.getTileEntity(x, y, z);
        if (!(tile instanceof RealityEngineAI.TileEntityComputer)) {
            return null;
        }
        return new ContainerComputer(player, (RealityEngineAI.TileEntityComputer) tile);
    }

    @Override
    public Object getClientGuiElement(int id, EntityPlayer player, World world, int x, int y, int z) {
        if (id != RealityEngineAI.GUI_COMPUTER) {
            return null;
        }
        TileEntity tile = world.getTileEntity(x, y, z);
        if (!(tile instanceof RealityEngineAI.TileEntityComputer)) {
            return null;
        }
        return new GuiComputer(new ContainerComputer(player, (RealityEngineAI.TileEntityComputer) tile));
    }
}
