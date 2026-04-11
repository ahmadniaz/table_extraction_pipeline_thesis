"""
Claude-specific prompts for PDF table extraction.

get_system_prompt() and get_table_extraction_prompt() now delegate to
shared_prompts so Claude, GPT-5, and Mistral use an identical extraction
contract.  All other prompts (metadata, quality, chunk, summarize) remain
Claude-specific and are unchanged.
"""

from app.services.ai.shared_prompts import SYSTEM_PROMPT, USER_PROMPT


class ClaudePrompts:
    """Prompts for Claude Document AI extraction"""

    @staticmethod
    def get_system_prompt() -> str:
        """
        Universal system prompt shared with GPT-5 and Mistral.
        Ensures symmetric evaluation conditions across all LLM tools.
        """
        return SYSTEM_PROMPT

    @staticmethod
    def get_table_extraction_prompt() -> str:
        """
        Universal user prompt shared with GPT-5 and Mistral.
        Used as the text block alongside the base64-encoded PDF document.
        """
        return USER_PROMPT

    @staticmethod
    def get_metadata_extraction_prompt() -> str:
        """Prompt for extracting document metadata (carrier, date, broker, etc.)"""
        return """You are an expert at extracting metadata from insurance commission statement documents.

Your task is to analyze the document and extract:

1. **CARRIER NAME** - The insurance company that issued this statement
   - Look in headers, logos, letterhead, and document branding
   - Look at page footers where companies often place their logos
   - Common carriers: Aetna, Blue Cross Blue Shield, Cigna, UnitedHealthcare, Allied Benefit Systems, Humana, etc.
   - DO NOT extract from table data columns - look at document structure elements only
   
2. **STATEMENT DATE** - The date of this commission statement
   - Extract the ACTUAL date shown in the document - NEVER use current date or any default/fallback date
   - Look for "Statement Date:", "Commission Summary For:", "Report Date:", "Period:", "Period Ending:", "Date Range:", "Statement Period:", "Reporting Period:"
   - Look in document headers, titles, and top section of the first page
   - **CRITICAL FOR DATE RANGES**: If you see a date range (e.g., "Period: 01/01/2025 - 01/31/2025"), USE THE END DATE (the second date) as the statement date
   - For date ranges like "MM/DD/YYYY - MM/DD/YYYY", always extract the SECOND date (end date)
   - Format: YYYY-MM-DD (Example: "Period: 01/01/2025 - 01/31/2025" → use "2025-01-31")
   - If no date is visible or you cannot confidently extract it, return null with a low confidence score
   - DO NOT extract dates from table data, policy effective dates, or transaction dates - only extract the statement/report date from the document header

3. **BROKER/AGENT COMPANY** - The broker or agent entity receiving commissions
   - Look for "Agent:", "Broker:", "Agency:", "To:", "Prepared For:" labels
   - Usually appears near the top of the document or in the header
   - This is different from the carrier - it's the entity receiving the statement
   - Common examples: "Innovative BPS", "ABC Insurance Agency", "XYZ Benefits Group"

4. **DOCUMENT TYPE** - Classification of the document
   - commission_statement, billing_statement, summary_report, etc.

Return your response in this exact JSON format:
{
  "carrier_name": "Exact carrier name as it appears",
  "carrier_confidence": 0.95,
  "statement_date": "2024-01-31",
  "date_confidence": 0.90,
  "broker_company": "Broker/Agent company name as it appears",
  "broker_confidence": 0.85,
  "document_type": "commission_statement",
  "total_pages": 5,
  "evidence": "Brief explanation of where you found this information"
}

If you cannot find the information with high confidence, use null for the value and a lower confidence score."""

    @staticmethod
    def get_quality_assessment_prompt() -> str:
        """Prompt for assessing extraction quality"""
        return """You are a quality assurance expert for document extraction systems.

Your task is to assess the quality of the extracted data and identify any issues.

Review the extracted tables and metadata, then provide:

1. **Overall Confidence Score** (0.0-1.0)
   - How confident are you in the extraction accuracy?
   
2. **Table Structure Score** (0.0-1.0)
   - Are table structures preserved correctly?
   - Are headers and rows properly aligned?
   
3. **Data Completeness** (0.0-1.0)
   - Is all visible data captured?
   - Are there any obvious missing values?
   
4. **Issues Detected**
   - List any problems: missing data, misalignment, unclear text, etc.

5. **Quality Grade**
   - A: Excellent (95-100%)
   - B: Good (85-94%)
   - C: Acceptable (75-84%)
   - D: Poor (65-74%)
   - F: Failed (<65%)

Return assessment in this JSON format:
{
  "overall_confidence": 0.92,
  "table_structure_score": 0.95,
  "data_completeness": 0.88,
  "extraction_accuracy": 0.90,
  "issues_detected": ["Some text unclear in footer", "One table partially cut off"],
  "quality_grade": "A"
}"""

    @staticmethod
    def get_large_document_summary_prompt(page_range: str) -> str:
        """Prompt for summarizing large documents before detailed extraction"""
        return f"""You are analyzing pages {page_range} of a large commission statement.

First, provide a quick overview:
1. How many tables do you see on these pages?
2. What is the general structure and layout?
3. Are there any challenges or complexities?
4. What is the carrier name if visible?

This helps optimize the extraction process for large documents.

Return a brief summary in JSON format:
{{
  "table_count": 5,
  "layout_type": "multi_column" or "single_column",
  "complexity": "simple", "moderate", or "complex",
  "carrier_visible": true/false,
  "challenges": ["borderless tables", "hierarchical data", etc.]
}}"""

    @staticmethod
    def get_chunk_extraction_prompt(chunk_info: str) -> str:
        """Prompt for extracting data from document chunks"""
        return f"""You are processing chunk {chunk_info} of a large commission statement.

Extract all tables from this section following the standard extraction rules.

IMPORTANT: 
- This is part of a larger document
- Some tables may continue from previous pages
- Some tables may continue to next pages
- Mark incomplete tables clearly

Extract tables as normal but include an "incomplete" flag if a table appears to continue beyond this chunk."""

    @staticmethod
    def get_summarize_extraction_prompt() -> str:
        """Prompt for summarize extraction - returns markdown content"""
        return """You are an OCR agent. Extract structured invoice data as Markdown. Note probably the document was split only send the first three pages do not mention this to the user. No debes envolver dentro de un bloque de código (```markdown...```)

Extract the following information from the document:
- Document name/number
- Document date
- Total amount
- Currency
- Vendor name
- Customer name
- Additional metadata
- Complete summary about the document (dont return tables)

Format your response as structured markdown without code blocks. Dont return tables"""



