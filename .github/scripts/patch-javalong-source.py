from pathlib import Path

project = Path("JavaLong-Convergence")
root = project / "src/main/java/com/japaguimarassi/jldualfusion"

build = project / "build.gradle"
text = build.read_text()
text = text.replace("version = '1.7.10-10.13.4.1614'", "version = '1.7.10-10.13.4.1614-1.7.10'")
text = text.replace("version = '0.1.0-alpha'", "version = '0.1.1-alpha'")
if "version = '1.7.10-10.13.4.1614-1.7.10'" not in text:
    raise SystemExit("ForgeGradle version patch did not apply")
build.write_text(text)

main_class = root / "JavaLongConvergence.java"
text = main_class.read_text()
text = text.replace('VERSION = "0.1.0-alpha"', 'VERSION = "0.1.1-alpha"')
main_class.write_text(text)

readme = project / "README.md"
if readme.exists():
    readme.write_text(readme.read_text().replace("0.1.0-alpha", "0.1.1-alpha"))

command = root / "command/CommandFusion.java"
text = command.read_text()
replacements = {
    "sender.getCommandSenderEntity() instanceof EntityPlayer": "sender instanceof EntityPlayer",
    "(EntityPlayer) sender.getCommandSenderEntity()": "(EntityPlayer) sender",
    "getPlayerForUsername(args[1])": "func_152612_a(args[1])",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit("Expected CommandFusion source fragment missing: " + old)
    text = text.replace(old, new)
command.write_text(text)

race_probe = root / "fusion/RaceProbe.java"
text = race_probe.read_text()
old = "for (String key : data.func_150296_c()) {"
new = "for (Object rawKey : data.func_150296_c()) {\n            String key = (String) rawKey;"
if text.count(old) != 2:
    raise SystemExit("Expected two raw NBT key loops in RaceProbe")
text = text.replace(old, new)
old = """        if (entity instanceof EntityPlayer) {
            DualLong jrmScore = readJrmPlayerStats((EntityPlayer) entity);
            if (!jrmScore.isZero()) {
                return jrmScore;
            }
        }
        DualLong savedPower = readPower(savedData);"""
new = """        if (entity instanceof EntityPlayer) {
            DualLong nativeJrmPower = readJrmPlayerPower((EntityPlayer) entity);
            if (!nativeJrmPower.isZero()) {
                return nativeJrmPower;
            }
        }
        DualLong savedPower = readPower(savedData);"""
if old not in text:
    raise SystemExit("JRM score priority source block missing")
text = text.replace(old, new)
old = """        DualLong customPower = readPower(customData);
        if (!customPower.isZero()) {
            return customPower;
        }
        BigInteger statTotal = BigInteger.ZERO;"""
new = """        DualLong customPower = readPower(customData);
        if (!customPower.isZero()) {
            return customPower;
        }
        if (entity instanceof EntityPlayer) {
            DualLong jrmStatEstimate = readJrmPlayerStats((EntityPlayer) entity);
            if (!jrmStatEstimate.isZero()) {
                return jrmStatEstimate;
            }
        }
        BigInteger statTotal = BigInteger.ZERO;"""
if old not in text:
    raise SystemExit("JRM stat estimate source block missing")
text = text.replace(old, new)
anchor = "    private static DualLong readJrmPlayerStats(EntityPlayer player) {"
method = """    private static DualLong readJrmPlayerPower(EntityPlayer player) {
        Number power = invokeJrmCoreNumber(player, "getInt", "jrmcPL");
        if (power == null || power.longValue() <= 0L) {
            power = invokeJrmCoreNumber(player, "getInt", "jrmcPwr");
        }
        if (power == null || power.longValue() <= 0L) {
            return DualLong.ZERO;
        }
        return DualLong.fromUnsignedLong(power.longValue());
    }

"""
if anchor not in text:
    raise SystemExit("readJrmPlayerStats method anchor missing")
text = text.replace(anchor, method + anchor)
race_probe.write_text(text)

fusion = root / "fusion/FusionService.java"
text = fusion.read_text()
old = """        String donorName = donor.getCommandSenderName();
        String customName = donor.getCustomNameTag();
        if (customName != null && !customName.trim().isEmpty()) {
            donorName = customName;
        }
"""
if old not in text:
    raise SystemExit("Legacy custom-name source block missing")
fusion.write_text(text.replace(old, "        String donorName = donor.getCommandSenderName();\n"))

print("Patched Minecraft 1.7.10 APIs, release version, and JRMCore score priority.")
