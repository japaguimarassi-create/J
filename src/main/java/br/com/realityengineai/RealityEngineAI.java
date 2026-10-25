package br.com.realityengineai;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import cpw.mods.fml.common.registry.EntityRegistry;
import cpw.mods.fml.common.registry.GameRegistry;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import net.minecraft.block.Block;
import net.minecraft.block.BlockContainer;
import net.minecraft.block.material.Material;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityCreature;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.EntityAIPanic;
import net.minecraft.entity.ai.EntityAISwimming;
import net.minecraft.entity.ai.EntityAIWander;
import net.minecraft.entity.ai.EntityAIWatchClosest;
import net.minecraft.entity.ai.EntityAILookIdle;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.MathHelper;
import net.minecraft.util.Vec3;
import net.minecraft.world.World;
import net.minecraft.world.WorldProvider;
import net.minecraft.world.WorldServer;
import net.minecraft.world.biome.BiomeGenBase;
import net.minecraft.world.biome.WorldChunkManagerHell;
import net.minecraft.world.chunk.IChunkProvider;
import net.minecraft.world.gen.ChunkProviderGenerate;
import net.minecraftforge.common.DimensionManager;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.ServerChatEvent;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

@Mod(modid = RealityEngineAI.MOD_ID, name = RealityEngineAI.NAME, version = RealityEngineAI.VERSION)
public final class RealityEngineAI {
    public static final String MOD_ID = "realityengineai";
    public static final String NAME = "Reality Engine AI";
    public static final String VERSION = "0.1.0";
    public static final Logger LOG = LogManager.getLogger(NAME);
    private static final Pattern METERS = Pattern.compile("(\\d+(?:[.,]\\d+)?)\\s*(?:metros|metro|m)\\b");
    private static final Map<Integer, String> DIMENSION_DESCRIPTIONS = new HashMap<Integer, String>();
    private static int providerType = -1;

    public static ItemRealityArtifact realityArtifact;
    public static BlockReality realityBlock;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        realityArtifact = new ItemRealityArtifact();
        GameRegistry.registerItem(realityArtifact, "reality_artifact");

        realityBlock = new BlockReality();
        GameRegistry.registerBlock(realityBlock, "reality_block");
        GameRegistry.registerTileEntity(TileEntityReality.class, MOD_ID + ":reality_block");

