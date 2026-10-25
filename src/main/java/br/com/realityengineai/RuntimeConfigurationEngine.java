package br.com.realityengineai;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import net.minecraft.block.Block;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.util.ChatComponentText;
import net.minecraft.world.World;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.EntityJoinWorldEvent;
import cpw.mods.fml.common.gameevent.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.world.BlockEvent;
import net.minecraftforge.oredict.OreDictionary;

public final class RuntimeConfigurationEngine {
    public static final RuntimeConfigurationEngine INSTANCE = new RuntimeConfigurationEngine();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final int MAX_RULES = 256;
    private static final int MAX_ACTIONS_PER_RULE = 8;
    private static final int MAX_ACTIONS_PER_EVENT = 32;
    private static final int MAX_COOLDOWN = 12000;
    private File rulesFile;
    private final List<Rule> rules = new ArrayList<Rule>();
    private final Map<String, Long> cooldowns = new HashMap<String, Long>();
    private long eventsHandled;
    private boolean dispatching;

    private RuntimeConfigurationEngine() {
    }

    public synchronized void initialize(File configDirectory) {
        File root = new File(configDirectory, "realityengineai");
        if (!root.exists() && !root.mkdirs()) {
            RealityEngineAI.LOG.error("Could not create runtime configuration directory: " + root);
            return;
        }
        rulesFile = new File(root, "runtime-rules.json");
        if (!rulesFile.isFile()) {
            writeDefaultConfiguration();
        }
        reload();
    }

    public synchronized boolean reload() {
        if (rulesFile == null || !rulesFile.isFile()) {
            return false;
        }
        try {
            JsonObject root = new JsonParser().parse(new String(java.nio.file.Files.readAllBytes(rulesFile.toPath()), StandardCharsets.UTF_8)).getAsJsonObject();
            if (!root.has("enabled") || !root.get("enabled").getAsBoolean()) {
                rules.clear();
                RealityEngineAI.LOG.info("Runtime configuration rules are disabled.");
                return true;
            }
            JsonArray input = root.getAsJsonArray("rules");
            List<Rule> parsed = new ArrayList<Rule>();
            if (input != null) {
                for (JsonElement element : input) {
                    if (parsed.size() >= MAX_RULES) {
                        break;
                    }
                    if (element == null || !element.isJsonObject()) {
                        continue;
                    }
                    Rule rule = Rule.parse(element.getAsJsonObject());
                    if (rule != null) {
                        parsed.add(rule);
                    }
                }
            }
            rules.clear();
            rules.addAll(parsed);
            cooldowns.clear();
            RealityEngineAI.LOG.info("Loaded " + rules.size() + " runtime configuration rules from " + rulesFile.getName());
            return true;
        } catch (Exception exception) {
            RealityEngineAI.LOG.error("Runtime rules are invalid; existing Minecraft files were not changed.", exception);
            return false;
        }
    }

    public synchronized int getRuleCount() {
        return rules.size();
    }

