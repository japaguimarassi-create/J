package dev.japaguimarassi.nexusoptimizer;

import net.minecraft.client.CloudStatus;
import net.minecraft.client.Minecraft;
import net.minecraft.client.ParticleStatus;
import net.minecraft.network.chat.Component;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod(NexusOptimizer.MOD_ID)
public final class NexusOptimizer {
    public static final String MOD_ID = "nexusoptimizer";

    public NexusOptimizer() {
    }

    @Mod.EventBusSubscriber(modid = MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
    public static final class AdaptiveOptimizer {
        private static final int SAMPLE_TICKS = 20;
        private static final int EVALUATION_TICKS = 100;
        private static final String[] PROFILE_NAMES = {
            "Original", "Leve", "Desempenho", "Desempenho máximo"
        };

        private static int ticks;
        private static int activeTier;
        private static int lowWindows;
        private static int recoveryWindows;
        private static double smoothedFps = 60.0D;
        private static double memoryPressure;
        private static boolean hasFpsSample;
        private static Baseline baseline;

        private AdaptiveOptimizer() {
        }

        @SubscribeEvent
        public static void onClientTick(TickEvent.ClientTickEvent event) {
            if (event.phase != TickEvent.Phase.END) {
                return;
            }

            Minecraft minecraft = Minecraft.getInstance();

            if (minecraft.level == null || minecraft.player == null) {
                leaveWorld(minecraft);
                return;
            }

            if (baseline == null) {
                baseline = new Baseline(minecraft);
                ticks = 0;
                activeTier = 0;
                lowWindows = 0;
                recoveryWindows = 0;
                smoothedFps = Math.max(1, minecraft.getFps());
                hasFpsSample = true;
            }

            ticks++;

            if (ticks % SAMPLE_TICKS == 0) {
                sample(minecraft);
            }

            if (ticks % EVALUATION_TICKS == 0) {
                evaluate(minecraft);
            }
        }

        private static void sample(Minecraft minecraft) {
            double fps = Math.max(1, minecraft.getFps());
            smoothedFps = hasFpsSample ? (smoothedFps * 0.70D) + (fps * 0.30D) : fps;
            hasFpsSample = true;

            Runtime runtime = Runtime.getRuntime();
            long maxMemory = Math.max(1L, runtime.maxMemory());
            long usedMemory = runtime.totalMemory() - runtime.freeMemory();
            memoryPressure = Math.min(1.0D, (double) usedMemory / (double) maxMemory);
        }

        private static void evaluate(Minecraft minecraft) {
            int suggestedTier = activeTier;

            if (smoothedFps < 20.0D || memoryPressure >= 0.92D) {
                suggestedTier = 3;
            } else if (smoothedFps < 30.0D || memoryPressure >= 0.86D) {
                suggestedTier = 2;
            } else if (smoothedFps < 44.0D || memoryPressure >= 0.78D) {
                suggestedTier = 1;
            } else if (smoothedFps >= 56.0D && memoryPressure < 0.72D) {
                suggestedTier = 0;
            }

            if (suggestedTier > activeTier) {
                lowWindows++;
                recoveryWindows = 0;
                int requiredWindows = suggestedTier == 3 ? 2 : 3;
                if (lowWindows >= requiredWindows) {
                    applyTier(minecraft, suggestedTier);
                }
            } else if (suggestedTier < activeTier) {
                recoveryWindows++;
                lowWindows = 0;
                if (recoveryWindows >= 6) {
                    applyTier(minecraft, suggestedTier);
                }
            } else {
                lowWindows = 0;
                recoveryWindows = 0;
            }
        }

        private static void applyTier(Minecraft minecraft, int newTier) {
            if (baseline == null || minecraft.options == null || newTier == activeTier) {
                return;
            }

            var options = minecraft.options;

            if (newTier == 0) {
                baseline.restore(options);
            } else {
                ParticleStatus particleTarget =
                    newTier == 1 && baseline.particles == ParticleStatus.ALL
                        ? ParticleStatus.DECREASED
                        : ParticleStatus.MINIMAL;

                options.particles().set(particleTarget);
                options.cloudStatus().set(CloudStatus.OFF);
                options.entityDistanceScaling().set(Math.min(
                    baseline.entityDistanceScaling,
                    newTier == 1 ? 0.80D : newTier == 2 ? 0.60D : 0.35D
                ));

                if (newTier >= 2) {
                    options.renderDistance().set(Math.min(
                        baseline.renderDistance, newTier == 2 ? 8 : 6
                    ));
                    options.simulationDistance().set(Math.min(
                        baseline.simulationDistance, newTier == 2 ? 6 : 4
                    ));
                } else {
                    options.renderDistance().set(baseline.renderDistance);
                    options.simulationDistance().set(baseline.simulationDistance);
                }

                options.entityShadows().set(newTier >= 3 ? false : baseline.entityShadows);
            }

            activeTier = newTier;
            lowWindows = 0;
            recoveryWindows = 0;
            minecraft.player.displayClientMessage(
                Component.literal("[Nexus Optimizer AI] Perfil: " + PROFILE_NAMES[newTier]
                    + " | FPS médios: " + Math.round(smoothedFps)
                    + " | Memória Java: " + Math.round(memoryPressure * 100.0D) + "%"),
                true
            );
        }

        private static void leaveWorld(Minecraft minecraft) {
            if (baseline != null) {
                if (activeTier != 0 && minecraft.options != null) {
                    baseline.restore(minecraft.options);
                }
                baseline = null;
            }
            ticks = 0;
            activeTier = 0;
            lowWindows = 0;
            recoveryWindows = 0;
            smoothedFps = 60.0D;
            memoryPressure = 0.0D;
            hasFpsSample = false;
        }

        private static final class Baseline {
            private final int renderDistance;
            private final int simulationDistance;
            private final ParticleStatus particles;
            private final CloudStatus clouds;
            private final double entityDistanceScaling;
            private final boolean entityShadows;

            private Baseline(Minecraft minecraft) {
                var options = minecraft.options;
                renderDistance = options.renderDistance().get();
                simulationDistance = options.simulationDistance().get();
                particles = options.particles().get();
                clouds = options.cloudStatus().get();
                entityDistanceScaling = options.entityDistanceScaling().get();
                entityShadows = options.entityShadows().get();
            }

            private void restore(net.minecraft.client.Options options) {
                options.renderDistance().set(renderDistance);
                options.simulationDistance().set(simulationDistance);
                options.particles().set(particles);
                options.cloudStatus().set(clouds);
                options.entityDistanceScaling().set(entityDistanceScaling);
                options.entityShadows().set(entityShadows);
            }
        }
    }
}
