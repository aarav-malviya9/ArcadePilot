"""Tests for lab instruction parser."""
from core.lab_parser import parse_markdown_steps, extract_gcloud_commands


def test_parse_numbered_steps():
    text = """1. Create a GCS bucket
2. Upload a file to the bucket
3. Verify the file exists
"""
    tasks = parse_markdown_steps(text)
    assert len(tasks) == 3
    assert "Create" in tasks[0].title
    assert "Upload" in tasks[1].title
    assert "Verify" in tasks[2].title


def test_extract_gcloud_commands():
    text = "Run `gcloud projects list` and then `python script.py`"
    cmds = extract_gcloud_commands(text)
    assert any("gcloud" in c for c in cmds)
    assert any("python" in c for c in cmds)


def test_empty_text():
    tasks = parse_markdown_steps("")
    assert len(tasks) >= 1
