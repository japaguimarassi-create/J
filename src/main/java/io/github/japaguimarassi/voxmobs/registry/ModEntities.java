package io.github.japaguimarassi.voxmobs.registry;

import io.github.japaguimarassi.voxmobs.VoxMobs;
import io.github.japaguimarassi.voxmobs.entity.TalkingVillagerEntity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public final class ModEntities {
    public static final DeferredRegister<EntityType<?>> ENTITY_TYPES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, VoxMobs.MOD_ID);

    public static final RegistryObject<EntityType<TalkingVillagerEntity>> TALKING_VILLAGER =
            ENTITY_TYPES.register("talking_villager", () -> EntityType.Builder
                    .of(TalkingVillagerEntity::new, MobCategory.CREATURE)
                    .sized(0.6F, 1.95F)
                    .clientTrackingRange(10)
                    .updateInterval(3)
                    .build("voxmobs:talking_villager"));

    private ModEntities() {
    }

    public static void register(IEventBus modBus) {
        ENTITY_TYPES.register(modBus);
        modBus.addListener(ModEntities::registerAttributes);
    }

    private static void registerAttributes(EntityAttributeCreationEvent event) {
        AttributeSupplier.Builder attributes = Villager.createAttributes();
        event.put(TALKING_VILLAGER.get(), attributes.build());
    }
}
