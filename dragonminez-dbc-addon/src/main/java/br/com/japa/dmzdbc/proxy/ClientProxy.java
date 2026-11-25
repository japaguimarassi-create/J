package br.com.japa.dmzdbc.proxy;

import br.com.japa.dmzdbc.client.ClientOverlay;
import net.minecraftforge.common.MinecraftForge;

public class ClientProxy extends CommonProxy {
    @Override
    public void init() {
        MinecraftForge.EVENT_BUS.register(new ClientOverlay());
    }
}
