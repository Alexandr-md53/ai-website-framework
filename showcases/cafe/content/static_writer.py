"""Static writer - writes generated public site to dist/cafe_site"""
from __future__ import annotations
import pathlib, shutil

def clean_dist(dist_path: pathlib.Path):
    if dist_path.exists():
        shutil.rmtree(dist_path)
    dist_path.mkdir(parents=True, exist_ok=True)

def write_file(dist_path: pathlib.Path, relative: str, content: str):
    target = dist_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return target
