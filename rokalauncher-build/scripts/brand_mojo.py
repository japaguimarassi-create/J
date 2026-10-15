import re
import shutil
import sys
from pathlib import Path

APP_ID = "com.rokalauncher.app"


def replace_required(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text and old not in text:
        return
    if old not in text:
        raise SystemExit(f"Expected {label} in {path}, but it was not found; upstream layout may have changed.")
    path.write_text(text.replace(old, new), encoding="utf-8")


def write_icon(res: Path) -> None:
    (res / "drawable").mkdir(parents=True, exist_ok=True)
    (res / "values").mkdir(parents=True, exist_ok=True)
    adaptive = res / "mipmap-anydpi-v26"
    adaptive.mkdir(parents=True, exist_ok=True)
    (res / "values" / "rokalauncher_colors.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="rokalauncher_icon_background">#101611</color>\n</resources>\n',
        encoding="utf-8",
    )
    (res / "drawable" / "rokalauncher_icon_foreground.xml").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#86D878" android:pathData="M54,16 L88,35 L54,54 L20,35 Z" />
    <path android:fillColor="#438D49" android:pathData="M20,35 L54,54 L54,92 L20,73 Z" />
    <path android:fillColor="#286039" android:pathData="M54,54 L88,35 L88,73 L54,92 Z" />
    <path android:fillColor="#F1F6EE" android:pathData="M41,38 L41,70 L48,70 L48,58 L59,70 L68,70 L55,54 L67,40 L58,40 L48,51 L48,38 Z" />
</vector>
""",
        encoding="utf-8",
    )
    icon = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/rokalauncher_icon_background" />
    <foreground android:drawable="@drawable/rokalauncher_icon_foreground" />
</adaptive-icon>
"""
    (adaptive / "ic_launcher.xml").write_text(icon, encoding="utf-8")
    (adaptive / "ic_launcher_round.xml").write_text(icon, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: brand_mojo.py /path/to/MojoLauncher")
    root = Path(sys.argv[1]).resolve()
    app = root / "app_mojo"
    gradle = app / "build.gradle"
    manifest = app / "src" / "main" / "AndroidManifest.xml"
    resources = app / "src" / "main" / "res"
    if not gradle.is_file() or not manifest.is_file() or not resources.is_dir():
        raise SystemExit("The upstream checkout does not match the expected MojoLauncher layout.")

    replace_required(gradle, 'applicationId "git.artdeell.mjlaunch"', f'applicationId "{APP_ID}"', "application ID")
    replace_required(gradle, "resValue 'string', 'storageProviderAuthorities', 'git.artdeell.mjlaunch.scoped.gamefolder.debug'", f"resValue 'string', 'storageProviderAuthorities', '{APP_ID}.scoped.gamefolder.debug'", "debug storage authority")
    replace_required(gradle, "resValue 'string', 'application_package', 'git.artdeell.mjlaunch.debug'", f"resValue 'string', 'application_package', '{APP_ID}.debug'", "debug application package")
    replace_required(gradle, "resValue 'string', 'storageProviderAuthorities', 'git.artdeell.mjlaunch.scoped.gamefolder'", f"resValue 'string', 'storageProviderAuthorities', '{APP_ID}.scoped.gamefolder'", "release storage authority")
    replace_required(gradle, "resValue 'string', 'application_package', 'git.artdeell.mjlaunch'", f"resValue 'string', 'application_package', '{APP_ID}'", "release application package")

    gradle_text = gradle.read_text(encoding="utf-8")
    target = "        release {\n            // Don't set to true or java.awt will be a.a or something similar.\n            minifyEnabled false"
    replacement = target + "\n            signingConfig signingConfigs.customDebug"
    if "signingConfig signingConfigs.customDebug" not in gradle_text:
        if target not in gradle_text:
            raise SystemExit("Unable to configure the release signing key; upstream Gradle layout changed.")
        gradle.write_text(gradle_text.replace(target, replacement, 1), encoding="utf-8")

    found_label = False
    for strings_file in (app / "src" / "main" / "res").glob("values*/strings.xml"):
        before = strings_file.read_text(encoding="utf-8")
        if re.search(r'<string\s+name="app_short_name">.*?</string>', before):
            found_label = True
        after = re.sub(r'(<string\s+name="app_short_name">).*?(</string>)', r'\1RokaLauncher\2', before, count=1)
        after = after.replace("MJLauncher", "RokaLauncher")
        if after != before:
            strings_file.write_text(after, encoding="utf-8")
    if not found_label:
        raise SystemExit("App display-name string was not found in upstream strings resources.")

    keystore_source = Path(__file__).resolve().parent.parent / "signing" / "rokalauncher-debug.keystore"
    if not keystore_source.is_file():
        raise SystemExit(f"Project signing key missing: {keystore_source}")
    shutil.copy2(keystore_source, app / "debug.keystore")
    write_icon(resources)
    print(f"RokaLauncher branding applied. Application ID: {APP_ID}")


if __name__ == "__main__":
    main()
