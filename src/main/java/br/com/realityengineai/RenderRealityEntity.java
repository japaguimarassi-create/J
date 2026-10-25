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
        return TEXTURE;
    }
}
