"""Tests for command safety engine."""
from core.safety import classify, RiskLevel


def test_safe_readonly_command():
    result = classify("gcloud projects list")
    assert result.risk == RiskLevel.SAFE


def test_dangerous_delete_command():
    result = classify("gcloud compute instances delete my-instance --zone us-central1-a")
    assert result.risk == RiskLevel.DANGEROUS
    assert result.requires_approval is True


def test_review_create_command():
    result = classify("gcloud compute instances create my-vm")
    assert result.risk == RiskLevel.REVIEW
    assert result.requires_approval is True


def test_empty_command():
    result = classify("")
    assert result.risk == RiskLevel.SAFE


def test_unrecognized_command():
    result = classify("some-random-command foo bar")
    assert result.risk == RiskLevel.REVIEW  # defaults to review
