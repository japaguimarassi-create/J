package br.com.japa.intx.network;

import br.com.japa.intx.IntXMod;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;

public final class SyncNumbersHandler implements IMessageHandler<SyncNumbersMessage, IMessage> {
    @Override
    public IMessage onMessage(SyncNumbersMessage message, MessageContext context) {
        IntXMod.proxy.handleSync(message.getValues());
        return null;
    }
}
