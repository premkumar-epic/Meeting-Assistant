import pytest
from pathlib import Path
from app.utils.temp_files import (
    create_temp_dir,
    build_temp_file_path,
    safe_unlink,
    safe_rmtree,
    ensure_parent_dir,
)

def test_create_temp_dir(tmp_path):
    temp_dir = create_temp_dir(base_dir=str(tmp_path), prefix="test_meeting_")
    assert temp_dir.exists()
    assert temp_dir.is_dir()
    assert temp_dir.name.startswith("test_meeting_")

def test_build_temp_file_path(tmp_path):
    file_path = build_temp_file_path(tmp_path, suffix=".wav", prefix="test_artifact")
    assert file_path.suffix == ".wav"
    assert file_path.name.startswith("test_artifact_")
    assert file_path.parent == tmp_path

def test_safe_unlink(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello", encoding="utf-8")
    assert test_file.exists()
    
    safe_unlink(test_file)
    assert not test_file.exists()

    # Should not raise exception on non-existent file
    safe_unlink(tmp_path / "non_existent.txt")

    # Should safely return on directory path instead of failing
    safe_unlink(tmp_path)

def test_safe_rmtree(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    (sub_dir / "file.txt").write_text("hello", encoding="utf-8")
    assert sub_dir.exists()
    
    safe_rmtree(sub_dir)
    assert not sub_dir.exists()

    # Should not raise error if target directory does not exist
    safe_rmtree(tmp_path / "non_existent")

def test_ensure_parent_dir(tmp_path):
    target = tmp_path / "nested" / "dir" / "file.txt"
    ensure_parent_dir(target)
    assert target.parent.exists()
