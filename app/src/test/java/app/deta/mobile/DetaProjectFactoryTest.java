package app.deta.mobile;

import org.junit.Test;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

public final class DetaProjectFactoryTest {
    @Test
    public void gameRequestProducesRunnableProjectArchive() throws Exception {
        DetaProjectFactory.Project project = DetaProjectFactory.create(
                "Crie um jogo chamado Neon Arena com pontuação, recorde e rodada de 30 segundos."
        );
        assertEquals("game", project.kind);
        assertEquals("Neon Arena", project.title);
        assertTrue(project.files.get("app.js").contains("pointerdown"));
        assertTrue(project.files.get("index.html").contains("Neon Arena"));
        assertEquals(
                List.of("index.html", "style.css", "app.js", "README.md", "project.json"),
                zipNames(project.zip)
        );
    }

    @Test
    public void socialRequestCreatesPostSearchAndCommentFeatures() throws Exception {
        DetaProjectFactory.Project project = DetaProjectFactory.create(
                "Crie uma rede social chamada Comunidade Deta com publicações e comentários."
        );
        assertEquals("social", project.kind);
        assertTrue(project.files.get("app.js").contains("localStorage"));
        assertTrue(project.files.get("app.js").contains("Comentar"));
        assertTrue(project.files.get("index.html").contains("Buscar publicações"));
    }

    @Test
    public void utilityRequestCreatesPersistentChecklist() throws Exception {
        DetaProjectFactory.Project project = DetaProjectFactory.create(
                "Crie um app de tarefas chamado Minha Rotina."
        );
        assertEquals("utility", project.kind);
        assertTrue(project.files.get("app.js").contains("localStorage"));
        assertTrue(project.files.get("app.js").contains("task.done"));
        assertTrue(project.files.get("app.js").contains("Excluir"));
    }

    @Test
    public void promptMarkupIsEscapedBeforePreview() throws Exception {
        DetaProjectFactory.Project project = DetaProjectFactory.create(
                "Crie um app com anotações <script>alert(1)</script> e lista de tarefas."
        );
        assertFalse(project.previewHtml().contains("<script>alert(1)</script>"));
        assertTrue(project.previewHtml().contains("&lt;script&gt;"));
    }

    @Test
    public void previewHasInlineCssAndJavaScript() throws Exception {
        DetaProjectFactory.Project project = DetaProjectFactory.create("Crie um jogo simples.");
        assertTrue(project.previewHtml().contains("<style>"));
        assertTrue(project.previewHtml().contains("<script>"));
        assertFalse(project.previewHtml().contains("src=\"app.js\""));
    }

    @Test
    public void blankPromptIsRejected() throws Exception {
        try {
            DetaProjectFactory.create("   ");
            throw new AssertionError("Empty request must be rejected.");
        } catch (IllegalArgumentException expected) {
            assertNotNull(expected.getMessage());
        }
    }

    private static List<String> zipNames(byte[] archive) throws IOException {
        List<String> names = new ArrayList<>();
        try (ZipInputStream input = new ZipInputStream(new ByteArrayInputStream(archive), StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = input.getNextEntry()) != null) {
                names.add(entry.getName());
                input.closeEntry();
            }
        }
        return names;
    }
}
