package br.com.realityengineai;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;

public final class OnlineResearchEngine {
    public static final OnlineResearchEngine INSTANCE = new OnlineResearchEngine();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final int MAX_QUERY_LENGTH = 180;
    private static final int MAX_RESULTS = 10;
    private static final int MAX_RESPONSE_BYTES = 524288;
    private static final Pattern LINKS = Pattern.compile("(?is)<a(?=[^>]*result__a)[^>]*href=([^ >]+)[^>]*>(.*?)</a>");
    private static final Pattern SNIPPETS = Pattern.compile("(?is)class=.result__snippet.>(.*?)</a>");
    private final ExecutorService workers = Executors.newFixedThreadPool(3, new ThreadFactory() {
        private final AtomicInteger index = new AtomicInteger();
        public Thread newThread(Runnable task) {
            Thread thread = new Thread(task, "RealityEngine-Research-" + index.incrementAndGet());
            thread.setDaemon(true);
            return thread;
        }
    });
    private final ConcurrentLinkedQueue<Completion> completions = new ConcurrentLinkedQueue<Completion>();
    private final AtomicInteger activeBatches = new AtomicInteger();
    private File researchDirectory;

    private OnlineResearchEngine() {
    }

    public synchronized void initialize(File configDirectory) {
        researchDirectory = new File(new File(new File(configDirectory, "realityengineai"), "knowledge"), "web-research");
        if (!researchDirectory.exists() && !researchDirectory.mkdirs()) {
            RealityEngineAI.LOG.warn("Could not create web research cache directory.");
        }
    }