    public synchronized boolean handleCreationPrompt(EntityPlayer player, String prompt) {
        if (player == null || prompt == null) {
            return false;
        }
        String normalized = ModKnowledgeBase.normalize(prompt);
        if (contains(normalized, "recarregar configuracao", "recarregar regras", "reload config", "reload rules")) {
            boolean ok = reload();
            player.addChatMessage(new ChatComponentText(ok
                ? "Reality Engine: regras recarregadas; " + rules.size() + " ativas."
                : "Reality Engine: não consegui carregar runtime-rules.json. Consulte latest.log."));
            return true;
        }
        if (contains(normalized, "listar configuracoes", "listar regras", "quantas regras", "list rules")) {
            player.addChatMessage(new ChatComponentText("Reality Engine: " + getRuleCount() + " regras de runtime carregadas. Arquivo: config/realityengineai/runtime-rules.json"));
            return true;
        }
        if (!contains(normalized, "configuracao", "regra de runtime", "runtime rule", "runtime config")) {
            return false;
        }
        Rule generated = generateRule(prompt, normalized);
        if (generated == null) {
            player.addChatMessage(new ChatComponentText("Reality Engine: não gerei a regra porque não consegui identificar um evento e uma ação suportados. Consulte runtime-rules.json para a DSL completa; nenhum arquivo do Minecraft foi alterado."));
            return true;
        }
        synchronized (this) {
            if (rulesFile == null || rules.size() >= MAX_RULES) {
                player.addChatMessage(new ChatComponentText("Reality Engine: limite de regras atingido ou configuração indisponível."));
                return true;
            }
            try {
                JsonObject root = new JsonParser().parse(new String(java.nio.file.Files.readAllBytes(rulesFile.toPath()), StandardCharsets.UTF_8)).getAsJsonObject();
                JsonArray array = root.has("rules") && root.get("rules").isJsonArray() ? root.getAsJsonArray("rules") : new JsonArray();
                array.add(generated.toJson());
                root.add("rules", array);
                try (OutputStreamWriter writer = new OutputStreamWriter(new FileOutputStream(rulesFile), StandardCharsets.UTF_8)) {
                    GSON.toJson(root, writer);
                }
                if (reload()) {
                    player.addChatMessage(new ChatComponentText("Reality Engine: configuração criada e ativada sem editar o código-base. Regras ativas: " + rules.size() + "."));
                } else {
                    player.addChatMessage(new ChatComponentText("Reality Engine: não consegui validar a configuração gerada; consulte latest.log."));
                }
            } catch (Exception exception) {
                RealityEngineAI.LOG.error("Could not persist generated runtime rule.", exception);
                player.addChatMessage(new ChatComponentText("Reality Engine: falha ao salvar a regra. Consulte latest.log."));
            }
        }
        return true;
    }

    private Rule generateRule(String prompt, String normalized) {
        String event;
        if (contains(normalized, "quando clicar", "ao clicar", "ao interagir", "on click", "when clicking")) {
            event = "player_interact";
        } else if (contains(normalized, "quando quebrar", "ao quebrar", "when breaking", "on break")) {
            event = "block_break";
        } else {
            return null;
        }

        JsonObject action = new JsonObject();
        String blockId = findRegistryId(normalized, "bloco", "block");
        if (contains(normalized, "coloque", "colocar", "crie um bloco", "set block", "place block")) {
            String targetId = findAfterAny(normalized, "coloque ", "colocar ", "set block ", "place block ");
            targetId = cleanRegistryId(targetId);
            if (targetId.isEmpty()) {
                return null;
            }
            action.addProperty("type", "set_block");
            action.addProperty("block", targetId);
            action.addProperty("offset_x", 0);
            action.addProperty("offset_y", 1);
            action.addProperty("offset_z", 0);
        } else if (contains(normalized, "dê o item", "dar item", "receber item", "give item", "give ")) {
            String itemId = cleanRegistryId(findAfterAny(normalized, "dê o item ", "dar item ", "receber item ", "give item ", "give "));
            if (itemId.isEmpty()) {
                return null;
            }
            action.addProperty("type", "give_item");
            action.addProperty("item", itemId);
            action.addProperty("count", 1);
        } else if (contains(normalized, "mensagem", "message")) {
            String message = findAfterAny(prompt, "mensagem ", "message ");
            if (message.isEmpty()) {
                message = "Regra de runtime executada.";
            }
            action.addProperty("type", "message");
            action.addProperty("text", message.length() > 160 ? message.substring(0, 160) : message);
        } else if (contains(normalized, "noite", "anoitecer", "night")) {
            action.addProperty("type", "set_time");
            action.addProperty("time", 18000);
        } else if (contains(normalized, "dia", "amanhecer", "day")) {
            action.addProperty("type", "set_time");
            action.addProperty("time", 1000);
        } else if (contains(normalized, "chuva", "chuvoso", "rain")) {
            action.addProperty("type", "weather");
            action.addProperty("raining", true);
        } else if (contains(normalized, "explosao", "explodir", "explode")) {
            action.addProperty("type", "explosion");
            action.addProperty("power", 1.0D);
        } else {
            return null;
        }

        JsonObject json = new JsonObject();
        json.addProperty("id", "ai_generated_" + UUID.randomUUID().toString().substring(0, 8));
        json.addProperty("event", event);
        if (!blockId.isEmpty()) {
            json.addProperty("block", blockId);
        }
        json.addProperty("cooldown_ticks", 20);
        JsonArray actions = new JsonArray();
        actions.add(action);
        json.add("actions", actions);
        return Rule.parse(json);
    }

