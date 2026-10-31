package io.github.japaguimarassi.voxmobs.ai;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;

import java.util.List;
import net.minecraft.core.registries.BuiltInRegistries;
import java.util.Locale;
import java.util.concurrent.ThreadLocalRandom;

public final class OfflineBrain {
    private OfflineBrain() {
    }

    public static AiReply answer(Mob mob, Player player, String message, List<String> history) {
        return answer(mob, player, message, history, null);
    }

    public static AiReply answer(Mob mob, Player player, String message, List<String> history,
                                 CognitivePrediction cognition) {
        String text = IntentInterpreter.normalize(message);
        String type = BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()) == null ? "criatura"
                : BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).getPath();
        ActionRequest request = IntentInterpreter.parseCommand(message);
        MobAction action = request.action();
        if (action != MobAction.NONE) {
            return actionReply(request, player.getName().getString(), type);
        }
        if (cognition != null && cognition.actionConfidence() >= 0.88F) {
            MobAction learned = learnedAction(cognition.action());
            if (learned != MobAction.NONE && learned != MobAction.SPAWN_MOB) {
                return actionReply(new ActionRequest(learned, ""), player.getName().getString(), type);
            }
        }
        if (contains(text, "oi", "ola", "e ai", "bom dia", "boa tarde", "boa noite", "tudo bem")) {
            return pick("Olá, " + player.getName().getString() + ". O que está fazendo por aqui?",
                    "Oi! Eu estava observando este lugar. Aconteceu alguma coisa?",
                    "Olá! Você parece querer conversar. Estou ouvindo.");
        }
        if (contains(text, "quem e voce", "qual seu nome", "seu nome", "o que voce e")) {
            return new AiReply("Sou um " + type + ". Cada criatura tem seu próprio jeito de pensar por aqui.", MobAction.LOOK, "curioso");
        }
        if (contains(text, "onde estamos", "que lugar e esse", "qual bioma", "onde fica")) {
            return new AiReply("Estamos em " + mob.level().getBiome(mob.blockPosition()).unwrapKey()
                    .map(key -> key.location().getPath().replace('_', ' ')).orElse("um lugar desconhecido")
                    + ". Eu conheço este lugar pelos meus sentidos, não por um mapa.", MobAction.LOOK, "observador");
        }
        if (contains(text, "esta com medo", "voce tem medo", "esta assustado", "tem medo")) {
            boolean cautious = Math.abs(mob.getUUID().hashCode()) % 2 == 0;
            return new AiReply(cautious ? "Às vezes. Este mundo pode ser perigoso, e eu prefiro prestar atenção." : "Não exatamente. Só tento não me meter em problemas desnecessários.", MobAction.LOOK, "pensativo");
        }
        if (contains(text, "obrigado", "obrigada", "valeu", "agradeco")) {
            return new AiReply("Não precisa agradecer. É bom quando alguém me trata com respeito.", MobAction.LOOK, "grato");
        }
        if (contains(text, "desculpa", "perdao", "foi mal")) {
            return new AiReply("Tudo bem. Só tente não fazer isso de novo.", MobAction.LOOK, "cauteloso");
        }
        if (contains(text, "voce gosta", "do que voce gosta", "o que voce quer", "qual sua comida")) {
            return new AiReply(preferenceFor(type), MobAction.NONE, "animado");
        }
        if (contains(text, "ataque", "inimigo", "perigo", "monstro", "zumbi")) {
            return new AiReply("Percebi que este mundo pode ficar perigoso. Fique atento e não se afaste muito.", MobAction.PROTECT, "alerta");
        }
        if (contains(text, "como voce esta", "como vai", "tudo certo")) {
            return new AiReply("Estou bem. O lugar está " + (mob.level().isDay() ? "claro" : "escuro") + " e continuo de olho no que acontece.", MobAction.LOOK, "tranquilo");
        }
        if (!history.isEmpty() && ThreadLocalRandom.current().nextBoolean()) {
            return new AiReply("Você já me contou algumas coisas antes. Ainda estou pensando sobre isso. O que mais aconteceu?", MobAction.LOOK, "reflexivo");
        }
        if (cognition != null && cognition.speechConfidence() >= 0.34F) {
            AiReply learnedReply = learnedSpeech(cognition.speechAct(), type);
            if (learnedReply != null) {
                return learnedReply;
            }
        }
        return pick("Não sei muito sobre isso, mas quero entender. Pode explicar de outro jeito?",
                "Interessante. Nunca tinha pensado nisso dessa maneira.",
                "Estou ouvindo, mas ainda não tenho certeza do que responder.");
    }

    private static AiReply actionReply(ActionRequest request, String player, String type) {
        MobAction action = request.action();
        return switch (action) {
            case FOLLOW -> new AiReply("Certo, " + player + ". Vou acompanhar você.", action, "companheiro");
            case APPROACH -> new AiReply("Vou chegar mais perto para ouvir melhor.", action, "curioso");
            case FLEE -> new AiReply("Tudo bem. Vou manter distância.", action, "cauteloso");
            case LOOK -> new AiReply("Estou olhando para você.", action, "atento");
            case SIT -> new AiReply("Vou descansar um pouco.", action, "calmo");
            case JUMP -> new AiReply("Olha só! Lá vou eu!", action, "animado");
            case STOP -> new AiReply("Vou esperar aqui.", action, "obediente");
            case PROTECT -> new AiReply("Fique perto. Vou prestar atenção nos perigos ao redor.", action, "protetor");
            case PICKUP_ITEM -> new AiReply("Vou tentar pegar o item mais próximo.", action, "concentrado");
            case DROP_ITEM -> new AiReply("Vou soltar o que estou segurando.", action, "calmo");
            case SPAWN_MOB -> request.argument().isBlank()
                    ? new AiReply("Preciso do identificador do mob, como minecraft:zombie ou modid:criatura.", MobAction.NONE, "confuso")
                    : new AiReply("Vou tentar chamar essa criatura para perto.", action, "animado", request.argument());
            default -> new AiReply("Sou um " + type + ". Estou ouvindo você.", MobAction.NONE, "neutro");
        };
    }


    private static MobAction learnedAction(int label) {
        return switch (label) {
            case 1 -> MobAction.FOLLOW;
            case 2 -> MobAction.APPROACH;
            case 3 -> MobAction.FLEE;
            case 4 -> MobAction.LOOK;
            case 5 -> MobAction.SIT;
            case 6 -> MobAction.JUMP;
            case 7 -> MobAction.STOP;
            case 8 -> MobAction.PROTECT;
            case 9 -> MobAction.PICKUP_ITEM;
            case 10 -> MobAction.DROP_ITEM;
            default -> MobAction.NONE;
        };
    }

    private static AiReply learnedSpeech(int label, String type) {
        return switch (label) {
            case 7 -> new AiReply("Posso tentar ajudar. Conte o que está acontecendo.", MobAction.LOOK, "prestativo");
            case 8 -> new AiReply("Estou percebendo algo estranho. É melhor ficar atento.", MobAction.LOOK, "alerta");
            case 10 -> new AiReply(preferenceFor(type.replace("minecraft:", "")), MobAction.NONE, "animado");
            case 11 -> new AiReply("Tenho algumas lembranças deste lugar, mas ainda estou organizando o que sei.", MobAction.LOOK, "reflexivo");
            case 12 -> new AiReply("Concordo com você. Faz sentido.", MobAction.LOOK, "grato");
            case 13 -> new AiReply("Não tenho certeza de que seja assim. Minha experiência foi diferente.", MobAction.LOOK, "pensativo");
            case 14 -> new AiReply("Isso despertou minha curiosidade. Pode me contar mais?", MobAction.LOOK, "curioso");
            case 15 -> new AiReply("Não se preocupe. Podemos lidar com isso juntos.", MobAction.LOOK, "acolhedor");
            default -> null;
        };
    }

    private static String preferenceFor(String type) {
        return switch (type.toLowerCase(Locale.ROOT)) {
            case "cow", "mooshroom" -> "Gosto de lugares tranquilos, grama fresca e de ficar perto do meu grupo.";
            case "wolf" -> "Gosto de companhia, exploração e de pessoas em quem posso confiar.";
            case "cat" -> "Gosto de sossego, peixe e de escolher quando quero companhia.";
            case "pig" -> "Comida é sempre uma boa ideia. Também gosto de explorar sem pressa.";
            case "sheep" -> "Prefiro campos abertos, grama e lugares onde não apareçam predadores.";
            case "villager" -> "Gosto de uma vila movimentada, bons negócios e noites tranquilas.";
            case "creeper" -> "Prefiro que não cheguem muito perto. Gosto de observar de longe.";
            case "enderman" -> "Gosto de lugares escuros e de manter meu espaço.";
            default -> "Gosto de explorar o mundo e descobrir coisas novas, desde que não seja perigoso.";
        };
    }

    private static AiReply pick(String... replies) {
        return new AiReply(replies[ThreadLocalRandom.current().nextInt(replies.length)], MobAction.NONE, "curioso");
    }

    private static boolean contains(String source, String... terms) {
        String padded = " " + source + " ";
        for (String term : terms) {
            if (padded.contains(" " + IntentInterpreter.normalize(term) + " ")) {
                return true;
            }
        }
        return false;
    }
}
