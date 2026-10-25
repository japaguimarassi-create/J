#!/usr/bin/env bash
set -euo pipefail
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
javac -source 8 -target 8 -d "$WORK" src/main/java/br/com/realityengineai/CreationPlan.java src/test/java/br/com/realityengineai/CreationPlanContractTest.java
java -cp "$WORK" br.com.realityengineai.CreationPlanContractTest
