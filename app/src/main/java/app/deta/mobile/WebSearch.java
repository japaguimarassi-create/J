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

final class WebSearch {
    private static final int MAX_RESPONSE_BYTES = 1_500_000;
    private static final Pattern ANCHOR_PATTERN = Pattern.compile("(?is)<a\\b([^>]*)>(.*?)</a>");
    private static final Pattern SNIPPET_PATTERN = Pattern.compile(
            "(?is)<(a|div|td|span)\\b(?=[^>]*\\bclass\\s*=\\s*(['\"])[^'\"]*(?:result__snippet|result-snippet)[^'\"]*\\2)[^>]*>(.*?)</\\1\\s*>"
    );
    private static final Pattern ATTRIBUTE_PATTERN = Pattern.compile(
            "(?is)\\b([a-z0-9_-]+)\\s*=\\s*(['\"])(.*?)\\2"
    );
    private static final Pattern REDIRECT_PATTERN = Pattern.compile("[?&]uddg=([^&]+)");
    private static final Pattern HTML_TAG_PATTERN = Pattern.compile("(?is)<[^>]+>");
    private static final Pattern HTML_ENTITY_PATTERN = Pattern.compile("&(#x?[0-9a-fA-F]+|amp|quot|apos|lt|gt|nbsp);");

    private WebSearch() {
    }

    static String answer(String input) {
        String question = input == null ? "" : input.trim();
        if (question.isEmpty()) return "Escreva uma pergunta ou consulta para pesquisar.";
        String normalized = normalize(question);
        if (normalized.equals("/ajuda") || normalized.contains("o que voce pode fazer")
                || normalized.equals("ajuda") || normalized.equals("funcoes")) {
            return "Deta — funções disponíveis nesta versão\n\n"
                    + "• Pesquisar na web pública sem API de IA.\n"
                    + "• Exibir títulos, resumos disponíveis e links das fontes.\n"
                    + "• Guardar conversas localmente neste dispositivo.\n"
                    + "• Pesquisar o histórico pelo menu lateral.\n"
                    + "• Usar ditado por voz quando o Android oferecer reconhecimento.\n\n"
                    + "As respostas factuais vêm dos resultados da web; esta versão ainda não executa o modelo neural de 400 mil parâmetros dentro do Android.";
        }
        if (isGreeting(normalized)) {
            return "Olá! Sou a Deta. Posso pesquisar um assunto na web pública e mostrar os links usados. "
                    + "Escreva uma pergunta específica ou toque em + para ver as ações.";
        }
        String query = question.replaceFirst("(?i)^\\s*(pesquisar na web|pesquise na web|buscar na web)\\s*:?\\s*", "").trim();
        if (query.isEmpty()) {
            return "Digite o que deseja pesquisar depois de “Pesquisar na web”.";
        }
        try {
            List<Result> results = search(query);
            if (results.isEmpty()) {
                return "A pesquisa terminou, mas o buscador não devolveu resultados legíveis para esta consulta. "
                        + "Tente palavras-chave mais específicas ou tente novamente com a internet ativa.";
            }
            StringBuilder response = new StringBuilder();
            response.append("Pesquisei a web pública para: “").append(query).append("”\n");
            response.append("Consulta sem API de IA; confira as fontes abaixo.\n\n");
            int index = 1;
            for (Result result : results) {
                response.append(index++).append(". ").append(result.title).append('\n');
                if (!result.snippet.isEmpty()) response.append(result.snippet).append('\n');
                response.append("Fonte: ").append(result.url).append("\n\n");
            }
            response.append("Estes são resultados recuperados da web, não uma resposta produzida por um LLM. "
                    + "Abra as fontes para confirmar detalhes.");
            return response.toString().trim();
        } catch (IOException | RuntimeException exception) {
            return "Não consegui concluir a pesquisa web agora. Confira a conexão e tente novamente.\n\n"
                    + "Esta função consulta resultados públicos por HTTPS e não usa uma API de IA. "
                    + "Se o buscador bloquear a solicitação, aguarde um pouco ou reformule a busca.";
        }
    }

    private static boolean isGreeting(String query) {
        return query.equals("oi") || query.equals("ola") || query.equals("ola deta")
                || query.equals("bom dia") || query.equals("boa tarde")
                || query.equals("boa noite") || query.equals("e ai") || query.equals("hey");
    }

    private static String normalize(String value) {
        return java.text.Normalizer.normalize(value.toLowerCase(Locale.ROOT), java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "").trim();
    }

    private static List<Result> search(String query) throws IOException {
        String encoded = URLEncoder.encode(query, StandardCharsets.UTF_8.name());
        IOException lastError = null;
        String[] endpoints = {
                "https://html.duckduckgo.com/html/?q=" + encoded,
                "https://lite.duckduckgo.com/lite/?q=" + encoded
        };
        for (String endpoint : endpoints) {
            try {
                String document = download(endpoint);
                List<Result> results = parseResults(document);
                if (!results.isEmpty()) return results;
            } catch (IOException exception) {
                lastError = exception;
            }
        }
        if (lastError != null) throw lastError;
        return new ArrayList<>();
    }

