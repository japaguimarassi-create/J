package br.com.realityengineai;

import net.minecraft.client.gui.GuiButton;
import net.minecraft.client.gui.inventory.GuiContainer;
import org.lwjgl.opengl.GL11;

public final class GuiComputer extends GuiContainer {
    private static final int WIDTH = 256;
    private static final int HEIGHT = 172;

    public GuiComputer(ContainerComputer container) {
        super(container);
        xSize = WIDTH;
        ySize = HEIGHT;
    }

    @Override
    public void initGui() {
        super.initGui();
        int left = (width - xSize) / 2;
        int top = (height - ySize) / 2;
        buttonList.clear();
        buttonList.add(new GuiButton(0, left + 12, top + 42, 112, 22, "Ler mods"));
        buttonList.add(new GuiButton(1, left + 132, top + 42, 112, 22, "Ler registries"));
        buttonList.add(new GuiButton(2, left + 12, top + 70, 112, 22, "Ajuda"));
        buttonList.add(new GuiButton(3, left + 132, top + 70, 112, 22, "Projeto atual"));
    }

    @Override
    protected void actionPerformed(GuiButton button) {
        if (button != null && mc != null && mc.playerController != null && inventorySlots != null) {
            mc.playerController.sendEnchantPacket(inventorySlots.windowId, button.id);
        }
    }

    @Override
    protected void drawGuiContainerBackgroundLayer(float partialTicks, int mouseX, int mouseY) {
        GL11.glColor4f(1.0F, 1.0F, 1.0F, 1.0F);
        int left = (width - xSize) / 2;
        int top = (height - ySize) / 2;
        drawRect(left, top, left + xSize, top + ySize, 0xEE101B2C);
        drawRect(left + 2, top + 2, left + xSize - 2, top + 28, 0xFF173D59);
        drawString(fontRendererObj, "REALITY / TERMINAL", left + 12, top + 10, 0xFF72E5FF);
        drawString(fontRendererObj, "Consulta local do ambiente Forge", left + 12, top + 30, 0xFFE5EEF8);
        drawString(fontRendererObj, "Acoes executadas no servidor", left + 12, top + 105, 0xFFA9C5D9);
        drawString(fontRendererObj, "Minecraft 1.7.10 | Offline", left + 12, top + 121, 0xFF72E5FF);
        drawString(fontRendererObj, "Feche com ESC", left + 12, top + 145, 0xFF8195A7);
    }
}
