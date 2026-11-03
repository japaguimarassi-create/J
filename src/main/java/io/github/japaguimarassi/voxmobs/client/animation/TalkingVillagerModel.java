package io.github.japaguimarassi.voxmobs.client.animation;

import io.github.japaguimarassi.voxmobs.VoxMobs;
import io.github.japaguimarassi.voxmobs.entity.TalkingVillagerEntity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

public final class TalkingVillagerModel extends GeoModel<TalkingVillagerEntity> {
    private static final ResourceLocation MODEL =
            new ResourceLocation(VoxMobs.MOD_ID, "geo/talking_villager.geo.json");
    private static final ResourceLocation TEXTURE =
            new ResourceLocation(VoxMobs.MOD_ID, "textures/entity/talking_villager.png");
    private static final ResourceLocation ANIMATIONS =
            new ResourceLocation(VoxMobs.MOD_ID, "animations/talking_villager.animation.json");

    @Override
    public ResourceLocation getModelResource(TalkingVillagerEntity animatable) {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(TalkingVillagerEntity animatable) {
        return TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(TalkingVillagerEntity animatable) {
        return ANIMATIONS;
    }
}
