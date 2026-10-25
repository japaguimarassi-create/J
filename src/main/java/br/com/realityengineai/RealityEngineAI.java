package br.com.realityengineai;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.SidedProxy;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import cpw.mods.fml.common.network.NetworkRegistry;
import cpw.mods.fml.common.registry.EntityRegistry;
import cpw.mods.fml.common.registry.GameRegistry;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import net.minecraft.block.Block;
import net.minecraft.block.BlockContainer;
import net.minecraft.block.material.Material;
import net.minecraft.client.renderer.texture.IIconRegister;
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
import net.minecraft.item.ItemFood;
import net.minecraft.item.ItemPickaxe;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemSword;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.IIcon;
import net.minecraft.util.MathHelper;
import net.minecraft.util.MovingObjectPosition;
import net.minecraft.util.Vec3;
import net.minecraft.world.World;
import net.minecraft.world.WorldProvider;
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
    public static final String VERSION = "0.2.0";
    public static final int GUI_COMPUTER = 7201;
    public static final Logger LOG = LogManager.getLogger(NAME);
    private static final Pattern DIMENSION_ID = Pattern.compile("(?:dimens[aã]o\\s*)?(\\d+)");
    private static final Map<Integer, String> DIMENSION_DESCRIPTIONS = new HashMap<Integer, String>();
    private static int providerType = -1;
    private static int latestDimensionId = Integer.MIN_VALUE;
    private static File dimensionFile;

    @Mod.Instance(MOD_ID)
    public static RealityEngineAI INSTANCE;

    @SidedProxy(clientSide = "br.com.realityengineai.ClientProxy", serverSide = "br.com.realityengineai.CommonProxy")
    public static CommonProxy PROXY;

    public static OfflineBrain BRAIN;
    public static ItemRealityArtifact realityArtifact;
    public static ItemRealitySword realitySword;
    public static ItemRealityPickaxe realityPickaxe;
    public static ItemRealityFood realityFood;
    public static BlockReality realityBlock;
    public static BlockComputer computerBlock;
    public static BlockCrystal crystalBlock;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        BRAIN = new OfflineBrain();

        realityArtifact = new ItemRealityArtifact();
        GameRegistry.registerItem(realityArtifact, "reality_artifact");
        realitySword = new ItemRealitySword();
        GameRegistry.registerItem(realitySword, "reality_sword");
        realityPickaxe = new ItemRealityPickaxe();
        GameRegistry.registerItem(realityPickaxe, "reality_pickaxe");
        realityFood = new ItemRealityFood();
        GameRegistry.registerItem(realityFood, "reality_food");

        realityBlock = new BlockReality();
        GameRegistry.registerBlock(realityBlock, "reality_block");
        computerBlock = new BlockComputer();
        GameRegistry.registerBlock(computerBlock, "reality_computer");
        crystalBlock = new BlockCrystal();
        GameRegistry.registerBlock(crystalBlock, "reality_crystal");
        GameRegistry.registerTileEntity(TileEntityReality.class, MOD_ID + ":reality_block");
        GameRegistry.registerTileEntity(TileEntityComputer.class, MOD_ID + ":reality_computer");
        GameRegistry.registerTileEntity(TileEntityCrystal.class, MOD_ID + ":reality_crystal");

        EntityRegistry.registerModEntity(EntityReality.class, "reality_entity", 1, this, 64, 3, true);
        registerDimensionProvider();
        loadDimensions(event.getModConfigurationDirectory());

        NetworkRegistry.INSTANCE.registerGuiHandler(this, new ComputerGuiHandler());
        MinecraftForge.EVENT_BUS.register(new ChatCreationHandler());
        if (PROXY != null) {
            PROXY.registerRenderers();
        }
        LOG.info("Reality Engine AI 0.2.0 initialized. brainReady=" + (BRAIN != null && BRAIN.isReady())
            + ", parameters=" + (BRAIN == null ? 0 : BRAIN.getParameterCount()));
    }

    private static void registerDimensionProvider() {
        for (int id = 128; id < 2048; id++) {
            if (DimensionManager.registerProviderType(id, RealityWorldProvider.class, false)) {
                providerType = id;
                return;
            }
        }
        LOG.error("No free Reality Engine dimension provider type was available.");
    }

    private static void loadDimensions(File configDirectory) {
        if (configDirectory == null) {
            return;
        }
        if (!configDirectory.exists() && !configDirectory.mkdirs()) {
            LOG.warn("Could not create configuration folder for dimensions.");
            return;
        }
        dimensionFile = new File(configDirectory, "realityengineai-dimensions.properties");
        Properties properties = new Properties();
        if (dimensionFile.isFile()) {
            FileInputStream input = null;
            try {
                input = new FileInputStream(dimensionFile);
                properties.load(input);
            } catch (IOException exception) {
                LOG.warn("Could not load saved dimension metadata.", exception);
            } finally {
                if (input != null) {
                    try {
                        input.close();
                    } catch (IOException ignored) {
                    }
                }
            }
        }
        int count;
        try {
            count = Math.min(128, Math.max(0, Integer.parseInt(properties.getProperty("count", "0"))));
        } catch (NumberFormatException exception) {
            count = 0;
        }
        for (int index = 0; index < count; index++) {
            try {
                int id = Integer.parseInt(properties.getProperty("dimension." + index + ".id", ""));
                String description = properties.getProperty("dimension." + index + ".description", "");
                if (id == 0 || id == -1 || description.isEmpty()) {
                    continue;
                }
                if (!DimensionManager.isDimensionRegistered(id) && providerType >= 0) {
                    DimensionManager.registerDimension(id, providerType);
                }
                if (DimensionManager.isDimensionRegistered(id)) {
                    DIMENSION_DESCRIPTIONS.put(Integer.valueOf(id), description);
                    latestDimensionId = id;
                }
            } catch (Exception exception) {
                LOG.warn("Skipping invalid saved dimension entry " + index + ".", exception);
            }
        }
    }

    private static void saveDimensions() {
        if (dimensionFile == null) {
            return;
        }
        Properties properties = new Properties();
        int index = 0;
        for (Map.Entry<Integer, String> entry : DIMENSION_DESCRIPTIONS.entrySet()) {
            properties.setProperty("dimension." + index + ".id", String.valueOf(entry.getKey().intValue()));
            properties.setProperty("dimension." + index + ".description", entry.getValue());
            index++;
        }
        properties.setProperty("count", String.valueOf(index));
        FileOutputStream output = null;
        try {
            output = new FileOutputStream(dimensionFile);
            properties.store(output, "Reality Engine AI dimensions; IDs are shared by this Minecraft installation.");
        } catch (IOException exception) {
            LOG.error("Could not persist Reality Engine dimensions.", exception);
        } finally {
            if (output != null) {
                try {
                    output.close();
                } catch (IOException ignored) {
                }
            }
        }
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
                event.player.addChatMessage(new ChatComponentText("Reality Engine: use 'crie <pedido>'. Exemplos: crie um computador em bloco; crie uma espada; crie uma dimensão de neve; crie lista de mods instalados."));
                return;
            }
            executeCreation(event.player, result.getPrompt());
        }
    }

    private static void executeCreation(EntityPlayer player, String prompt) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote || prompt == null || prompt.trim().isEmpty()) {
            return;
        }
        String normalized = ModKnowledgeBase.normalize(prompt);
        try {
            if (containsAny(normalized, "lista de mods", "mods instalados", "mods carregados", "quais mods", "modid", "catalogo de mods")) {
                ModKnowledgeBase.sendInstalledMods(player);
                return;
            }
            if (containsAny(normalized, "liste os blocos", "listar blocos", "catalogo de blocos", "blocos registrados", "itens registrados")) {
                ModKnowledgeBase.sendRegistrySummary(player);
                return;
            }
            if (containsAny(normalized, "buscar registro", "procure no mod", "buscar item do mod", "buscar bloco do mod")) {
                String query = normalized.replace("buscar registro", "").replace("procure no mod", "").replace("buscar item do mod", "").replace("buscar bloco do mod", "").trim();
                if (query.isEmpty()) {
                    query = prompt;
                }
                ModKnowledgeBase.sendRegistryMatches(player, query);
                return;
            }
            if (containsAny(normalized, "entrar na dimensao", "ir para dimensao", "entrar dimensao", "teleportar para dimensao", "ir para a dimensao")) {
                enterDimension(player, prompt);
                return;
            }
            if (containsAny(normalized, "ajuda", "o que sabe", "comandos", "capacidades", "como funciona")) {
                sendHelp(player);
                return;
            }

            String intent = resolveIntent(prompt, normalized);
            if ("ambiguous".equals(intent)) {
                player.addChatMessage(new ChatComponentText("Reality Engine: não vou gerar um objeto aleatório. Especifique o tipo: item, bloco/computador, criatura ou dimensão."));
                player.addChatMessage(new ChatComponentText("Exemplos: crie um computador em bloco | crie uma espada | crie um dragão | crie uma dimensão de neve"));
                return;
            }
            if (intent.startsWith("dimension_")) {
                createDimension(player, prompt);
            } else if (intent.startsWith("entity_")) {
                createEntity(player, prompt);
            } else if (intent.startsWith("block_")) {
                createBlock(player, prompt, intent);
            } else if (intent.startsWith("item_")) {
                createItem(player, prompt, intent);
            } else if ("query_mods".equals(intent)) {
                ModKnowledgeBase.sendInstalledMods(player);
            } else if ("query_blocks".equals(intent) || "query_items".equals(intent) || "query_entities".equals(intent) || "query_dimensions".equals(intent)) {
                ModKnowledgeBase.sendRegistrySummary(player);
            } else {
                player.addChatMessage(new ChatComponentText("Reality Engine: intenção não reconhecida com segurança; nada foi criado."));
            }
        } catch (Exception exception) {
            LOG.error("Creation failed: " + prompt, exception);
            player.addChatMessage(new ChatComponentText("Reality Engine: a operação falhou e não foi concluída. Consulte o latest.log."));
        }
    }

    private static String resolveIntent(String prompt, String normalized) {
        if (containsAny(normalized, "computador", "computer", "terminal em bloco", "pc em bloco", "maquina de computacao", "maquina computacional")) {
            return "block_computer";
        }
        if (containsAny(normalized, "dimensao", "planeta", "universo", "mundo novo")) {
            if (containsAny(normalized, "deserto", "areia", "duna")) {
                return "dimension_desert";
            }
            if (containsAny(normalized, "neve", "gelo", "frio", "congelado")) {
                return "dimension_cold";
            }
            if (containsAny(normalized, "floresta", "arvore", "selva")) {
                return "dimension_forest";
            }
            if (containsAny(normalized, "espaco", "vazio", "galaxia", "estrela")) {
                return "dimension_space";
            }
            if (containsAny(normalized, "infernal", "lava", "fogo", "vulcao")) {
                return "dimension_infernal";
            }
            return "dimension_generic";
        }
        if (containsAny(normalized, "dragao", "mob", "criatura", "monstro", "animal novo", "ser vivo", "boss")) {
            OfflineBrain.Prediction prediction = BRAIN == null ? null : BRAIN.predictDetailed(prompt);
            if (prediction != null && "entity_hostile".equals(prediction.label)) {
                return "entity_hostile";
            }
            return containsAny(normalized, "dragao") ? "entity_dragon" : "entity_creature";
        }
        if (containsAny(normalized, "bloco de cristal", "bloco cristalino", "cristal em bloco", "cristal luminoso")) {
            return "block_crystal";
        }
        if (containsAny(normalized, "bloco", "block", "maquina", "estrutura em bloco")) {
            return "block_generic";
        }
        if (containsAny(normalized, "espada", "sabre", "katana", "lamina")) {
            return "item_sword";
        }
        if (containsAny(normalized, "picareta", "machado", "ferramenta", "minerador", "mineracao")) {
            return "item_tool";
        }
        if (containsAny(normalized, "comida", "pao", "fruta", "alimento", "carne")) {
            return "item_food";
        }
        if (containsAny(normalized, "item", "objeto", "artefato", "varinha", "amuleto")) {
            return "item_generic";
        }

        OfflineBrain.Prediction prediction = BRAIN == null ? new OfflineBrain.Prediction("ambiguous", 0.0F) : BRAIN.predictDetailed(prompt);
        if (prediction.confidence >= 0.58F && !("ambiguous".equals(prediction.label) || prediction.label.startsWith("query_"))) {
            return prediction.label;
        }
        return "ambiguous";
    }

    private static boolean containsAny(String text, String... values) {
        for (String value : values) {
            if (text.contains(value)) {
                return true;
            }
        }
        return false;
    }

    private static void sendHelp(EntityPlayer player) {
        player.addChatMessage(new ChatComponentText("Reality Engine AI 0.2.0 - cérebro offline: " + (BRAIN != null && BRAIN.isReady() ? BRAIN.getParameterCount() + " parâmetros" : "pesos indisponíveis") + "."));
        player.addChatMessage(new ChatComponentText("Criações: computador em bloco, bloco de cristal, bloco, espada, picareta, comida, criatura e dimensão temática."));
        player.addChatMessage(new ChatComponentText("Conhecimento de mods: crie lista de mods instalados | crie liste os blocos registrados | crie buscar registro <namespace ou nome>."));
        player.addChatMessage(new ChatComponentText("Criar dimensão não teleporta. Use 'crie entrar na dimensão ID' depois de criar."));
    }

    private static void createItem(EntityPlayer player, String prompt, String intent) {
        Item selected;
        if ("item_sword".equals(intent)) {
            selected = realitySword;
        } else if ("item_tool".equals(intent)) {
            selected = realityPickaxe;
        } else if ("item_food".equals(intent)) {
            selected = realityFood;
        } else {
            selected = realityArtifact;
        }
        ItemStack stack = new ItemStack(selected, 1);
        String name = shorten(prompt, 56);
        stack.setStackDisplayName("§b" + name);
        NBTTagCompound tag = stack.getTagCompound();
        if (tag == null) {
            tag = new NBTTagCompound();
        }
        tag.setString("RealityDescription", prompt);
        tag.setString("RealityKind", intent);
        stack.setTagCompound(tag);
        if (!player.inventory.addItemStackToInventory(stack)) {
            player.dropPlayerItemWithRandomChoice(stack, false);
        }
        player.addChatMessage(new ChatComponentText("Reality Engine: criado " + name + ". Tipo funcional: " + intent + "."));
    }

    private static void createBlock(EntityPlayer player, String prompt, String intent) {
        World world = player.worldObj;
        Placement position = findPlacement(player);
        if (position == null) {
            player.addChatMessage(new ChatComponentText("Reality Engine: não encontrei um espaço livre à frente; nada foi colocado."));
            return;
        }
        Block chosen;
        if ("block_computer".equals(intent)) {
            chosen = computerBlock;
        } else if ("block_crystal".equals(intent)) {
            chosen = crystalBlock;
        } else {
            chosen = realityBlock;
        }
        if (!world.setBlock(position.x, position.y, position.z, chosen, 0, 3)) {
            player.addChatMessage(new ChatComponentText("Reality Engine: o jogo recusou a colocação; nada foi criado."));
            return;
        }
        TileEntity tile = world.getTileEntity(position.x, position.y, position.z);
        if (tile instanceof TileEntityComputer) {
            ((TileEntityComputer) tile).setDescription(prompt);
        } else if (tile instanceof TileEntityCrystal) {
            ((TileEntityCrystal) tile).setDescription(prompt);
        } else if (tile instanceof TileEntityReality) {
            ((TileEntityReality) tile).setDescription(prompt);
        }
        player.addChatMessage(new ChatComponentText("Reality Engine: bloco colocado à frente em " + position.x + ", " + position.y + ", " + position.z + "."));
        if ("block_computer".equals(intent)) {
            player.addChatMessage(new ChatComponentText("Clique com o botão direito no computador para abrir o painel interativo."));
        } else if ("block_crystal".equals(intent)) {
            player.addChatMessage(new ChatComponentText("Cristal personalizado criado; o bloco emite luz e guarda a descrição."));
        }
    }

    private static Placement findPlacement(EntityPlayer player) {
        World world = player.worldObj;
        int targetX;
        int targetY;
        int targetZ;
        MovingObjectPosition hit = player.rayTrace(6.0D, 1.0F);
        if (hit != null && hit.typeOfHit == MovingObjectPosition.MovingObjectType.BLOCK) {
            targetX = hit.blockX;
            targetY = hit.blockY;
            targetZ = hit.blockZ;
            switch (hit.sideHit) {
                case 0: targetY--; break;
                case 1: targetY++; break;
                case 2: targetZ--; break;
                case 3: targetZ++; break;
                case 4: targetX--; break;
                case 5: targetX++; break;
                default: break;
            }
        } else {
            Vec3 look = player.getLookVec();
            targetX = MathHelper.floor_double(player.posX + look.xCoord * 3.0D);
            targetY = MathHelper.floor_double(player.posY + player.getEyeHeight() + look.yCoord * 3.0D - 0.5D);
            targetZ = MathHelper.floor_double(player.posZ + look.zCoord * 3.0D);
        }
        int[][] offsets = new int[][] {
            {0, 0, 0}, {0, 1, 0}, {0, 2, 0},
            {1, 0, 0}, {-1, 0, 0}, {0, 0, 1}, {0, 0, -1},
            {1, 1, 0}, {-1, 1, 0}, {0, 1, 1}, {0, 1, -1},
            {2, 0, 0}, {-2, 0, 0}, {0, 0, 2}, {0, 0, -2}
        };
        for (int[] offset : offsets) {
            int x = targetX + offset[0];
            int y = targetY + offset[1];
            int z = targetZ + offset[2];
            if (y > 0 && y < 255 && world.isAirBlock(x, y, z)) {
                return new Placement(x, y, z);
            }
        }
        return null;
    }

    private static void createEntity(EntityPlayer player, String prompt) {
        World world = player.worldObj;
        EntityReality entity = new EntityReality(world);
        Vec3 look = player.getLookVec();
        double x = player.posX + look.xCoord * 3.0D;
        double y = Math.max(1.0D, Math.min(245.0D, player.posY + look.yCoord * 3.0D));
        double z = player.posZ + look.zCoord * 3.0D;
        entity.setLocationAndAngles(x, y, z, player.rotationYaw, 0.0F);
        entity.setDescription(prompt);
        if (!world.spawnEntityInWorld(entity)) {
            player.addChatMessage(new ChatComponentText("Reality Engine: não foi possível gerar a criatura neste local."));
            return;
        }
        player.addChatMessage(new ChatComponentText("Reality Engine: criatura criada com textura personalizada e IA de movimento básica."));
    }

    private static void createDimension(EntityPlayer player, String prompt) {
        if (!(player instanceof EntityPlayerMP) || providerType < 0) {
            player.addChatMessage(new ChatComponentText("Reality Engine: o provedor de dimensão não está disponível; nada foi registrado."));
            return;
        }
        int id = DimensionManager.getNextFreeDimId();
        if (id == 0 || id == -1 || DimensionManager.isDimensionRegistered(id)) {
            player.addChatMessage(new ChatComponentText("Reality Engine: não encontrei um ID de dimensão livre."));
            return;
        }
        try {
            DimensionManager.registerDimension(id, providerType);
            DIMENSION_DESCRIPTIONS.put(Integer.valueOf(id), prompt);
            latestDimensionId = id;
            saveDimensions();
            player.addChatMessage(new ChatComponentText("Reality Engine: dimensão " + id + " registrada e salva: " + shorten(prompt, 80) + "."));
            player.addChatMessage(new ChatComponentText("Você permanece no mundo atual. Para entrar depois: crie entrar na dimensão " + id + "."));
        } catch (Exception exception) {
            DIMENSION_DESCRIPTIONS.remove(Integer.valueOf(id));
            LOG.error("Could not register requested dimension: " + prompt, exception);
            player.addChatMessage(new ChatComponentText("Reality Engine: registro de dimensão falhou; o jogador não foi teleportado."));
        }
    }

    private static void enterDimension(EntityPlayer player, String prompt) {
        if (!(player instanceof EntityPlayerMP)) {
            player.addChatMessage(new ChatComponentText("Reality Engine: entrar em dimensões exige o servidor."));
            return;
        }
        Matcher matcher = DIMENSION_ID.matcher(ModKnowledgeBase.normalize(prompt));
        int id = latestDimensionId;
        if (matcher.find()) {
            try {
                id = Integer.parseInt(matcher.group(1));
            } catch (NumberFormatException ignored) {
                id = latestDimensionId;
            }
        }
        if (id == Integer.MIN_VALUE || !DIMENSION_DESCRIPTIONS.containsKey(Integer.valueOf(id)) || !DimensionManager.isDimensionRegistered(id)) {
            player.addChatMessage(new ChatComponentText("Reality Engine: dimensão não encontrada. Crie uma dimensão primeiro ou forneça o ID."));
            return;
        }
        ((EntityPlayerMP) player).travelToDimension(id);
        player.addChatMessage(new ChatComponentText("Reality Engine: entrada na dimensão " + id + " concluída."));
    }

    private static String shorten(String value, int limit) {
        if (value == null) {
            return "";
        }
        return value.length() > limit ? value.substring(0, limit - 3) + "..." : value;
    }

    private static final class Placement {
        private final int x;
        private final int y;
        private final int z;

        private Placement(int x, int y, int z) {
            this.x = x;
            this.y = y;
            this.z = z;
        }
    }

    public static final class ItemRealityArtifact extends Item {
        public ItemRealityArtifact() {
            setUnlocalizedName("reality_artifact");
            setTextureName(MOD_ID + ":reality_artifact");
            setMaxStackSize(1);
            setCreativeTab(CreativeTabs.tabMisc);
        }

        @Override
        public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
            if (!world.isRemote) {
                NBTTagCompound tag = stack.getTagCompound();
                String description = tag == null ? "" : ModKnowledgeBase.normalize(tag.getString("RealityDescription"));
                if (description.contains("cura") || description.contains("heal") || description.contains("vida")) {
                    player.heal(8.0F);
                    player.addChatMessage(new ChatComponentText("Artefato: restaurou 8 pontos de vida."));
                } else if (description.contains("velocidade") || description.contains("speed")) {
                    player.addPotionEffect(new PotionEffect(Potion.moveSpeed.id, 20 * 20, 1));
                    player.addChatMessage(new ChatComponentText("Artefato: velocidade aumentada por 20 segundos."));
                } else if (description.contains("forca") || description.contains("strength")) {
                    player.addPotionEffect(new PotionEffect(Potion.damageBoost.id, 20 * 20, 1));
                    player.addChatMessage(new ChatComponentText("Artefato: força aumentada por 20 segundos."));
                } else {
                    player.addChatMessage(new ChatComponentText("Artefato ativo: nenhum poder reconhecido com segurança. Descrição salva no item."));
                }
            }
            return stack;
        }
    }

    public static final class ItemRealitySword extends ItemSword {
        public ItemRealitySword() {
            super(Item.ToolMaterial.EMERALD);
            setUnlocalizedName("reality_sword");
            setTextureName(MOD_ID + ":reality_sword");
            setCreativeTab(CreativeTabs.tabCombat);
        }
    }

    public static final class ItemRealityPickaxe extends ItemPickaxe {
        public ItemRealityPickaxe() {
            super(Item.ToolMaterial.EMERALD);
            setUnlocalizedName("reality_pickaxe");
            setTextureName(MOD_ID + ":reality_pickaxe");
            setCreativeTab(CreativeTabs.tabTools);
        }
    }

    public static final class ItemRealityFood extends ItemFood {
        public ItemRealityFood() {
            super(8, 1.2F, false);
            setUnlocalizedName("reality_food");
            setTextureName(MOD_ID + ":reality_food");
            setCreativeTab(CreativeTabs.tabFood);
        }
    }

    public static final class BlockReality extends BlockContainer {
        public BlockReality() {
            super(Material.rock);
            setBlockName("reality_block");
            setBlockTextureName(MOD_ID + ":reality_block");
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
                String description = tile instanceof TileEntityReality ? ((TileEntityReality) tile).getDescription() : "";
                String normalized = ModKnowledgeBase.normalize(description);
                if (normalized.contains("cura") || normalized.contains("medico") || normalized.contains("heal")) {
                    player.heal(4.0F);
                    player.addChatMessage(new ChatComponentText("Bloco funcional: restaurou 4 pontos de vida."));
                } else if (normalized.contains("energia") || normalized.contains("velocidade")) {
                    player.addPotionEffect(new PotionEffect(Potion.moveSpeed.id, 20 * 10, 0));
                    player.addChatMessage(new ChatComponentText("Bloco funcional: concedeu impulso de velocidade por 10 segundos."));
                } else {
                    player.addChatMessage(new ChatComponentText("Bloco ativo. Tipo: bloco de realidade. Coordenadas: " + x + ", " + y + ", " + z + "."));
                    player.addChatMessage(new ChatComponentText("Descrição salva: " + shorten(description, 100)));
                }
            }
            return true;
        }
    }

    public static final class BlockComputer extends BlockContainer {
        @SideOnly(Side.CLIENT)
        private IIcon front;
        @SideOnly(Side.CLIENT)
        private IIcon side;
        @SideOnly(Side.CLIENT)
        private IIcon top;

        public BlockComputer() {
            super(Material.iron);
            setBlockName("reality_computer");
            setHardness(3.0F);
            setResistance(12.0F);
            setStepSound(soundTypeMetal);
            setCreativeTab(CreativeTabs.tabRedstone);
        }

        @SideOnly(Side.CLIENT)
        @Override
        public void registerBlockIcons(IIconRegister register) {
            front = register.registerIcon(MOD_ID + ":computer_front");
            side = register.registerIcon(MOD_ID + ":computer_side");
            top = register.registerIcon(MOD_ID + ":computer_top");
        }

        @SideOnly(Side.CLIENT)
        @Override
        public IIcon getIcon(int sideHit, int metadata) {
            if (sideHit == 1 || sideHit == 0) {
                return top;
            }
            if (sideHit == 2) {
                return front;
            }
            return side;
        }

        @Override
        public TileEntity createNewTileEntity(World world, int metadata) {
            return new TileEntityComputer();
        }

        @Override
        public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player, int sideHit, float hitX, float hitY, float hitZ) {
            if (!world.isRemote && INSTANCE != null) {
                player.openGui(INSTANCE, GUI_COMPUTER, world, x, y, z);
            }
            return true;
        }
    }

    public static final class BlockCrystal extends BlockContainer {
        public BlockCrystal() {
            super(Material.glass);
            setBlockName("reality_crystal");
            setBlockTextureName(MOD_ID + ":reality_crystal");
            setHardness(1.5F);
            setResistance(6.0F);
            setLightLevel(0.8F);
            setStepSound(soundTypeGlass);
            setCreativeTab(CreativeTabs.tabBlock);
        }

        @Override
        public TileEntity createNewTileEntity(World world, int metadata) {
            return new TileEntityCrystal();
        }

        @Override
        public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player, int side, float hitX, float hitY, float hitZ) {
            if (!world.isRemote) {
                player.addChatMessage(new ChatComponentText("Cristal de realidade: emite luz e responde à interação."));
            }
            return true;
        }
    }

    public static class TileEntityReality extends TileEntity {
        private String description = "";

        public void setDescription(String value) {
            description = value == null ? "" : value;
            markDirty();
            if (worldObj != null && !worldObj.isRemote) {
                worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
            }
        }

        public String getDescription() {
            return description;
        }

        @Override
        public void readFromNBT(NBTTagCompound tag) {
            super.readFromNBT(tag);
            description = tag.getString("RealityDescription");
        }

        @Override
        public void writeToNBT(NBTTagCompound tag) {
            super.writeToNBT(tag);
            tag.setString("RealityDescription", description);
        }
    }

    public static final class TileEntityComputer extends TileEntity {
        private String description = "";

        public void setDescription(String value) {
            description = value == null ? "" : value;
            markDirty();
        }

        public String getDescription() {
            return description;
        }

        @Override
        public void readFromNBT(NBTTagCompound tag) {
            super.readFromNBT(tag);
            description = tag.getString("RealityDescription");
        }

        @Override
        public void writeToNBT(NBTTagCompound tag) {
            super.writeToNBT(tag);
            tag.setString("RealityDescription", description);
        }
    }

    public static final class TileEntityCrystal extends TileEntity {
        private String description = "";

        public void setDescription(String value) {
            description = value == null ? "" : value;
            markDirty();
        }

        public String getDescription() {
            return description;
        }

        @Override
        public void readFromNBT(NBTTagCompound tag) {
            super.readFromNBT(tag);
            description = tag.getString("RealityDescription");
        }

        @Override
        public void writeToNBT(NBTTagCompound tag) {
            super.writeToNBT(tag);
            tag.setString("RealityDescription", description);
        }
    }

    public static final class EntityReality extends EntityCreature {
        private static final Pattern METERS = Pattern.compile("(\\d+(?:[.,]\\d+)?)\\s*(?:metros|metro|m)\\b");

        public EntityReality(World world) {
            super(world);
            setSize(0.8F, 1.8F);
            tasks.addTask(0, new EntityAISwimming(this));
            tasks.addTask(1, new EntityAIPanic(this, 1.2D));
            tasks.addTask(4, new EntityAIWander(this, 1.0D));
            tasks.addTask(5, new EntityAIWatchClosest(this, EntityPlayer.class, 16.0F));
            tasks.addTask(6, new EntityAILookIdle(this));
        }

        public void setDescription(String value) {
            String description = value == null ? "" : value;
            float height = 1.8F;
            Matcher matcher = METERS.matcher(ModKnowledgeBase.normalize(description));
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
        public void readEntityFromNBT(NBTTagCompound tag) {
            super.readEntityFromNBT(tag);
            setDescription(tag.getString("RealityDescription"));
        }

        @Override
        public void writeEntityToNBT(NBTTagCompound tag) {
            super.writeEntityToNBT(tag);
            tag.setString("RealityDescription", getEntityData().getString("RealityDescription"));
        }
    }

    public static final class RealityWorldProvider extends WorldProvider {
        @Override
        public void registerWorldChunkManager() {
            String description = DIMENSION_DESCRIPTIONS.containsKey(Integer.valueOf(dimensionId))
                ? ModKnowledgeBase.normalize(DIMENSION_DESCRIPTIONS.get(Integer.valueOf(dimensionId))) : "";
            BiomeGenBase biome = BiomeGenBase.plains;
            if (containsAny(description, "deserto", "areia", "duna")) {
                biome = BiomeGenBase.desert;
            } else if (containsAny(description, "neve", "gelo", "frio", "congelado")) {
                biome = BiomeGenBase.icePlains;
            } else if (containsAny(description, "floresta", "arvore", "selva")) {
                biome = BiomeGenBase.forest;
            } else if (containsAny(description, "infernal", "fogo", "vulcao")) {
                biome = BiomeGenBase.desert;
            }
            worldChunkMgr = new WorldChunkManagerHell(biome, 0.5F);
            hasNoSky = containsAny(description, "espaco", "vazio", "galaxia");
        }

        @Override
        public IChunkProvider createChunkGenerator() {
            return new ChunkProviderGenerate(worldObj, worldObj.getSeed(), true);
        }

        @Override
        public String getDimensionName() {
            String description = DIMENSION_DESCRIPTIONS.get(Integer.valueOf(dimensionId));
            return description == null || description.isEmpty() ? "Reality Dimension " + dimensionId : "Reality: " + shorten(description, 40);
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
