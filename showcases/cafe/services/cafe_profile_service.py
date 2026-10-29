from pathlib import Path
import json
from typing import Dict

DATA_PATH = Path("showcases/cafe/data/profile.json")
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE = {
    "name": {"ru": "Cafe Name", "ro": "Cafe Name", "en": "Cafe Name"},
    "city": {"ru": "City", "ro": "City", "en": "City"},
    "tagline": {"ru": "specialty coffee", "ro": "specialty coffee", "en": "specialty coffee"},
    "about": {"ru": "demo", "ro": "demo", "en": "demo"},
    "contact": {
        "phone": "",
        "email": "",
        "address": {"ru": "Strada", "ro": "Strada", "en": "Street"},
        "hours": {"ru": "Mon-Sun", "ro": "Mon-Sun", "en": "Mon-Sun"},
        "map_url": ""
    }
}

class CafeProfileService:
    def _load(self) -> Dict:
        if DATA_PATH.exists():
            try:
                return json.loads(DATA_PATH.read_text(encoding="utf-8"))
            except:
                pass
        return json.loads(json.dumps(DEFAULT_PROFILE))

    def _save(self, data: Dict):
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_profile(self) -> Dict:
        data = self._load()
        # ensure keys
        for k,v in DEFAULT_PROFILE.items():
            if k not in data:
                data[k]=v
        return data

    def get_profile_for_lang(self, lang: str) -> Dict:
        data = self.get_profile()
        return {
            "name": data["name"].get(lang) or data["name"].get("en") or "Cafe Name",
            "city": data["city"].get(lang) or data["city"].get("en") or "",
            "tagline": data["tagline"].get(lang) or "",
            "about": data["about"].get(lang) or "",
            "address": data["contact"]["address"].get(lang) or "",
            "hours": data["contact"]["hours"].get(lang) or "",
            "phone": data["contact"].get("phone") or "",
            "email": data["contact"].get("email") or "",
            "map_url": data["contact"].get("map_url") or "",
        }

    def update_profile(self, payload: Dict):
        data = self._load()
        for k in ["name","city","tagline","about"]:
            if k in payload and isinstance(payload[k], dict):
                if k not in data:
                    data[k]={}
                data[k].update(payload[k])
        if "contact" in payload:
            if "contact" not in data:
                data["contact"]=DEFAULT_PROFILE["contact"].copy()
            for ck, cv in payload["contact"].items():
                if isinstance(cv, dict):
                    if ck not in data["contact"]:
                        data["contact"][ck]={}
                    data["contact"][ck].update(cv)
                else:
                    data["contact"][ck]=cv
        self._save(data)
        return data

cafe_profile_service = CafeProfileService()
