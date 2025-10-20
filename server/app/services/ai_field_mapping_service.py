"""
AI-Powered Field Mapping Service

This service uses Mistral AI to intelligently map extracted table headers
to database fields WITHOUT hardcoded patterns. It learns from:
- Semantic meaning of field names
- Context from the document
- Historical mappings from previous uploads
- Business logic understanding

The system provides:
- Confidence scores for each mapping
- Multiple mapping suggestions
- Reasoning for why a mapping was suggested
- Learning from user corrections
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from mistralai import Mistral
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.models import DatabaseField, CarrierFormatLearning, Company
from uuid import UUID

logger = logging.getLogger(__name__)


class AIFieldMappingService:
    """
    Intelligent Field Mapping Service using Mistral AI
    
    This service uses AI to understand field semantics and provide intelligent
    mapping suggestions without relying on hardcoded patterns.
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
                logger.warning("MISTRAL_API_KEY not found - AI field mapping will not be available")
                return
            
            self.client = Mistral(api_key=api_key)
            logger.info("AI Field Mapping Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Field Mapping client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if AI mapping service is available"""
        return self.client is not None
    
    async def get_intelligent_field_mappings(
        self,
        db: AsyncSession,
        extracted_headers: List[str],
        table_sample_data: List[List[str]],
        carrier_id: Optional[UUID] = None,
        document_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get intelligent field mapping suggestions using AI
        
        Args:
            db: Database session
            extracted_headers: List of column headers from extracted table
            table_sample_data: Sample rows from the table for context
            carrier_id: Optional carrier ID to use learned formats
            document_context: Optional document context (carrier name, date, etc.)
            
        Returns:
            Dictionary with mapping suggestions, confidence scores, and reasoning
        """
        try:
            if not self.is_available():
                return {
                    "success": False,
                    "error": "AI Field Mapping service not available",
                    "fallback": True
                }
            
            logger.info(f"🤖 AI Mapping: Analyzing {len(extracted_headers)} headers with AI intelligence")
            logger.info(f"🔍 AI Mapping: carrier_id provided: {carrier_id is not None} (value: {carrier_id if carrier_id else 'None'})")
            
            # Step 1: Get available database fields
            database_fields = await self._get_database_fields(db)
            if not database_fields:
                return {
                    "success": False,
                    "error": "No database fields available for mapping"
                }
            
            # Step 2: Check for learned formats if carrier is known
            learned_mapping = None
            if carrier_id:
                logger.info(f"🎯 Carrier ID is valid, attempting to retrieve learned mapping for carrier {carrier_id}")
                learned_mapping = await self._get_learned_mapping(db, carrier_id, extracted_headers)
                if learned_mapping:
                    logger.info(f"🎯 Found learned mapping for carrier with {learned_mapping.get('match_score', 0):.2f} confidence")
                else:
                    logger.info(f"❌ No learned mapping found for carrier {carrier_id}")
            else:
                logger.warning(f"⚠️ No carrier_id provided - skipping learned format lookup")
            
            # Step 3: If learned mapping exists with high confidence, use it directly
            if learned_mapping and learned_mapping.get('match_score', 0) >= 0.8:
                logger.info(f"🎯 Using learned mappings directly with match score {learned_mapping.get('match_score')}") 
                
                # Convert learned field_mapping to AI mapping format with high confidence
                learned_field_mapping = learned_mapping.get('field_mapping', {})
                direct_mappings = []
                unmapped = []
                
                for header in extracted_headers:
                    # Check if this header has a learned mapping
                    mapped_field = learned_field_mapping.get(header)
                    
                    if mapped_field:
                        # Find the database field details
                        db_field = next((f for f in database_fields if f['display_name'] == mapped_field), None)
                        if db_field:
                            direct_mappings.append({
                                "extracted_field": header,
                                "mapped_to": mapped_field,
                                "mapped_to_column": db_field.get('column_name', mapped_field.lower().replace(' ', '_')),
                                "database_field_id": db_field['id'],
                                "confidence": 0.95,  # High confidence for learned mappings
                                "reasoning": f"Learned from previous mapping (match score: {learned_mapping.get('match_score'):.2f})",
                                "alternatives": [],
                                "requires_review": False
                            })
                        else:
                            unmapped.append(header)
                    else:
                        unmapped.append(header)
                
                response = {
                    "success": True,
                    "mappings": direct_mappings,
                    "overall_confidence": 0.95 if direct_mappings else 0.0,
                    "unmapped_fields": unmapped,
                    "reasoning": {
                        "learned_mappings_applied": len(direct_mappings),
                        "match_score": learned_mapping.get('match_score'),
                        "usage_count": learned_mapping.get('usage_count', 1)
                    },
                    "suggestions_count": len(direct_mappings),
                    "learned_format_used": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"✅ Applied {len(direct_mappings)} learned mappings directly")
                return response
            
            # Step 4: Use AI to understand fields and suggest mappings (when no learned mapping or low confidence)
            ai_mappings = await self._generate_ai_mappings(
                extracted_headers=extracted_headers,
                table_sample_data=table_sample_data,
                database_fields=database_fields,
                learned_mapping=learned_mapping,
                document_context=document_context
            )
            
            # Step 5: Calculate overall confidence and prepare response
            response = {
                "success": True,
                "mappings": ai_mappings.get("mappings", []),
                "overall_confidence": ai_mappings.get("overall_confidence", 0.0),
                "unmapped_fields": ai_mappings.get("unmapped_fields", []),
                "reasoning": ai_mappings.get("reasoning", {}),
                "suggestions_count": len(ai_mappings.get("mappings", [])),
                "learned_format_used": learned_mapping is not None and learned_mapping.get('match_score', 0) < 0.8,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ AI Mapping: Generated {len(ai_mappings.get('mappings', []))} mappings with {ai_mappings.get('overall_confidence', 0):.2f} confidence")
            
            return response
            
        except Exception as e:
            logger.error(f"AI field mapping failed: {e}")
            return {
                "success": False,
                "error": f"AI field mapping failed: {str(e)}",
                "fallback": True
            }
    
    async def _get_database_fields(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get active database fields with descriptions"""
        try:
            result = await db.execute(
                select(DatabaseField).where(DatabaseField.is_active == 1)
            )
            fields = result.scalars().all()
            
            return [
                {
                    "id": str(field.id),
                    "display_name": field.display_name,
                    "description": field.description or "",
                    "column_name": field.display_name.lower().replace(" ", "_")
                }
                for field in fields
            ]
            
        except Exception as e:
            logger.error(f"Failed to get database fields: {e}")
            return []
    
    async def _get_learned_mapping(
        self,
        db: AsyncSession,
        carrier_id: UUID,
        headers: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get learned field mapping for this carrier if available"""
        try:
            # CRITICAL FIX: Use the same signature generation logic as format learning service
            # Import the format learning service to use consistent signature generation
            from app.services.format_learning_service import FormatLearningService
            format_learning_service = FormatLearningService()
            
            # Generate format signature using the same method as when saving
            table_structure = {
                'column_count': len(headers),
                'has_header_row': True
            }
            headers_signature = format_learning_service.generate_format_signature(headers, table_structure)
            
            logger.info(f"🔍 Generated format signature for lookup: {headers_signature}")
            logger.info(f"🔍 Looking up learned format for carrier {carrier_id} with {len(headers)} headers")
            
            # Look for exact or similar format match
            result = await db.execute(
                select(CarrierFormatLearning).where(
                    and_(
                        CarrierFormatLearning.company_id == carrier_id,
                        CarrierFormatLearning.format_signature == headers_signature
                    )
                )
            )
            
            format_learning = result.scalar_one_or_none()
            
            if format_learning and format_learning.field_mapping:
                logger.info(f"✅ Found EXACT match for learned format with signature {headers_signature}")
                logger.info(f"✅ Learned field mapping has {len(format_learning.field_mapping)} mappings")
                return {
                    "field_mapping": format_learning.field_mapping,
                    "confidence_score": format_learning.confidence_score / 100.0,
                    "match_score": 1.0,  # Exact match
                    "usage_count": format_learning.usage_count,
                    "table_editor_settings": format_learning.table_editor_settings
                }
            
            logger.info(f"❌ No exact match found, trying fuzzy matching...")
            
            # If no exact match, look for similar formats (fuzzy match)
            result = await db.execute(
                select(CarrierFormatLearning).where(
                    CarrierFormatLearning.company_id == carrier_id
                ).order_by(CarrierFormatLearning.usage_count.desc())
            )
            
            formats = result.scalars().all()
            logger.info(f"🔍 Found {len(formats)} saved formats for fuzzy matching")
            
            # Find best matching format using header similarity
            best_match = None
            best_score = 0.0
            
            for fmt in formats:
                if not fmt.headers or not fmt.field_mapping:
                    continue
                
                # Calculate similarity score
                similarity = self._calculate_header_similarity(headers, fmt.headers)
                logger.info(f"🔍 Format signature {fmt.format_signature}: similarity = {similarity:.2f}")
                
                if similarity > best_score and similarity > 0.5:  # Lower threshold to 0.5 for better matching
                    best_score = similarity
                    best_match = {
                        "field_mapping": fmt.field_mapping,
                        "confidence_score": fmt.confidence_score / 100.0,
                        "match_score": similarity,
                        "usage_count": fmt.usage_count,
                        "table_editor_settings": fmt.table_editor_settings
                    }
                    logger.info(f"✅ New best match with similarity {similarity:.2f}")
            
            if best_match:
                logger.info(f"✅ Found similar format with {best_score:.2f} similarity score")
            else:
                logger.info(f"❌ No matching format found")
            
            return best_match
            
        except Exception as e:
            logger.error(f"Failed to get learned mapping: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_header_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """Calculate similarity between two header lists with improved matching"""
        try:
            # Use format learning service's header similarity calculation for consistency
            from app.services.format_learning_service import FormatLearningService
            format_learning_service = FormatLearningService()
            
            similarity = format_learning_service._calculate_header_similarity(headers1, headers2)
            
            return similarity
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            # Fallback to simple Jaccard similarity
            try:
                h1_norm = [h.lower().strip() for h in headers1]
                h2_norm = [h.lower().strip() for h in headers2]
                
                set1 = set(h1_norm)
                set2 = set(h2_norm)
                
                intersection = len(set1.intersection(set2))
                union = len(set1.union(set2))
                
                if union == 0:
                    return 0.0
                
                return intersection / union
            except Exception as fallback_error:
                logger.error(f"Fallback similarity calculation also failed: {fallback_error}")
                return 0.0
    
    async def _generate_ai_mappings(
        self,
        extracted_headers: List[str],
        table_sample_data: List[List[str]],
        database_fields: List[Dict[str, Any]],
        learned_mapping: Optional[Dict[str, Any]],
        document_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use AI to generate intelligent field mappings"""
        try:
            # Prepare sample data for context (first 3 rows)
            sample_rows = table_sample_data[:3] if table_sample_data else []
            
            # Create intelligent prompt
            prompt = self._create_mapping_prompt(
                extracted_headers=extracted_headers,
                sample_rows=sample_rows,
                database_fields=database_fields,
                learned_mapping=learned_mapping,
                document_context=document_context
            )
            
            # Call Mistral AI for intelligent mapping
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in data field mapping for commission tracking systems.
Your task is to intelligently map extracted table headers to database fields by understanding:
- Semantic meaning of field names
- Context from sample data
- Business logic in commission tracking
- Common field naming patterns

Provide confidence scores (0.0-1.0) based on:
- Semantic similarity
- Data type compatibility
- Context alignment
- Business logic fit

Return ONLY valid JSON with no additional text."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent mapping
                max_tokens=2000
            )
            
            # Parse AI response
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                ai_result = json.loads(content)
                
                logger.info("✅ AI successfully generated field mappings")
                return self._process_ai_mappings(ai_result, extracted_headers, database_fields)
            
            return {
                "mappings": [],
                "overall_confidence": 0.0,
                "unmapped_fields": extracted_headers,
                "reasoning": {"error": "No response from AI"}
            }
            
        except Exception as e:
            logger.error(f"AI mapping generation failed: {e}")
            # Fallback to rule-based mapping
            return await self._fallback_mapping(extracted_headers, database_fields)
    
    def _create_mapping_prompt(
        self,
        extracted_headers: List[str],
        sample_rows: List[List[str]],
        database_fields: List[Dict[str, Any]],
        learned_mapping: Optional[Dict[str, Any]],
        document_context: Optional[Dict[str, Any]]
    ) -> str:
        """Create intelligent prompt for AI field mapping"""
        
        # Format sample data for context
        sample_data_str = ""
        if sample_rows and extracted_headers:
            sample_data_str = "\n\nSAMPLE DATA (first 3 rows):\n"
            for i, row in enumerate(sample_rows[:3], 1):
                sample_data_str += f"Row {i}:\n"
                for header, value in zip(extracted_headers, row):
                    sample_data_str += f"  {header}: {value}\n"
        
        # Format database fields
        db_fields_str = "\n".join([
            f"- {field['display_name']}: {field['description']}" 
            for field in database_fields
        ])
        
        # Format learned mapping if available
        learned_str = ""
        if learned_mapping:
            learned_str = f"\n\nLEARNED MAPPINGS (from previous uploads, {learned_mapping['confidence_score']:.2f} confidence):\n"
            learned_str += json.dumps(learned_mapping.get('field_mapping', {}), indent=2)
        
        # Format document context
        context_str = ""
        if document_context:
            context_str = f"\n\nDOCUMENT CONTEXT:\n"
            context_str += f"- Carrier: {document_context.get('carrier_name', 'Unknown')}\n"
            context_str += f"- Date: {document_context.get('statement_date', 'Unknown')}\n"
            context_str += f"- Document Type: {document_context.get('document_type', 'Commission Statement')}\n"
        
        return f"""Analyze these extracted table headers and map them to the appropriate database fields.

EXTRACTED HEADERS:
{json.dumps(extracted_headers, indent=2)}
{sample_data_str}

AVAILABLE DATABASE FIELDS:
{db_fields_str}
{learned_str}{context_str}

TASK:
For each extracted header, suggest the best matching database field(s) with:
1. Confidence score (0.0-1.0) based on semantic similarity and context
2. Reasoning explaining why this mapping makes sense
3. Alternative suggestions if confidence is low

Consider:
- Semantic meaning (e.g., "Group Name" → "Company Name")
- Data type from samples (e.g., currency values → commission fields)
- Business context (commission tracking system)
- Learned patterns from previous mappings

RESPONSE FORMAT (JSON only, no additional text):
{{
  "mappings": [
    {{
      "extracted_field": "Policy_Num",
      "mapped_to": "Policy Number",
      "mapped_to_column": "policy_number",
      "confidence": 0.95,
      "reasoning": "Direct semantic match, common policy identifier field",
      "alternatives": [
        {{
          "field": "Group Id",
          "confidence": 0.3,
          "reasoning": "Could be a group identifier but less likely"
        }}
      ]
    }}
  ],
  "unmapped_fields": ["Field1", "Field2"],
  "overall_confidence": 0.85,
  "reasoning": {{
    "high_confidence_mappings": 5,
    "low_confidence_mappings": 2,
    "unmapped_count": 2,
    "notes": "Most fields have clear semantic matches"
  }}
}}

Provide ONLY the JSON response with no additional explanation or text."""
    
    def _process_ai_mappings(
        self,
        ai_result: Dict[str, Any],
        extracted_headers: List[str],
        database_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and validate AI mapping results"""
        try:
            mappings = ai_result.get("mappings", [])
            unmapped = ai_result.get("unmapped_fields", [])
            
            # Validate and enrich mappings
            processed_mappings = []
            for mapping in mappings:
                # Ensure all required fields are present
                if not all(key in mapping for key in ["extracted_field", "mapped_to", "confidence"]):
                    continue
                
                # Add database field details
                db_field = next(
                    (f for f in database_fields if f["display_name"] == mapping["mapped_to"]),
                    None
                )
                
                if db_field:
                    processed_mapping = {
                        **mapping,
                        "database_field_id": db_field["id"],
                        "column_name": db_field["column_name"],
                        "requires_review": mapping["confidence"] < 0.7
                    }
                    processed_mappings.append(processed_mapping)
            
            # Calculate overall metrics
            avg_confidence = sum(m["confidence"] for m in processed_mappings) / len(processed_mappings) if processed_mappings else 0.0
            
            return {
                "mappings": processed_mappings,
                "unmapped_fields": unmapped,
                "overall_confidence": avg_confidence,
                "reasoning": ai_result.get("reasoning", {}),
                "mapping_statistics": {
                    "total_fields": len(extracted_headers),
                    "mapped_count": len(processed_mappings),
                    "unmapped_count": len(unmapped),
                    "high_confidence_count": sum(1 for m in processed_mappings if m["confidence"] >= 0.8),
                    "medium_confidence_count": sum(1 for m in processed_mappings if 0.5 <= m["confidence"] < 0.8),
                    "low_confidence_count": sum(1 for m in processed_mappings if m["confidence"] < 0.5)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process AI mappings: {e}")
            return {
                "mappings": [],
                "unmapped_fields": extracted_headers,
                "overall_confidence": 0.0,
                "reasoning": {"error": str(e)}
            }
    
    async def _fallback_mapping(
        self,
        extracted_headers: List[str],
        database_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fallback to simple similarity-based mapping when AI fails"""
        try:
            logger.info("Using fallback similarity-based mapping")
            
            mappings = []
            unmapped = []
            
            for header in extracted_headers:
                best_match = None
                best_score = 0.0
                
                # Calculate similarity with each database field
                for db_field in database_fields:
                    score = self._calculate_string_similarity(
                        header.lower(),
                        db_field["display_name"].lower()
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_match = db_field
                
                # Only include if similarity is above threshold
                if best_match and best_score > 0.4:
                    mappings.append({
                        "extracted_field": header,
                        "mapped_to": best_match["display_name"],
                        "mapped_to_column": best_match["column_name"],
                        "database_field_id": best_match["id"],
                        "confidence": best_score,
                        "reasoning": f"String similarity match (score: {best_score:.2f})",
                        "requires_review": best_score < 0.7,
                        "alternatives": []
                    })
                else:
                    unmapped.append(header)
            
            avg_confidence = sum(m["confidence"] for m in mappings) / len(mappings) if mappings else 0.0
            
            return {
                "mappings": mappings,
                "unmapped_fields": unmapped,
                "overall_confidence": avg_confidence,
                "reasoning": {
                    "method": "fallback_similarity",
                    "note": "AI mapping not available, using similarity matching"
                },
                "mapping_statistics": {
                    "total_fields": len(extracted_headers),
                    "mapped_count": len(mappings),
                    "unmapped_count": len(unmapped)
                }
            }
            
        except Exception as e:
            logger.error(f"Fallback mapping failed: {e}")
            return {
                "mappings": [],
                "unmapped_fields": extracted_headers,
                "overall_confidence": 0.0,
                "reasoning": {"error": str(e)}
            }
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using Levenshtein distance"""
        try:
            # Normalize strings
            s1 = str1.lower().strip()
            s2 = str2.lower().strip()
            
            # Simple character-based similarity
            if s1 == s2:
                return 1.0
            
            # Calculate Levenshtein distance
            len1, len2 = len(s1), len(s2)
            if len1 == 0 or len2 == 0:
                return 0.0
            
            # Create matrix
            matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
            
            for i in range(len1 + 1):
                matrix[i][0] = i
            for j in range(len2 + 1):
                matrix[0][j] = j
            
            for i in range(1, len1 + 1):
                for j in range(1, len2 + 1):
                    cost = 0 if s1[i-1] == s2[j-1] else 1
                    matrix[i][j] = min(
                        matrix[i-1][j] + 1,      # deletion
                        matrix[i][j-1] + 1,      # insertion
                        matrix[i-1][j-1] + cost  # substitution
                    )
            
            distance = matrix[len1][len2]
            max_len = max(len1, len2)
            
            return 1.0 - (distance / max_len)
            
        except Exception as e:
            logger.error(f"String similarity calculation failed: {e}")
            return 0.0
    
    async def save_user_corrections(
        self,
        db: AsyncSession,
        upload_id: UUID,
        carrier_id: Optional[UUID],
        original_mappings: Dict[str, str],
        corrected_mappings: Dict[str, str],
        headers: List[str]
    ) -> bool:
        """
        Save user corrections to learn from them
        
        This allows the system to improve over time by learning from user feedback
        """
        try:
            if not carrier_id:
                logger.warning("Cannot save corrections without carrier_id")
                return False
            
            # Generate format signature
            from hashlib import md5
            headers_signature = md5(json.dumps(sorted(headers)).encode()).hexdigest()
            
            # Look for existing format learning entry
            result = await db.execute(
                select(CarrierFormatLearning).where(
                    and_(
                        CarrierFormatLearning.company_id == carrier_id,
                        CarrierFormatLearning.format_signature == headers_signature
                    )
                )
            )
            
            format_learning = result.scalar_one_or_none()
            
            if format_learning:
                # Update existing entry
                format_learning.field_mapping = corrected_mappings
                format_learning.usage_count += 1
                format_learning.confidence_score = min(100, format_learning.confidence_score + 5)  # Increase confidence
                format_learning.last_used = datetime.utcnow()
                format_learning.updated_at = datetime.utcnow()
                
                logger.info(f"✅ Updated learned format with user corrections (confidence: {format_learning.confidence_score})")
            else:
                # Create new format learning entry
                format_learning = CarrierFormatLearning(
                    company_id=carrier_id,
                    format_signature=headers_signature,
                    headers=headers,
                    field_mapping=corrected_mappings,
                    confidence_score=70,  # Start with medium confidence
                    usage_count=1
                )
                db.add(format_learning)
                
                logger.info("✅ Created new format learning entry from user corrections")
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user corrections: {e}")
            await db.rollback()
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "ai_field_mapping",
            "version": "1.0.0",
            "status": "active" if self.is_available() else "inactive",
            "model": self.model,
            "capabilities": {
                "semantic_understanding": True,
                "context_aware_mapping": True,
                "learned_format_integration": True,
                "confidence_scoring": True,
                "user_correction_learning": True,
                "fallback_similarity_matching": True
            },
            "features": [
                "AI-powered semantic field mapping",
                "No hardcoded patterns - learns from context",
                "Confidence scores for each mapping",
                "Multiple suggestion alternatives",
                "Integration with format learning",
                "User correction feedback loop",
                "Automatic fallback for reliability"
            ]
        }

