#!/usr/bin/env python3
"""
Create Desktop Launcher for Metadelphi on Unix systems
This script creates desktop launchers for Linux and MacOS
"""

import os
import sys
import platform
from pathlib import Path
import shutil


def create_linux_launcher():
    """Create a .desktop file for Linux systems"""
    try:
        # Determine paths
        app_dir = Path(__file__).parent.parent.resolve()
        launcher_script = app_dir / "launcher.sh"
        icon_path = Path(__file__).parent / "icon.png"

        # Desktop entry content
        desktop_entry = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Metadelphi
Comment=Multi-Agent Debate System for LLM Comparison
Exec={launcher_script}
Icon={icon_path if icon_path.exists() else ''}
Terminal=true
Categories=Development;Education;Science;
StartupNotify=true
Keywords=AI;LLM;Chat;Agent;
"""

        # Create .desktop file in multiple locations
        desktop_locations = []

        # 1. User's desktop
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            legacy_desktop_file = desktop / "UnifyLLM.desktop"
            if legacy_desktop_file.exists():
                legacy_desktop_file.unlink()
            desktop_file = desktop / "Metadelphi.desktop"
            desktop_locations.append(desktop_file)

        # 2. Local applications directory
        local_apps = Path.home() / ".local" / "share" / "applications"
        local_apps.mkdir(parents=True, exist_ok=True)
        legacy_apps_file = local_apps / "UnifyLLM.desktop"
        if legacy_apps_file.exists():
            legacy_apps_file.unlink()
        desktop_file_apps = local_apps / "Metadelphi.desktop"
        desktop_locations.append(desktop_file_apps)

        # Write desktop files
        created_files = []
        for desktop_file in desktop_locations:
            try:
                with open(desktop_file, 'w') as f:
                    f.write(desktop_entry)
                # Make executable
                os.chmod(desktop_file, 0o755)
                created_files.append(str(desktop_file))
                print(f"✓ Created launcher: {desktop_file}")
            except Exception as e:
                print(f"Warning: Could not create launcher at {desktop_file}: {e}")

        # Update desktop database if available
        try:
            import subprocess
            subprocess.run(['update-desktop-database', str(local_apps)],
                         capture_output=True, timeout=5)
        except:
            pass

        if created_files:
            return True
        else:
            print("Warning: Could not create any desktop launchers")
            return False

    except Exception as e:
        print(f"Warning: Could not create desktop launcher: {e}")
        return False


def create_macos_launcher():
    """Create a proper MacOS .app bundle"""
    try:
        # Determine paths
        app_dir = Path(__file__).parent.parent.resolve()
        launcher_script = app_dir / "launcher.sh"
        icon_png = Path(__file__).parent / "icon.png"

        # Create .app bundle in /Applications
        app_bundle = Path.home() / "Applications" / "Metadelphi.app"
        legacy_app_bundle = Path.home() / "Applications" / "UnifyLLM.app"

        # Create directory structure
        contents_dir = app_bundle / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"

        # Remove existing app bundle if it exists
        if app_bundle.exists():
            shutil.rmtree(app_bundle)
        if legacy_app_bundle.exists():
            shutil.rmtree(legacy_app_bundle)

        # Create directories
        macos_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Create Info.plist
        info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Metadelphi</string>
    <key>CFBundleDisplayName</key>
    <string>Metadelphi</string>
    <key>CFBundleIdentifier</key>
    <string>com.metadelphi.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>Metadelphi</string>
    <key>CFBundleIconFile</key>
    <string>Metadelphi.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
</dict>
</plist>"""

        with open(contents_dir / "Info.plist", 'w') as f:
            f.write(info_plist)

        # Create executable launcher script that opens Terminal
        launcher_content = f"""#!/bin/bash
# Open Terminal and run launcher.sh
osascript -e 'tell application "Terminal"
    do script "cd \\"{app_dir}\\" && ./launcher.sh"
    activate
end tell'
"""

        launcher_path = macos_dir / "Metadelphi"
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        os.chmod(launcher_path, 0o755)

        # Convert PNG to ICNS if possible
        if icon_png.exists():
            try:
                # Try using sips (built-in macOS tool)
                import subprocess
                iconset_dir = resources_dir / "Metadelphi.iconset"
                iconset_dir.mkdir(exist_ok=True)

                # Generate different icon sizes
                sizes = [16, 32, 64, 128, 256, 512]
                for size in sizes:
                    subprocess.run([
                        'sips', '-z', str(size), str(size),
                        str(icon_png),
                        '--out', str(iconset_dir / f"icon_{size}x{size}.png")
                    ], capture_output=True, timeout=10)

                    # Create @2x versions
                    if size <= 256:
                        subprocess.run([
                            'sips', '-z', str(size * 2), str(size * 2),
                            str(icon_png),
                            '--out', str(iconset_dir / f"icon_{size}x{size}@2x.png")
                        ], capture_output=True, timeout=10)

                # Convert iconset to icns
                subprocess.run([
                    'iconutil', '-c', 'icns',
                    str(iconset_dir),
                    '-o', str(resources_dir / "Metadelphi.icns")
                ], capture_output=True, timeout=10)

                # Clean up iconset
                shutil.rmtree(iconset_dir)

            except Exception as e:
                print(f"Warning: Could not convert icon to .icns format: {e}")
                # Copy PNG as fallback
                try:
                    shutil.copy(icon_png, resources_dir / "Metadelphi.png")
                except:
                    pass

        print(f"✓ Created application: {app_bundle}")
        print("  The app will appear in Launchpad shortly")
        print("  You can also find it in ~/Applications/")

        return True

    except Exception as e:
        print(f"Error: Could not create MacOS application: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    if sys.platform == "win32":
        print("This script is for Unix systems (Linux/MacOS)")
        print("For Windows, use create_shortcut.py instead")
        return 1

    system = platform.system()

    if system == "Linux":
        print("Creating Linux desktop launcher...")
        return 0 if create_linux_launcher() else 1

    elif system == "Darwin":  # MacOS
        print("Creating MacOS launcher...")
        return 0 if create_macos_launcher() else 1

    else:
        print(f"Unsupported system: {system}")
        print("You can still launch Metadelphi by running: ./launcher.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