    private static String download(String address) throws IOException {
        URL url = new URL(address);
        if (!"https".equalsIgnoreCase(url.getProtocol())
                || !("html.duckduckgo.com".equalsIgnoreCase(url.getHost())
                || "lite.duckduckgo.com".equalsIgnoreCase(url.getHost()))) {
            throw new IOException("Blocked web-search destination.");
        }
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(9000);
        connection.setReadTimeout(12000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("User-Agent", "DetaAndroid/0.2 public-web-search");
        connection.setRequestProperty("Accept", "text/html,application/xhtml+xml");
        connection.setRequestProperty("Accept-Language", "pt-BR,pt;q=0.9,en;q=0.8");
        try {
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) throw new IOException("Search host returned HTTP " + status);
            try (java.io.InputStream input = connection.getInputStream();
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int total = 0;
                int read;
                while ((read = input.read(buffer)) != -1) {
                    total += read;
                    if (total > MAX_RESPONSE_BYTES) throw new IOException("Search response exceeded size limit.");
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
        Matcher snippetMatcher = SNIPPET_PATTERN.matcher(document);
        while (snippetMatcher.find()) {
            String snippet = clean(snippetMatcher.group(3));
            if (!snippet.isEmpty()) snippets.add(snippet);
        }

        List<Result> results = new ArrayList<>();
        Matcher matcher = ANCHOR_PATTERN.matcher(document);
        while (matcher.find() && results.size() < 5) {
            String attributes = matcher.group(1);
            String classes = attribute(attributes, "class");
            if (!classes.contains("result__a") && !classes.contains("result-link")) continue;
            String title = clean(matcher.group(2));
            String address = sourceUrl(attribute(attributes, "href"));
            if (title.isEmpty() || address.isEmpty()) continue;
            String snippet = snippets.size() >= results.size() + 1 ? snippets.get(results.size()) : "";
            boolean duplicate = false;
            for (Result result : results) {
                if (result.url.equals(address)) {
                    duplicate = true;
                    break;
                }
            }
            if (!duplicate) results.add(new Result(title, address, snippet));
        }
        return results;
    }

    private static String attribute(String attributes, String name) {
        Matcher matcher = ATTRIBUTE_PATTERN.matcher(attributes);
        while (matcher.find()) {
            if (matcher.group(1).equalsIgnoreCase(name)) return matcher.group(3);
        }
        return "";
    }

    private static String sourceUrl(String raw) {
        String value = raw == null ? "" : raw.replace("&amp;", "&").trim();
        Matcher redirect = REDIRECT_PATTERN.matcher(value);
        if (redirect.find()) {
            try {
                value = java.net.URLDecoder.decode(redirect.group(1), StandardCharsets.UTF_8.name());
            } catch (Exception ignored) {
                return "";
            }
        } else if (value.startsWith("//")) {
            value = "https:" + value;
        }
        try {
            URL url = new URL(value);
            String host = url.getHost().toLowerCase(Locale.ROOT);
            if (!"https".equalsIgnoreCase(url.getProtocol()) || host.isEmpty()
                    || host.endsWith("duckduckgo.com") || url.getUserInfo() != null
                    || url.getPort() != -1 && url.getPort() != 443
                    || host.equals("localhost") || host.endsWith(".local") || host.endsWith(".internal")
                    || host.matches("\\d{1,3}(\\.\\d{1,3}){3}")) return "";
            return url.toString();
        } catch (Exception exception) {
            return "";
        }
    }

    private static String clean(String value) {
        String stripped = HTML_TAG_PATTERN.matcher(value == null ? "" : value).replaceAll(" ");
        Matcher matcher = HTML_ENTITY_PATTERN.matcher(stripped);
        StringBuffer decoded = new StringBuffer();
        while (matcher.find()) {
            String entity = matcher.group(1).toLowerCase(Locale.ROOT);
            String replacement;
            switch (entity) {
                case "amp": replacement = "&"; break;
                case "quot": replacement = "\""; break;
                case "apos": replacement = "'"; break;
                case "lt": replacement = "<"; break;
                case "gt": replacement = ">"; break;
                case "nbsp": replacement = " "; break;
                default:
                    try {
                        int radix = entity.startsWith("#x") ? 16 : 10;
                        String digits = entity.substring(radix == 16 ? 2 : 1);
                        int codePoint = Integer.parseInt(digits, radix);
                        replacement = Character.isValidCodePoint(codePoint)
                                ? new String(Character.toChars(codePoint)) : "";
                    } catch (RuntimeException exception) {
                        replacement = "";
                    }
            }
            matcher.appendReplacement(decoded, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(decoded);
        return decoded.toString().replace('\u00a0', ' ').replaceAll("\\s+", " ").trim();
    }

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
}
