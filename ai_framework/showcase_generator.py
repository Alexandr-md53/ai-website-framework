# coding: utf-8, ASCII only
"""C3.2 - Generate manifest.json from ShowcaseManifest contract."""
from __future__ import annotations
import json
from pathlib import Path
from ai_framework.showcase_manifest import KNOWN_SHOWCASES

def generate_all() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    generated = []
    for showcase in KNOWN_SHOWCASES:
        showcase_dir = root / "showcases" / showcase.name
        showcase_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = showcase_dir / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(showcase.to_dict(), f, indent=2, ensure_ascii=False)
            f.write("\n")
        generated.append(manifest_path)
        print(f"[gen] {manifest_path.relative_to(root)} -> {showcase.version}")
    return generated

if __name__ == "__main__":
    generate_all()
