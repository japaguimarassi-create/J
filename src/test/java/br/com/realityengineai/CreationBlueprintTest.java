package br.com.realityengineai;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public final class CreationBlueprintTest {
    @Test
    public void separatesTheRequestedItemFromItsAbilities() {
        String prompt = "crie uma espada de gelo que congela inimigos e cura o jogador";
        CreationBlueprint blueprint = CreationBlueprint.parse(prompt);
        assertEquals("Espada de gelo", blueprint.objectName);
        assertEquals(CreationPlan.ITEM, blueprint.kind);
        assertEquals("sword", blueprint.archetype);
        assertTrue(blueprint.hasEffect("freeze_attack"));
        assertTrue(blueprint.hasEffect("heal"));
        assertTrue(blueprint.purpose.contains("congela"));
    }

    @Test
    public void preservesCompleteRequestAndExtractsMultipleEffects() {
        String prompt = "crie um amuleto de proteção que cura o jogador e aumenta a velocidade";
        CreationBlueprint blueprint = CreationBlueprint.parse(prompt);
        assertEquals(prompt, blueprint.fullPrompt);
        assertEquals("Amuleto de proteção", blueprint.objectName);
        assertTrue(blueprint.hasEffect("heal"));
        assertTrue(blueprint.hasEffect("resistance"));
        assertTrue(blueprint.hasEffect("speed"));
        assertTrue(blueprint.purpose.contains("cura"));
    }

    @Test
    public void keepsMaterialAndCombatEffectsSeparate() {
        CreationBlueprint blueprint = CreationBlueprint.parse("crie uma adaga de obsidiana que envenena inimigos");
        assertEquals("Adaga de obsidiana", blueprint.objectName);
        assertEquals("obsidian", blueprint.material);
        assertTrue(blueprint.hasEffect("poison_attack"));
        assertFalse(blueprint.hasEffect("heal"));
    }

    @Test
    public void doesNotInventAnAbilityWhenThePromptDoesNotSpecifyOne() {
        CreationBlueprint blueprint = CreationBlueprint.parse("crie uma espada de pedra");
        assertEquals("Espada de pedra", blueprint.objectName);
        assertTrue(blueprint.getEffects().isEmpty());
        assertEquals("stone", blueprint.material);
    }
}
