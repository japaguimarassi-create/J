package br.com.japa.dmzdbc.player;

import br.com.japa.dmzdbc.config.DMZDBCConfig;
import net.minecraft.entity.Entity;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.world.World;
import net.minecraftforge.common.IExtendedEntityProperties;

public class DMZDBCData implements IExtendedEntityProperties {
    public static final String KEY = "dmzdbc.playerdata";

    private boolean angelUnlocked;
    private int divineEnergy = 100;
    private int activeTicks;
    private int cooldownTicks;
    private int regenCounter;

    @Override
    public void saveNBTData(NBTTagCompound compound) {
        NBTTagCompound data = new NBTTagCompound();
        data.setBoolean("AngelUnlocked", angelUnlocked);
        data.setInteger("DivineEnergy", divineEnergy);
        data.setInteger("ActiveTicks", activeTicks);
        data.setInteger("CooldownTicks", cooldownTicks);
        compound.setTag(KEY, data);
    }

    @Override
    public void loadNBTData(NBTTagCompound compound) {
        if (!compound.hasKey(KEY)) {
            return;
        }

        NBTTagCompound data = compound.getCompoundTag(KEY);
        angelUnlocked = data.getBoolean("AngelUnlocked");
        divineEnergy = clamp(data.getInteger("DivineEnergy"), 0, DMZDBCConfig.MAX_ENERGY);
        activeTicks = Math.max(0, data.getInteger("ActiveTicks"));
        cooldownTicks = Math.max(0, data.getInteger("CooldownTicks"));
    }

    @Override
    public void init(Entity entity, World world) {
        divineEnergy = DMZDBCConfig.MAX_ENERGY;
    }

    public static DMZDBCData get(EntityPlayer player) {
        DMZDBCData data = (DMZDBCData) player.getExtendedProperties(KEY);
        if (data == null) {
            data = new DMZDBCData();
            player.registerExtendedProperties(KEY, data);
        }
        return data;
    }

    public void copyFrom(DMZDBCData other) {
        angelUnlocked = other.angelUnlocked;
        divineEnergy = other.divineEnergy;
        activeTicks = 0;
        cooldownTicks = other.cooldownTicks;
        regenCounter = 0;
    }

    public boolean isAngelUnlocked() {
        return angelUnlocked;
    }

    public void unlockAngel() {
        angelUnlocked = true;
        divineEnergy = DMZDBCConfig.MAX_ENERGY;
    }

    public void reset() {
        angelUnlocked = false;
        divineEnergy = DMZDBCConfig.MAX_ENERGY;
        activeTicks = 0;
        cooldownTicks = 0;
        regenCounter = 0;
    }

    public int getDivineEnergy() {
        return divineEnergy;
    }

    public int getActiveTicks() {
        return activeTicks;
    }

    public int getCooldownTicks() {
        return cooldownTicks;
    }

    public boolean isActive() {
        return activeTicks > 0;
    }

    public int activateDivineInstinct() {
        if (!angelUnlocked) {
            return 1;
        }
        if (isActive()) {
            return 2;
        }
        if (cooldownTicks > 0) {
            return 3;
        }
        if (divineEnergy < DMZDBCConfig.ENERGY_COST) {
            return 4;
        }

        divineEnergy -= DMZDBCConfig.ENERGY_COST;
        activeTicks = DMZDBCConfig.ACTIVE_TICKS;
        cooldownTicks = DMZDBCConfig.COOLDOWN_TICKS;
        return 0;
    }

    public boolean tickServer() {
        boolean wasActive = isActive();

        if (activeTicks > 0) {
            activeTicks--;
        }

        if (cooldownTicks > 0) {
            cooldownTicks--;
        }

        if (!isActive() && divineEnergy < DMZDBCConfig.MAX_ENERGY) {
            regenCounter++;
            if (regenCounter >= DMZDBCConfig.REGEN_INTERVAL_TICKS) {
                divineEnergy++;
                regenCounter = 0;
            }
        } else {
            regenCounter = 0;
        }

        return wasActive && !isActive();
    }

    public void applySync(boolean unlocked, int energy, int active, int cooldown) {
        angelUnlocked = unlocked;
        divineEnergy = clamp(energy, 0, DMZDBCConfig.MAX_ENERGY);
        activeTicks = Math.max(0, active);
        cooldownTicks = Math.max(0, cooldown);
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
