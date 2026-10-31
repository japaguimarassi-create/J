package io.github.japaguimarassi.voxmobs.speech;

import net.minecraftforge.fml.loading.FMLPaths;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import java.util.concurrent.CompletableFuture;

public final class SpeechModelManager {
    private SpeechModelManager() {
    }

    public static Path modelDirectory() {
        return FMLPaths.CONFIGDIR.get().resolve("voxmobs").resolve("models").resolve("pt-br-small");
    }

    public static Path nativeDirectory() {
        return FMLPaths.CONFIGDIR.get().resolve("voxmobs").resolve("native").resolve(platformFolder());
    }

    public static boolean isInstalled() {
        try {
            return Files.isRegularFile(modelDirectory().resolve("am").resolve("final.mdl"))
                    && Files.isRegularFile(nativeDirectory().resolve(nativeLibraryName()));
        } catch (RuntimeException exception) {
            return false;
        }
    }

    public static CompletableFuture<Path> ensurePortugueseModel() {
        if (!isInstalled()) {
            return CompletableFuture.failedFuture(new IllegalStateException(
                    "A instalação de voz é totalmente local. Copie o modelo Vosk pt-BR para "
                            + modelDirectory() + " e a biblioteca nativa para " + nativeDirectory()
                            + ". Consulte VOICE_INSTALL.md. Nenhum download automático ou chamada de API será feito."));
        }
        System.setProperty("jna.library.path", nativeDirectory().toAbsolutePath().toString());
        return CompletableFuture.completedFuture(modelDirectory());
    }

    private static String platformFolder() {
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        String arch = System.getProperty("os.arch", "").toLowerCase(Locale.ROOT);
        if (os.contains("win") && (arch.equals("amd64") || arch.equals("x86_64"))) {
            return "windows-x64";
        }
        if (os.contains("linux") && (arch.equals("amd64") || arch.equals("x86_64"))) {
            return "linux-x64";
        }
        if (os.contains("linux") && (arch.equals("aarch64") || arch.equals("arm64"))) {
            return "linux-arm64";
        }
        throw new IllegalStateException("plataforma não suportada pelo Vosk: " + os + " / " + arch);
    }

    private static String nativeLibraryName() {
        return platformFolder().startsWith("windows") ? "libvosk.dll" : "libvosk.so";
    }
}
