"""Tests for merge_similar_tables_global."""

from app.services.evaluation.table_merging import merge_similar_tables_global


def test_merge_identical_headers_across_pages():
    t0 = {
        "headers": ["A", "B"],
        "rows": [["1", "2"]],
        "page_number": 0,
        "table_index": 0,
    }
    t1 = {
        "headers": ["A", "B"],
        "rows": [["3", "4"]],
        "page_number": 1,
        "table_index": 0,
    }
    out = merge_similar_tables_global([t1, t0])
    assert len(out) == 1
    assert out[0]["rows"] == [["1", "2"], ["3", "4"]]
    assert out[0]["row_count"] == 2
    assert out[0]["merged_from"] == 2
    assert out[0]["merged_page_range"] == (0, 1)
    assert out[0]["metadata"]["merge_info"]["merged_from"] == 2


def test_different_headers_not_merged():
    a = {
        "headers": ["Foo"],
        "rows": [["x"]],
        "page_number": 0,
        "table_index": 0,
    }
    b = {
        "headers": ["Bar"],
        "rows": [["y"]],
        "page_number": 0,
        "table_index": 1,
    }
    out = merge_similar_tables_global([a, b])
    assert len(out) == 2


def test_separator_table_breaks_chain():
    a = {
        "headers": ["H"],
        "rows": [["1"]],
        "page_number": 0,
        "table_index": 0,
    }
    mid = {
        "headers": ["Other"],
        "rows": [["z"]],
        "page_number": 0,
        "table_index": 1,
    }
    c = {
        "headers": ["H"],
        "rows": [["2"]],
        "page_number": 0,
        "table_index": 2,
    }
    out = merge_similar_tables_global([c, a, mid])
    assert len(out) == 3
    assert "merged_from" not in out[0] and "merged_from" not in out[1]
    assert "merged_from" not in out[2]


def test_all_empty_headers_not_merged():
    a = {
        "headers": ["", ""],
        "rows": [["1", "2"]],
        "page_number": 0,
        "table_index": 0,
    }
    b = {
        "headers": ["", ""],
        "rows": [["3", "4"]],
        "page_number": 0,
        "table_index": 1,
    }
    out = merge_similar_tables_global([a, b])
    assert len(out) == 2
