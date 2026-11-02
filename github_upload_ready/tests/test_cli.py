"""Tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from capturetrust.cli import main


def _write(tmp_path: Path, name: str, image: np.ndarray) -> Path:
    path = tmp_path / name
    cv2.imwrite(str(path), image)
    return path


def test_inspect_text_output(tmp_path, sharp_image, capsys) -> None:
    path = _write(tmp_path, "a.png", sharp_image)
    code = main(["inspect", str(path)])
    out = capsys.readouterr().out
    assert "Score:" in out
    assert code in (0, 1)


def test_inspect_json_output(tmp_path, sharp_image, capsys) -> None:
    path = _write(tmp_path, "a.png", sharp_image)
    main(["inspect", str(path), "--json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "score" in parsed


def test_inspect_pretty_output(tmp_path, sharp_image, capsys) -> None:
    path = _write(tmp_path, "a.png", sharp_image)
    main(["inspect", str(path), "--pretty"])
    out = capsys.readouterr().out
    assert json.loads(out)["score"] >= 0


def test_inspect_missing_file_errors(capsys) -> None:
    code = main(["inspect", "no-such-file.png"])
    assert code == 2
    assert "Error" in capsys.readouterr().err


def test_inspect_config_flags(tmp_path, sharp_image) -> None:
    path = _write(tmp_path, "a.png", sharp_image)
    code = main(
        [
            "inspect",
            str(path),
            "--min-width",
            "1024",
            "--min-height",
            "768",
            "--disable-document-check",
            "--enable-screen-check",
        ]
    )
    assert code in (0, 1)


def test_batch_text(tmp_path, sharp_image, dark_image, capsys) -> None:
    _write(tmp_path, "a.png", sharp_image)
    _write(tmp_path, "b.png", dark_image)
    code = main(["batch", str(tmp_path)])
    out = capsys.readouterr().out
    assert "a.png" in out and "b.png" in out
    assert code == 0


def test_batch_json_output(tmp_path, sharp_image, capsys) -> None:
    _write(tmp_path, "a.png", sharp_image)
    out_file = tmp_path / "results.json"
    main(["batch", str(tmp_path), "--json-output", str(out_file)])
    payload = json.loads(out_file.read_text())
    assert payload["total"] >= 1
    assert "results" in payload and "skipped" in payload


def test_batch_bad_directory(capsys) -> None:
    code = main(["batch", "definitely-not-a-directory-xyz"])
    assert code == 2


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "capturetrust" in capsys.readouterr().out
