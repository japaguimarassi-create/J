package io.github.japaguimarassi.voxmobs.client;

import io.github.japaguimarassi.voxmobs.config.VoxMobsConfig;
import io.github.japaguimarassi.voxmobs.network.MobMessagePacket;
import io.github.japaguimarassi.voxmobs.network.NetworkHandler;
import io.github.japaguimarassi.voxmobs.speech.SpeechModelManager;
import io.github.japaguimarassi.voxmobs.speech.VoskRecognizerService;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.lwjgl.glfw.GLFW;

public final class ClientVoiceController {
    private static final KeyMapping TALK_KEY = new KeyMapping("key.voxmobs.talk", GLFW.GLFW_KEY_J, "key.categories.voxmobs");
    private static MicrophoneCapture capture;
    private static int targetEntityId = -1;
    private static long startedAt;
    private static boolean recording;
    private static boolean keyWasDown;

    private ClientVoiceController() {
    }

    public static void registerKeys(RegisterKeyMappingsEvent event) {
        event.register(TALK_KEY);
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        boolean canRecord = minecraft.player != null && minecraft.level != null && minecraft.screen == null
                && VoxMobsConfig.CLIENT_VALUES.microphoneEnabled.get();
        boolean keyDown = canRecord && TALK_KEY.isDown();
        if (keyDown && !keyWasDown) {
            begin(minecraft);
        } else if (!keyDown && keyWasDown) {
            finish(minecraft);
        }
        keyWasDown = keyDown;
        if (recording && System.currentTimeMillis() - startedAt
                > VoxMobsConfig.CLIENT_VALUES.maxRecordingSeconds.get() * 1000L) {
            finish(minecraft);
        }
    }

    private static void begin(Minecraft minecraft) {
        if (!(minecraft.hitResult instanceof EntityHitResult hit) || !(hit.getEntity() instanceof Mob mob)) {
            minecraft.player.displayClientMessage(Component.literal("VoxMobs: mire para um mob antes de segurar J."), true);
            return;
        }
        try {
            capture = new MicrophoneCapture();
            capture.start();
            targetEntityId = mob.getId();
            startedAt = System.currentTimeMillis();
            recording = true;
            minecraft.player.displayClientMessage(Component.literal("VoxMobs: ouvindo... solte J para enviar."), true);
        } catch (Exception exception) {
            capture = null;
            targetEntityId = -1;
            recording = false;
            minecraft.player.displayClientMessage(Component.literal("VoxMobs: não foi possível abrir o microfone. Verifique o dispositivo e a permissão."), true);
        }
    }

    private static void finish(Minecraft minecraft) {
        recording = false;
        int entityId = targetEntityId;
        targetEntityId = -1;
        MicrophoneCapture current = capture;
        capture = null;
        if (current == null || entityId < 0) {
            return;
        }
        byte[] audio = current.stopAs16kMono();
        if (audio.length < 1600) {
            if (minecraft.player != null) {
                minecraft.player.displayClientMessage(Component.literal("VoxMobs: não detectei áudio suficiente."), true);
            }
            return;
        }
        if (minecraft.player != null) {
            minecraft.player.displayClientMessage(Component.literal("VoxMobs: reconhecendo fala localmente..."), true);
        }
        SpeechModelManager.ensurePortugueseModel().thenApplyAsync(path -> {
            try {
                return VoskRecognizerService.transcribe(audio);
            } catch (Exception exception) {
                throw new IllegalStateException(exception);
            }
        }).whenComplete((text, error) -> minecraft.execute(() -> {
            if (minecraft.player == null) {
                return;
            }
            if (error != null) {
                minecraft.player.displayClientMessage(Component.literal("VoxMobs: falha no reconhecimento offline. " + rootMessage(error)), true);
                return;
            }
            if (text == null || text.isBlank()) {
                minecraft.player.displayClientMessage(Component.literal("VoxMobs: não consegui entender. Tente falar mais perto do microfone."), true);
                return;
            }
            if (VoxMobsConfig.CLIENT_VALUES.showRecognizedText.get()) {
                minecraft.player.displayClientMessage(Component.literal("Você disse: " + text), false);
            }
            NetworkHandler.sendToServer(new MobMessagePacket(entityId, text));
        }));
    }

    private static String rootMessage(Throwable error) {
        Throwable current = error;
        while (current.getCause() != null) {
            current = current.getCause();
        }
        String message = current.getMessage();
        return message == null ? "erro desconhecido" : message;
    }
}
