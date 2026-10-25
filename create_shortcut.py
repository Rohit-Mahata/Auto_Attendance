"""
Desktop Shortcut Generator for Auto Attendance System
Dynamically identifies current project root and current user desktop across any Windows machine.
"""
import os
import sys
from pathlib import Path

def create_desktop_shortcut():
    project_dir = Path(__file__).resolve().parent
    bat_target = project_dir / "Launch_Attendance_App.bat"
    
    # Check OneDrive Desktop first, then local Desktop
    userprofile = os.environ.get("USERPROFILE", "")
    desktop = Path(userprofile) / "OneDrive" / "Desktop"
    if not desktop.exists():
        desktop = Path(userprofile) / "Desktop"
    
    if not desktop.exists():
        print(f"Could not locate Desktop directory at {desktop}")
        return False
        
    shortcut_path = desktop / "Auto Attendance System.lnk"
    
    # Use PowerShell COM interface so no external pip packages are needed
    ps_cmd = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{str(shortcut_path)}')
    $Shortcut.TargetPath = '{str(bat_target)}'
    $Shortcut.WorkingDirectory = '{str(project_dir)}'
    $Shortcut.Description = 'Auto Attendance Intelligence System'
    $Shortcut.IconLocation = 'shell32.dll,13'
    $Shortcut.Save()
    """
    
    import subprocess
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[OK] Desktop Shortcut successfully created at: {shortcut_path}")
        return True
    else:
        print(f"[!] Warning creating shortcut: {result.stderr}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
