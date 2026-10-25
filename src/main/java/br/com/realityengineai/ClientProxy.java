package br.com.realityengineai;

import cpw.mods.fml.client.registry.RenderingRegistry;

public final class ClientProxy extends CommonProxy {
    @Override
    public void registerRenderers() {
        RenderingRegistry.registerEntityRenderingHandler(RealityEngineAI.EntityReality.class, new RenderRealityEntity());
    }
}
