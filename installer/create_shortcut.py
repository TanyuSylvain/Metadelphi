#!/usr/bin/env python3
"""
Create Windows Desktop Shortcut for Metadelphi
This script creates a desktop shortcut on Windows systems
"""

import os
import sys
from pathlib import Path


def create_windows_shortcut():
    """Create a Windows desktop shortcut"""
    if sys.platform != "win32":
        print("This script is only for Windows systems")
        return False

    try:
        # Method 1: Try using pywin32 (if available)
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")

            # Get desktop path
            desktop = shell.SpecialFolders("Desktop")
            legacy_shortcut_path = os.path.join(desktop, "UnifyLLM.lnk")
            if os.path.exists(legacy_shortcut_path):
                os.unlink(legacy_shortcut_path)
            shortcut_path = os.path.join(desktop, "Metadelphi.lnk")

            # Create shortcut
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = str(Path(__file__).parent.parent / "launcher.bat")
            shortcut.WorkingDirectory = str(Path(__file__).parent.parent)
            shortcut.Description = "Metadelphi Multi-Agent Debate System"

            # Try to set icon if available
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                shortcut.IconLocation = str(icon_path)

            shortcut.Save()
            print(f"✓ Desktop shortcut created at: {shortcut_path}")
            return True

        except ImportError:
            # Method 2: Fallback to VBScript method (no dependencies)
            import tempfile
            import subprocess

            # Get desktop path from environment
            desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            if not os.path.exists(desktop):
                desktop = os.path.join(os.environ.get('HOMEDRIVE', 'C:'),
                                      os.environ.get('HOMEPATH', '\\Users\\' + os.environ.get('USERNAME', 'User')),
                                      'Desktop')

            legacy_shortcut_path = os.path.join(desktop, "UnifyLLM.lnk")
            if os.path.exists(legacy_shortcut_path):
                os.unlink(legacy_shortcut_path)
            shortcut_path = os.path.join(desktop, "Metadelphi.lnk")
            launcher_path = str(Path(__file__).parent.parent / "launcher.bat").replace('/', '\\')
            working_dir = str(Path(__file__).parent.parent).replace('/', '\\')

            # Get icon path if available
            icon_path = Path(__file__).parent / "icon.ico"
            icon_location = str(icon_path).replace('/', '\\') if icon_path.exists() else launcher_path

            # Create VBScript to make shortcut
            vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{launcher_path}"
oLink.WorkingDirectory = "{working_dir}"
oLink.Description = "Metadelphi Multi-Agent Debate System"
oLink.IconLocation = "{icon_location}"
oLink.Save
'''

            # Write VBScript to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.vbs', delete=False) as f:
                f.write(vbs_script)
                vbs_path = f.name

            try:
                # Execute VBScript
                subprocess.run(['cscript', '//Nologo', vbs_path], check=True,
                             capture_output=True, text=True)
                print(f"✓ Desktop shortcut created at: {shortcut_path}")
                return True
            finally:
                # Clean up VBScript file
                try:
                    os.unlink(vbs_path)
                except:
                    pass

    except Exception as e:
        print(f"Warning: Could not create desktop shortcut: {e}")
        print("You can still launch Metadelphi by running launcher.bat")
        return False


def main():
    """Main entry point"""
    if sys.platform == "win32":
        return 0 if create_windows_shortcut() else 1
    else:
        print("This script is only for Windows systems")
        print("For Linux/MacOS, use create_launcher.py instead")
        return 1


if __name__ == "__main__":
    sys.exit(main())
