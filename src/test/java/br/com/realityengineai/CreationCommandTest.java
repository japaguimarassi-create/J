package br.com.realityengineai;

import org.junit.Test;
import static org.junit.Assert.*;

public final class CreationCommandTest {
    @Test
    public void acceptsCommandAtStartCaseInsensitively() {
        CreationCommand.ParseResult result = CreationCommand.parse("CrIe um dragão");
        assertTrue(result.isTriggered());
        assertTrue(result.hasPrompt());
        assertEquals("um dragão", result.getPrompt());
    }

    @Test
    public void acceptsLeadingAndRepeatedWhitespace() {
        CreationCommand.ParseResult result = CreationCommand.parse("  crie   uma espada  ");
        assertTrue(result.isTriggered());
        assertEquals("uma espada", result.getPrompt());
    }

    @Test
    public void triggersWithoutPromptButDoesNotCreate() {
        CreationCommand.ParseResult result = CreationCommand.parse("crie");
        assertTrue(result.isTriggered());
        assertFalse(result.hasPrompt());
    }

    @Test
    public void ignoresCommandNotAtStart() {
        assertFalse(CreationCommand.parse("quero crie um dragão").isTriggered());
    }

    @Test
    public void ignoresSlashCommand() {
        assertFalse(CreationCommand.parse("/crie um dragão").isTriggered());
    }

    @Test
    public void ignoresWordsThatOnlyStartWithCrie() {
        assertFalse(CreationCommand.parse("crielobo").isTriggered());
        assertFalse(CreationCommand.parse("crie, um dragão").isTriggered());
    }

    @Test
    public void ignoresNullAndBlankMessages() {
        assertFalse(CreationCommand.parse(null).isTriggered());
        assertFalse(CreationCommand.parse("   ").isTriggered());
    }
}
