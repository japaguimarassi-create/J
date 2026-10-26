package br.com.realityengineai;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import com.google.gson.JsonParser;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.common.registry.GameRegistry;
import net.minecraft.block.Block;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.MathHelper;
import net.minecraft.util.Vec3;
import net.minecraft.world.World;

public final class BotPromptEngine {
    public static final BotPromptEngine INSTANCE = new BotPromptEngine();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Pattern DIMENSIONS = Pattern.compile("(\\d{1,3})\\s*[x×]\\s*(\\d{1,3})\\s*[x×]\\s*(\\d{1,2})");
    private static final Pattern RADIUS = Pattern.compile("(?:raio\\s*(\\d{1,3})|(\\d{1,3})\\s*blocos)");
    private static final int MAX_OPERATIONS = 1000000;
    private final List<Job> jobs = new ArrayList<Job>();
    private final List<ModuleDefinition> modules = new ArrayList<ModuleDefinition>();
    private final Map<String, Block> blockCache = new HashMap<String, Block>();
    private File modulesDir;
    private File settingsFile;
    private Settings settings = new Settings();
    private long nextJobId = 1L;

    private BotPromptEngine() {
    }

    public synchronized void initialize(File configDirectory) {
        File root = new File(configDirectory, "realityengineai");
        modulesDir = new File(root, "modules");
        settingsFile = new File(root, "bot-settings.json");
        if (!root.exists() && !root.mkdirs()) {
            RealityEngineAI.LOG.error("Could not create config/realityengineai.");
            return;
        }
        if (!modulesDir.exists() && !modulesDir.mkdirs()) {
            RealityEngineAI.LOG.error("Could not create config/realityengineai/modules.");
            return;
        }
        writeIfMissing(settingsFile, settingsJson());
        writeIfMissing(new File(modulesDir, "starter-builders.json"), defaultModulesJson());
        writeIfMissing(new File(modulesDir, "README.txt"),
            "Reality Engine AI Bot modules\\n\\n"
            + "Add JSON files with a templates array here. Supported shapes: generic, house, tower, castle, bridge, wall, platform, arena, maze, city, computer, vehicle.\\n"
            + "Fields: id, keywords, shape, width, depth, height, block, metadata, floor, floor_metadata, roof, roof_metadata, glass, fence.\\n"
            + "Edit files and run /bot recarregar. Modules are declarative configurations, not arbitrary Java code.\\n");
        reloadModules();
    }

