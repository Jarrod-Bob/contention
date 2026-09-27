"""Curating Channels into a Niche's Channel list."""

import json
from pathlib import Path

from contention.niche import TIERS, load_niche
from contention.youtube import YouTube


def _toml_string(value: str) -> str:
    return json.dumps(value)  # JSON string escapes are valid TOML basic-string escapes


def add_channel(niche_folder: Path, youtube: YouTube, handle: str, tier: str, reason: str) -> None:
    """Append a Channel to the Niche's `channels.toml`, after checking YouTube knows the handle.

    Raises ValueError, leaving the list unchanged, if the Tier isn't one of TIERS,
    the Channel is already listed, or YouTube has no Channel with that handle.
    """
    if tier not in TIERS:
        raise ValueError(f"{tier!r} isn't a Tier; use one of {', '.join(TIERS)}")
    if any(c.handle == handle for c in load_niche(niche_folder).channels):
        raise ValueError(f"{handle} is already in the Channel list")
    if youtube.channel_by_handle(handle) is None:
        raise ValueError(f"there's no YouTube Channel with the handle {handle}")
    entry = (
        "\n[[channels]]\n"
        f"handle = {_toml_string(handle)}\n"
        f"tier = {_toml_string(tier)}\n"
        f"reason = {_toml_string(reason)}\n"
    )
    with open(Path(niche_folder) / "channels.toml", "a") as file:
        file.write(entry)
