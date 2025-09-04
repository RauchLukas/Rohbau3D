
from pathlib import Path
from typing import Any
import yaml


class Config(dict):
    """dict with attribute (dot) access. Recursively converts nested dicts/lists.
    Note: dot access only works for keys that are valid identifiers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    # --- attribute access ---
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as e:
            # also allow underscore→dash alias (handy for YAML keys with -)
            alt = name.replace("_", "-")
            if alt in self:
                return self[alt]
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value: Any) -> None:
        # write to dict; supports cfg.foo = 1
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, self._convert(value))

    def update(self, *args, **kwargs) -> None:
        data = {}
        if args:
            data.update(args[0])
        data.update(kwargs)
        for k, v in data.items():
            super().__setitem__(k, self._convert(v))

    @staticmethod
    def _convert(v: Any) -> Any:
        if isinstance(v, dict):
            return Config(v)
        if isinstance(v, list):
            return [Config._convert(i) for i in v]
        return v

    def to_dict(self) -> dict[str, Any]:
        """Back to plain dict (for saving)."""
        def un(v):
            if isinstance(v, Config):
                return {k: un(x) for k, x in v.items()}
            if isinstance(v, list):
                return [un(i) for i in v]
            return v
        return un(self)
    

    
def load_config(path: str | Path) -> Config:
    """Read YAML → Config (dot-access)."""
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise TypeError(f"Top-level YAML must be a mapping, got {type(data)}")
    return Config(data)