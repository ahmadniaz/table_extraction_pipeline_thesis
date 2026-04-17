"""Unit tests for Textract single-page vs multi-page routing (no live AWS calls)."""

from unittest.mock import MagicMock

import fitz
import pytest

from app.services.textract.service import TextractService


@pytest.fixture
def single_page_pdf(tmp_path):
    p = tmp_path / "one.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(p))
    doc.close()
    return p


@pytest.fixture
def multi_page_pdf(tmp_path):
    p = tmp_path / "multi.pdf"
    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
    doc.save(str(p))
    doc.close()
    return p


def test_multipage_without_s3_uses_sync_per_page(multi_page_pdf, monkeypatch):
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    mock_client = MagicMock()
    mock_client.analyze_document.return_value = {"Blocks": []}

    def fake_get_client(self):
        return mock_client

    monkeypatch.setattr(TextractService, "_get_client", fake_get_client)
    svc = TextractService()
    out = svc.analyze_document_tables(str(multi_page_pdf))

    assert mock_client.analyze_document.call_count == 3
    mock_client.start_document_analysis.assert_not_called()
    assert out["tool"] == "aws_textract"
    assert out["tables"] == []
    assert out["pages_analyzed"] == 3


def test_single_page_uses_sync_analyze_document(single_page_pdf, monkeypatch):
    mock_client = MagicMock()
    mock_client.analyze_document.return_value = {"Blocks": []}

    def fake_get_client(self):
        return mock_client

    monkeypatch.setattr(TextractService, "_get_client", fake_get_client)
    svc = TextractService()
    out = svc.analyze_document_tables(str(single_page_pdf))

    mock_client.analyze_document.assert_called_once()
    mock_client.start_document_analysis.assert_not_called()
    assert out["tool"] == "aws_textract"
    assert out["tables"] == []
    assert out["pages_analyzed"] == 0


def test_multipage_async_path_invokes_start_document_analysis(
    multi_page_pdf, monkeypatch
):
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

    s3_mock = MagicMock()
    textract_mock = MagicMock()
    textract_mock.start_document_analysis.return_value = {"JobId": "job-1"}
    textract_mock.get_document_analysis.return_value = {
        "JobStatus": "SUCCEEDED",
        "Blocks": [],
        "NextToken": None,
    }

    svc = TextractService()
    monkeypatch.setattr(svc, "_get_client", lambda: textract_mock)
    monkeypatch.setattr(svc, "_get_s3_client", lambda: s3_mock)

    out = svc.analyze_document_tables(str(multi_page_pdf))

    textract_mock.start_document_analysis.assert_called_once()
    textract_mock.analyze_document.assert_not_called()
    s3_mock.upload_file.assert_called_once()
    s3_mock.delete_object.assert_called_once()
    assert out["tool"] == "aws_textract"
