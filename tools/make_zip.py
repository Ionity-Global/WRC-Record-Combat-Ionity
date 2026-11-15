# Builds release/WRC-<version>.zip for CurseForge: one WRC folder at the root,
# forward-slash paths, no executables. Version is read from addon/WRC/WRC.toc.
import os, re, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "addon", "WRC")
ver = re.search(r"## Version:\s*([\d.]+)", open(os.path.join(ADDON, "WRC.toc"), encoding="utf-8").read()).group(1)
out = os.path.join(ROOT, "release", "WRC-%s.zip" % ver)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in sorted(os.listdir(ADDON)):
        if name.endswith((".exe", ".py", ".pyc")) or name.startswith("."):
            continue
        z.write(os.path.join(ADDON, name), "WRC/" + name)
print(out)
print("\n".join(zipfile.ZipFile(out).namelist()))
