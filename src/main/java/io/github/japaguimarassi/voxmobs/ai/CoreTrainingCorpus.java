package io.github.japaguimarassi.voxmobs.ai;

import java.util.ArrayList;
import java.util.List;

public final class CoreTrainingCorpus {
    private static final String[] GENERAL_MOBS = {
            "minecraft:wolf", "minecraft:villager", "minecraft:creeper",
            "minecraft:cat", "minecraft:cow", "minecraft:zombie"
    };

    private CoreTrainingCorpus() {
    }

    public static List<TrainingExample> examples() {
        List<TrainingExample> data = new ArrayList<>();
        add(data, 1, 0, 1, 0, 2, "oi", "olá", "e aí tudo bem", "bom dia", "boa noite", "saudações", "opa amigo");
        add(data, 2, 0, 14, 0, 0, "quem é você", "qual é o seu nome", "como você se chama", "o que você é", "de qual espécie você é");
        add(data, 3, 0, 1, 0, 9, "onde estamos", "que lugar é este", "qual é esse bioma", "o que aconteceu aqui", "por que está escuro");
        add(data, 4, 0, 2, 0, 10, "obrigado", "valeu pela ajuda", "agradeço", "muito obrigado amigo");
        add(data, 5, 0, 7, 0, 5, "desculpa", "foi mal", "perdão por isso", "não queria te assustar");
        add(data, 6, 0, 1, 0, 9, "até mais", "tchau", "vou embora", "nos vemos depois");
        add(data, 7, 0, 13, 0, 0, "preciso de ajuda", "me ajuda por favor", "estou perdido", "estou em perigo");
        add(data, 8, 0, 9, 0, 6, "tem um inimigo por perto", "cuidado com o perigo", "um zumbi está vindo", "fique alerta");
        add(data, 9, 1, 10, 0, 2, "me siga", "vem comigo", "me acompanhe", "siga meus passos", "não se afaste", "venha atrás de mim", "fique comigo e siga", "acompanhe meu caminho");
        add(data, 9, 2, 1, 0, 2, "venha aqui", "chegue perto", "se aproxime", "vem para cá");
        add(data, 9, 3, 3, 0, 0, "fuja", "saia daqui", "fique longe", "se afaste do perigo");
        add(data, 9, 4, 1, 0, 9, "olhe para mim", "olhe aqui", "preste atenção em mim");
        add(data, 9, 5, 0, 0, 0, "sente", "sente-se aqui", "descanse um pouco");
        add(data, 9, 6, 10, 0, 0, "pule", "dê um salto", "salte agora");
        add(data, 9, 7, 0, 0, 0, "pare", "fique parado", "espere aqui", "não se mexa");
        add(data, 9, 8, 10, 0, 6, "me proteja", "defenda-me", "fique de guarda", "proteja o jogador");
        add(data, 9, 9, 10, 0, 8, "pegue o item", "recolha esse objeto", "apanhe o item no chão", "pegue aquilo", "recolha o objeto mais próximo");
        add(data, 9, 10, 10, 0, 8, "solte o item", "largue o que está segurando", "deixe o item no chão", "jogue isso no chão", "quero que solte o objeto");
        add(data, 9, 11, 10, 0, 0, "spawn minecraft:zombie", "invoque minecraft:cow", "crie um mob minecraft:skeleton");
        add(data, 10, 0, 14, 2, 2, "do que você gosta", "qual é sua comida favorita", "o que você prefere", "você gosta de mim");
        add(data, 11, 0, 14, 9, 4, "vou te contar uma coisa", "hoje aconteceu algo estranho", "lembra do que fizemos ontem");
        add(data, 12, 0, 2, 0, 5, "sim", "com certeza", "concordo", "isso mesmo", "está certo");
        add(data, 13, 0, 12, 0, 5, "não concordo", "isso está errado", "não é assim", "discordo disso");
        add(data, 14, 0, 1, 0, 9, "por que isso acontece", "como funciona", "me conte mais", "quero entender melhor");
        add(data, 15, 0, 7, 2, 5, "não fique triste", "vai ficar tudo bem", "estou aqui com você");

        addForMob(data, "minecraft:creeper", 1, "não chegue tão perto", "estou nervoso", "isso parece perigoso");
        addForMob(data, "minecraft:creeper", 8, "cuidado, vou explodir", "afaste-se agora");
        addForMob(data, "minecraft:wolf", 2, "somos amigos", "vou ficar ao seu lado", "confio em você");
        addForMob(data, "minecraft:wolf", 8, "vou proteger você", "tem algo se aproximando");
        addForMob(data, "minecraft:cat", 6, "não quero colo agora", "vou observar de longe", "talvez eu aceite um peixe");
        addForMob(data, "minecraft:villager", 1, "bem-vindo à vila", "temos bons negócios", "bom dia viajante");
        addForMob(data, "minecraft:zombie", 3, "grrr, perigo", "não gosto de luz", "vou atacar se chegar perto");
        addForMob(data, "minecraft:enderman", 3, "não olhe diretamente para mim", "mantenha distância", "este lugar é estranho");
        addForMob(data, "minecraft:cow", 1, "gosto de pastos tranquilos", "a grama está boa hoje");
        addForMob(data, "minecraft:sheep", 3, "fiquei assustada", "não faça movimentos bruscos");
        return List.copyOf(data);
    }

    private static void add(List<TrainingExample> data, int speech, int action, int reaction,
                            int memory, int voice, String... phrases) {
        for (String phrase : phrases) {
            data.add(new TrainingExample(phrase, "minecraft:generic", speech, action, reaction, memory, voice));
            for (String mobType : GENERAL_MOBS) {
                data.add(new TrainingExample(phrase, mobType, speech, action, reaction, memory, voice));
            }
        }
    }

    private static void addForMob(List<TrainingExample> data, String mobType, int reaction, String... phrases) {
        for (String phrase : phrases) {
            data.add(new TrainingExample(phrase, mobType, 14, 0, reaction, 9, reaction));
        }
    }
}
