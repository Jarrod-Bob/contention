"""Niches: everything niche-specific, loaded from a niche folder as data."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


# Bands of Channel subscriber counts. Mirrors the `tier` enum in the database.
TIERS = ("1k-10k", "10k-100k", "100k-500k", "500k-1M", "1M+")


@dataclass(frozen=True)
class CuratedChannel:
    """A Channel the user curated into a Niche, as written in its `channels.toml`."""

    handle: str
    tier: str
    reason: str


@dataclass(frozen=True)
class Niche:
    name: str
    description: str
    formats: tuple[str, ...]
    channels: tuple[CuratedChannel, ...] = ()


def load_niche(folder: Path) -> Niche:
    """Load a Niche from its folder: `niche.toml`, plus the Channel list in `channels.toml`.

    The folder name is the Niche's name.

    Raises ValueError if the Format list doesn't include "other" (the fallback
    every Video must be able to fall into), or a listed Channel's Tier isn't one of TIERS.
    """
    folder = Path(folder)
    data = tomllib.loads((folder / "niche.toml").read_text())
    if "other" not in data["formats"]:
        raise ValueError(f'{folder.name}: the Format list must include "other"')
    channels_file = folder / "channels.toml"
    listed = tomllib.loads(channels_file.read_text()).get("channels", []) if channels_file.exists() else []
    for entry in listed:
        if entry["tier"] not in TIERS:
            raise ValueError(f"{folder.name}: {entry['handle']} has Tier {entry['tier']!r}; use one of {', '.join(TIERS)}")
    return Niche(
        name=folder.name,
        description=data["description"].strip(),
        formats=tuple(data["formats"]),
        channels=tuple(CuratedChannel(c["handle"], c["tier"], c["reason"]) for c in listed),
    )