        EntityRegistry.registerModEntity(EntityReality.class, "reality_entity", 1, this, 64, 3, true);
        registerDimensionProvider();
        MinecraftForge.EVENT_BUS.register(new ChatCreationHandler());
        LOG.info("Initialized. Creation requests must begin with 'crie'.");
    }

    private static void registerDimensionProvider() {
        for (int id = 128; id < 1024; id++) {
            if (DimensionManager.registerProviderType(id, RealityWorldProvider.class, false)) {
                providerType = id;
                return;
            }
        }
        throw new IllegalStateException("No free Reality Engine provider type was found.");
    }

    public static final class ChatCreationHandler {
        @SubscribeEvent
        public void onServerChat(ServerChatEvent event) {
            CreationCommand.ParseResult result = CreationCommand.parse(event.message);
            if (!result.isTriggered()) {
                return;
            }

            event.setCanceled(true);
            if (!result.hasPrompt()) {
                event.player.addChatMessage(new ChatComponentText("Reality Engine AI: use 'crie <descrição>'."));
                return;
            }
            executeCreation(event.player, result.getPrompt());
        }
    }

    private static void executeCreation(EntityPlayer player, String prompt) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote || prompt == null || prompt.trim().isEmpty()) {
            return;
        }

        String normalized = prompt.toLowerCase(Locale.ROOT);
        try {
            if (containsAny(normalized, "dimensão", "dimensao", "planeta", "universo", "mundo novo")) {
                createDimension(player, prompt);
            } else if (containsAny(normalized, "entidade", "criatura", "dragão", "dragao", "monstro", "ser vivo")) {
                createEntity(player, prompt);
            } else if (containsAny(normalized, "bloco", "block")) {
                createBlock(player, prompt);
            } else {
                createItem(player, prompt);
            }
        } catch (Exception exception) {
            LOG.error("Creation failed for prompt: " + prompt, exception);
            player.addChatMessage(new ChatComponentText("Reality Engine AI: a criação falhou. Consulte o log do jogo."));
        }
    }

    private static boolean containsAny(String value, String... options) {
        for (String option : options) {
            if (value.contains(option)) {
                return true;
            }
        }
        return false;
    }

    private static void createItem(EntityPlayer player, String prompt) {
        ItemStack stack = new ItemStack(realityArtifact, 1);
        String name = shorten(prompt, 56);
        stack.setStackDisplayName("§b" + name);
        NBTTagCompound tag = stack.getTagCompound();
        if (tag == null) {
            tag = new NBTTagCompound();
        }
        tag.setString("RealityDescription", prompt);
        stack.setTagCompound(tag);

        if (!player.inventory.addItemStackToInventory(stack)) {
            player.dropPlayerItemWithRandomChoice(stack, false);
        }
        player.addChatMessage(new ChatComponentText("Reality Engine AI: artefato criado: " + name));
    }

    private static void createBlock(EntityPlayer player, String prompt) {
        World world = player.worldObj;
        Vec3 look = player.getLookVec();
        int x = MathHelper.floor_double(player.posX + look.xCoord * 3.0D);
        int y = Math.max(1, Math.min(250, MathHelper.floor_double(player.posY + look.yCoord * 3.0D)));
        int z = MathHelper.floor_double(player.posZ + look.zCoord * 3.0D);

        if (!world.isAirBlock(x, y, z)) {
            y++;
        }
        if (y > 250 || !world.isAirBlock(x, y, z)) {
            player.addChatMessage(new ChatComponentText("Reality Engine AI: não encontrei espaço livre para o bloco."));
            return;
        }
        if (!world.setBlock(x, y, z, realityBlock, 0, 3)) {
            player.addChatMessage(new ChatComponentText("Reality Engine AI: o Minecraft recusou a colocação do bloco."));
            return;
        }

        TileEntity tile = world.getTileEntity(x, y, z);
        if (tile instanceof TileEntityReality) {
            ((TileEntityReality) tile).setDescription(prompt);
        }
        player.addChatMessage(new ChatComponentText("Reality Engine AI: bloco criado em " + x + ", " + y + ", " + z + "."));
    }

    private static void createEntity(EntityPlayer player, String prompt) {
        World world = player.worldObj;
        EntityReality entity = new EntityReality(world);
        Vec3 look = player.getLookVec();
        double x = player.posX + look.xCoord * 4.0D;
        double y = Math.max(1.0D, Math.min(245.0D, player.posY + look.yCoord * 4.0D));
        double z = player.posZ + look.zCoord * 4.0D;
        entity.setLocationAndAngles(x, y, z, player.rotationYaw, 0.0F);
        entity.setDescription(prompt);

        if (!world.spawnEntityInWorld(entity)) {
            player.addChatMessage(new ChatComponentText("Reality Engine AI: não foi possível gerar a entidade neste local."));
            return;
        }
        player.addChatMessage(new ChatComponentText("Reality Engine AI: entidade criada. A escala está limitada para manter a estabilidade."));
    }

    private static void createDimension(EntityPlayer player, String prompt) {
        if (!(player instanceof EntityPlayerMP)) {
            player.addChatMessage(new ChatComponentText("Reality Engine AI: dimensões exigem o lado servidor."));
            return;
        }
        if (providerType < 0) {
            throw new IllegalStateException("Reality Engine provider was not registered.");
        }

        int dimensionId = -1;
        try {
            dimensionId = DimensionManager.getNextFreeDimId();
            if (DimensionManager.isDimensionRegistered(dimensionId)) {
                throw new IllegalStateException("Forge returned an occupied dimension ID.");
            }
            DimensionManager.registerDimension(dimensionId, providerType);
            DIMENSION_DESCRIPTIONS.put(dimensionId, prompt);
            DimensionManager.initDimension(dimensionId);
            WorldServer destination = DimensionManager.getWorld(dimensionId);
            if (destination == null) {
                throw new IllegalStateException("Forge did not initialize the new dimension.");
            }
            ((EntityPlayerMP) player).travelToDimension(dimensionId);
            player.addChatMessage(new ChatComponentText("Reality Engine AI: dimensão criada. ID " + dimensionId + "."));
        } catch (Exception exception) {
            if (dimensionId >= 0 && DimensionManager.getWorld(dimensionId) == null) {
                DimensionManager.unregisterDimension(dimensionId);
                DIMENSION_DESCRIPTIONS.remove(dimensionId);
            }
            throw exception;
        }
    }

    private static String shorten(String text, int limit) {
        return text.length() > limit ? text.substring(0, limit - 3) + "..." : text;
    }

    public static final class ItemRealityArtifact extends Item {
        public ItemRealityArtifact() {
            setUnlocalizedName("reality_artifact");
            setTextureName("minecraft:nether_star");
            setMaxStackSize(1);
            setCreativeTab(CreativeTabs.tabMisc);
        }
    }

    public static final class BlockReality extends BlockContainer {
        public BlockReality() {
            super(Material.rock);
            setBlockName("reality_block");
            setBlockTextureName("minecraft:obsidian");
            setHardness(2.0F);
            setResistance(10.0F);
            setStepSound(soundTypeStone);
            setCreativeTab(CreativeTabs.tabBlock);
        }

        @Override
        public TileEntity createNewTileEntity(World world, int metadata) {
            return new TileEntityReality();
        }

        @Override
        public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player, int side, float hitX, float hitY, float hitZ) {
            if (!world.isRemote) {
                TileEntity tile = world.getTileEntity(x, y, z);
                if (tile instanceof TileEntityReality) {
                    player.addChatMessage(new ChatComponentText("Criação: " + shorten(((TileEntityReality) tile).getDescription(), 120)));
                }
            }
            return true;
        }
    }

    public static final class TileEntityReality extends TileEntity {
        private String description = "";

        public void setDescription(String description) {
            this.description = description == null ? "" : description;
            markDirty();
            if (worldObj != null && !worldObj.isRemote) {
                worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
            }
        }

        public String getDescription() {
            return description;
        }

        @Override
        public void readFromNBT(NBTTagCompound compound) {
            super.readFromNBT(compound);
            description = compound.getString("RealityDescription");
        }

        @Override
        public void writeToNBT(NBTTagCompound compound) {
            super.writeToNBT(compound);
            compound.setString("RealityDescription", description);
        }
    }

    public static final class EntityReality extends EntityCreature {
        public EntityReality(World world) {
            super(world);
            setSize(0.8F, 1.8F);
            tasks.addTask(0, new EntityAISwimming(this));
            tasks.addTask(1, new EntityAIPanic(this, 1.2D));
            tasks.addTask(4, new EntityAIWander(this, 1.0D));
            tasks.addTask(5, new EntityAIWatchClosest(this, EntityPlayer.class, 16.0F));
            tasks.addTask(6, new EntityAILookIdle(this));
        }

        public void setDescription(String description) {
            float height = 1.8F;
            Matcher matcher = METERS.matcher(description.toLowerCase(Locale.ROOT));
            if (matcher.find()) {
                try {
                    float meters = Float.parseFloat(matcher.group(1).replace(',', '.'));
                    height = Math.min(8.0F, Math.max(1.8F, meters / 10.0F));
                } catch (NumberFormatException ignored) {
                    height = 1.8F;
                }
            }
            setSize(Math.min(4.0F, height * 0.5F), height);
            setCustomNameTag("§d" + shorten(description, 48));
            setAlwaysRenderNameTag(true);
            getEntityData().setString("RealityDescription", description);
        }

        @Override
        protected void applyEntityAttributes() {
            super.applyEntityAttributes();
            getEntityAttribute(SharedMonsterAttributes.maxHealth).setBaseValue(40.0D);
            getEntityAttribute(SharedMonsterAttributes.movementSpeed).setBaseValue(0.25D);
            getEntityAttribute(SharedMonsterAttributes.followRange).setBaseValue(32.0D);
        }

        @Override
        public void readEntityFromNBT(NBTTagCompound compound) {
            super.readEntityFromNBT(compound);
            setDescription(compound.getString("RealityDescription"));
        }

        @Override
        public void writeEntityToNBT(NBTTagCompound compound) {
            super.writeEntityToNBT(compound);
            compound.setString("RealityDescription", getEntityData().getString("RealityDescription"));
        }
    }

    public static final class RealityWorldProvider extends WorldProvider {
        @Override
        public void registerWorldChunkManager() {
            String description = DIMENSION_DESCRIPTIONS.containsKey(dimensionId) ? DIMENSION_DESCRIPTIONS.get(dimensionId).toLowerCase(Locale.ROOT) : "";
            BiomeGenBase biome = BiomeGenBase.plains;
            if (description.contains("deserto") || description.contains("areia")) {
                biome = BiomeGenBase.desert;
            } else if (description.contains("neve") || description.contains("gelo") || description.contains("frio")) {
                biome = BiomeGenBase.icePlains;
            } else if (description.contains("inferno") || description.contains("lava") || description.contains("fogo")) {
                biome = BiomeGenBase.hell;
            } else if (description.contains("floresta") || description.contains("arvore") || description.contains("árvore")) {
                biome = BiomeGenBase.forest;
            }
            worldChunkMgr = new WorldChunkManagerHell(biome, 0.5F);
            hasNoSky = description.contains("espaço") || description.contains("espaco") || description.contains("vazio");
        }

        @Override
        public IChunkProvider createChunkGenerator() {
            return new ChunkProviderGenerate(worldObj, worldObj.getSeed(), true);
        }

        @Override
        public String getDimensionName() {
            String description = DIMENSION_DESCRIPTIONS.get(dimensionId);
            return description == null || description.isEmpty() ? "Reality Dimension" : "Reality: " + shorten(description, 40);
        }

        @Override
        public boolean canRespawnHere() {
            return true;
        }

        @Override
        public boolean isSurfaceWorld() {
            return !hasNoSky;
        }
    }
}
