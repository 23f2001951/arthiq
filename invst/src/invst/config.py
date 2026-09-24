"""invst — Configuration management module.

Loads YAML configuration files (settings.yaml, scoring_weights.yaml, sectors.yaml)
from the config/ directory, validates scoring weights, resolves relative paths,
applies environment variable overrides, and exposes an immutable, frozen Config object
with dotted-attribute access.
"""

import math
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]


def get_project_root() -> Path:
    """Find and return the project root directory by searching for pyproject.toml.

    Traverses parent directories upwards starting from the location of this file,
    and if not found, from the current working directory. Falls back to finding
    config/settings.yaml or the package root hierarchy (src/invst/config.py -> root).

    Returns:
        Path: Absolute, resolved path to the project root directory.
    """
    # 1. Search parent directories of this file
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate

    # 2. Search parent directories of current working directory
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate

    # 3. Search for config/settings.yaml marker
    for candidate in [current, *current.parents, cwd, *cwd.parents]:
        if (candidate / "config" / "settings.yaml").is_file():
            return candidate

    # 4. Fallback based on known repository structure: src/invst/config.py -> parents[2]
    return Path(__file__).resolve().parents[2]


def _parse_yaml_scalar(val: str) -> Any:
    """Parse a primitive YAML scalar into a Python object."""
    val = val.strip()
    if not val:
        return None
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "none", "~"):
        return None
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        items = [_parse_yaml_scalar(x) for x in val[1:-1].split(",") if x.strip()]
        return items
    try:
        if "." in val or "e" in val.lower():
            return float(val)
        return int(val)
    except ValueError:
        return val


def _fallback_yaml_load(text: str) -> dict[str, Any]:
    """Lightweight pure-Python fallback YAML parser for basic nested dicts and lists.

    Used when PyYAML is not installed in the current Python environment.
    Supports mappings, lists, strings, numbers, booleans, and inline lists.
    """
    lines = text.splitlines()
    cleaned: list[tuple[int, str]] = []
    for line in lines:
        s = line
        in_quote = False
        quote_char = ""
        comment_pos = -1
        for i, ch in enumerate(s):
            if ch in ('"', "'"):
                if not in_quote:
                    in_quote = True
                    quote_char = ch
                elif quote_char == ch:
                    in_quote = False
            elif ch == "#" and not in_quote:
                comment_pos = i
                break
        if comment_pos >= 0:
            s = s[:comment_pos]
        if s.strip():
            indent = len(s) - len(s.lstrip(" "))
            cleaned.append((indent, s.strip()))

    def parse_block(idx: int, current_indent: int) -> tuple[Any, int]:
        if idx >= len(cleaned):
            return None, idx
        first_indent, first_line = cleaned[idx]
        if first_indent < current_indent:
            return None, idx

        if first_line.startswith("- "):
            result_list: list[Any] = []
            while idx < len(cleaned):
                ind, line = cleaned[idx]
                if ind < current_indent:
                    break
                if ind == current_indent and line.startswith("- "):
                    item_str = line[2:].strip()
                    idx += 1
                    if not item_str:
                        nested, idx = parse_block(idx, ind + 2)
                        result_list.append(nested)
                    elif ":" in item_str and not item_str.startswith(('"', "'")):
                        k, v = item_str.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if not v:
                            sub_nested, idx = parse_block(idx, ind + 2)
                            result_list.append({k: sub_nested})
                        else:
                            result_list.append({k: _parse_yaml_scalar(v)})
                    else:
                        result_list.append(_parse_yaml_scalar(item_str))
                elif ind > current_indent:
                    idx += 1
                else:
                    break
            return result_list, idx
        else:
            result_dict: dict[str, Any] = {}
            while idx < len(cleaned):
                ind, line = cleaned[idx]
                if ind < current_indent:
                    break
                if ind == current_indent:
                    if ":" not in line:
                        idx += 1
                        continue
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    idx += 1
                    if not v:
                        if idx < len(cleaned) and cleaned[idx][0] > ind:
                            nested, idx = parse_block(idx, cleaned[idx][0])
                            result_dict[k] = nested
                        else:
                            result_dict[k] = None
                    else:
                        result_dict[k] = _parse_yaml_scalar(v)
                elif ind > current_indent:
                    idx += 1
                else:
                    break
            return result_dict, idx

    res, _ = parse_block(0, 0)
    return res if isinstance(res, dict) else {}


