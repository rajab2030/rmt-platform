"""Exercise the real restore script with fake Docker/tar/rm, never live volumes."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = next(
    parent / "scripts/restore-volume.sh"
    for parent in Path(__file__).resolve().parents
    if (parent / "scripts/restore-volume.sh").is_file()
)


@pytest.fixture
def restore_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.jsonl"
    driver = f"#!{sys.executable}\n" + '''
import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["RESTORE_TEST_LOG"], "a") as stream:
    stream.write(json.dumps([name, *args]) + "\\n")
if name == "docker" and args[0] == "run":
    index = args.index("sh")
    sys.exit(subprocess.run(args[index:], env=os.environ).returncode)
if name == "tar" and args[0] == "tzf":
    sys.exit(int(os.environ.get("RESTORE_TEST_BAD_ARCHIVE", "0")))
'''
    for name in ("docker", "tar", "rm"):
        target = bin_dir / name
        target.write_text(driver)
        target.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", RESTORE_TEST_LOG=str(log))

    def run(filename, volume="restore_test_volume"):
        return subprocess.run(
            ["bash", str(SCRIPT), filename, volume], cwd=tmp_path, env=env,
            capture_output=True, text=True, timeout=5,
        )

    def calls():
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    return tmp_path, env, run, calls


@pytest.mark.parametrize("filename", [
    "backup; touch INJECTED; #.tgz", "backup$(touch INJECTED).tgz",
    "backup with 'quotes'.tgz",
])
def test_filename_is_data_not_shell_code(restore_env, filename):
    tmp, _, run, calls = restore_env
    (tmp / filename).write_text("fake archive; fake tar validates it")
    assert run(filename).returncode == 0
    assert not (tmp / "INJECTED").exists()
    assert ["tar", "xzf", f"/backup/{filename}", "-C", "/volume"] in calls()
    docker_run = next(c for c in calls() if c[:2] == ["docker", "run"])
    assert f"{tmp}:/backup:ro" in docker_run


def test_bad_archive_never_reaches_deletion(restore_env):
    tmp, env, run, calls = restore_env
    (tmp / "bad.tgz").write_text("invalid")
    env["RESTORE_TEST_BAD_ARCHIVE"] = "2"
    assert run("bad.tgz").returncode != 0
    assert not any(c[0] == "rm" for c in calls())
    assert not any(c[:2] == ["tar", "xzf"] for c in calls())


@pytest.mark.parametrize("filename,volume", [
    ("missing.tgz", "restore_test"), ("../archive.tgz", "restore_test"),
    ("archive.tgz", "/"), ("archive.tgz", "host:/volume"),
])
def test_invalid_input_never_calls_docker(restore_env, filename, volume):
    tmp, _, run, calls = restore_env
    (tmp / "archive.tgz").write_text("archive")
    assert run(filename, volume).returncode != 0
    assert calls() == []