    public void research(EntityPlayer player, String rawQuery) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote) return;
        final String query = sanitize(rawQuery);
        if (query.isEmpty()) {
            player.addChatMessage(new ChatComponentText("Reality Engine Research: informe o assunto. Exemplo: /bot pesquisar Forge 1.7.10 entidades."));
            return;
        }
        if (researchDirectory == null) {
            player.addChatMessage(new ChatComponentText("Reality Engine Research: cache local indisponível."));
            return;
        }
        int active = activeBatches.incrementAndGet();
        if (active > 4) {
            activeBatches.decrementAndGet();
            player.addChatMessage(new ChatComponentText("Reality Engine Research: limite de quatro pesquisas simultâneas atingido; tente novamente depois."));
            return;
        }
        player.addChatMessage(new ChatComponentText("Reality Engine Research: executando três buscas paralelas. Fontes e resumos serão guardados na pasta knowledge/web-research."));
        final Batch batch = new Batch(player, query);
        String[] variants = {query, "Minecraft Forge 1.7.10 " + query, "site:github.com Minecraft mod " + query};
        for (final String variant : variants) {
            workers.execute(new Runnable() {
                public void run() {
                    try {
                        batch.results.addAll(search(variant));
                    } catch (Exception exception) {
                        RealityEngineAI.LOG.debug("Web research subquery failed.", exception);
                    } finally {
                        if (batch.remaining.decrementAndGet() == 0) finish(batch);
                    }
                }
            });
        }
    }

    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event == null || event.phase != TickEvent.Phase.END) return;
        Completion completion;
        while ((completion = completions.poll()) != null) {
            EntityPlayer player = completion.player;
            if (player == null || player.isDead || player.worldObj == null || player.worldObj.isRemote) continue;
            if (completion.error != null) {
                player.addChatMessage(new ChatComponentText("Reality Engine Research: falha ao guardar os resultados: " + shorten(completion.error, 100)));
                continue;
            }
            if (completion.results.isEmpty()) {
                player.addChatMessage(new ChatComponentText("Reality Engine Research: nenhum resultado legível. O provedor pode ter bloqueado a busca; não foi inventado aprendizado."));
                continue;
            }
            player.addChatMessage(new ChatComponentText("Reality Engine Research: " + completion.results.size() + " fontes únicas salvas em knowledge/web-research/" + completion.fileName));
            for (int i = 0; i < Math.min(5, completion.results.size()); i++) {
                ResearchResult result = completion.results.get(i);
                player.addChatMessage(new ChatComponentText((i + 1) + ". " + shorten(result.title, 65)));
                player.addChatMessage(new ChatComponentText(shorten(result.url, 120)));
            }
        }
    }

    private void finish(Batch batch) {
        try {
            Map<String, ResearchResult> unique = new LinkedHashMap<String, ResearchResult>();
            for (ResearchResult result : batch.results) {
                if (result != null && !result.url.isEmpty() && !unique.containsKey(result.url)) unique.put(result.url, result);
            }
            List<ResearchResult> results = new ArrayList<ResearchResult>(unique.values());
            if (results.size() > MAX_RESULTS) results = new ArrayList<ResearchResult>(results.subList(0, MAX_RESULTS));
            completions.add(new Completion(batch.player, results, persist(batch.query, results), null));
        } catch (Exception exception) {
            RealityEngineAI.LOG.error("Failed to save web research results.", exception);
            completions.add(new Completion(batch.player, Collections.<ResearchResult>emptyList(), "", exception.getMessage()));
        } finally {
            activeBatches.decrementAndGet();
        }
    }

    private List<ResearchResult> search(String query) throws IOException {
        String encoded = URLEncoder.encode(query, "UTF-8");
        HttpURLConnection connection = (HttpURLConnection) new URL("https://html.duckduckgo.com/html/?q=" + encoded).openConnection();
        connection.setConnectTimeout(6000);
        connection.setReadTimeout(8000);
        connection.setInstanceFollowRedirects(true);
        connection.setRequestProperty("User-Agent", "RealityEngineAI/0.5.0 (user-initiated Minecraft mod research)");
        connection.setRequestProperty("Accept", "text/html,application/xhtml+xml");
        String html;
        try {
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) throw new IOException("Search provider HTTP " + status);
            try (InputStream input = connection.getInputStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (output.size() + count > MAX_RESPONSE_BYTES) throw new IOException("Search response exceeded size limit");
                    output.write(buffer, 0, count);
                }
                html = new String(output.toByteArray(), StandardCharsets.UTF_8);
            }
        } finally {
            connection.disconnect();
        }
        List<String> snippets = new ArrayList<String>();
        Matcher sm = SNIPPETS.matcher(html);
        while (sm.find() && snippets.size() < MAX_RESULTS) snippets.add(plainText(sm.group(1)));
        List<ResearchResult> results = new ArrayList<ResearchResult>();
        Matcher matcher = LINKS.matcher(html);
        while (matcher.find() && results.size() < MAX_RESULTS) {
            String href = normalizeUrl(decode(matcher.group(1).replace("\"", "")));
            String title = plainText(matcher.group(2));
            if (href.isEmpty() || title.isEmpty()) continue;
            String snippet = results.size() < snippets.size() ? snippets.get(results.size()) : "";
            results.add(new ResearchResult(title, href, snippet, query));
        }
        return results;
    }

    private synchronized String persist(String query, List<ResearchResult> results) throws IOException {
        if (researchDirectory == null) throw new IOException("Research directory is not initialized");
        if (!researchDirectory.exists() && !researchDirectory.mkdirs()) throw new IOException("Could not create research directory");
        String slug = CreationPlan.normalize(query).replaceAll("[^a-z0-9]+", "-").replaceAll("^-|-$", "");
        if (slug.length() > 32) slug = slug.substring(0, 32);
        if (slug.isEmpty()) slug = "research";
        String fileName = System.currentTimeMillis() + "-" + slug + "-" + UUID.randomUUID().toString().substring(0, 6) + ".json";
        JsonObject root = new JsonObject();
        root.addProperty("query", query);
        root.addProperty("created_at_epoch_ms", System.currentTimeMillis());
        root.addProperty("search_provider", "DuckDuckGo HTML");
        root.addProperty("result_count", results.size());
        root.addProperty("learning_mode", "source cache; model weights are not updated by raw snippets");
        JsonArray array = new JsonArray();
        for (ResearchResult result : results) {
            JsonObject item = new JsonObject();
            item.addProperty("title", result.title);
            item.addProperty("url", result.url);
            item.addProperty("snippet", result.snippet);
            item.addProperty("matched_query", result.query);
            array.add(item);
        }
        root.add("results", array);
        File target = new File(researchDirectory, fileName);
        try (OutputStreamWriter writer = new OutputStreamWriter(Files.newOutputStream(target.toPath()), StandardCharsets.UTF_8)) {
            GSON.toJson(root, writer);
        }
        return fileName;
    }

    private static String normalizeUrl(String raw) {
        try {
            String url = raw == null ? "" : raw.trim().replace("\"", "");
            if (url.startsWith("//")) url = "https:" + url;
            if (url.startsWith("/l/?") || url.contains("duckduckgo.com/l/?")) {
                int index = url.indexOf("uddg=");
                if (index >= 0) {
                    String encoded = url.substring(index + 5);
                    int amp = encoded.indexOf('&');
                    if (amp >= 0) encoded = encoded.substring(0, amp);
                    url = URLDecoder.decode(encoded, "UTF-8");
                }
            }
            URL parsed = new URL(url);
            String protocol = parsed.getProtocol().toLowerCase(Locale.ROOT);
            String host = parsed.getHost().toLowerCase(Locale.ROOT);
            if (!"http".equals(protocol) && !"https".equals(protocol)) return "";
            if (host.isEmpty() || host.equals("localhost") || host.endsWith(".local") || host.equals("127.0.0.1")
                    || host.equals("0.0.0.0") || host.startsWith("10.") || host.startsWith("192.168.")
                    || host.equals("169.254.169.254") || host.matches("172\\.(1[6-9]|2[0-9]|3[0-1])\\..*")
                    || host.equals("duckduckgo.com") || host.endsWith(".duckduckgo.com")) return "";
            return parsed.toExternalForm();
        } catch (Exception ignored) {
            return "";
        }
    }

    private static String plainText(String html) {
        if (html == null) return "";
        return decode(html.replaceAll("(?is)<script[^>]*>.*?</script>", " ")
            .replaceAll("(?is)<style[^>]*>.*?</style>", " ")
            .replaceAll("(?is)<[^>]+>", " ")).replaceAll("\\s+", " ").trim();
    }

    private static String decode(String value) {
        if (value == null) return "";
        return value.replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'")
            .replace("&#x27;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ");
    }

    private static String sanitize(String value) {
        if (value == null) return "";
        String query = value.trim().replaceAll("\\s+", " ");
        return query.length() > MAX_QUERY_LENGTH ? query.substring(0, MAX_QUERY_LENGTH) : query;
    }

    private static String shorten(String value, int limit) {
        if (value == null) return "";
        return value.length() <= limit ? value : value.substring(0, limit - 3) + "...";
    }

    private static final class Batch {
        final EntityPlayer player;
        final String query;
        final AtomicInteger remaining = new AtomicInteger(3);
        final List<ResearchResult> results = Collections.synchronizedList(new ArrayList<ResearchResult>());
        Batch(EntityPlayer player, String query) { this.player = player; this.query = query; }
    }

    private static final class ResearchResult {
        final String title, url, snippet, query;
        ResearchResult(String title, String url, String snippet, String query) {
            this.title = shorten(title, 180); this.url = shorten(url, 300); this.snippet = shorten(snippet, 500); this.query = query;
        }
    }

    private static final class Completion {
        final EntityPlayer player;
        final List<ResearchResult> results;
        final String fileName, error;
        Completion(EntityPlayer player, List<ResearchResult> results, String fileName, String error) {
            this.player = player; this.results = results; this.fileName = fileName; this.error = error;
        }
    }
}
