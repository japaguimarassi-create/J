package br.com.realityengineai;

import net.minecraft.entity.EntityCreature;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.EntityAIWander;
import net.minecraft.entity.ai.EntityAILookIdle;
import net.minecraft.entity.ai.EntityAISwimming;
import net.minecraft.entity.ai.EntityAIWatchClosest;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.world.World;

public final class EntityRealityBot extends EntityCreature {
    private String ownerName = "";
    private String currentTask = "";

    public EntityRealityBot(World world) {
        super(world);
        setSize(0.6F, 1.8F);
        tasks.addTask(0, new EntityAISwimming(this));
        tasks.addTask(2, new EntityAIWatchClosest(this, EntityPlayer.class, 16.0F));
        tasks.addTask(3, new EntityAIWander(this, 0.9D));
        tasks.addTask(4, new EntityAILookIdle(this));
        setAlwaysRenderNameTag(true);
        updateName();
    }

    public void setOwnerName(String owner) {
        ownerName = owner == null ? "" : owner;
        getEntityData().setString("BotOwner", ownerName);
        updateName();
    }

    public String getOwnerName() {
        if (ownerName.isEmpty()) ownerName = getEntityData().getString("BotOwner");
        return ownerName;
    }

    public void setCurrentTask(String task) {
        currentTask = task == null ? "" : task;
        getEntityData().setString("BotTask", currentTask);
        updateName();
    }

    private void updateName() {
        setCustomNameTag(currentTask.isEmpty()
            ? (getOwnerName().isEmpty() ? "Reality Bot" : "Bot: " + getOwnerName())
            : "Bot: " + currentTask);
        setAlwaysRenderNameTag(true);
    }

    @Override
    protected void applyEntityAttributes() {
        super.applyEntityAttributes();
        getEntityAttribute(SharedMonsterAttributes.maxHealth).setBaseValue(30.0D);
        getEntityAttribute(SharedMonsterAttributes.movementSpeed).setBaseValue(0.30D);
        getEntityAttribute(SharedMonsterAttributes.followRange).setBaseValue(48.0D);
    }

    @Override
    public void onUpdate() {
        super.onUpdate();
        if (worldObj == null || worldObj.isRemote || ticksExisted % 20 != 0) return;
        String owner = getOwnerName();
        if (owner.isEmpty()) return;
        for (Object object : worldObj.playerEntities) {
            if (object instanceof EntityPlayer) {
                EntityPlayer player = (EntityPlayer) object;
                if (owner.equalsIgnoreCase(player.getCommandSenderName())) {
                    double distance = getDistanceSqToEntity(player);
                    if (distance > 25.0D && distance < 4096.0D) getNavigator().tryMoveToEntityLiving(player, 1.1D);
                    return;
                }
            }
        }
    }

    @Override
    public void readEntityFromNBT(NBTTagCompound tag) {
        super.readEntityFromNBT(tag);
        ownerName = tag.getString("BotOwner");
        currentTask = tag.getString("BotTask");
        updateName();
    }

    @Override
    public void writeEntityToNBT(NBTTagCompound tag) {
        super.writeEntityToNBT(tag);
        tag.setString("BotOwner", getOwnerName());
        tag.setString("BotTask", currentTask);
    }
}
