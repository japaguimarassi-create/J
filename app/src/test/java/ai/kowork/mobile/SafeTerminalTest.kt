package ai.kowork.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class SafeTerminalTest {
    @Test
    fun unknownCommandsAreBlocked() {
        assertTrue(safeTerminalCommand("rm -rf /").contains("bloqueado"))
    }

    @Test
    fun helpListsAllowedCommands() {
        assertTrue(safeTerminalCommand("help").contains("status"))
    }

    @Test
    fun statusDoesNotClaimModelIsConnected() {
        assertTrue(safeTerminalCommand("status").contains("não conectado"))
    }
}
