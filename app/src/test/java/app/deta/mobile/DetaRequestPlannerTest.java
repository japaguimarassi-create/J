package app.deta.mobile;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class DetaRequestPlannerTest {
    @Test
    public void greetingIsConversationAndNeverProjectCreation() {
        assertEquals(DetaRequestPlanner.Route.CONVERSATION, DetaRequestPlanner.analyze("Olá").route);
        assertEquals(DetaRequestPlanner.Route.CONVERSATION, DetaRequestPlanner.analyze("Bom dia!").route);
        assertEquals(DetaRequestPlanner.Route.CONVERSATION, DetaRequestPlanner.analyze("Tudo bem?").route);
    }

    @Test
    public void explicitCreationRequestIsPlannedBeforeFiles() {
        DetaRequestPlanner.Plan plan = DetaRequestPlanner.analyze(
                "Crie um jogo chamado Neon Arena com recorde e cronômetro."
        );
        assertEquals(DetaRequestPlanner.Route.CREATE_PROJECT, plan.route);
        assertEquals(DetaRequestPlanner.Kind.GAME, plan.kind);
        assertEquals("Neon Arena", plan.title);
        assertTrue(plan.features.size() >= 3);
        assertTrue(plan.steps.size() >= 4);
        assertTrue(plan.render().indexOf("PLANO DE IMPLEMENTAÇÃO") == 0);
    }

    @Test
    public void researchIntentIsNotMistakenForProjectCreation() {
        DetaRequestPlanner.Plan plan = DetaRequestPlanner.analyze("Pesquise na web sobre Android Gradle.");
        assertEquals(DetaRequestPlanner.Route.WEB_SEARCH, plan.route);
    }

    @Test
    public void requestedRemoteInfrastructureIsDeclaredAsLimitation() {
        DetaRequestPlanner.Plan plan = DetaRequestPlanner.analyze(
                "Crie uma rede social com login e sincronização na nuvem."
        );
        assertEquals(DetaRequestPlanner.Route.CREATE_PROJECT, plan.route);
        assertTrue(plan.limitations.size() > 0);
    }

    @Test
    public void appCommandInPortugueseDoesNotNeedTheExactWordCrie() {
        assertEquals(DetaRequestPlanner.Route.CREATE_PROJECT,
                DetaRequestPlanner.analyze("Faz um app de tarefas chamado Minha Rotina.").route);
    }
}
