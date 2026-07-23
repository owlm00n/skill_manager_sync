import json
import shutil
from pathlib import Path
from datetime import datetime


class TrashManager:
    def __init__(self, trash_file: Path, trash_dir: Path):
        self.trash_file = trash_file
        self.trash_dir = trash_dir

    def load(self) -> list:
        if self.trash_file.exists():
            return json.loads(self.trash_file.read_text(encoding="utf-8"))
        return []

    def save(self, items: list):
        self.trash_file.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, skill_name: str, skill_dir: Path):
        trash = self.load()
        trash.append({"name": skill_name, "deleted_at": datetime.now().isoformat(), "dir": str(skill_dir)})
        self.save(trash)
        trash_dest = self.trash_dir / skill_name
        trash_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(skill_dir), str(trash_dest))

    def restore(self, skill_name: str, target_dir: Path) -> bool:
        trash_src = self.trash_dir / skill_name
        if not trash_src.exists():
            return False
        shutil.move(str(trash_src), str(target_dir))
        trash = self.load()
        trash = [t for t in trash if t["name"] != skill_name]
        self.save(trash)
        return True
