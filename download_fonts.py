"""Download Inter and Fira Code fonts directly from GitHub releases."""
import urllib.request
import zipfile
import io
import shutil
from pathlib import Path

FONTS_DIR = Path("hydrosim/resources/fonts")
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Direct zip downloads from GitHub releases
SOURCES = [
    (
        "Inter (GitHub)",
        "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip",
        {
            "Inter-Regular.ttf":  ["Inter-Regular.ttf", "Inter Regular.ttf", "InterVariable.ttf"],
            "Inter-Medium.ttf":   ["Inter-Medium.ttf",  "Inter Medium.ttf"],
            "Inter-SemiBold.ttf": ["Inter-SemiBold.ttf","Inter SemiBold.ttf"],
            "Inter-Bold.ttf":     ["Inter-Bold.ttf",    "Inter Bold.ttf"],
        },
    ),
    (
        "Fira Code (GitHub)",
        "https://github.com/tonsky/FiraCode/releases/download/6.2/Fira_Code_v6.2.zip",
        {
            "FiraCode-Regular.ttf":  ["ttf/FiraCode-Regular.ttf"],
            "FiraCode-Medium.ttf":   ["ttf/FiraCode-Medium.ttf"],
            "FiraCode-SemiBold.ttf": ["ttf/FiraCode-SemiBold.ttf"],
        },
    ),
]

def best_match(zf_names, candidates):
    """Find the first candidate that exists in the zip (case-insensitive suffix match)."""
    lower_map = {n.lower(): n for n in zf_names}
    for c in candidates:
        key = c.lower()
        if key in lower_map:
            return lower_map[key]
        # also try just the basename
        base = Path(c).name.lower()
        for zname_lower, zname in lower_map.items():
            if Path(zname_lower).name == base:
                return zname
    return None

for label, url, wanted in SOURCES:
    print(f"Downloading {label}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf_names = zf.namelist()
            for dest_name, candidates in wanted.items():
                match = best_match(zf_names, candidates)
                if match:
                    dest = FONTS_DIR / dest_name
                    with zf.open(match) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"  -> {dest_name}")
                else:
                    print(f"  MISSING: {dest_name} (candidates: {candidates})")
    except Exception as e:
        print(f"  WARNING: {e}")
        print(f"  App will use system font fallbacks.")

print("\nDone. Fonts directory:")
for f in sorted(FONTS_DIR.glob("*.ttf")):
    print(f"  {f.name}")
if not list(FONTS_DIR.glob("*.ttf")):
    print("  (empty — system fonts will be used)")
