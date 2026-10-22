package app.deta.mobile;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class DetaRequestPlanner {
    enum Route { CONVERSATION, CREATE_PROJECT, WEB_SEARCH }
    enum Kind { GAME, SOCIAL, UTILITY }

    static final class Plan {
        final Route route;
        final Kind kind;
        final String title;
        final String originalPrompt;
        final List<String> features;
        final List<String> limitations;
        final List<String> steps;

        Plan(Route route, Kind kind, String title, String originalPrompt,
             List<String> features, List<String> limitations, List<String> steps) {
            this.route = route;
            this.kind = kind;
            this.title = title;
            this.originalPrompt = originalPrompt;
            this.features = Collections.unmodifiableList(new ArrayList<>(features));
            this.limitations = Collections.unmodifiableList(new ArrayList<>(limitations));
            this.steps = Collections.unmodifiableList(new ArrayList<>(steps));
        }

        String asModelPlanningPrompt() {
            return "User: Prepare a concise implementation plan for this app request. Identify user-facing behavior, files, and tests before writing code.\n"
                    + "Request: " + originalPrompt + "\nAssistant:";
        }

        String render() {
            StringBuilder out = new StringBuilder("PLANO DE IMPLEMENTAÇÃO\n");
            out.append("Projeto: ").append(title).append('\n');
            out.append("Tipo: ").append(kindLabel(kind)).append("\n\n");
            out.append("Requisitos identificados:\n");
            for (String feature : features) out.append("• ").append(feature).append('\n');
            out.append("\nOrdem de execução:\n");
            for (int i = 0; i < steps.size(); i++) {
                out.append(i + 1).append(". ").append(steps.get(i)).append('\n');
            }
            if (!limitations.isEmpty()) {
                out.append("\nLimitações que não serão simuladas como concluídas:\n");
                for (String limitation : limitations) out.append("• ").append(limitation).append('\n');
            }
            out.append("\nVou gerar os arquivos depois deste planejamento.");
            return out.toString().trim();
        }

        private static String kindLabel(Kind kind) {
            if (kind == Kind.GAME) return "jogo de navegador";
            if (kind == Kind.SOCIAL) return "aplicativo social";
            return "aplicativo utilitário";
        }
    }

    private static final Pattern TITLE_PATTERN = Pattern.compile(
            "(?iu)(?:chamado|chamada|com o nome|nomeado|nomeada|intitulado|intitulada)\\s+[\"“]?([\\p{L}\\p{N}][^\"”\\n,.]{0,48})"
    );
    private static final Pattern CREATE_VERB = Pattern.compile(
            "(?iu)(^|\\b)(crie|criar|cria|desenvolva|desenvolver|construa|construir|gere|gerar|faca|faz|fazer|monte|montar|implemente|implementar|programa|programe|build|create|make|develop|implement|generate)(\\b)"
    );

    private DetaRequestPlanner() {}

    static Plan analyze(String input) {
        String prompt = input == null ? "" : input.trim();
        String value = normalize(prompt);
        if (prompt.isEmpty()) {
            return simple(Route.CONVERSATION, prompt);
        }
        if (isWebSearch(value)) {
            return simple(Route.WEB_SEARCH, prompt);
        }
        if (!isCreationRequest(value)) {
            return simple(Route.CONVERSATION, prompt);
        }

        Kind kind = chooseKind(value);
        String title = titleFrom(prompt, kind);
        ArrayList<String> features = new ArrayList<>();
        ArrayList<String> steps = new ArrayList<>();
        ArrayList<String> limitations = new ArrayList<>();

        if (kind == Kind.GAME) {
            features.add("Área de jogo que aceita toque e mouse");
            features.add("Pontuação, estado da partida e reinício");
            if (containsAny(value, "tempo", "timer", "segundos", "cronometro", "cronometro")) {
                features.add("Temporizador ajustado ao pedido");
            }
            if (containsAny(value, "recorde", "melhor pontuacao", "high score", "highscore")) {
                features.add("Recorde persistido localmente");
            }
            steps.add("Definir regras, entrada do jogador e condição de fim.");
            steps.add("Implementar estado, controles e interface responsiva.");
        } else if (kind == Kind.SOCIAL) {
            features.add("Criar e listar publicações");
            features.add("Pesquisar publicações e reagir a elas");
            if (containsAny(value, "comentario", "comentar", "responder")) {
                features.add("Adicionar e consultar comentários");
            }
            features.add("Persistir os dados no dispositivo");
            steps.add("Modelar os dados da publicação e as operações do feed.");
            steps.add("Implementar busca, reações e controles de exclusão.");
        } else {
            features.add("Criar, listar, concluir e remover itens");
            features.add("Validar entrada e estado vazio");
            features.add("Persistir dados no dispositivo");
            steps.add("Definir a estrutura de dados e os estados da interface.");
            steps.add("Implementar operações, validação e persistência local.");
        }

        if (containsAny(value, "login", "autenticacao", "conta de usuario", "multiusuario", "multiplayer",
                "multijogador", "servidor", "sincronizacao na nuvem", "pagamento", "stripe",
                "push notification", "notificacao push", "banco de dados remoto")) {
            limitations.add("O pedido menciona recursos que precisam de infraestrutura externa; o protótipo gerado não os tratará como serviços já conectados.");
        }
        if (containsAny(value, "apk nativo", "aplicativo android nativo", "compilar um apk")) {
            limitations.add("Esta versão exporta projetos web em ZIP; não compila automaticamente qualquer pedido em um APK nativo.");
        }
        steps.add("Gerar os arquivos do projeto e registrar instruções de execução.");
        steps.add("Validar estrutura, escape de entrada e conteúdo do ZIP.");
        steps.add("Disponibilizar prévia local e exportação para inspeção.");

        return new Plan(Route.CREATE_PROJECT, kind, title, prompt, features, limitations, steps);
    }

    private static Plan simple(Route route, String prompt) {
        return new Plan(route, Kind.UTILITY, "", prompt,
                Collections.emptyList(), Collections.emptyList(), Collections.emptyList());
    }

    static boolean isCreationRequest(String normalizedPrompt) {
        String value = normalize(normalizedPrompt);
        if (value.isEmpty() || isGreeting(value) || isWebSearch(value)) return false;
        boolean hasObject = containsAny(value, "app", "aplicativo", "aplicacao", "site", "website",
                "jogo", "game", "rede social", "ferramenta", "programa", "software", "plataforma",
                "feed", "editor", "calculadora", "agenda", "lista de tarefas", "chat");
        boolean hasVerb = CREATE_VERB.matcher(value).find();
        boolean implied = value.matches(".*\\b(quero|preciso|gostaria de|faz pra mim|faca pra mim|faz um)\\b.*")
                && hasObject;
        return hasObject && (hasVerb || implied);
    }

    private static boolean isGreeting(String value) {
        return value.matches("^(oi|ola|ola deta|opa|e ai|eae|bom dia|boa tarde|boa noite|hey|hi|hello|tudo bem|obrigado|obrigada|valeu)[.!? ]*$");
    }

    private static boolean isWebSearch(String value) {
        return value.matches("^(pesquise|pesquisar|pesquisa|busque|buscar|procure|procurar)\\s+(na\\s+)?(web|internet|online)\\b.*")
                || value.startsWith("pesquise na web:")
                || value.startsWith("pesquisar na web:")
                || value.startsWith("buscar na web:")
                || value.startsWith("pesquise sobre ");
    }

    private static Kind chooseKind(String value) {
        if (containsAny(value, "jogo", "game", "rpg", "arcade", "plataforma 2d", "runner", "puzzle", "aventura")) {
            return Kind.GAME;
        }
        if (containsAny(value, "rede social", "social", "comunidade", "feed", "publicacao", "publicacoes", "seguidores")) {
            return Kind.SOCIAL;
        }
        return Kind.UTILITY;
    }

    private static String titleFrom(String prompt, Kind kind) {
        Matcher matcher = TITLE_PATTERN.matcher(prompt);
        if (matcher.find()) {
            String title = matcher.group(1).trim().replaceAll("\\s+", " ");
            title = title.replaceFirst("(?iu)\\s+(?:com|para|que tenha|com suporte a|e com)\\s+.*$", "").trim();
            if (!title.isEmpty()) return title.length() > 48 ? title.substring(0, 48).trim() : title;
        }
        if (kind == Kind.GAME) return "Jogo criado";
        if (kind == Kind.SOCIAL) return "Comunidade";
        return "Aplicativo";
    }

    private static boolean containsAny(String value, String... terms) {
        for (String term : terms) if (value.contains(term)) return true;
        return false;
    }

    static String normalize(String value) {
        return Normalizer.normalize(value == null ? "" : value.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "").replaceAll("\\s+", " ").trim();
    }
}
