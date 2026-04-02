from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    import winreg
else:
    winreg = None


class AutostartService:
    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    VALUE_NAME = "ProcWatch"

    def is_supported(self) -> bool:
        return sys.platform == "win32" and winreg is not None

    def is_enabled(self) -> bool:
        if not self.is_supported():
            return False
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_READ,
            ) as key:
                value, _ = winreg.QueryValueEx(key, self.VALUE_NAME)
                return bool(value)
        except OSError:
            return False

    def set_enabled(self, enabled: bool, executable_path: Path) -> None:
        if not self.is_supported():
            return
        command = f'"{executable_path}" --minimized'
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            self.REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, self.VALUE_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, self.VALUE_NAME)
                except FileNotFoundError:
                    pass
