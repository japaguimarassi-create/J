package br.com.realityengineai;

public final class CreationPlanContractTest {
    private static final String[][] CASES = {
        {"ENTITY","corruptor","uma entidade que corrompe todos os blocos ao redor"},
        {"ENTITY","corruptor","uma criatura que infecta os blocos próximos"},
        {"ENTITY","corruptor","um mob que contamina os blocos ao redor"},
        {"ENTITY","corruptor","um monstro que corrompe os blocos próximos"},
        {"ENTITY","corruptor","entidade que transforma blocos vizinhos em blocos corrompidos"},
        {"ENTITY","corruptor","criatura corrompedora que infecta blocos no raio 4"},
        {"ENTITY","corruptor","crie um boss que corrompe todos os blocos ao redor"},
        {"ENTITY","corruptor","uma entidade infecta blocos próximos em um raio 5"},
        {"ENTITY","corruptor","um mob que transforma o terreno ao redor"},
        {"ENTITY","corruptor","uma entidade que contamina todos os blocos em 6 blocos"},
        {"ENTITY","car","um carro(entidade)"},
        {"ENTITY","car","um carro como entidade"},
        {"ENTITY","car","uma entidade carro"},
        {"ENTITY","car","um veículo que pode ser pilotado"},
        {"ENTITY","car","um automóvel como mob"},
        {"ENTITY","car","um caminhão que anda pelo mundo"},
        {"ENTITY","car","uma moto como entidade"},
        {"ENTITY","car","uma bicicleta entidade"},
        {"ENTITY","car","um ônibus que se move"},
        {"ENTITY","car","um carro dirigível no Minecraft"},
        {"ENTITY","car","um tanque como entidade"},
        {"ENTITY","dragon","um dragão com asas"},
        {"ENTITY","dragon","uma entidade dragão de 100 metros"},
        {"ENTITY","hostile_creature","um monstro hostil que ataca"},
        {"ENTITY","creature","um mob amigável"},
        {"BLOCK","crystal","um bloco de cristal"},
        {"BLOCK","generic","um bloco de pedra azul"},
        {"BLOCK","generic","uma máquina em bloco"},
        {"BLOCK","generic","um bloco que cura ao clicar"},
        {"BLOCK","generic","uma estrutura como bloco"},
        {"BLOCK","generic","um bloco de metal chamado ônix"},
        {"ITEM","sword","uma espada de energia"},
        {"ITEM","tool","uma picareta de cristal"},
        {"ITEM","food","uma comida especial"},
        {"ITEM","artifact","um item de cura"},
        {"ITEM","artifact","um artefato chamado amuleto"},
        {"DIMENSION","cold","uma dimensão de neve"},
        {"DIMENSION","desert","um planeta desértico"},
        {"DIMENSION","forest","uma dimensão de floresta"},
        {"DIMENSION","space","uma dimensão no espaço"},
        {"DIMENSION","infernal","um mundo de lava"},
        {"QUERY","internet_research","pesquise na internet sobre entidades personalizadas no Forge 1.7.10"},
        {"QUERY","query_mods","lista de mods instalados"},
        {"QUERY","query_registry","liste os blocos registrados"},
        {"QUERY","query_registry_search","buscar registro tinkers"},
        {"QUERY","help","ajuda"},
        {"AMBIGUOUS","type_not_explicit","crie algo incrível"},
        {"AMBIGUOUS","type_not_explicit","crie aquilo"},
        {"AMBIGUOUS","type_not_explicit","faça alguma coisa poderosa"},
        {"AMBIGUOUS","type_not_explicit","quero algo diferente"},
        {"AMBIGUOUS","type_not_explicit","surpreenda-me"}
    };

    public static void main(String[] args) {
        int assertions = 0;
        for (int i = 0; i < CASES.length; i++) {
            String expectedKind = CASES[i][0].toLowerCase();
            String expectedArchetype = CASES[i][1];
            String prompt = CASES[i][2];
            for (int variant = 0; variant < 22; variant++) {
                String utterance = variant(prompt, variant);
                CreationPlan plan = CreationPlan.resolve(utterance);
                if (!expectedKind.equals(plan.kind) || !expectedArchetype.equals(plan.archetype)) {
                    throw new AssertionError("Case " + (i + 1) + ", variant " + variant + ": " + utterance
                        + " expected " + expectedKind + "/" + expectedArchetype
                        + " but got " + plan.kind + "/" + plan.archetype + "/" + plan.behavior);
                }
                if (expectedArchetype.equals("corruptor") && (!"corrupt_nearby_blocks".equals(plan.behavior) || plan.radius < 1 || plan.radius > 6)) {
                    throw new AssertionError("Corruptor lost its behavior or radius: " + utterance);
                }
                if (expectedArchetype.equals("car") && !"vehicle".equals(plan.behavior)) {
                    throw new AssertionError("Car was parsed without vehicle behavior: " + utterance);
                }
                assertions++;
            }
        }
        if (CASES.length < 50 || assertions < 1001) {
            throw new AssertionError("The contract suite must contain at least 50 scenarios and 1001 utterance checks.");
        }
        System.out.println("INTENT CONTRACT PASS: " + CASES.length + " advanced scenarios, " + assertions + " utterance variants.");
    }

    private static String variant(String prompt, int index) {
        switch (index) {
            case 0: return prompt;
            case 1: return "crie " + prompt;
            case 2: return "CRIE " + prompt;
            case 3: return "CrIe " + prompt + " por favor";
            case 4: return "  crie   " + prompt + "   ";
            case 5: return "crie por favor " + prompt;
            case 6: return "CRIE " + prompt.toUpperCase() + "!";
            case 7: return "crie " + prompt + " no Minecraft";
            case 8: return "crie " + prompt + " agora";
            case 9: return "crie " + prompt + " por gentileza";
            case 10: return "crie, por favor " + prompt;
            case 11: return "crie " + prompt.replace(" ", "  ");
            case 12: return "CRIE   " + prompt;
            case 13: return "crie " + prompt + ".";
            case 14: return "crie " + prompt + " por favor no mundo";
            case 15: return "crie " + prompt + " para mim";
            case 16: return "crie um " + prompt;
            case 17: return "crie " + prompt + " dentro do jogo";
            case 18: return "crie " + prompt + " no meu mundo";
            case 19: return "crie " + prompt + " imediatamente";
            case 20: return "crie gentilmente " + prompt;
            default: return "crie " + prompt + " por favor!";
        }
    }
}
