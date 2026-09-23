import pytest

from app.pipeline.backgrounds import (
    BackgroundError,
    get_background,
    list_backgrounds,
    thumbnail_path,
)
from tests.helpers import make_clip


def test_lists_only_video_files(tmp_settings):
    make_clip(tmp_settings.backgrounds_dir / "minecraft_parkour.mp4")
    (tmp_settings.backgrounds_dir / "notes.txt").write_text("hi")
    items = list_backgrounds()
    assert [b.id for b in items] == ["minecraft_parkour.mp4"]
    assert items[0].name == "Minecraft Parkour"
    assert 2.5 < items[0].duration < 3.5


def test_lookup_by_id_and_random(tmp_settings):
    make_clip(tmp_settings.backgrounds_dir / "a.mp4")
    assert get_background("a.mp4").id == "a.mp4"
    assert get_background("random").id == "a.mp4"


@pytest.mark.parametrize("bad_id", ["nope.mp4", "../secret.mp4", "/etc/passwd"])
def test_unknown_or_traversal_ids_are_rejected(tmp_settings, bad_id):
    make_clip(tmp_settings.backgrounds_dir / "a.mp4")
    with pytest.raises(BackgroundError, match="Unknown background"):
        get_background(bad_id)


def test_no_backgrounds_gives_helpful_error(tmp_settings):
    with pytest.raises(BackgroundError, match="No background videos"):
        get_background("random")


def test_thumbnail_is_generated_and_cached(tmp_settings):
    make_clip(tmp_settings.backgrounds_dir / "a.mp4")
    bg = get_background("a.mp4")
    thumb = thumbnail_path(bg)
    assert thumb.exists() and thumb.stat().st_size > 0
    mtime = thumb.stat().st_mtime
    assert thumbnail_path(bg).stat().st_mtime == mtime