    private static String findRegistryId(String text, String... prefixes) {
        for (String prefix : prefixes) {
            int index = text.indexOf(prefix + " ");
            if (index >= 0) {
                String tail = text.substring(index + prefix.length() + 1).trim();
                String[] words = tail.split("\\s+");
                if (words.length > 0) {
                    String id = cleanRegistryId(words[0]);
                    if (!id.isEmpty()) {
                        return id;
                    }
                }
            }
        }
        return "";
    }

    private static String findAfterAny(String text, String... prefixes) {
        String lower = text.toLowerCase(Locale.ROOT);
        for (String prefix : prefixes) {
            int index = lower.indexOf(prefix.toLowerCase(Locale.ROOT));
            if (index >= 0) {
                return text.substring(index + prefix.length()).trim();
            }
        }
        return "";
    }

    private static String cleanRegistryId(String raw) {
        if (raw == null) {
            return "";
        }
        String firstToken = raw.trim().split("\\s+", 2)[0];
        String value = firstToken.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_:.\\-/]", "");
        if (value.indexOf(':') < 0 && !value.isEmpty()) {
            value = "minecraft:" + value;
        }
        if (value.length() > 96) {
            return "";
        }
        return value;
    }

    private static boolean contains(String text, String... phrases) {
        for (String phrase : phrases) {
            if (text.contains(ModKnowledgeBase.normalize(phrase))) {
                return true;
            }
        }
        return false;
    }

    @SubscribeEvent
    public void onPlayerInteract(PlayerInteractEvent event) {
        if (event == null || event.world == null || event.entityPlayer == null || event.world.isRemote) {
            return;
        }
        if (event.action != PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK && event.action != PlayerInteractEvent.Action.RIGHT_CLICK_AIR) {
            return;
        }
        Block block = event.action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK
            ? event.world.getBlock(event.x, event.y, event.z) : null;
        fire("player_interact", event.world, event.entityPlayer, event.entityPlayer, block,
            event.action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK ? event.x : floor(event.entityPlayer.posX),
            event.action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK ? event.y : floor(event.entityPlayer.posY),
            event.action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK ? event.z : floor(event.entityPlayer.posZ));
    }

    @SubscribeEvent
    public void onBlockBreak(BlockEvent.BreakEvent event) {
        if (event == null || event.world == null || event.world.isRemote || event.getPlayer() == null) {
            return;
        }
        fire("block_break", event.world, event.getPlayer(), event.getPlayer(), event.block, event.x, event.y, event.z);
    }

    @SubscribeEvent
    public void onLivingUpdate(LivingEvent.LivingUpdateEvent event) {
        if (event == null || event.entityLiving == null || event.entityLiving.worldObj == null || event.entityLiving.worldObj.isRemote
            || event.entityLiving.ticksExisted % 20 != 0) {
            return;
        }
        Entity entity = event.entityLiving;
        EntityPlayer player = entity instanceof EntityPlayer ? (EntityPlayer) entity : null;
        fire("entity_tick", entity.worldObj, player, entity, null, floor(entity.posX), floor(entity.posY), floor(entity.posZ));
    }

    @SubscribeEvent
    public void onLivingHurt(LivingHurtEvent event) {
        if (event == null || event.entityLiving == null || event.entityLiving.worldObj == null || event.entityLiving.worldObj.isRemote) {
            return;
        }
        Entity entity = event.entityLiving;
        EntityPlayer player = entity instanceof EntityPlayer ? (EntityPlayer) entity : null;
        fire("living_hurt", entity.worldObj, player, entity, null, floor(entity.posX), floor(entity.posY), floor(entity.posZ));
    }

    @SubscribeEvent
    public void onLivingDeath(LivingDeathEvent event) {
        if (event == null || event.entityLiving == null || event.entityLiving.worldObj == null || event.entityLiving.worldObj.isRemote) {
            return;
        }
        Entity entity = event.entityLiving;
        EntityPlayer player = entity instanceof EntityPlayer ? (EntityPlayer) entity : null;
        fire("living_death", entity.worldObj, player, entity, null, floor(entity.posX), floor(entity.posY), floor(entity.posZ));
    }

    @SubscribeEvent
    public void onEntityJoinWorld(EntityJoinWorldEvent event) {
        if (event == null || event.entity == null || event.world == null || event.world.isRemote) {
            return;
        }
        Entity entity = event.entity;
        EntityPlayer player = entity instanceof EntityPlayer ? (EntityPlayer) entity : null;
        fire("entity_join_world", event.world, player, entity, null, floor(entity.posX), floor(entity.posY), floor(entity.posZ));
    }

    @SubscribeEvent
    public void onPlayerLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event == null || event.player == null || event.player.worldObj == null || event.player.worldObj.isRemote) {
            return;
        }
        fire("player_login", event.player.worldObj, event.player, event.player, null,
            floor(event.player.posX), floor(event.player.posY), floor(event.player.posZ));
    }

    @SubscribeEvent
    public void onPlayerRespawn(PlayerEvent.PlayerRespawnEvent event) {
        if (event == null || event.player == null || event.player.worldObj == null || event.player.worldObj.isRemote) {
            return;
        }
        fire("player_respawn", event.player.worldObj, event.player, event.player, null,
            floor(event.player.posX), floor(event.player.posY), floor(event.player.posZ));
    }

    @SubscribeEvent
    public void onWorldTick(TickEvent.WorldTickEvent event) {
        if (event == null || event.phase != TickEvent.Phase.END || event.world == null || event.world.isRemote
            || event.world.getTotalWorldTime() % 20L != 0L) {
            return;
        }
        fire("world_tick", event.world, null, null, null, 0, 64, 0);
    }

    private synchronized void fire(String eventName, World world, EntityPlayer player, Entity entity, Block block, int x, int y, int z) {
        if (dispatching || world == null) {
            return;
        }
        dispatching = true;
        try {
            int actionsRun = 0;
            long now = world.getTotalWorldTime();
            Iterator<Rule> iterator = rules.iterator();
            while (iterator.hasNext() && actionsRun < MAX_ACTIONS_PER_EVENT) {
                Rule rule = iterator.next();
                if (!rule.enabled || !eventName.equals(rule.event) || !rule.matches(block, entity)) {
                    continue;
                }
                String subject = player != null ? player.getUniqueID().toString() : (entity != null ? entity.getUniqueID().toString() : "world");
                String key = rule.id + ":" + world.provider.dimensionId + ":" + subject;
                Long last = cooldowns.get(key);
                if (last != null && now - last.longValue() < rule.cooldownTicks) {
                    continue;
                }
                cooldowns.put(key, Long.valueOf(now));
                for (JsonObject action : rule.actions) {
                    if (actionsRun >= MAX_ACTIONS_PER_EVENT) {
                        break;
                    }
                    try {
                        executeAction(action, world, player, entity, x, y, z);
                    } catch (Exception exception) {
                        RealityEngineAI.LOG.warn("Runtime action failed in rule " + rule.id + ": " + exception.getMessage());
                    }
                    actionsRun++;
                }
                eventsHandled++;
            }
            if (cooldowns.size() > 4096) {
                cooldowns.clear();
            }
        } finally {
            dispatching = false;
        }
    }

    private void executeAction(JsonObject action, World world, EntityPlayer player, Entity entity, int x, int y, int z) {
        String type = string(action, "type", "");
        if ("message".equals(type)) {
            if (player != null) {
                player.addChatMessage(new ChatComponentText(string(action, "text", "Runtime rule executed.")));
            }
        } else if ("set_block".equals(type)) {
            if (player == null && entity == null) {
                return;
            }
            Block target = resolveBlock(string(action, "block", ""));
            int tx = x + integer(action, "offset_x", 0);
            int ty = y + integer(action, "offset_y", 1);
            int tz = z + integer(action, "offset_z", 0);
            if (target != null && ty > 0 && ty < 255 && world.blockExists(tx, ty, tz)) {
                world.setBlock(tx, ty, tz, target, 0, 3);
            }
        } else if ("give_item".equals(type)) {
            if (player != null) {
                Item item = resolveItem(string(action, "item", ""));
                if (item != null) {
                    int count = Math.max(1, Math.min(64, integer(action, "count", 1)));
                    ItemStack stack = new ItemStack(item, count);
                    if (!player.inventory.addItemStackToInventory(stack)) {
                        player.dropPlayerItemWithRandomChoice(stack, false);
                    }
                }
            }
        } else if ("potion".equals(type)) {
            if (entity != null) {
                int id = Math.max(1, Math.min(Potion.potionTypes.length - 1, integer(action, "potion_id", 1)));
                Potion potion = Potion.potionTypes[id];
                if (potion != null) {
                    int duration = Math.max(20, Math.min(12000, integer(action, "duration_ticks", 200)));
                    int amplifier = Math.max(0, Math.min(4, integer(action, "amplifier", 0)));
                    entity.addPotionEffect(new PotionEffect(id, duration, amplifier));
                }
            }
        } else if ("set_time".equals(type)) {
            world.setWorldTime(Math.max(0L, integer(action, "time", 1000)));
        } else if ("weather".equals(type)) {
            boolean rain = bool(action, "raining", true);
            world.getWorldInfo().setRaining(rain);
            world.getWorldInfo().setThundering(false);
            world.getWorldInfo().setRainTime(6000);
        } else if ("explosion".equals(type)) {
            if (player == null && entity == null) {
                return;
            }
            float power = Math.max(0.1F, Math.min(2.0F, (float) number(action, "power", 1.0D)));
            world.newExplosion(entity, x + 0.5D, y + 0.5D, z + 0.5D, power, false, true);
        } else if ("spawn_entity".equals(type)) {
            if (player == null && entity == null) {
                return;
            }
            Entity spawned = EntityList.createEntityByName(string(action, "entity", ""), world);
            if (spawned != null) {
                spawned.setPosition(x + 0.5D, y + 1.0D, z + 0.5D);
                world.spawnEntityInWorld(spawned);
            }
        }
    }

    private static Block resolveBlock(String id) {
        String[] parts = splitId(id);
        return parts == null ? null : GameRegistryLookup.findBlock(parts[0], parts[1]);
    }

    private static Item resolveItem(String id) {
        String[] parts = splitId(id);
        return parts == null ? null : GameRegistryLookup.findItem(parts[0], parts[1]);
    }

    private static String[] splitId(String id) {
        if (id == null || id.trim().isEmpty()) {
            return null;
        }
        int separator = id.indexOf(':');
        if (separator <= 0 || separator == id.length() - 1) {
            return null;
        }
        return new String[] {id.substring(0, separator), id.substring(separator + 1)};
    }

    private static int floor(double value) {
        return (int) Math.floor(value);
    }

    private static String string(JsonObject object, String key, String fallback) {
        try {
            return object.has(key) ? object.get(key).getAsString() : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private static int integer(JsonObject object, String key, int fallback) {
        try {
            return object.has(key) ? object.get(key).getAsInt() : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private static double number(JsonObject object, String key, double fallback) {
        try {
            return object.has(key) ? object.get(key).getAsDouble() : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private static boolean bool(JsonObject object, String key, boolean fallback) {
        try {
            return object.has(key) ? object.get(key).getAsBoolean() : fallback;
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private void writeDefaultConfiguration() {
        JsonObject root = new JsonObject();
        root.addProperty("enabled", true);
        JsonArray rulesArray = new JsonArray();
        JsonObject example = new JsonObject();
        example.addProperty("id", "example_right_click_stone");
        example.addProperty("enabled", false);
        example.addProperty("event", "player_interact");
        example.addProperty("block", "minecraft:stone");
        example.addProperty("cooldown_ticks", 20);
        JsonArray actions = new JsonArray();
        JsonObject message = new JsonObject();
        message.addProperty("type", "message");
        message.addProperty("text", "A regra de exemplo foi ativada.");
        actions.add(message);
        example.add("actions", actions);
        rulesArray.add(example);
        root.add("rules", rulesArray);
        try (OutputStreamWriter writer = new OutputStreamWriter(new FileOutputStream(rulesFile), StandardCharsets.UTF_8)) {
            GSON.toJson(root, writer);
        } catch (IOException exception) {
            RealityEngineAI.LOG.error("Could not create default runtime-rules.json.", exception);
        }
    }

    private static final class Rule {
        final String id;
        final String event;
        final String blockId;
        final String entityType;
        final boolean enabled;
        final int cooldownTicks;
        final List<JsonObject> actions;

        private Rule(String id, String event, String blockId, String entityType, boolean enabled, int cooldownTicks, List<JsonObject> actions) {
            this.id = id;
            this.event = event;
            this.blockId = blockId;
            this.entityType = entityType;
            this.enabled = enabled;
            this.cooldownTicks = cooldownTicks;
            this.actions = actions;
        }

        static Rule parse(JsonObject json) {
            String id = string(json, "id", "");
            String event = string(json, "event", "");
            if (id.isEmpty() || !(event.equals("player_interact") || event.equals("block_break") || event.equals("entity_tick") || event.equals("world_tick")
                || event.equals("living_hurt") || event.equals("living_death") || event.equals("entity_join_world")
                || event.equals("player_login") || event.equals("player_respawn"))) {
                return null;
            }
            String block = string(json, "block", "");
            String entity = string(json, "entity_class", "");
            int cooldown = Math.max(0, Math.min(MAX_COOLDOWN, integer(json, "cooldown_ticks", 20)));
            boolean enabled = bool(json, "enabled", true);
            JsonArray array = json.has("actions") && json.get("actions").isJsonArray() ? json.getAsJsonArray("actions") : new JsonArray();
            List<JsonObject> actions = new ArrayList<JsonObject>();
            for (JsonElement element : array) {
                if (actions.size() >= MAX_ACTIONS_PER_RULE) {
                    break;
                }
                if (element != null && element.isJsonObject()) {
                    JsonObject action = element.getAsJsonObject();
                    String type = string(action, "type", "");
                    if (type.equals("message") || type.equals("set_block") || type.equals("give_item") || type.equals("potion")
                        || type.equals("set_time") || type.equals("weather") || type.equals("explosion") || type.equals("spawn_entity")) {
                        actions.add(action);
                    }
                }
            }
            if (actions.isEmpty()) {
                return null;
            }
            return new Rule(id, event, block, entity, enabled, cooldown, actions);
        }

        boolean matches(Block block, Entity entity) {
            if (!blockId.isEmpty()) {
                if (block == null || !blockId.equals(block.getUnlocalizedName().replace("tile.", ""))) {
                    String registryId = block == null ? "" : String.valueOf(Block.blockRegistry.getNameForObject(block));
                    if (!blockId.equals(registryId)) {
                        return false;
                    }
                }
            }
            if (!entityType.isEmpty()) {
                if (entity == null || !(entity.getClass().getSimpleName().equalsIgnoreCase(entityType)
                    || entity.getCommandSenderName().equalsIgnoreCase(entityType))) {
                    return false;
                }
            }
            return true;
        }

        JsonObject toJson() {
            JsonObject object = new JsonObject();
            object.addProperty("id", id);
            object.addProperty("event", event);
            if (!blockId.isEmpty()) {
                object.addProperty("block", blockId);
            }
            if (!entityType.isEmpty()) {
                object.addProperty("entity_class", entityType);
            }
            object.addProperty("enabled", enabled);
            object.addProperty("cooldown_ticks", cooldownTicks);
            JsonArray array = new JsonArray();
            for (JsonObject action : actions) {
                array.add(action);
            }
            object.add("actions", array);
            return object;
        }
    }

    private static final class GameRegistryLookup {
        static Block findBlock(String modId, String name) {
            return cpw.mods.fml.common.registry.GameRegistry.findBlock(modId, name);
        }

        static Item findItem(String modId, String name) {
            return cpw.mods.fml.common.registry.GameRegistry.findItem(modId, name);
        }
    }
}
