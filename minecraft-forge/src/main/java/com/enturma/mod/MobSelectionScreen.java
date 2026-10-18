package com.enturma.mod;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public final class MobSelectionScreen extends Screen {
    private final Screen parent;
    private EditBox entityIds;
    private Button allMobsButton;
    private boolean allMobs;

    public MobSelectionScreen(Screen parent) {
        super(Component.literal("Enturma AI — criaturas falantes"));
        this.parent = parent;
        this.allMobs = MobSettings.allMobsEnabled();
    }

    @Override
    protected void init() {
        int center = width / 2;
        entityIds = new EditBox(font, center - 145, height / 2 - 15, 290, 20, Component.literal("IDs de entidade"));
        entityIds.setMaxLength(1500);
        entityIds.setValue(MobSettings.idsCsv());
        addRenderableWidget(entityIds);
        allMobsButton = addRenderableWidget(Button.builder(allMobsLabel(), button -> {
            allMobs = !allMobs;
            button.setMessage(allMobsLabel());
        }).bounds(center - 100, height / 2 + 17, 200, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Salvar e voltar"), button -> {
            MobSettings.save(allMobs, entityIds.getValue());
            if (minecraft != null) minecraft.setScreen(parent);
        }).bounds(center - 100, height / 2 + 47, 200, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Cancelar"), button -> {
            if (minecraft != null) minecraft.setScreen(parent);
        }).bounds(center - 100, height / 2 + 73, 200, 20).build());
    }

    private Component allMobsLabel() {
        return Component.literal("Todos os mobs: " + (allMobs ? "ATIVADO" : "desativado"));
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        renderBackground(graphics);
        graphics.drawCenteredString(font, title, width / 2, 35, 0xFFFFFF);
        graphics.drawCenteredString(font, "IDs separados por vírgula (aceita mobs de outros mods)", width / 2, height / 2 - 38, 0xDDDDDD);
        graphics.drawCenteredString(font, "Ex.: minecraft:villager, alexsmobs:capuchin", width / 2, height / 2 - 26, 0x999999);
        super.render(graphics, mouseX, mouseY, partialTick);
    }

    @Override
    public void onClose() {
        if (minecraft != null) minecraft.setScreen(parent);
    }
}
