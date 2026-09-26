from pathlib import Path

import pytest

from contention.niche import load_niche

NICHES = Path(__file__).parent.parent / "niches"


def test_loads_the_tech_careers_niche():
    niche = load_niche(NICHES / "tech-careers")

    assert niche.name == "tech-careers"
    assert "software" in niche.description
    assert niche.formats == (
        "personal story",
        "tutorial / how-to",
        "advice / tips list",
        "commentary / opinion",
        "interview / podcast",
        "day-in-the-life",
        "mock interview / walkthrough",
        "review / reaction",
        "news / update",
        "Q&A",
        "other",
    )


@pytest.mark.parametrize("formats", ['[]', '["tutorial / how-to"]'])
def test_rejects_a_format_list_without_other(tmp_path, formats):
    folder = tmp_path / "broken-niche"
    folder.mkdir()
    (folder / "niche.toml").write_text(f'description = "A niche."\nformats = {formats}\n')

    with pytest.raises(ValueError, match="other"):
        load_niche(folder)
