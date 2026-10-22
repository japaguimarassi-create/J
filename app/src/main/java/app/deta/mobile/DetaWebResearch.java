package app.deta.mobile;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class DetaWebResearch {
    private static final int MAX_BYTES = 1_500_000;
    private static final int RESULT_LIMIT = 6;
    private static final Pattern RESULT_LINK = Pattern.compile("(?is)<a\\b([^>]*)>(.*?)</a>");
    private static final Pattern SNIPPET = Pattern.compile(
            "(?is)<(?:a|div|td|span)\\b([^>]*)>(.*?)</(?:a|div|td|span)>"
    );
    private static final Pattern ATTR = Pattern.compile("(?is)\\b([a-z0-9_-]+)\\s*=\\s*(['\"])(.*?)\\2");
    private static final Pattern REDIRECT = Pattern.compile("[?&]uddg=([^&]+)");
    private static final Pattern TAGS = Pattern.compile("(?is)<[^>]*>");
    private static final Pattern ENTITY = Pattern.compile("&(#x?[0-9a-fA-F]+|amp|quot|apos|lt|gt|nbsp);");

    static final class Result {
        final String title;
        final String url;
        final String snippet;

        Result(String title, String url, String snippet) {
            this.title = title;
            this.url = url;
            this.snippet = snippet;
        }
    }

    private DetaWebResearch() {}

    static String research(String rawQuery) throws IOException {
        String query = rawQuery == null ? "" : rawQuery.trim();
        query = query.replaceFirst("(?iu)^\\s*(pesquise|pesquisa|pesquisar|busque|buscar|procure|procurar)(\\s+sobre)?\\s+(na\\s+)?(web|internet|online)\\s*:?\\s*", "").trim();
        query = query.replaceFirst("(?iu)^pesquise\\s+sobre\\s*", "").trim();
        if (query.isEmpty()) throw new IllegalArgumentException("Informe um assunto para pesquisar.");
        List<Result> results = search(query);
        if (results.isEmpty()) throw new IOException("O buscador não retornou resultados públicos legíveis para esta consulta.");

        StringBuilder answer = new StringBuilder();
        answer.append("Pesquisa na web: ").append(query).append("\n\n");
        for (int i = 0; i < results.size(); i++) {
            Result result = results.get(i);
            answer.append(i + 1).append(". ").append(result.title).append('\n');
            if (!result.snippet.isEmpty()) answer.append(result.snippet).append('\n');
            answer.append(result.url).append("\n\n");
        }
        return answer.toString().trim();
    }

    static List<Result> search(String query) throws IOException {
        String encoded = URLEncoder.encode(query, StandardCharsets.UTF_8.name());
        IOException last = null;
        for (String endpoint : new String[]{
                "https://html.duckduckgo.com/html/?q=" + encoded,
                "https://lite.duckduckgo.com/lite/?q=" + encoded
        }) {
            try {
                List<Result> results = parseResults(download(endpoint));
                if (!results.isEmpty()) return results;
            } catch (IOException exception) {
                last = exception;
            }
        }
        if (last != null) throw last;
        return new ArrayList<>();
    }

    private static String download(String address) throws IOException {
        URL url = new URL(address);
        if (!"https".equalsIgnoreCase(url.getProtocol())
                || !("html.duckduckgo.com".equalsIgnoreCase(url.getHost())
                || "lite.duckduckgo.com".equalsIgnoreCase(url.getHost()))) {
            throw new IOException("Search destination is not allowlisted.");
        }
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(9000);
        connection.setReadTimeout(12000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("User-Agent", "DetaAndroid/1.3 public-web-research");
        connection.setRequestProperty("Accept", "text/html,application/xhtml+xml");
        connection.setRequestProperty("Accept-Language", "pt-BR,pt;q=0.9,en;q=0.8");
        try {
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) throw new IOException("Search engine HTTP " + status);
            try (java.io.InputStream input = connection.getInputStream();
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int read;
                int total = 0;
                while ((read = input.read(buffer)) != -1) {
                    total += read;
                    if (total > MAX_BYTES) throw new IOException("Search response exceeded the size limit.");
                    output.write(buffer, 0, read);
                }
                return output.toString(StandardCharsets.UTF_8.name());
            }
        } finally {
            connection.disconnect();
        }
    }

    static List<Result> parseResults(String document) {
        List<String> snippets = new ArrayList<>();
        Matcher snippetMatcher = SNIPPET.matcher(document == null ? "" : document);
        while (snippetMatcher.find()) {
            String classes = attribute(snippetMatcher.group(1), "class");
            if (!classes.contains("result__snippet") && !classes.contains("result-snippet")
                    && !classes.contains("result__extras__url")) continue;
            String snippet = clean(snippetMatcher.group(2));
            if (snippet.length() > 700) snippet = snippet.substring(0, 700);
            if (!snippet.isEmpty()) snippets.add(snippet);
        }

        List<Result> results = new ArrayList<>();
        Matcher matcher = RESULT_LINK.matcher(document == null ? "" : document);
        while (matcher.find() && results.size() < RESULT_LIMIT) {
            String attributes = matcher.group(1);
            String classes = attribute(attributes, "class");
            if (!classes.contains("result__a") && !classes.contains("result-link")) continue;
            String title = clean(matcher.group(2));
            String link = sourceUrl(attribute(attributes, "href"));
            if (title.isEmpty() || link.isEmpty()) continue;
            boolean duplicate = false;
            for (Result existing : results) if (existing.url.equals(link)) { duplicate = true; break; }
            if (!duplicate) {
                String snippet = results.size() < snippets.size() ? snippets.get(results.size()) : "";
                results.add(new Result(title, link, snippet));
            }
        }
        return results;
    }

    private static String attribute(String attributes, String name) {
        Matcher matcher = ATTR.matcher(attributes == null ? "" : attributes);
        while (matcher.find()) if (matcher.group(1).equalsIgnoreCase(name)) return matcher.group(3);
        return "";
    }

    private static String sourceUrl(String raw) {
        String value = raw == null ? "" : raw.replace("&amp;", "&").trim();
        Matcher redirect = REDIRECT.matcher(value);
        if (redirect.find()) {
            try {
                value = java.net.URLDecoder.decode(redirect.group(1), StandardCharsets.UTF_8.name());
            } catch (IllegalArgumentException exception) {
                return "";
            }
        } else if (value.startsWith("//")) {
            value = "https:" + value;
        }
        try {
            URL url = new URL(value);
            String host = url.getHost().toLowerCase(Locale.ROOT);
            if (!"https".equalsIgnoreCase(url.getProtocol()) || host.isEmpty() || url.getUserInfo() != null
                    || url.getPort() != -1 && url.getPort() != 443
                    || host.endsWith("duckduckgo.com") || host.equals("localhost")
                    || host.endsWith(".local") || host.endsWith(".internal")
                    || host.matches("\\d{1,3}(\\.\\d{1,3}){3}")) return "";
            return url.toString();
        } catch (Exception exception) {
            return "";
        }
    }

    private static String clean(String text) {
        String value = TAGS.matcher(text == null ? "" : text).replaceAll(" ");
        Matcher matcher = ENTITY.matcher(value);
        StringBuffer decoded = new StringBuffer();
        while (matcher.find()) {
            String name = matcher.group(1).toLowerCase(Locale.ROOT);
            String replacement;
            switch (name) {
                case "amp": replacement = "&"; break;
                case "quot": replacement = "\""; break;
                case "apos": replacement = "'"; break;
                case "lt": replacement = "<"; break;
                case "gt": replacement = ">"; break;
                case "nbsp": replacement = " "; break;
                default:
                    try {
                        int radix = name.startsWith("#x") ? 16 : 10;
                        replacement = new String(Character.toChars(Integer.parseInt(name.substring(radix == 16 ? 2 : 1), radix)));
                    } catch (RuntimeException exception) {
                        replacement = "";
                    }
            }
            matcher.appendReplacement(decoded, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(decoded);
        return decoded.toString().replace('\u00a0', ' ').replaceAll("\\s+", " ").trim();
    }
}
