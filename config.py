import json
from pathlib import Path


class ConfigManager:
    """Manages YAML config parsing and updates for config.yaml."""

    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self):
        if not Path(self.config_path).exists():
            return {}
        text = Path(self.config_path).read_text(encoding="utf-8")
        return self._parse_yaml(text)

    def _parse_yaml(self, text: str) -> dict:
        root = {}
        stack = [(root, -1)]
        for line in text.splitlines():
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            while len(stack) > 1 and indent <= stack[-1][1]:
                stack.pop()
            parent, _ = stack[-1]
            if stripped.startswith("- "):
                val = stripped[2:].strip()
                if isinstance(parent, list):
                    parent.append(self._yaml_val(val))
                continue
            if ":" not in stripped:
                continue
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
                parent[key] = items
            elif val == "":
                child = {}
                parent[key] = child
                stack.append((child, indent))
            else:
                parent[key] = self._yaml_val(val)
        return root

    @staticmethod
    def _yaml_val(s):
        if s.lower() == "true": return True
        if s.lower() == "false": return False
        return s

    def update_value(self, key_path: str, value, agent_name: str = None):
        text = Path(self.config_path).read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        if key_path == "default_mode":
            for i, line in enumerate(lines):
                if line.strip().startswith("default_mode:"):
                    indent = line[:len(line) - len(line.lstrip())]
                    lines[i] = f'{indent}default_mode: {value}\n'
                    break
        elif key_path == "active_presets":
            if agent_name:
                # Find the specific agent's active_presets
                in_agent = False
                for i, line in enumerate(lines):
                    stripped = line.lstrip()
                    # Agent config lines start with 2 spaces (under agents:)
                    if stripped.startswith(f"{agent_name}:") and line.startswith("  "):
                        in_agent = True
                        continue
                    if in_agent and "active_presets:" in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        lines[i] = f'{indent}active_presets: {json.dumps(value)}\n'
                        break
                    # Exit agent block when hitting another agent or top-level section
                    if in_agent and line.strip() and not line.startswith("    ") and not line.startswith("\n"):
                        break
            else:
                for i, line in enumerate(lines):
                    if "active_presets:" in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        lines[i] = f'{indent}active_presets: {json.dumps(value)}\n'
                        break
        Path(self.config_path).write_text("".join(lines), encoding="utf-8")

    def add_agent_config(self, config_name: str, tool: str, skills_path: str, presets: list = None):
        """Add a new agent config block to config.yaml."""
        text = Path(self.config_path).read_text(encoding="utf-8")
        presets_str = json.dumps(presets or ["universal"])
        new_block = f"\n  {config_name}:\n    tool: {tool}\n    path: \"{skills_path}\"\n    active_presets: {presets_str}\n"
        # Insert after 'agents:' section
        if "\nagents:" in text:
            text = text.replace("\nagents:", "\nagents:" + new_block, 1)
        else:
            text += f"\nagents:{new_block}"
        Path(self.config_path).write_text(text, encoding="utf-8")
