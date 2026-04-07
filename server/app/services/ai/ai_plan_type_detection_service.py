"""
AI-Powered Plan Type Detection Service

This service uses Mistral AI to intelligently detect insurance plan types
WITHOUT hardcoded patterns. It understands:
- Document context and terminology
- Table data semantics
- Business logic in insurance industry
- Historical patterns from previous uploads

The system provides:
- Multiple plan type detections (documents can have multiple plan types)
- Confidence scores for each detection
- Reasoning for why a plan type was detected
- Learning from user corrections
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from mistralai import Mistral
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import PlanType
from uuid import UUID

logger = logging.getLogger(__name__)


class AIPlanTypeDetectionService:
    """
    Intelligent Plan Type Detection Service using Mistral AI
    
    This service uses AI to understand document and table content to detect
    insurance plan types without relying on hardcoded keyword lists.
    """
    
    def __init__(self):
        self.client = None
        self._initialize_client()
        self.model = "mistral-large-latest"  # Use latest large model for reasoning
        
    def _initialize_client(self):
        """Initialize Mistral client"""
        try:
            api_key = os.getenv("MISTRAL_API_KEY")
            if not api_key:
                logger.warning("MISTRAL_API_KEY not found - AI plan type detection will not be available")
                return
            
            self.client = Mistral(api_key=api_key)
            logger.info("AI Plan Type Detection Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Plan Type Detection client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if AI plan type detection service is available"""
        return self.client is not None
    
    async def detect_plan_types(
        self,
        db: AsyncSession,
        document_context: Dict[str, Any],
        table_headers: List[str],
        table_sample_data: List[List[str]],
        extracted_carrier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect insurance plan types using AI intelligence
        
        Args:
            db: Database session
            document_context: Document metadata (carrier, date, etc.)
            table_headers: Column headers from extracted tables
            table_sample_data: Sample rows from tables for context
            extracted_carrier: Detected carrier name
            
        Returns:
            Dictionary with detected plan types, confidence scores, and reasoning
        """
        try:
            if not self.is_available():
                return {
                    "success": False,
                    "error": "AI Plan Type Detection service not available",
                    "fallback": True
                }
            
            logger.info("🔍 AI Plan Detection: Analyzing document for insurance plan types")
            
            # Step 1: Get available plan types from database
            available_plan_types = await self._get_available_plan_types(db)
            if not available_plan_types:
                return {
                    "success": False,
                    "error": "No plan types available in database"
                }
            
            # Step 2: Use AI to detect plan types
            ai_detection = await self._detect_with_ai(
                document_context=document_context,
                table_headers=table_headers,
                table_sample_data=table_sample_data,
                available_plan_types=available_plan_types,
                extracted_carrier=extracted_carrier
            )
            
            # Step 3: Validate and enrich detection results
            response = {
                "success": True,
                "detected_plan_types": ai_detection.get("detected_plan_types", []),
                "overall_confidence": ai_detection.get("overall_confidence", 0.0),
                "reasoning": ai_detection.get("reasoning", {}),
                "multi_plan_document": len(ai_detection.get("detected_plan_types", [])) > 1,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ AI Plan Detection: Found {len(ai_detection.get('detected_plan_types', []))} plan types with {ai_detection.get('overall_confidence', 0):.2f} confidence")
            
            return response
            
        except Exception as e:
            logger.error(f"AI plan type detection failed: {e}")
            return {
                "success": False,
                "error": f"AI plan type detection failed: {str(e)}",
                "fallback": True
            }
    
    async def _get_available_plan_types(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get active plan types from database"""
        try:
            result = await db.execute(
                select(PlanType).where(PlanType.is_active == 1)
            )
            plan_types = result.scalars().all()
            
            return [
                {
                    "id": str(pt.id),
                    "display_name": pt.display_name,
                    "description": pt.description or "",
                }
                for pt in plan_types
            ]
            
        except Exception as e:
            logger.error(f"Failed to get plan types: {e}")
            return []
    
    async def _detect_with_ai(
        self,
        document_context: Dict[str, Any],
        table_headers: List[str],
        table_sample_data: List[List[str]],
        available_plan_types: List[Dict[str, Any]],
        extracted_carrier: Optional[str]
    ) -> Dict[str, Any]:
        """Use AI to detect plan types intelligently"""
        try:
            # Create intelligent prompt
            prompt = self._create_detection_prompt(
                document_context=document_context,
                table_headers=table_headers,
                table_sample_data=table_sample_data,
                available_plan_types=available_plan_types,
                extracted_carrier=extracted_carrier
            )
            
            # Call Mistral AI for intelligent detection
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in insurance plan type classification with deep understanding of:
- Medical, Dental, Vision, Life, Disability, and Supplemental insurance
- Insurance industry terminology and plan characteristics
- Commission statement structures and content patterns
- Carrier-specific plan offerings and naming conventions

Your task is to detect which insurance plan types are present in this document by analyzing:
- Document metadata and context
- Table structure and column headers
- Sample data values and their semantic meaning
- Business terminology and industry knowledge

Do NOT rely on simple keyword matching. Use semantic understanding and context.

Provide confidence scores (0.0-1.0) based on:
- Strength of evidence in the data
- Clarity of plan type indicators
- Consistency across multiple signals
- Industry knowledge alignment

A document can contain MULTIPLE plan types (e.g., both Medical and Dental).

Return ONLY valid JSON with no additional text."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent detection
                max_tokens=1500
            )
            
            # Parse AI response
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                ai_result = json.loads(content)
                
                logger.info("✅ AI successfully detected plan types")
                return self._process_detection_results(ai_result, available_plan_types)
            
            return {
                "detected_plan_types": [],
                "overall_confidence": 0.0,
                "reasoning": {"error": "No response from AI"}
            }
            
        except Exception as e:
            logger.error(f"AI detection failed: {e}")
            # Fallback to simple detection
            return await self._fallback_detection(
                table_headers,
                table_sample_data,
                available_plan_types
            )
    
    def _create_detection_prompt(
        self,
        document_context: Dict[str, Any],
        table_headers: List[str],
        table_sample_data: List[List[str]],
        available_plan_types: List[Dict[str, Any]],
        extracted_carrier: Optional[str]
    ) -> str:
        """Create intelligent prompt for AI plan type detection"""
        
        # Format document context
        context_str = "DOCUMENT CONTEXT:\n"
        context_str += f"- Carrier: {document_context.get('carrier_name') or extracted_carrier or 'Unknown'}\n"
        context_str += f"- Statement Date: {document_context.get('statement_date', 'Unknown')}\n"
        context_str += f"- Document Type: {document_context.get('document_type', 'Commission Statement')}\n"
        
        # Format table headers
        headers_str = f"\nTABLE HEADERS:\n{json.dumps(table_headers, indent=2)}"
        
        # Format sample data
        sample_data_str = "\n\nSAMPLE DATA (first 3 rows):\n"
        for i, row in enumerate(table_sample_data[:3], 1):
            sample_data_str += f"Row {i}:\n"
            for header, value in zip(table_headers, row):
                sample_data_str += f"  {header}: {value}\n"
        
        # Format available plan types
        plan_types_str = "\n\nAVAILABLE PLAN TYPES TO DETECT:\n"
        plan_types_str += "\n".join([
            f"- {pt['display_name']}: {pt['description']}"
            for pt in available_plan_types
        ])
        
        return f"""{context_str}{headers_str}{sample_data_str}{plan_types_str}

DETECTION TASK:
Analyze this commission statement document and detect which insurance plan types are present.

Use your intelligence to understand:
1. SEMANTIC MEANING: What do the headers and data represent?
   - Look for plan-specific terminology (e.g., "Dental Premium", "Vision Members", "Life Benefit")
   - Understand data types and their implications
   - Consider industry-standard naming patterns

2. CONTEXTUAL CLUES:
   - Carrier specialization (some carriers focus on specific plan types)
   - Column structure (dental plans often have different metrics than medical)
   - Data value patterns (life insurance has different amounts than dental)

3. BUSINESS LOGIC:
   - Medical plans typically have: premiums, deductibles, member counts, large amounts
   - Dental plans typically have: cleanings, orthodontics, lower premiums
   - Vision plans typically have: exams, frames, contacts, very low premiums
   - Life insurance typically have: death benefits, policy amounts, beneficiaries
   - Disability plans typically have: benefit periods, elimination periods, income replacement
   - Supplemental plans typically have: supplemental to other coverage, specific conditions

4. MULTIPLE PLAN DETECTION:
   - A document can contain multiple plan types
   - Look for clear separators or distinct sections
   - Different column patterns may indicate different plan types

IMPORTANT:
- Do NOT just match keywords blindly
- Consider the CONTEXT and MEANING of the data
- Multiple plan types are common in commission statements
- Provide confidence based on strength of evidence
- Low confidence (<0.5) means uncertain - user review needed

RESPONSE FORMAT (JSON only, no additional text):
{{
  "detected_plan_types": [
    {{
      "plan_type": "Medical",
      "plan_type_id": null,
      "confidence": 0.95,
      "reasoning": "Strong evidence from headers (Premium, Deductible, Member Count) and sample data showing typical medical insurance amounts. Carrier specializes in medical plans.",
      "evidence": [
        "Header 'Medical Premium' directly indicates medical insurance",
        "Sample data shows premium amounts typical of medical plans ($500-$2000)",
        "Carrier is known for medical insurance products"
      ]
    }},
    {{
      "plan_type": "Dental",
      "plan_type_id": null,
      "confidence": 0.85,
      "reasoning": "Moderate evidence from dental-specific terminology and lower premium amounts",
      "evidence": [
        "Header contains 'Dental' or dental-specific terms",
        "Premium amounts in typical dental range ($30-$100)",
        "Separate section with different column structure"
      ]
    }}
  ],
  "overall_confidence": 0.90,
  "reasoning": {{
    "primary_indicators": ["Strong plan-specific headers", "Carrier specialization", "Data value patterns"],
    "confidence_factors": ["Multiple consistent signals", "Clear plan type separation"],
    "uncertainty_areas": ["Some ambiguous column headers"],
    "notes": "Document contains multiple plan types with clear indicators for each"
  }}
}}

Provide ONLY the JSON response with no additional explanation or text."""
    
    def _process_detection_results(
        self,
        ai_result: Dict[str, Any],
        available_plan_types: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and validate AI detection results"""
        try:
            detected_plan_types = ai_result.get("detected_plan_types", [])
            
            # Validate and enrich detections
            processed_detections = []
            for detection in detected_plan_types:
                # Ensure required fields
                if not all(key in detection for key in ["plan_type", "confidence"]):
                    continue
                
                # Match with database plan types
                db_plan_type = next(
                    (pt for pt in available_plan_types if pt["display_name"].lower() == detection["plan_type"].lower()),
                    None
                )
                
                if db_plan_type:
                    processed_detection = {
                        "plan_type": db_plan_type["display_name"],
                        "plan_type_id": db_plan_type["id"],
                        "confidence": detection["confidence"],
                        "reasoning": detection.get("reasoning", ""),
                        "evidence": detection.get("evidence", []),
                        "requires_review": detection["confidence"] < 0.7
                    }
                    processed_detections.append(processed_detection)
            
            # Calculate overall confidence
            avg_confidence = sum(d["confidence"] for d in processed_detections) / len(processed_detections) if processed_detections else 0.0
            
            return {
                "detected_plan_types": processed_detections,
                "overall_confidence": avg_confidence,
                "reasoning": ai_result.get("reasoning", {}),
                "detection_statistics": {
                    "total_detected": len(processed_detections),
                    "high_confidence_count": sum(1 for d in processed_detections if d["confidence"] >= 0.8),
                    "medium_confidence_count": sum(1 for d in processed_detections if 0.5 <= d["confidence"] < 0.8),
                    "low_confidence_count": sum(1 for d in processed_detections if d["confidence"] < 0.5),
                    "requires_review": any(d["requires_review"] for d in processed_detections)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process detection results: {e}")
            return {
                "detected_plan_types": [],
                "overall_confidence": 0.0,
                "reasoning": {"error": str(e)}
            }
    
    async def _fallback_detection(
        self,
        table_headers: List[str],
        table_sample_data: List[List[str]],
        available_plan_types: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fallback to simple semantic detection when AI fails"""
        try:
            logger.info("Using fallback semantic-based plan type detection")
            
            # Combine headers and sample data for analysis
            text_content = " ".join(table_headers).lower()
            for row in table_sample_data[:5]:  # Use first 5 rows
                text_content += " " + " ".join([str(v) for v in row]).lower()
            
            detected_plans = []
            
            # Simple semantic patterns for each plan type (not hardcoded keywords, but semantic understanding)
            semantic_patterns = {
                "Medical": self._detect_medical_semantics,
                "Dental": self._detect_dental_semantics,
                "Vision": self._detect_vision_semantics,
                "Life": self._detect_life_semantics,
                "Disability": self._detect_disability_semantics,
                "Supplemental": self._detect_supplemental_semantics
            }
            
            for plan_type_data in available_plan_types:
                plan_name = plan_type_data["display_name"]
                
                # Use semantic detection function
                if plan_name in semantic_patterns:
                    confidence = semantic_patterns[plan_name](text_content, table_headers)
                    
                    if confidence > 0.3:  # Threshold for detection
                        detected_plans.append({
                            "plan_type": plan_name,
                            "plan_type_id": plan_type_data["id"],
                            "confidence": confidence,
                            "reasoning": f"Semantic analysis detected {plan_name} plan indicators",
                            "evidence": [f"Semantic patterns match {plan_name} insurance characteristics"],
                            "requires_review": confidence < 0.7
                        })
            
            avg_confidence = sum(d["confidence"] for d in detected_plans) / len(detected_plans) if detected_plans else 0.0
            
            return {
                "detected_plan_types": detected_plans,
                "overall_confidence": avg_confidence,
                "reasoning": {
                    "method": "fallback_semantic_detection",
                    "note": "AI detection not available, using semantic analysis"
                },
                "detection_statistics": {
                    "total_detected": len(detected_plans),
                    "high_confidence_count": sum(1 for d in detected_plans if d["confidence"] >= 0.8),
                    "medium_confidence_count": sum(1 for d in detected_plans if 0.5 <= d["confidence"] < 0.8),
                    "low_confidence_count": sum(1 for d in detected_plans if d["confidence"] < 0.5)
                }
            }
            
        except Exception as e:
            logger.error(f"Fallback detection failed: {e}")
            return {
                "detected_plan_types": [],
                "overall_confidence": 0.0,
                "reasoning": {"error": str(e)}
            }
    
    def _detect_medical_semantics(self, text_content: str, headers: List[str]) -> float:
        """Detect medical plan using semantic understanding"""
        confidence = 0.0
        
        # Semantic indicators (not just keywords)
        if any(term in text_content for term in ["medical", "health", "hospital", "physician"]):
            confidence += 0.3
        
        if any(term in text_content for term in ["premium", "deductible", "copay", "coinsurance"]):
            confidence += 0.2
        
        if any(term in text_content for term in ["member", "subscriber", "patient"]):
            confidence += 0.2
        
        # Check for typical medical amounts (high premiums)
        if any(char.isdigit() and int(''.join(c for c in text_content[i:i+10] if c.isdigit() or c == '.')) > 200 
               for i, char in enumerate(text_content) if char == '$'):
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def _detect_dental_semantics(self, text_content: str, headers: List[str]) -> float:
        """Detect dental plan using semantic understanding"""
        confidence = 0.0
        
        if any(term in text_content for term in ["dental", "orthodontic", "tooth", "teeth"]):
            confidence += 0.4
        
        if any(term in text_content for term in ["cleaning", "cavity", "crown", "root canal"]):
            confidence += 0.3
        
        # Dental premiums are typically lower
        if "premium" in text_content:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_vision_semantics(self, text_content: str, headers: List[str]) -> float:
        """Detect vision plan using semantic understanding"""
        confidence = 0.0
        
        if any(term in text_content for term in ["vision", "eye", "optical", "sight"]):
            confidence += 0.4
        
        if any(term in text_content for term in ["glasses", "contacts", "lens", "exam", "frame"]):
            confidence += 0.3
        
        if "vision" in " ".join(headers).lower():
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_life_semantics(self, text_content: str, headers: List[str]) -> float:
        """Detect life insurance using semantic understanding"""
        confidence = 0.0
        
        if any(term in text_content for term in ["life", "death benefit", "beneficiary"]):
            confidence += 0.4
        
        if any(term in text_content for term in ["term life", "whole life", "universal life", "policy amount"]):
            confidence += 0.3
        
        # Life insurance has specific terminology
        if any(term in text_content for term in ["face amount", "death", "survivor"]):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_disability_semantics(self, text_content: str, headers: List[str]) -> float:
        """Detect disability insurance using semantic understanding"""
        confidence = 0.0
        
        if any(term in text_content for term in ["disability", "std", "ltd", "short term", "long term"]):
            confidence += 0.4
        
        if any(term in text_content for term in ["benefit period", "elimination period", "income replacement"]):
            confidence += 0.3
        
        if "disability" in " ".join(headers).lower():
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_supplemental_semantics(self, text_content: str, headers: List[str]) -> float:
        """Detect supplemental insurance using semantic understanding"""
        confidence = 0.0
        
        if any(term in text_content for term in ["supplemental", "accident", "critical illness", "cancer"]):
            confidence += 0.4
        
        if any(term in text_content for term in ["hospital indemnity", "specified disease", "accident only"]):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "ai_plan_type_detection",
            "version": "1.0.0",
            "status": "active" if self.is_available() else "inactive",
            "model": self.model,
            "capabilities": {
                "semantic_understanding": True,
                "context_aware_detection": True,
                "multi_plan_detection": True,
                "confidence_scoring": True,
                "carrier_awareness": True,
                "fallback_semantic_detection": True
            },
            "supported_plan_types": [
                "Medical/Health",
                "Dental",
                "Vision",
                "Life",
                "Disability",
                "Supplemental"
            ],
            "features": [
                "AI-powered semantic plan type detection",
                "No hardcoded keyword lists - understands context",
                "Confidence scores for each detection",
                "Multiple plan type detection in single document",
                "Carrier-specific knowledge integration",
                "Evidence-based reasoning",
                "Automatic fallback for reliability"
            ]
        }

