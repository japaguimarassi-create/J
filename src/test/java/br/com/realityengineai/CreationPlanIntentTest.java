package br.com.realityengineai;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class CreationPlanIntentTest {
    @Test
    public void separatesObjectTypesFromTerrainAndBuildings() {
        expect("item","sword","crie uma espada de pedra");
        expect("block","generic","crie um bloco de pedra");
        expect("structure","generic","crie uma construção de pedra");
        expect("terrain","plain","crie um terreno de pedra");
        expect("map","procedural","crie um mapa do zero raio 24");
        expect("dimension","desert","crie uma dimensão de deserto");
        expect("terrain","desert","crie terreno desértico raio 12");
        expect("terrain","mountain","crie terreno montanhoso");
        expect("structure","castle","crie um castelo de pedra");
        expect("block","machine","crie um bloco de máquina");
        expect("block","corrupted","crie um bloco corrompido");
        expect("item","staff","crie um cajado mágico");
        expect("item","amulet","crie um amuleto de proteção");
        expect("item","dagger","crie uma adaga de cristal");
        expect("entity","dragon","crie uma entidade dragão");
    }

    @Test
    public void distinctPlansAreValidCreations() {
        CreationPlan terrain=CreationPlan.resolve("crie terreno montanhoso");
        CreationPlan house=CreationPlan.resolve("crie uma casa de pedra");
        assertTrue(terrain.isCreation());
        assertTrue(house.isCreation());
        assertEquals(CreationPlan.TERRAIN,terrain.kind);
        assertEquals(CreationPlan.STRUCTURE,house.kind);
    }

    @Test
    public void unclearRequestsRemainAmbiguous() {
        assertEquals(CreationPlan.AMBIGUOUS,CreationPlan.resolve("crie algo incrível").kind);
    }

    private static void expect(String kind,String archetype,String prompt) {
        CreationPlan plan=CreationPlan.resolve(prompt);
        assertEquals(prompt+" kind",kind,plan.kind);
        assertEquals(prompt+" archetype",archetype,plan.archetype);
    }
}
