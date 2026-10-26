package br.com.realityengineai;

import net.minecraft.client.model.ModelBiped;
import net.minecraft.client.renderer.entity.RenderLiving;
import net.minecraft.entity.Entity;
import net.minecraft.util.ResourceLocation;

public final class RenderRealityEntity extends RenderLiving {
    private static final ResourceLocation TEXTURE = new ResourceLocation(RealityEngineAI.MOD_ID, "textures/entity/reality_creature.png");

    public RenderRealityEntity() {
        super(new ModelBiped(), 0.45F);
    }

    @Override
    protected ResourceLocation getEntityTexture(Entity entity) {
        if (entity instanceof RealityEngineAI.EntityReality) {
            String description = CreationPlan.normalize(entity.getEntityData().getString("RealityDescription"));
            if (description.contains("dragao") || description.contains("dragon")) return new ResourceLocation(RealityEngineAI.MOD_ID, "textures/entity/reality_dragon.png");
            if (description.contains("hostil") || description.contains("boss") || description.contains("monstro")) return new ResourceLocation(RealityEngineAI.MOD_ID, "textures/entity/reality_hostile.png");
            if (description.contains("robo") || description.contains("robot") || description.contains("android")) return new ResourceLocation(RealityEngineAI.MOD_ID, "textures/entity/reality_robot.png");
        }
        return TEXTURE;
    }
}
