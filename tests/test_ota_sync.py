"""Tests for OTA sync: backup, sync, validate, rollback."""

from pathlib import Path

import pytest

from aquarela.main import _OTA_EXCLUDE, _ota_sync_and_validate


@pytest.fixture
def fake_repo(tmp_path):
    """Build a fake live repo with a couple of files we'll overwrite."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "aquarela").mkdir()
    (repo / "aquarela" / "main.py").write_text("ORIGINAL_MAIN\napp = 'live'\n")
    (repo / "aquarela" / "helper.py").write_text("ORIGINAL_HELPER\n")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "tool.py").write_text("ORIGINAL_TOOL\n")
    (repo / "data").mkdir()
    (repo / "data" / "aquarela.db").write_bytes(b"USER_DATA_DO_NOT_TOUCH")
    return repo


@pytest.fixture
def good_tarball_extract(tmp_path):
    """Simulated extracted tarball that's valid (validation will pass)."""
    src = tmp_path / "user-repo-abc1234"
    src.mkdir()
    (src / "aquarela").mkdir()
    (src / "aquarela" / "main.py").write_text("UPDATED_MAIN\napp = 'new'\n")
    (src / "aquarela" / "helper.py").write_text("UPDATED_HELPER\n")
    (src / "scripts").mkdir()
    (src / "scripts" / "tool.py").write_text("UPDATED_TOOL\n")
    # Should not be touched even if present
    (src / "data").mkdir()
    (src / "data" / "stuff.txt").write_text("OTA SHOULD NOT WRITE THIS")
    return src


@pytest.fixture
def broken_tarball_extract(tmp_path):
    """Tarball that produces 0-byte files (the actual bug we hit in prod)."""
    src = tmp_path / "user-repo-broken1"
    src.mkdir()
    (src / "aquarela").mkdir()
    (src / "aquarela" / "main.py").write_bytes(b"")  # 0-byte main.py
    (src / "aquarela" / "helper.py").write_text("UPDATED_HELPER\n")
    return src


def _passing_validation(repo: Path):
    """Fast validation cmd that just confirms the new main.py was written."""
    return ["sh", "-c",
            f"grep -q UPDATED_MAIN {repo / 'aquarela' / 'main.py'}"]


def _failing_validation():
    return ["sh", "-c", "exit 1"]


class TestOtaSyncAndValidate:
    def test_happy_path_replaces_files(self, fake_repo, good_tarball_extract):
        steps, ok = _ota_sync_and_validate(
            good_tarball_extract, fake_repo,
            validation_cmd=_passing_validation(fake_repo),
        )
        assert ok is True
        assert (fake_repo / "aquarela" / "main.py").read_text() == "UPDATED_MAIN\napp = 'new'\n"
        assert (fake_repo / "aquarela" / "helper.py").read_text() == "UPDATED_HELPER\n"
        assert (fake_repo / "scripts" / "tool.py").read_text() == "UPDATED_TOOL\n"
        # Steps include backup + sync + validate, all ok
        assert all(s["ok"] for s in steps)
        assert {s["step"] for s in steps} >= {"backup", "sync", "validate"}

    def test_data_dir_is_never_touched(self, fake_repo, good_tarball_extract):
        # Sanity: 'data' is in the excluded set
        assert "data" in _OTA_EXCLUDE
        original_db = (fake_repo / "data" / "aquarela.db").read_bytes()
        _ota_sync_and_validate(
            good_tarball_extract, fake_repo,
            validation_cmd=_passing_validation(fake_repo),
        )
        # User data preserved exactly
        assert (fake_repo / "data" / "aquarela.db").read_bytes() == original_db
        # Tarball's `data/stuff.txt` was NOT copied in
        assert not (fake_repo / "data" / "stuff.txt").exists()

    def test_validation_failure_rolls_back(self, fake_repo, good_tarball_extract):
        original_main = (fake_repo / "aquarela" / "main.py").read_text()
        original_helper = (fake_repo / "aquarela" / "helper.py").read_text()
        original_tool = (fake_repo / "scripts" / "tool.py").read_text()

        steps, ok = _ota_sync_and_validate(
            good_tarball_extract, fake_repo,
            validation_cmd=_failing_validation(),
        )
        assert ok is False
        # All originals restored
        assert (fake_repo / "aquarela" / "main.py").read_text() == original_main
        assert (fake_repo / "aquarela" / "helper.py").read_text() == original_helper
        assert (fake_repo / "scripts" / "tool.py").read_text() == original_tool
        # Validate step recorded the failure
        validate_step = next(s for s in steps if s["step"] == "validate")
        assert validate_step["ok"] is False
        assert "ROLLBACK" in validate_step["output"]

    def test_zero_byte_main_py_is_caught_and_rolled_back(
        self, fake_repo, broken_tarball_extract,
    ):
        """The exact prod bug: tarball has main.py at 0 bytes.

        With a real validation that imports the module, this would fail.
        We simulate that with a check for non-empty content.
        """
        original_main = (fake_repo / "aquarela" / "main.py").read_text()
        validation = ["sh", "-c",
                      f"test -s {fake_repo / 'aquarela' / 'main.py'}"]

        steps, ok = _ota_sync_and_validate(
            broken_tarball_extract, fake_repo,
            validation_cmd=validation,
        )

        assert ok is False
        # Critical: the live tree is back to its pre-OTA state.
        assert (fake_repo / "aquarela" / "main.py").read_text() == original_main
        # main.py is NOT 0 bytes (the prod failure mode)
        assert (fake_repo / "aquarela" / "main.py").stat().st_size > 0

    def test_backup_dir_is_cleaned_up_on_success(
        self, fake_repo, good_tarball_extract,
    ):
        _ota_sync_and_validate(
            good_tarball_extract, fake_repo,
            validation_cmd=_passing_validation(fake_repo),
        )
        # The temp backup dir should be gone after a clean run
        backup = fake_repo.parent / f"{fake_repo.name}.ota-backup"
        assert not backup.exists()

    def test_backup_dir_is_cleaned_up_on_rollback(
        self, fake_repo, good_tarball_extract,
    ):
        _ota_sync_and_validate(
            good_tarball_extract, fake_repo,
            validation_cmd=_failing_validation(),
        )
        backup = fake_repo.parent / f"{fake_repo.name}.ota-backup"
        assert not backup.exists()
