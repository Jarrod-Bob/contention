import pytest

from contention.channels import add_channel
from contention.niche import CuratedChannel, load_niche

from fake_youtube import FakeYouTube, channel_details


@pytest.fixture
def niche_folder(tmp_path):
    folder = tmp_path / "tech-careers"
    folder.mkdir()
    (folder / "niche.toml").write_text('description = "Tech careers."\nformats = ["other"]\n')
    (folder / "channels.toml").write_text("# The curated Channels.\n")
    return folder


def test_adds_a_curated_channel_to_the_niche_folder(niche_folder):
    youtube = FakeYouTube({"@example": channel_details("UC1")}, [])

    add_channel(niche_folder, youtube, "@example", "10k-100k", 'Clear "how I got promoted" stories')

    assert load_niche(niche_folder).channels == (
        CuratedChannel("@example", "10k-100k", 'Clear "how I got promoted" stories'),
    )
    assert (niche_folder / "channels.toml").read_text().startswith("# The curated Channels.\n")


@pytest.mark.parametrize("handle, tier, problem", [
    ("@nobody", "10k-100k", "no YouTube Channel"),
    ("@example", "10k-50k", "Tier"),
    ("@already", "1M+", "already"),
])
def test_refuses_bad_channels_and_leaves_the_list_unchanged(niche_folder, handle, tier, problem):
    youtube = FakeYouTube({"@example": channel_details("UC1"), "@already": channel_details("UC2")}, [])
    add_channel(niche_folder, youtube, "@already", "1M+", "Big channel")
    before = (niche_folder / "channels.toml").read_text()

    with pytest.raises(ValueError, match=problem):
        add_channel(niche_folder, youtube, handle, tier, "A reason")

    assert (niche_folder / "channels.toml").read_text() == before
