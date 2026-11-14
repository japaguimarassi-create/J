package br.com.japa.intx.data;

import br.com.japa.intx.numeric.NumberStore;
import net.minecraft.entity.Entity;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.world.World;
import net.minecraftforge.common.IExtendedEntityProperties;
import java.math.BigInteger;
import java.util.Map;

public final class PlayerNumbers implements IExtendedEntityProperties {
    public static final String ID = "intx.playerNumbers";
    private final NumberStore store = new NumberStore();

    public static PlayerNumbers get(EntityPlayer player) {
        if (player == null) throw new IllegalArgumentException("Player cannot be null");
        Object existing = player.getExtendedProperties(ID);
        if (existing instanceof PlayerNumbers) return (PlayerNumbers) existing;
        PlayerNumbers created = new PlayerNumbers();
        player.registerExtendedProperties(ID, created);
        return created;
    }

    @Override public void init(Entity entity, World world) { }

    @Override
    public void saveNBTData(NBTTagCompound compound) {
        compound.setTag(ID, store.writeToNBT());
    }

    @Override
    public void loadNBTData(NBTTagCompound compound) {
        if (compound.hasKey(ID, 10)) store.readFromNBT(compound.getCompoundTag(ID));
    }

    public BigInteger get(String key) { return store.get(key); }
    public boolean contains(String key) { return store.contains(key); }
    public void set(String key, BigInteger value) { store.set(key, value); }
    public BigInteger add(String key, BigInteger amount) { return store.add(key, amount); }
    public void remove(String key) { store.remove(key); }
    public Map<String, BigInteger> snapshot() { return store.snapshot(); }
    public void replace(Map<String, BigInteger> values) { store.replace(values); }

    public void copyFrom(PlayerNumbers other) {
        if (other != null) store.copyFrom(other.store);
    }
}
