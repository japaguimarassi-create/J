package br.japa.wormhole.client;
import br.japa.wormhole.network.PortalControlNetwork;
import br.japa.wormhole.network.PortalControlPacket;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
public final class PortalSettingsScreen extends Screen {
    private final int entityId;
    private final String linkId;
    private double radius;
    private double activationRange;
    private boolean enabled;
    private String destination;
    private boolean border;
    public PortalSettingsScreen(int entityId, String linkId, double radius, double activationRange, boolean enabled, String destination, boolean border) {
        super(Component.translatable("screen.wormhole_portals.settings"));
        this.entityId = entityId; this.linkId = linkId; this.radius = radius; this.activationRange = activationRange;
        this.enabled = enabled; this.destination = destination; this.border = border;
    }
    @Override protected void init() {
        int center = width / 2; int top = height / 2 - 92;
        addRenderableWidget(Button.builder(Component.literal("Radius −"), button -> adjust(0, -0.25F)).bounds(center - 154, top + 22, 94, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Radius +"), button -> adjust(0, 0.25F)).bounds(center + 60, top + 22, 94, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Alcance −"), button -> adjust(1, -2.0F)).bounds(center - 154, top + 52, 94, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Alcance +"), button -> adjust(1, 2.0F)).bounds(center + 60, top + 52, 94, 20).build());
        addRenderableWidget(Button.builder(Component.literal(enabled ? "Desativar" : "Ativar"), button -> { send(2, 0); enabled = !enabled; rebuildWidgets(); }).bounds(center - 154, top + 82, 148, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Remover par"), button -> { send(3, 0); onClose(); }).bounds(center + 6, top + 82, 148, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Próxima dimensão"), button -> { send(6, 0); destination = "atualizando..."; }).bounds(center - 154, top + 112, 148, 20).build());
        addRenderableWidget(Button.builder(Component.literal(border ? "Borda: ligada" : "Borda: desligada"), button -> { send(5, 0); border = !border; rebuildWidgets(); }).bounds(center + 6, top + 112, 148, 20).build());
        addRenderableWidget(Button.builder(Component.translatable("gui.done"), button -> onClose()).bounds(center - 60, top + 146, 120, 20).build());
    }
    private void adjust(int action, float amount) {
        send(action, amount);
        if (action == 0) radius = Math.max(1.0, Math.min(8.0, radius + amount));
        if (action == 1) activationRange = Math.max(2.0, Math.min(128.0, activationRange + amount));
    }
    private void send(int action, float value) { PortalControlNetwork.CHANNEL.sendToServer(new PortalControlPacket(entityId, action, value)); }
    @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        renderBackground(graphics);
        int center = width / 2; int top = height / 2 - 92;
        graphics.drawCenteredString(font, title, center, top - 18, 0xFFFFFF);
        graphics.drawCenteredString(font, "Link: " + linkId, center, top - 2, 0xA0A0A0);
        graphics.drawCenteredString(font, String.format(java.util.Locale.ROOT, "Raio: %.2f blocos", radius), center, top + 27, 0xFFFFFF);
        graphics.drawCenteredString(font, String.format(java.util.Locale.ROOT, "Ativação: %.1f blocos", activationRange), center, top + 57, 0xFFFFFF);
        graphics.drawCenteredString(font, enabled ? "Estado: ativo" : "Estado: inativo", center, top + 87, enabled ? 0x75E6A5 : 0xFF8989);
        graphics.drawCenteredString(font, "Destino: " + destination, center, top + 138, 0xBDAEFF);
        super.render(graphics, mouseX, mouseY, partialTick);
    }
    @Override public boolean isPauseScreen() { return false; }
}