def load_yaml_file(file_path: Path | str) -> dict[str, Any]:
    """Load a YAML file into a dictionary, using PyYAML if available or fallback parser.

    Args:
        file_path: Path to the YAML file to read.

    Returns:
        dict[str, Any]: Parsed configuration mapping.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    return _fallback_yaml_load(text)


def _resolve_relative_path(path_val: str | Path, base_dir: Path) -> Path:
    """Resolve a path relative to base_dir if it is not already absolute."""
    p = Path(path_val)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    else:
        p = p.resolve()
    return p


def validate_scoring_weights(scoring_weights: Mapping[str, Any]) -> None:
    """Validate that weights sum to 1.0 within each scoring stage.

    Checks stages: 'quality', 'valuation', 'risk', and 'composite'.
    Uses floating-point tolerance of 1e-4.

    Args:
        scoring_weights: Parsed dictionary from scoring_weights.yaml.

    Raises:
        ValueError: If weights in any stage do not sum to 1.0 within tolerance.
    """
    stages_to_check = ["quality", "valuation", "risk", "composite"]
    for stage in stages_to_check:
        if stage not in scoring_weights:
            continue
        stage_weights = scoring_weights[stage]
        if not isinstance(stage_weights, Mapping):
            continue
        numeric_vals = [v for v in stage_weights.values() if isinstance(v, (int, float))]
        if not numeric_vals:
            continue
        total = sum(numeric_vals)
        if not math.isclose(total, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError(
                f"Scoring weights for stage '{stage}' must sum to 1.0, "
                f"got {total:.4f}. Weights: {dict(stage_weights)}"
            )


class ConfigNode(Mapping[str, Any]):
    """An immutable, frozen mapping wrapper providing dotted attribute access.

    Attributes can be accessed via dot notation (e.g. `node.key`) or dictionary
    indexing (e.g. `node['key']`). Any attempt to modify, add, or delete an
    attribute or item raises a TypeError.
    """

    __slots__ = (
        "_data",
        "_frozen",
        "_project_root",
        "_settings_node",
        "_scoring_weights_node",
        "_sectors_node",
    )

    def __init__(self, data: Mapping[str, Any] | None = None) -> None:
        raw: dict[str, Any] = {}
        if data:
            for k, v in data.items():
                raw[k] = self._freeze_value(v)
        object.__setattr__(self, "_data", raw)
        object.__setattr__(self, "_frozen", True)

    @classmethod
    def _freeze_value(cls, val: Any) -> Any:
        """Recursively freeze dictionary and list values into immutable types."""
        if isinstance(val, Mapping):
            return ConfigNode(val)
        if isinstance(val, (list, set)):
            return tuple(cls._freeze_value(item) for item in val)
        return val

    def __getattr__(self, name: str) -> Any:
        data = getattr(self, "_data", None)
        if data is not None and name in data:
            return data[name]
        raise AttributeError(f"Configuration node has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise TypeError(f"Config is immutable; cannot set attribute '{name}'")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if getattr(self, "_frozen", False):
            raise TypeError(f"Config is immutable; cannot delete attribute '{name}'")
        object.__delattr__(self, name)

    def __setitem__(self, key: str, value: Any) -> None:
        raise TypeError(f"Config is immutable; cannot set item '{key}'")

    def __delitem__(self, key: str) -> None:
        raise TypeError(f"Config is immutable; cannot delete item '{key}'")

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for key if key is in the configuration, else default."""
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Recursively convert this ConfigNode back to standard Python dicts/lists."""
        out: dict[str, Any] = {}
        for k, v in self._data.items():
            if isinstance(v, ConfigNode):
                out[k] = v.to_dict()
            elif isinstance(v, tuple):
                out[k] = [item.to_dict() if isinstance(item, ConfigNode) else item for item in v]
            else:
                out[k] = v
        return out

    def __repr__(self) -> str:
        return f"ConfigNode({self._data!r})"

    def __dir__(self) -> list[str]:
        """Enable auto-completion for configuration keys."""
        return list(super().__dir__()) + [
            k for k in self._data.keys() if isinstance(k, str) and k.isidentifier()
        ]


class Config(ConfigNode):
    """Frozen root configuration for the invst application.

    Exposes dotted attribute and mapping access to merged settings, scoring weights,
    sector mappings, and project root (e.g. `config.database.path`,
    `config.scoring_weights.quality.roe_5yr_avg`).
    """

    def __init__(
        self,
        merged_data: Mapping[str, Any],
        project_root: Path,
        settings_data: Mapping[str, Any],
        scoring_weights_data: Mapping[str, Any],
        sectors_data: Mapping[str, Any],
    ) -> None:
        sectors_map = (
            sectors_data.get("sectors", sectors_data)
            if isinstance(sectors_data, Mapping)
            else sectors_data
        )
        object.__setattr__(self, "_project_root", project_root)
        object.__setattr__(self, "_settings_node", ConfigNode(settings_data))
        object.__setattr__(self, "_scoring_weights_node", ConfigNode(scoring_weights_data))
        object.__setattr__(self, "_sectors_node", ConfigNode(sectors_map))
        super().__init__(merged_data)

    @property
    def project_root(self) -> Path:
        """Return the resolved project root directory."""
        return self._project_root

    @property
    def settings(self) -> ConfigNode:
        """Return the full settings configuration node."""
        return self._settings_node

    @property
    def scoring_weights(self) -> ConfigNode:
        """Return the scoring weights configuration node."""
        return self._scoring_weights_node

    @property
    def sectors(self) -> ConfigNode:
        """Return the sector classification configuration node."""
        return self._sectors_node

    @classmethod
    def get_instance(
        cls,
        config_dir: Path | str | None = None,
        project_root: Path | str | None = None,
        reload: bool = False,
    ) -> "Config":
        """Return the cached singleton instance."""
        return get_config(config_dir=config_dir, project_root=project_root, reload=reload)


def load_config(
    config_dir: Path | str | None = None,
    project_root: Path | str | None = None,
) -> Config:
    """Load, validate, and return the immutable application configuration.

    Loads settings.yaml, scoring_weights.yaml, and sectors.yaml.
    Validates that scoring weights sum to 1.0 within each stage.
    Applies environment variable overrides:
      - `INVST_DB_PATH` overrides `database.path`
      - `INVST_LOG_LEVEL` overrides `logging.level`
      - `INVST_LOG_FILE` overrides `logging.file`
    Resolves relative file paths against the project root.

    Args:
        config_dir: Optional path to config directory. Defaults to <project_root>/config.
        project_root: Optional path to project root. Defaults to get_project_root().

    Returns:
        Config: Frozen, immutable configuration object.

    Raises:
        FileNotFoundError: If any required configuration file is missing.
        ValueError: If scoring weights fail validation.
    """
    resolved_root = Path(project_root).resolve() if project_root is not None else get_project_root()

    if config_dir is not None:
        resolved_config_dir = Path(config_dir).resolve()
    else:
        env_config_dir = os.environ.get("INVST_CONFIG_DIR")
        if env_config_dir:
            resolved_config_dir = _resolve_relative_path(env_config_dir, resolved_root)
        else:
            resolved_config_dir = (resolved_root / "config").resolve()

    settings_file = resolved_config_dir / "settings.yaml"
    scoring_weights_file = resolved_config_dir / "scoring_weights.yaml"
    sectors_file = resolved_config_dir / "sectors.yaml"

    settings = load_yaml_file(settings_file)
    scoring_weights = load_yaml_file(scoring_weights_file)
    sectors = load_yaml_file(sectors_file)

    # Validate scoring weights sum to 1.0 within each stage
    validate_scoring_weights(scoring_weights)

    # Resolve filesystem paths relative to project root
    if "database" in settings and isinstance(settings["database"], dict):
        if "path" in settings["database"]:
            settings["database"]["path"] = _resolve_relative_path(
                settings["database"]["path"], resolved_root
            )

    if "data" in settings and isinstance(settings["data"], dict):
        for path_key in ("raw_dir", "interim_dir", "processed_dir"):
            if path_key in settings["data"]:
                settings["data"][path_key] = _resolve_relative_path(
                    settings["data"][path_key], resolved_root
                )

    if "logging" in settings and isinstance(settings["logging"], dict):
        if "file" in settings["logging"]:
            settings["logging"]["file"] = _resolve_relative_path(
                settings["logging"]["file"], resolved_root
            )

    # Environment variable overrides
    env_db_path = os.environ.get("INVST_DB_PATH")
    if env_db_path:
        if "database" not in settings or not isinstance(settings["database"], dict):
            settings["database"] = {}
        settings["database"]["path"] = _resolve_relative_path(env_db_path, resolved_root)

    env_log_level = os.environ.get("INVST_LOG_LEVEL")
    if env_log_level:
        if "logging" not in settings or not isinstance(settings["logging"], dict):
            settings["logging"] = {}
        settings["logging"]["level"] = env_log_level.upper()

    env_log_file = os.environ.get("INVST_LOG_FILE")
    if env_log_file:
        if "logging" not in settings or not isinstance(settings["logging"], dict):
            settings["logging"] = {}
        settings["logging"]["file"] = _resolve_relative_path(env_log_file, resolved_root)

    # Build merged data structure for top-level access
    merged_data: dict[str, Any] = dict(settings)
    merged_data["scoring_weights"] = scoring_weights
    merged_data["sectors"] = (
        sectors.get("sectors", sectors) if isinstance(sectors, dict) else sectors
    )

    # Direct access to scoring stages (quality, valuation, risk, etc.)
    for stage_name, stage_val in scoring_weights.items():
        if stage_name not in merged_data:
            merged_data[stage_name] = stage_val

    return Config(
        merged_data=merged_data,
        project_root=resolved_root,
        settings_data=settings,
        scoring_weights_data=scoring_weights,
        sectors_data=sectors,
    )


_CONFIG_CACHE: Config | None = None


def get_config(
    config_dir: Path | str | None = None,
    project_root: Path | str | None = None,
    reload: bool = False,
) -> Config:
    """Return the cached Config singleton instance, loading if necessary.

    Args:
        config_dir: Optional path to directory containing YAML configs.
        project_root: Optional path to project root.
        reload: If True, invalidate cache and reload configuration from disk.

    Returns:
        Config: Frozen, immutable configuration object.
    """
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None or reload:
        _CONFIG_CACHE = load_config(config_dir=config_dir, project_root=project_root)
    return _CONFIG_CACHE