    public synchronized boolean reloadModules() {
        if (modulesDir == null) return false;
        readSettings();
        File[] files = modulesDir.listFiles();
        if (files == null) return false;
        Arrays.sort(files);
        List<ModuleDefinition> loaded = new ArrayList<ModuleDefinition>();
        for (File file : files) {
            if (!file.isFile() || !file.getName().toLowerCase(Locale.ROOT).endsWith(".json")) continue;
            try {
                JsonObject root = new JsonParser().parse(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8)).getAsJsonObject();
                if (root.has("enabled") && !root.get("enabled").getAsBoolean()) continue;
                JsonArray templates = root.has("templates") && root.get("templates").isJsonArray() ? root.getAsJsonArray("templates") : new JsonArray();
                for (JsonElement element : templates) {
                    if (loaded.size() >= 128) break;
                    if (element == null || !element.isJsonObject()) continue;
                    ModuleDefinition module = ModuleDefinition.parse(element.getAsJsonObject());
                    if (module != null && !hasModule(loaded, module.id)) loaded.add(module);
                }
            } catch (Exception exception) {
                RealityEngineAI.LOG.warn("Ignoring invalid bot module " + file.getName(), exception);
            }
        }
        modules.clear();
        modules.addAll(loaded);
        RealityEngineAI.LOG.info("Loaded " + modules.size() + " bot modules.");
        return true;
    }

    public synchronized int getModuleCount() {
        return modules.size();
    }

    public synchronized int getActiveJobCount() {
        return jobs.size();
    }

    public synchronized int getOperationsPerTick() {
        return settings.operationsPerTick;
    }

    public synchronized EntityRealityBot findOwnedBot(EntityPlayer player) {
        if (player == null || player.worldObj == null) return null;
        for (Object object : player.worldObj.loadedEntityList) {
            if (object instanceof EntityRealityBot) {
                EntityRealityBot bot = (EntityRealityBot) object;
                if (!bot.isDead && player.getCommandSenderName().equalsIgnoreCase(bot.getOwnerName())) return bot;
            }
        }
        return null;
    }

    public EntityRealityBot spawnBot(EntityPlayer player) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote) return null;
        EntityRealityBot existing = findOwnedBot(player);
        if (existing != null) return existing;
        Vec3 look = player.getLookVec();
        int x = MathHelper.floor_double(player.posX + look.xCoord * 2.0D);
        int z = MathHelper.floor_double(player.posZ + look.zCoord * 2.0D);
        int y = Math.max(1, Math.min(250, player.worldObj.getTopSolidOrLiquidBlock(x, z)));
        EntityRealityBot bot = new EntityRealityBot(player.worldObj);
        bot.setOwnerName(player.getCommandSenderName());
        bot.setLocationAndAngles(x + 0.5D, y, z + 0.5D, player.rotationYaw, 0.0F);
        return player.worldObj.spawnEntityInWorld(bot) ? bot : null;
    }

    public boolean submit(EntityPlayer player, EntityRealityBot bot, String prompt) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote || prompt == null || prompt.trim().isEmpty()) return false;
        if (prompt.length() > 4096) {
            player.addChatMessage(new ChatComponentText("Reality Engine Bot: prompt muito longo (limite de 4096 caracteres)."));
            return false;
        }
        String normalized = CreationPlan.normalize(prompt);
        synchronized (this) {
            if (!settings.enabled) {
                player.addChatMessage(new ChatComponentText("Reality Engine Bot está desativado em config/realityengineai/bot-settings.json."));
                return false;
            }
        }
        if (contains(normalized, "recarregar modulos", "recarregar modulo", "reload modules")) {
            boolean ok = reloadModules();
            player.addChatMessage(new ChatComponentText("Módulos recarregados=" + ok + "; total=" + getModuleCount() + "."));
            return true;
        }
        if (contains(normalized, "modulo chamado", "modulo chamada", "crie modulo", "criar modulo", "adicionar modulo", "novo modulo de criacao")) {
            createModule(player, prompt, normalized);
            return true;
        }
        if (contains(normalized, "configuracao: quando", "regra de runtime", "runtime rule", "runtime config", "configuracao de runtime")) {
            if (!RuntimeConfigurationEngine.INSTANCE.handleCreationPrompt(player, prompt)) {
                player.addChatMessage(new ChatComponentText("Não reconheci a regra. Use a DSL em config/realityengineai/runtime-rules.json ou crie um módulo JSON."));
            }
            return true;
        }
        CreationPlan plan = CreationPlan.resolve(prompt);
        if (CreationPlan.QUERY.equals(plan.kind) && "internet_research".equals(plan.archetype)) {
            OnlineResearchEngine.INSTANCE.research(player, plan.query);
            return true;
        }
        if (CreationPlan.MAP.equals(plan.kind)) {
            scheduleMap(player, bot, prompt, normalized);
            return true;
        }
        if (CreationPlan.TERRAIN.equals(plan.kind)) {
            scheduleTerrain(player, bot, prompt, normalized, plan.archetype, plan.radius);
            return true;
        }
        if (CreationPlan.STRUCTURE.equals(plan.kind)) {
            ModuleDefinition selected = findModule(normalized);
            if (selected == null) selected = ModuleDefinition.genericFromPrompt(prompt, normalized);
            scheduleStructure(player, bot, prompt, selected, normalized);
            return true;
        }
        if (CreationPlan.QUERY.equals(plan.kind) || CreationPlan.ENTITY.equals(plan.kind)
                || CreationPlan.BLOCK.equals(plan.kind) || CreationPlan.ITEM.equals(plan.kind)
                || CreationPlan.DIMENSION.equals(plan.kind)) {
            RealityEngineAI.executeCreation(player, prompt);
            return true;
        }
        ModuleDefinition module = findModule(normalized);
        if (module != null) {
            scheduleStructure(player, bot, prompt, module, normalized);
            return true;
        }
        ModuleDefinition generic = ModuleDefinition.genericFromPrompt(prompt, normalized);
        scheduleStructure(player, bot, prompt, generic, normalized);
        player.addChatMessage(new ChatComponentText("Bot: tipo não reconhecido; criei estrutura genérica em vez de alegar implementação específica. Personalize módulos JSON."));
        return true;
    }

    public synchronized int cancelOwnedJobs(String owner) {
        int removed = 0;
        for (Iterator<Job> it = jobs.iterator(); it.hasNext();) {
            if (it.next().owner.equalsIgnoreCase(owner)) {
                it.remove();
                removed++;
            }
        }
        return removed;
    }

    public synchronized int removeOwnedBots(EntityPlayer player) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote) return 0;
        List<?> entities = new ArrayList<Object>(player.worldObj.loadedEntityList);
        int removed = 0;
        for (Object object : entities) {
            if (object instanceof EntityRealityBot) {
                EntityRealityBot bot = (EntityRealityBot) object;
                if (player.getCommandSenderName().equalsIgnoreCase(bot.getOwnerName())) {
                    bot.setDead();
                    removed++;
                }
            }
        }
        return removed;
    }

    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event == null || event.phase != TickEvent.Phase.END) return;
        synchronized (this) {
            if (!settings.enabled) return;
            int budget = settings.operationsPerTick;
            int index = 0;
            while (budget > 0 && index < jobs.size()) {
                Job job = jobs.get(index);
                int localBudget = Math.max(1, budget / Math.max(1, jobs.size() - index));
                boolean finished = false;
                for (int i = 0; i < localBudget; i++) {
                    BlockEdit edit = job.generator.next();
                    if (edit == null) {
                        finished = true;
                        break;
                    }
                    job.processed++;
                    if (job.world != null && !job.world.isRemote && edit.y > 0 && edit.y < 255 && job.world.blockExists(edit.x, edit.y, edit.z)) {
                        Block block = resolveBlock(edit.block);
                        if (block != null && job.world.setBlock(edit.x, edit.y, edit.z, block, edit.metadata, 2)) job.applied++;
                        else job.skipped++;
                    } else {
                        job.skipped++;
                    }
                    budget--;
                }
                if (finished || job.generator.isFinished()) {
                    finish(job);
                    jobs.remove(index);
                } else {
                    index++;
                }
            }
        }
    }

    private void scheduleMap(EntityPlayer player, EntityRealityBot bot, String prompt, String normalized) {
        int radius = parseRadius(normalized, settings.defaultMapRadius, settings.maxMapRadius);
        Vec3 look = player.getLookVec();
        int centerX = MathHelper.floor_double(player.posX + look.xCoord * (radius + 8.0D));
        int centerZ = MathHelper.floor_double(player.posZ + look.zCoord * (radius + 8.0D));
        int baseY = Math.max(5, Math.min(220, player.worldObj.getTopSolidOrLiquidBlock(centerX, centerZ) - 1));
        String surface = "minecraft:grass";
        String soil = "minecraft:dirt";
        String stone = "minecraft:stone";
        if (contains(normalized, "deserto", "desert", "areia", "duna")) {
            surface = "minecraft:sand";
            soil = "minecraft:sandstone";
        } else if (contains(normalized, "neve", "gelo", "snow", "ice")) {
            surface = "minecraft:snow_block";
        } else if (contains(normalized, "infernal", "vulcao", "nether", "lava")) {
            surface = "minecraft:netherrack";
            soil = "minecraft:netherrack";
            stone = "minecraft:netherrack";
        } else if (contains(normalized, "espaco", "vazio", "lua", "space", "end")) {
            surface = "minecraft:end_stone";
            soil = "minecraft:end_stone";
            stone = "minecraft:obsidian";
        }
        int minY = Math.max(1, baseY - 4);
        int maxY = Math.min(250, baseY + 24);
        enqueue(player, bot, prompt, new MapGenerator(centerX, centerZ, baseY, radius, minY, maxY, surface, soil, stone));
    }
 
    private void scheduleTerrain(EntityPlayer player, EntityRealityBot bot, String prompt, String normalized, String type, int requestedRadius) {
        int radius = Math.max(4, Math.min(32, requestedRadius > 0 ? requestedRadius : settings.defaultMapRadius / 2));
        Vec3 look = player.getLookVec();
        int centerX = MathHelper.floor_double(player.posX + look.xCoord * (radius + 6.0D));
        int centerZ = MathHelper.floor_double(player.posZ + look.zCoord * (radius + 6.0D));
        int baseY = Math.max(5, Math.min(220, player.worldObj.getTopSolidOrLiquidBlock(centerX, centerZ) - 1));
        String surface = "minecraft:grass", soil = "minecraft:dirt", stone = "minecraft:stone";
        int depth = 8, amplitude = 3;
        if ("desert".equals(type)) {
            surface = "minecraft:sand"; soil = "minecraft:sandstone"; stone = "minecraft:sandstone";
        } else if ("snow".equals(type)) {
            surface = "minecraft:snow_block";
        } else if ("mountain".equals(type)) {
            surface = "minecraft:stone"; soil = "minecraft:stone"; stone = "minecraft:stone"; depth = 22; amplitude = 14;
        } else if ("volcanic".equals(type)) {
            surface = "minecraft:netherrack"; soil = "minecraft:netherrack"; stone = "minecraft:netherrack"; amplitude = 6;
        }
        enqueue(player, bot, prompt, new TerrainGenerator(centerX, centerZ, baseY, radius, depth, amplitude, type, surface, soil, stone));
    }

    private void scheduleStructure(EntityPlayer player, EntityRealityBot bot, String prompt, ModuleDefinition module, String normalized) {
        int width = clamp(module.width, 3, 128);
        int depth = clamp(module.depth, 3, 128);
        int height = clamp(module.height, 2, 64);
        long total = (long) width * depth * height;
        if (total > MAX_OPERATIONS || total > settings.maxOperationsPerJob) {
            player.addChatMessage(new ChatComponentText("A estrutura exige " + total + " operações, acima do limite " + settings.maxOperationsPerJob + ". Reduza as dimensões no módulo."));
            return;
        }
        String block = module.block;
        if (contains(normalized, "pedra", "stone")) block = "minecraft:stonebrick";
        else if (contains(normalized, "ferro", "metal")) block = "minecraft:iron_block";
        else if (contains(normalized, "madeira", "wood")) block = "minecraft:planks";
        else if (contains(normalized, "vidro", "glass")) block = "minecraft:glass";
        Vec3 look = player.getLookVec();
        int offset = Math.max(width, depth) / 2 + 5;
        int centerX = MathHelper.floor_double(player.posX + look.xCoord * offset);
        int centerZ = MathHelper.floor_double(player.posZ + look.zCoord * offset);
        int baseY = Math.max(1, Math.min(220, player.worldObj.getTopSolidOrLiquidBlock(centerX, centerZ) - 1));
        enqueue(player, bot, prompt, new StructureGenerator(centerX, centerZ, baseY, module.withBlock(block)));
    }

    private synchronized void enqueue(EntityPlayer player, EntityRealityBot bot, String prompt, Generator generator) {
        if (jobs.size() >= settings.maxQueuedJobs) {
            player.addChatMessage(new ChatComponentText("Fila cheia (" + jobs.size() + "/" + settings.maxQueuedJobs + "). Use /bot parar ou aguarde."));
            return;
        }
        Job job = new Job(nextJobId++, player.getCommandSenderName(), player.worldObj, prompt, generator);
        jobs.add(job);
        if (bot != null) bot.setCurrentTask("Tarefa #" + job.id);
        player.addChatMessage(new ChatComponentText("Bot: tarefa #" + job.id + " enfileirada; até " + generator.getTotal()
            + " operações. Limite atual: " + settings.operationsPerTick + " por tick. Veja /bot status."));
    }

    private void finish(Job job) {
        EntityPlayer player = findPlayer(job.world, job.owner);
        if (player != null) {
            player.addChatMessage(new ChatComponentText("Bot: tarefa #" + job.id + " concluída. Aplicadas=" + job.applied + ", ignoradas=" + job.skipped + "."));
        }
        for (Object object : job.world.loadedEntityList) {
            if (object instanceof EntityRealityBot) {
                EntityRealityBot bot = (EntityRealityBot) object;
                if (job.owner.equalsIgnoreCase(bot.getOwnerName())) {
                    bot.setCurrentTask("");
                    break;
                }
            }
        }
    }

    private static EntityPlayer findPlayer(World world, String name) {
        if (world == null) return null;
        for (Object object : world.playerEntities) {
            if (object instanceof EntityPlayer && name.equalsIgnoreCase(((EntityPlayer) object).getCommandSenderName())) return (EntityPlayer) object;
        }
        return null;
    }

    private ModuleDefinition findModule(String normalized) {
        synchronized (this) {
            for (ModuleDefinition module : modules) {
                for (String keyword : module.keywords) {
                    if (!keyword.isEmpty() && normalized.contains(CreationPlan.normalize(keyword))) return module;
                }
            }
        }
        return null;
    }

    private void createModule(EntityPlayer player, String prompt, String normalized) {
        String id = moduleId(normalized);
        int[] dimensions = parseDimensions(prompt);
        String shape = inferShape(normalized);
        String block = contains(normalized, "madeira", "wood") ? "minecraft:planks"
            : contains(normalized, "ferro", "metal") ? "minecraft:iron_block" : "minecraft:stonebrick";
        JsonObject template = makeModule(id, new String[] {id}, shape, dimensions[0], dimensions[1], dimensions[2],
            block, "minecraft:planks", block, "minecraft:glass", "minecraft:fence");
        JsonObject root = new JsonObject();
        root.addProperty("enabled", true);
        JsonArray templates = new JsonArray();
        templates.add(template);
        root.add("templates", templates);
        try {
            File file = new File(modulesDir, "custom_" + id + ".json");
            try (OutputStreamWriter writer = new OutputStreamWriter(new FileOutputStream(file), StandardCharsets.UTF_8)) {
                GSON.toJson(root, writer);
            }
            reloadModules();
            player.addChatMessage(new ChatComponentText("Módulo '" + id + "' salvo em config/realityengineai/modules/custom_" + id
                + ".json. Forma=" + shape + ", dimensões=" + dimensions[0] + "x" + dimensions[1] + "x" + dimensions[2] + "."));
        } catch (Exception exception) {
            RealityEngineAI.LOG.error("Could not write bot module.", exception);
            player.addChatMessage(new ChatComponentText("Falha ao salvar módulo; consulte latest.log."));
        }
    }

    private void readSettings() {
        if (settingsFile == null || !settingsFile.isFile()) {
            settings = new Settings();
            return;
        }
        try {
            JsonObject json = new JsonParser().parse(new String(Files.readAllBytes(settingsFile.toPath()), StandardCharsets.UTF_8)).getAsJsonObject();
            Settings next = new Settings();
            next.enabled = bool(json, "enabled", true);
            next.maxQueuedJobs = clamp(integer(json, "maxQueuedJobs", 8), 1, 64);
            next.operationsPerTick = clamp(integer(json, "operationsPerTick", 128), 1, 4096);
            next.maxOperationsPerJob = clamp(integer(json, "maxOperationsPerJob", MAX_OPERATIONS), 1, MAX_OPERATIONS);
            next.defaultMapRadius = clamp(integer(json, "defaultMapRadius", 16), 4, 64);
            next.maxMapRadius = clamp(integer(json, "maxMapRadius", 64), next.defaultMapRadius, 64);
            settings = next;
        } catch (Exception exception) {
            RealityEngineAI.LOG.warn("Invalid bot-settings.json; safe defaults are active.", exception);
            settings = new Settings();
        }
    }

    static boolean isMapPrompt(String normalized) {
        return contains(normalized, "mapa", "mapa do zero", "mundo do zero", "terreno do zero", "paisagem", "create a map", "generate a map");
    }

    static int parseRadius(String normalized, int fallback, int maximum) {
        Matcher matcher = RADIUS.matcher(normalized == null ? "" : normalized);
        if (matcher.find()) {
            String raw = matcher.group(1) == null ? matcher.group(2) : matcher.group(1);
            try {
                return clamp(Integer.parseInt(raw), 4, clamp(maximum, 4, 64));
            } catch (NumberFormatException ignored) {
                return clamp(fallback, 4, clamp(maximum, 4, 64));
            }
        }
        return clamp(fallback, 4, clamp(maximum, 4, 64));
    }

    static int[] parseDimensions(String prompt) {
        Matcher matcher = DIMENSIONS.matcher(CreationPlan.normalize(prompt == null ? "" : prompt));
        if (!matcher.find()) return new int[] {9, 9, 6};
        try {
            return new int[] {
                clamp(Integer.parseInt(matcher.group(1)), 3, 128),
                clamp(Integer.parseInt(matcher.group(2)), 3, 128),
                clamp(Integer.parseInt(matcher.group(3)), 2, 64)
            };
        } catch (NumberFormatException ignored) {
            return new int[] {9, 9, 6};
        }
    }

    private static String moduleId(String normalized) {
        String tail = "";
        int index = normalized.indexOf("modulo chamado ");
        if (index >= 0) tail = normalized.substring(index + "modulo chamado ".length());
        if (tail.isEmpty()) {
            index = normalized.indexOf("modulo chamada ");
            if (index >= 0) tail = normalized.substring(index + "modulo chamada ".length());
        }
        if (tail.isEmpty()) {
            index = normalized.indexOf("modulo ");
            if (index >= 0) tail = normalized.substring(index + "modulo ".length());
        }
        String[] words = tail.split("\\s+");
        int i = 0;
        while (i < words.length && ("um".equals(words[i]) || "uma".equals(words[i]) || "de".equals(words[i]) || "para".equals(words[i]) || "chamado".equals(words[i]))) i++;
        String id = i < words.length ? words[i] : "custom";
        id = id.replaceAll("[^a-z0-9_-]", "");
        if (id.isEmpty()) id = "custom";
        return id.length() > 40 ? id.substring(0, 40) : id;
    }

    private static String inferShape(String text) {
        if (contains(text, "casa", "house", "garagem")) return "house";
        if (contains(text, "castelo", "fortaleza", "castle")) return "castle";
        if (contains(text, "torre", "tower")) return "tower";
        if (contains(text, "ponte", "bridge")) return "bridge";
        if (contains(text, "plataforma", "platform")) return "platform";
        if (contains(text, "muro", "parede", "wall")) return "wall";
        if (contains(text, "arena")) return "arena";
        if (contains(text, "labirinto", "maze")) return "maze";
        if (contains(text, "cidade", "city")) return "city";
        if (contains(text, "computador", "computer", "pc")) return "computer";
        if (contains(text, "carro", "veiculo", "automovel", "nave", "aviao")) return "vehicle";
        return "generic";
    }

    private static Block resolveBlock(String id) {
        if (id == null || id.isEmpty()) return null;
        Block cached = INSTANCE.blockCache.get(id);
        if (cached != null || INSTANCE.blockCache.containsKey(id)) return cached;
        Block block = null;
        int colon = id.indexOf(':');
        if (colon > 0 && colon < id.length() - 1) block = GameRegistry.findBlock(id.substring(0, colon), id.substring(colon + 1));
        if (block == null) {
            Object entry = Block.blockRegistry.getObject(id);
            if (entry instanceof Block) block = (Block) entry;
        }
        INSTANCE.blockCache.put(id, block);
        return block;
    }

    private static JsonObject makeModule(String id, String[] keywords, String shape, int width, int depth, int height,
            String block, String floor, String roof, String glass, String fence) {
        JsonObject json = new JsonObject();
        json.addProperty("id", id);
        JsonArray words = new JsonArray();
        for (String keyword : keywords) words.add(new JsonPrimitive(keyword));
        json.add("keywords", words);
        json.addProperty("shape", shape);
        json.addProperty("width", width);
        json.addProperty("depth", depth);
        json.addProperty("height", height);
        json.addProperty("block", block);
        json.addProperty("floor", floor);
        json.addProperty("roof", roof);
        json.addProperty("glass", glass);
        json.addProperty("fence", fence);
        return json;
    }

    private static String settingsJson() {
        JsonObject json = new JsonObject();
        json.addProperty("enabled", true);
        json.addProperty("maxQueuedJobs", 8);
        json.addProperty("operationsPerTick", 128);
        json.addProperty("maxOperationsPerJob", MAX_OPERATIONS);
        json.addProperty("defaultMapRadius", 16);
        json.addProperty("maxMapRadius", 64);
        return GSON.toJson(json);
    }

    private static String defaultModulesJson() {
        JsonObject root = new JsonObject();
        root.addProperty("enabled", true);
        JsonArray templates = new JsonArray();
        templates.add(makeModule("house", new String[] {"casa", "house"}, "house", 9, 9, 6, "minecraft:planks", "minecraft:planks", "minecraft:wooden_slab", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("castle", new String[] {"castelo", "fortaleza", "castle"}, "castle", 25, 25, 12, "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:stone_slab", "minecraft:glass", "minecraft:nether_brick_fence"));
        templates.add(makeModule("tower", new String[] {"torre", "tower"}, "tower", 9, 9, 18, "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:stone_slab", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("bridge", new String[] {"ponte", "bridge"}, "bridge", 3, 21, 3, "minecraft:planks", "minecraft:planks", "minecraft:planks", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("wall", new String[] {"muro", "parede", "wall"}, "wall", 21, 2, 5, "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:stone_slab", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("platform", new String[] {"plataforma", "platform"}, "platform", 15, 15, 3, "minecraft:cobblestone", "minecraft:cobblestone", "minecraft:cobblestone", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("arena", new String[] {"arena"}, "arena", 31, 31, 7, "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:stone_slab", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("maze", new String[] {"labirinto", "maze"}, "maze", 31, 31, 5, "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("city", new String[] {"cidade", "city"}, "city", 49, 49, 8, "minecraft:stonebrick", "minecraft:grass", "minecraft:planks", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("computer", new String[] {"computador", "computer", "pc"}, "computer", 9, 7, 7, "minecraft:iron_block", "minecraft:planks", "minecraft:iron_block", "minecraft:lapis_block", "minecraft:fence"));
        templates.add(makeModule("vehicle", new String[] {"carro", "veiculo", "automovel", "nave", "aviao"}, "vehicle", 9, 5, 5, "minecraft:iron_block", "minecraft:iron_block", "minecraft:glass", "minecraft:glass", "minecraft:fence"));
        templates.add(makeModule("generic", new String[] {"objeto tridimensional", "estrutura generica"}, "generic", 9, 9, 6, "minecraft:stonebrick", "minecraft:stonebrick", "minecraft:stone_slab", "minecraft:glass", "minecraft:fence"));
        root.add("templates", templates);
        return GSON.toJson(root);
    }

    private static boolean hasModule(List<ModuleDefinition> list, String id) {
        for (ModuleDefinition module : list) if (module.id.equalsIgnoreCase(id)) return true;
        return false;
    }

    private static void writeIfMissing(File file, String text) {
        if (file == null || file.isFile()) return;
        try {
            File parent = file.getParentFile();
            if (parent != null && !parent.exists()) parent.mkdirs();
            Files.write(file.toPath(), text.getBytes(StandardCharsets.UTF_8));
        } catch (IOException exception) {
            RealityEngineAI.LOG.error("Could not write bot config " + file.getName(), exception);
        }
    }

    private static int integer(JsonObject json, String key, int fallback) {
        try { return json.has(key) ? json.get(key).getAsInt() : fallback; } catch (Exception ignored) { return fallback; }
    }

    private static boolean bool(JsonObject json, String key, boolean fallback) {
        try { return json.has(key) ? json.get(key).getAsBoolean() : fallback; } catch (Exception ignored) { return fallback; }
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private static boolean contains(String text, String... options) {
        if (text == null) return false;
        for (String option : options) if (text.contains(CreationPlan.normalize(option))) return true;
        return false;
    }

    private static final class Settings {
        boolean enabled = true;
        int maxQueuedJobs = 8;
        int operationsPerTick = 128;
        int maxOperationsPerJob = MAX_OPERATIONS;
        int defaultMapRadius = 16;
        int maxMapRadius = 64;
    }

    private static final class Job {
        final long id;
        final String owner;
        final World world;
        final String prompt;
        final Generator generator;
        int applied;
        int skipped;
        int processed;
        Job(long id, String owner, World world, String prompt, Generator generator) {
            this.id = id;
            this.owner = owner;
            this.world = world;
            this.prompt = prompt;
            this.generator = generator;
        }
    }

    private interface Generator {
        BlockEdit next();
        boolean isFinished();
        long getTotal();
    }

    private static final class BlockEdit {
        final int x;
        final int y;
        final int z;
        final String block;
        final int metadata;
        BlockEdit(int x, int y, int z, String block, int metadata) {
            this.x = x;
            this.y = y;
            this.z = z;
            this.block = block;
            this.metadata = metadata;
        }
    }

    private static final class MapGenerator implements Generator {
        final int centerX, centerZ, baseY, radius, minY, maxY;
        final String surface, soil, stone;
        final long total;
        long cursor;
        MapGenerator(int x, int z, int baseY, int radius, int minY, int maxY, String surface, String soil, String stone) {
            centerX = x; centerZ = z; this.baseY = baseY; this.radius = radius; this.minY = minY; this.maxY = maxY;
            this.surface = surface; this.soil = soil; this.stone = stone;
            total = (long) (radius * 2 + 1) * (radius * 2 + 1) * (maxY - minY + 1);
        }
        public BlockEdit next() {
            if (cursor >= total) return null;
            long index = cursor++;
            int vertical = maxY - minY + 1;
            long column = index / vertical;
            int y = minY + (int) (index % vertical);
            int width = radius * 2 + 1;
            int x = centerX + (int) (column / width) - radius;
            int z = centerZ + (int) (column % width) - radius;
            double wave = Math.sin((x + 19) * 0.19D) * 1.7D + Math.cos((z - 7) * 0.16D) * 1.5D + Math.sin((x + z) * 0.08D) * 1.3D;
            int surfaceY = baseY + (int) Math.round(wave);
            String block = y > surfaceY ? "minecraft:air" : y == minY ? "minecraft:bedrock"
                : y == surfaceY ? surface : y >= surfaceY - 3 ? soil : stone;
            return new BlockEdit(x, y, z, block, 0);
        }
        public boolean isFinished() { return cursor >= total; }
        public long getTotal() { return total; }
    }

    private static final class TerrainGenerator implements Generator {
        final int centerX, centerZ, baseY, radius, depth, amplitude;
        final String type, surface, soil, stone;
        final long total;
        long cursor;
        TerrainGenerator(int x, int z, int y, int radius, int depth, int amplitude, String type, String surface, String soil, String stone) {
            centerX=x; centerZ=z; baseY=y; this.radius=radius; this.depth=depth; this.amplitude=amplitude;
            this.type=type; this.surface=surface; this.soil=soil; this.stone=stone;
            total=(long)(radius*2+1)*(radius*2+1)*(depth+amplitude+4);
        }
        public BlockEdit next() {
            while(cursor<total) {
                long index=cursor++;
                int layers=depth+amplitude+4;
                long column=index/layers;
                int layer=(int)(index%layers);
                int width=radius*2+1;
                int x=centerX+(int)(column/width)-radius;
                int z=centerZ+(int)(column%width)-radius;
                double wave=Math.sin(x*.19D)*1.7D+Math.cos(z*.17D)*1.5D+Math.sin((x+z)*.08D);
                if("mountain".equals(type)) wave=Math.sin(x*.12D)*5.0D+Math.cos(z*.15D)*4.0D+Math.sin((x+z)*.07D)*3.0D;
                if("volcanic".equals(type)) wave=Math.sin(x*.14D)*2.5D+Math.cos(z*.11D)*2.5D+Math.sin((x-z)*.09D)*2.0D;
                int top=baseY+(int)Math.round(wave*amplitude/4.0D);
                int y=baseY-depth+layer;
                if(y>top||y<=0||y>=255) continue;
                String block=y==top?surface:y>=top-2?soil:stone;
                return new BlockEdit(x,y,z,block,0);
            }
            return null;
        }
        public boolean isFinished(){return cursor>=total;}
        public long getTotal(){return total;}
    }

    private static final class StructureGenerator implements Generator {
        final int centerX, centerZ, baseY;
        final ModuleDefinition module;
        final long total;
        long cursor;
        StructureGenerator(int x, int z, int y, ModuleDefinition module) {
            centerX = x; centerZ = z; baseY = y; this.module = module;
            total = (long) module.width * module.depth * module.height;
        }
        public BlockEdit next() {
            while (cursor < total) {
                long index = cursor++;
                int x = (int) (index % module.width);
                int z = (int) ((index / module.width) % module.depth);
                int y = (int) (index / ((long) module.width * module.depth));
                String block = choose(x, y, z);
                if (block == null) continue;
                int metadata = block.equals(module.floor) ? module.floorMetadata : block.equals(module.roof) ? module.roofMetadata : module.metadata;
                return new BlockEdit(centerX + x - module.width / 2, baseY + y, centerZ + z - module.depth / 2, block, metadata);
            }
            return null;
        }
        private String choose(int x, int y, int z) {
            boolean edge = x == 0 || z == 0 || x == module.width - 1 || z == module.depth - 1;
            if ("platform".equals(module.shape)) return y == 0 ? module.floor : "minecraft:air";
            if ("bridge".equals(module.shape)) return y == 0 ? module.floor : y == 1 && (x == 0 || x == module.width - 1) ? module.fence : "minecraft:air";
            if ("wall".equals(module.shape)) return y == module.height - 1 ? module.roof : module.block;
            if ("city".equals(module.shape)) {
                if (y == 0) return x % 12 <= 2 || z % 12 <= 2 ? "minecraft:cobblestone" : module.floor;
                boolean road = x % 12 <= 2 || z % 12 <= 2;
                int lx = x % 12, lz = z % 12;
                boolean building = !road && lx >= 4 && lx <= 9 && lz >= 4 && lz <= 9;
                if (!building) return "minecraft:air";
                if (y <= 4 && (lx == 4 || lx == 9 || lz == 4 || lz == 9)) return module.block;
                return y == 5 ? module.roof : "minecraft:air";
            }
            if ("maze".equals(module.shape)) {
                if (y == 0) return module.floor;
                boolean wall = x == 0 || z == 0 || x == module.width - 1 || z == module.depth - 1
                    || x % 4 == 0 && z % 7 != (x / 4) % 7 || z % 4 == 0 && x % 7 != (z / 4) % 7;
                return y < module.height - 1 && wall ? module.block : "minecraft:air";
            }
            if ("arena".equals(module.shape)) {
                double dx = x - (module.width - 1) / 2.0D, dz = z - (module.depth - 1) / 2.0D;
                double r = Math.min(module.width, module.depth) / 2.0D;
                boolean inside = dx * dx + dz * dz <= r * r;
                boolean rim = inside && dx * dx + dz * dz >= (r - 1.5D) * (r - 1.5D);
                if (!inside) return "minecraft:air";
                if (y == 0) return module.floor;
                if (rim && y < module.height - 1) return module.block;
                return y == module.height - 1 && (x + z) % 2 == 0 ? module.roof : "minecraft:air";
            }
            if ("computer".equals(module.shape)) {
                if (y == 0) return module.floor;
                if (x <= 2 && z >= 1 && z <= module.depth - 2 && y <= 4) return x == 1 && z == 1 && y == 4 ? "minecraft:redstone_block" : module.block;
                if (x >= module.width - 5 && z == 1 && y >= 2) {
                    return x > module.width - 5 && x < module.width - 1 && y > 2 && y < module.height - 1 ? module.glass : module.block;
                }
                if (x == module.width - 3 && z == 2 && y == 1) return module.block;
                if (x >= module.width - 6 && z >= 3 && z <= module.depth - 2 && y == 1) return "minecraft:stone_slab";
                return "minecraft:air";
            }
            if ("vehicle".equals(module.shape)) {
                if (y == 0) return (x == 1 || x == module.width - 2) && (z == 1 || z == module.depth - 2) ? "minecraft:coal_block" : "minecraft:air";
                if (y == 1) return module.floor;
                if (y == 2 && x >= 2 && x <= module.width - 3 && z >= 1 && z <= module.depth - 2) return module.block;
                if (y == 3 && x >= 3 && x <= module.width - 4 && z >= 1 && z <= module.depth - 2)
                    return x == 3 || x == module.width - 4 || z == 1 || z == module.depth - 2 ? module.glass : "minecraft:air";
                return y == 4 && x >= 3 && x <= module.width - 4 && z >= 1 && z <= module.depth - 2 ? module.roof : "minecraft:air";
            }
            if (y == 0) return module.floor;
            if (y == module.height - 1) return "castle".equals(module.shape) && x % 2 == 0 && z % 2 == 0 ? module.block : module.roof;
            boolean door = "house".equals(module.shape) && z == 0 && x == module.width / 2 && y <= 2;
            boolean window = y == 2 && (((z == 0 || z == module.depth - 1) && (x == module.width / 3 || x == module.width * 2 / 3))
                || ((x == 0 || x == module.width - 1) && (z == module.depth / 3 || z == module.depth * 2 / 3)));
            if (door) return "minecraft:air";
            if (window) return module.glass;
            if (edge) return module.block;
            if ("tower".equals(module.shape) && (x == 1 || z == 1 || x == module.width - 2 || z == module.depth - 2)) return module.block;
            return "minecraft:air";
        }
        public boolean isFinished() { return cursor >= total; }
        public long getTotal() { return total; }
    }

    private static final class ModuleDefinition {
        final String id, shape, block, floor, roof, glass, fence;
        final List<String> keywords;
        final int width, depth, height, metadata, floorMetadata, roofMetadata;
        ModuleDefinition(String id, List<String> keywords, String shape, int width, int depth, int height, String block, int metadata,
                String floor, int floorMetadata, String roof, int roofMetadata, String glass, String fence) {
            this.id = id; this.keywords = keywords; this.shape = shape; this.width = width; this.depth = depth; this.height = height;
            this.block = block; this.metadata = metadata; this.floor = floor; this.floorMetadata = floorMetadata; this.roof = roof;
            this.roofMetadata = roofMetadata; this.glass = glass; this.fence = fence;
        }
        ModuleDefinition withBlock(String block) {
            return new ModuleDefinition(id, keywords, shape, width, depth, height, block, metadata, floor, floorMetadata, roof, roofMetadata, glass, fence);
        }
        static ModuleDefinition parse(JsonObject json) {
            String id = string(json, "id", "").replaceAll("[^a-zA-Z0-9_-]", "");
            String shape = string(json, "shape", "generic").toLowerCase(Locale.ROOT);
            if (id.isEmpty() || !isShape(shape)) return null;
            JsonArray input = json.has("keywords") && json.get("keywords").isJsonArray() ? json.getAsJsonArray("keywords") : new JsonArray();
            List<String> keywords = new ArrayList<String>();
            keywords.add(id);
            for (JsonElement el : input) if (el != null && el.isJsonPrimitive() && keywords.size() < 32 && !keywords.contains(el.getAsString())) keywords.add(el.getAsString());
            int width = clamp(integer(json, "width", 9), 3, 128);
            int depth = clamp(integer(json, "depth", 9), 3, 128);
            int height = clamp(integer(json, "height", 6), 2, 64);
            String block = cleanId(string(json, "block", "minecraft:stonebrick"));
            String floor = cleanId(string(json, "floor", block));
            String roof = cleanId(string(json, "roof", block));
            String glass = cleanId(string(json, "glass", "minecraft:glass"));
            String fence = cleanId(string(json, "fence", "minecraft:fence"));
            if (block.isEmpty() || floor.isEmpty() || roof.isEmpty() || glass.isEmpty() || fence.isEmpty()) return null;
            return new ModuleDefinition(id, keywords, shape, width, depth, height, block, clamp(integer(json, "metadata", 0), 0, 15),
                floor, clamp(integer(json, "floor_metadata", 0), 0, 15), roof, clamp(integer(json, "roof_metadata", 0), 0, 15), glass, fence);
        }
        static ModuleDefinition genericFromPrompt(String prompt, String normalized) {
            int[] d = parseDimensions(prompt);
            String shape = inferShape(normalized);
            String block = contains(normalized, "madeira", "wood") ? "minecraft:planks"
                : contains(normalized, "ferro", "metal", "computador", "pc") ? "minecraft:iron_block" : "minecraft:stonebrick";
            return new ModuleDefinition("prompt_generated", new ArrayList<String>(), shape, d[0], d[1], d[2], block, 0,
                "minecraft:planks", 0, block, 0, "minecraft:glass", "minecraft:fence");
        }
        private static boolean isShape(String value) {
            return value.equals("generic") || value.equals("house") || value.equals("tower") || value.equals("castle") || value.equals("bridge")
                || value.equals("wall") || value.equals("platform") || value.equals("arena") || value.equals("maze") || value.equals("city")
                || value.equals("computer") || value.equals("vehicle");
        }
        private static String cleanId(String value) {
            if (value == null) return "";
            String id = value.trim().toLowerCase(Locale.ROOT);
            return id.matches("[a-z0-9_.-]+:[a-z0-9_./-]+") && id.length() <= 96 ? id : "";
        }
        private static String string(JsonObject json, String key, String fallback) {
            try { return json.has(key) ? json.get(key).getAsString() : fallback; } catch (Exception ignored) { return fallback; }
        }
        private static int integer(JsonObject json, String key, int fallback) {
            try { return json.has(key) ? json.get(key).getAsInt() : fallback; } catch (Exception ignored) { return fallback; }
        }
    }
}
