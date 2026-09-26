"""Niches: everything niche-specific, loaded from a niche folder as data."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Niche:
    name: str
    description: str
    formats: list[str]


def load_niche(folder: Path) -> Niche:
    """Load a Niche from its folder's `niche.toml`. The folder name is the Niche's name.

    Raises ValueError if the Format list doesn't include "other", the fallback
    every Video must be able to fall into.
    """
    folder = Path(folder)
    data = tomllib.loads((folder / "niche.toml").read_text())
    if "other" not in data["formats"]:
        raise ValueError(f'{folder.name}: the Format list must include "other"')
    return Niche(
        name=folder.name,
        description=data["description"].strip(),
        formats=list(data["formats"]),
    )
