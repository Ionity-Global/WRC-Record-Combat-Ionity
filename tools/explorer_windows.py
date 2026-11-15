# Lists open Explorer windows (to check whether the clips folder did open).
import subprocess
ps = "(New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.LocationURL + '  hwnd=' + $_.HWND + '  left=' + $_.Left + ' top=' + $_.Top }"
print(subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout or "(no Explorer windows)")
