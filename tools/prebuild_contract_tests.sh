#!/usr/bin/env bash
set -euo pipefail
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
STUB="$WORK/stubs/br/com/realityengineai"
mkdir -p "$STUB"
cat > "$STUB/OfflineBrain.java" <<'JAVA'
package br.com.realityengineai;
public final class OfflineBrain {
    public Prediction predictDetailed(String input) { return new Prediction("ambiguous", 0.0F); }
    public static final class Prediction {
        public final String label;
        public final float confidence;
        public Prediction(String label, float confidence) { this.label = label; this.confidence = confidence; }
    }
}
JAVA
cat > "$STUB/RealityEngineAI.java" <<'JAVA'
package br.com.realityengineai;
public final class RealityEngineAI {
    public static OfflineBrain BRAIN;
}
JAVA
javac -source 8 -target 8 -sourcepath "$WORK/stubs" -d "$WORK" "$STUB/OfflineBrain.java" "$STUB/RealityEngineAI.java" src/main/java/br/com/realityengineai/CreationPlan.java src/test/java/br/com/realityengineai/CreationPlanContractTest.java
java -cp "$WORK" br.com.realityengineai.CreationPlanContractTest
