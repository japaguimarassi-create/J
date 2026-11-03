package io.github.japaguimarassi.voxmobs.client.renderer;

import io.github.japaguimarassi.voxmobs.client.animation.TalkingVillagerModel;
import io.github.japaguimarassi.voxmobs.entity.TalkingVillagerEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

public final class TalkingVillagerRenderer extends GeoEntityRenderer<TalkingVillagerEntity> {
    public TalkingVillagerRenderer(EntityRendererProvider.Context context) {
        super(context, new TalkingVillagerModel());
        this.shadowRadius = 0.5F;
    }
}
