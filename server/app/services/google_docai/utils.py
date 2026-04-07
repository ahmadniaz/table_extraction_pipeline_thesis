"""
Utility functions for Google Document AI table extraction.
"""

from typing import Dict, List, Any, Tuple
from datetime import datetime


def extract_rows_from_tableblock(tableblock: Dict[str, Any]) -> Tuple[List[str], List[List[str]]]:
    """
    Extract headers and rows from a Google Document AI tableBlock object.
    
    This adapter function handles Document AI's Layout Parser JSON output format:
    tableBlock → bodyRows → cells → blocks → textBlock structure.
    
    Args:
        tableblock: Dictionary representing a tableBlock from Document AI Layout Parser
        
    Returns:
        Tuple of (headers, rows) where:
        - headers: List of strings representing column headers
        - rows: List of lists of strings representing table data rows
    """
    try:
        headers = []
        rows = []
        
        # Extract header rows if present
        header_rows = tableblock.get("headerRows", [])
        if header_rows:
            for header_row in header_rows:
                row_cells = []
                for cell in header_row.get("cells", []):
                    cell_text = ""
                    # Extract text from all blocks in the cell
                    for block in cell.get("blocks", []):
                        if "textBlock" in block and "text" in block["textBlock"]:
                            cell_text += block["textBlock"]["text"] + " "
                    row_cells.append(cell_text.strip())
                if row_cells:
                    headers.extend(row_cells)
        
        # Extract body rows
        body_rows = tableblock.get("bodyRows", [])
        for body_row in body_rows:
            row_cells = []
            for cell in body_row.get("cells", []):
                cell_text = ""
                # Extract text from all blocks in the cell
                for block in cell.get("blocks", []):
                    if "textBlock" in block and "text" in block["textBlock"]:
                        cell_text += block["textBlock"]["text"] + " "
                row_cells.append(cell_text.strip())
            if row_cells:
                rows.append(row_cells)
        
        # If no headers were extracted, try to use first row as headers
        if not headers and rows:
            headers = rows[0]
            rows = rows[1:]
        
        # Ensure all rows have the same number of columns as headers
        if headers:
            max_cols = len(headers)
            normalized_rows = []
            for row in rows:
                # Pad with empty strings if row has fewer columns
                normalized_row = row[:max_cols] + [""] * (max_cols - len(row))
                normalized_rows.append(normalized_row)
            rows = normalized_rows
        
        return headers, rows
        
    except Exception as e:
        print(f"Error extracting rows from tableBlock: {e}")
        return [], []


def adapt_tableblock_to_standard_format(
    tableblock: Dict[str, Any], 
    page_num: int = 0, 
    table_index: int = 0
) -> Dict[str, Any]:
    """
    Adapt a Google Document AI tableBlock to the standard table format expected by utilities.
    
    Args:
        tableblock: Dictionary representing a tableBlock from Document AI Layout Parser
        page_num: Page number where the table was found
        table_index: Index of the table on the page
        
    Returns:
        Standard table dictionary with headers, rows, and metadata
    """
    try:
        # Extract headers and rows using the adapter
        headers, rows = extract_rows_from_tableblock(tableblock)
        
        # Generate default headers if none were detected
        if not headers and rows:
            max_cols = max(len(row) for row in rows) if rows else 0
            headers = [f"Column_{i+1}" for i in range(max_cols)]
        
        # Extract metadata from tableBlock
        confidence = tableblock.get("confidence", 0.0)
        bbox = tableblock.get("boundingBox", {})
        
        # Convert bbox format if present
        bbox_dict = {}
        if bbox and "vertices" in bbox:
            vertices = bbox["vertices"]
            if len(vertices) >= 4:
                bbox_dict = {
                    "x0": vertices[0].get("x", 0),
                    "y0": vertices[0].get("y", 0),
                    "x1": vertices[2].get("x", 0),
                    "y1": vertices[2].get("y", 0)
                }
        
        # Create standard table format
        table_dict = {
            "header": headers,
            "rows": rows,
            "confidence": confidence,
            "bbox": bbox_dict,
            "page_number": page_num + 1,
            "table_index": table_index,
            "extractor": "google_docai_layout_parser",
            "metadata": {
                "page_number": page_num + 1,
                "table_index": table_index,
                "extraction_method": "google_docai_layout_parser",
                "timestamp": datetime.now().isoformat(),
                "source_format": "tableBlock"
            }
        }
        
        return table_dict
        
    except Exception as e:
        print(f"Error adapting tableBlock to standard format: {e}")
        return {
            "header": [],
            "rows": [],
            "confidence": 0.0,
            "bbox": {},
            "page_number": page_num + 1,
            "table_index": table_index,
            "extractor": "google_docai_layout_parser",
            "metadata": {
                "page_number": page_num + 1,
                "table_index": table_index,
                "extraction_method": "google_docai_layout_parser",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        }

