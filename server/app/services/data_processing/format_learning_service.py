import hashlib
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud, schemas
from app.utils.db_retry import with_db_retry
from difflib import SequenceMatcher


class FormatLearningService:
    """
    Service for learning and analyzing carrier file formats.
    """
    
    def __init__(self):
        self.data_type_patterns = {
            'date': [
                r'\d{1,2}/\d{1,2}/\d{2,4}',
                r'\d{4}-\d{2}-\d{2}',
                r'\d{1,2}-\d{1,2}-\d{2,4}',
                r'\d{1,2}\.\d{1,2}\.\d{2,4}'
            ],
            'currency': [
                r'^\$?\d{1,3}(,\d{3})*(\.\d{2})?$',
                r'^\d{1,3}(,\d{3})*(\.\d{2})?$'
            ],
            'percentage': [
                r'^\d+(\.\d+)?%$',
                r'^\d+(\.\d+)?\s*%$'
            ],
            'phone': [
                r'^\d{3}-\d{3}-\d{4}$',
                r'^\(\d{3}\)\s*\d{3}-\d{4}$',
                r'^\d{10}$'
            ],
            'ssn': [
                r'^\d{3}-\d{2}-\d{4}$',
                r'^\d{9}$'
            ]
        }
    
    def _convert_numpy_types(self, obj):
        """
        Convert numpy types to native Python types for JSON serialization.
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        else:
            return obj
    
    def generate_format_signature(self, headers: List[str], table_structure: dict) -> str:
        """
        Generate a more flexible signature for a table format based on headers and structure.
        This version is more tolerant of minor variations while still being specific enough.
        """
        # Create a more flexible normalized representation
        normalized_headers = []
        for h in headers:
            if h:
                # Remove common variations and normalize
                normalized = h.lower().strip()
                # Remove common prefixes/suffixes that don't affect meaning
                normalized = re.sub(r'^(total|sum|amount|value|price|cost|fee|charge|commission|earned|paid|due|balance|net|gross)\s*', '', normalized)
                normalized = re.sub(r'\s*(total|sum|amount|value|price|cost|fee|charge|commission|earned|paid|due|balance|net|gross)$', '', normalized)
                # Remove punctuation and extra spaces
                normalized = re.sub(r'[^\w\s]', '', normalized)
                normalized = re.sub(r'\s+', ' ', normalized).strip()
                if normalized:
                    normalized_headers.append(normalized)
        
        # Sort for consistency but keep some order information
        normalized_headers.sort()
        
        # Include structural information but be more flexible
        structure_info = {
            'column_count': table_structure.get('column_count', len(headers)),
            'has_header_row': table_structure.get('has_header_row', True)
        }
        
        # Create signature string
        signature_data = {
            'headers': normalized_headers,
            'structure': structure_info
        }
        
        # Generate hash
        signature_string = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_string.encode()).hexdigest()
    
    def analyze_column_types(self, table_data: List[List[str]], headers: List[str]) -> Dict[str, str]:
        """
        Analyze data types for each column based on sample values.
        """
        if not table_data or not headers:
            return {}
        
        column_types = {}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(table_data, columns=headers)
        
        for column in headers:
            if column not in df.columns:
                continue
            
            # Get non-null values
            values = df[column].dropna().astype(str)
            if len(values) == 0:
                column_types[column] = 'string'
                continue
            
            # Sample values for analysis
            sample_values = values.head(20).tolist()
            
            # Analyze patterns
            detected_type = self._detect_column_type(sample_values)
            column_types[column] = detected_type
        
        return column_types
    
    def _detect_column_type(self, values: List[str]) -> str:
        """
        Detect the most likely data type for a column based on sample values.
        """
        if not values:
            return 'string'
        
        # Count matches for each pattern type
        type_scores = {
            'date': 0,
            'currency': 0,
            'percentage': 0,
            'phone': 0,
            'ssn': 0,
            'number': 0,
            'string': 0
        }
        
        for value in values:
            value = str(value).strip()
            
            # Check specific patterns
            for pattern_type, patterns in self.data_type_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, value):
                        type_scores[pattern_type] += 1
                        break
            
            # Check if numeric
            try:
                float(value.replace(',', '').replace('$', '').replace('%', ''))
                type_scores['number'] += 1
            except ValueError:
                type_scores['string'] += 1
        
        # Find the type with highest score
        best_type = max(type_scores, key=type_scores.get)
        
        # If no specific pattern matched, default to string
        if best_type == 'string' and type_scores['number'] > 0:
            best_type = 'number'
        
        return best_type
    
    def extract_column_patterns(self, table_data: List[List[str]], headers: List[str]) -> Dict[str, str]:
        """
        Extract regex patterns for each column based on sample values.
        """
        if not table_data or not headers:
            return {}
        
        column_patterns = {}
        df = pd.DataFrame(table_data, columns=headers)
        
        for column in headers:
            if column not in df.columns:
                continue
            
            values = df[column].dropna().astype(str)
            if len(values) == 0:
                continue
            
            # Get sample values
            sample_values = values.head(10).tolist()
            
            # Generate pattern
            pattern = self._generate_pattern_from_values(sample_values)
            if pattern:
                column_patterns[column] = pattern
        
        return column_patterns
    
    def _generate_pattern_from_values(self, values: List[str]) -> Optional[str]:
        """
        Generate a regex pattern from sample values.
        """
        if not values:
            return None
        
        # Simple pattern generation based on common formats
        first_value = values[0]
        
        # Date patterns
        if re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', first_value):
            return r'\d{1,2}/\d{1,2}/\d{2,4}'
        
        # Currency patterns
        if re.match(r'^\$?\d{1,3}(,\d{3})*(\.\d{2})?$', first_value):
            return r'^\$?\d{1,3}(,\d{3})*(\.\d{2})?$'
        
        # Percentage patterns
        if re.match(r'^\d+(\.\d+)?%$', first_value):
            return r'^\d+(\.\d+)?%$'
        
        # Phone patterns
        if re.match(r'^\d{3}-\d{3}-\d{4}$', first_value):
            return r'^\d{3}-\d{3}-\d{4}$'
        
        # SSN patterns
        if re.match(r'^\d{3}-\d{2}-\d{4}$', first_value):
            return r'^\d{3}-\d{2}-\d{4}$'
        
        return None
    
    def analyze_table_structure(self, table_data: List[List[str]], headers: List[str]) -> Dict[str, Any]:
        """
        Analyze the structure of a table.
        """
        if not table_data:
            return {}
        
        structure = {
            'column_count': len(headers),
            'row_count': len(table_data),
            'typical_row_count': len(table_data),
            'has_header_row': True,
            'max_column_lengths': {},
            'min_column_lengths': {},
            'avg_column_lengths': {}
        }
        
        # Analyze column lengths
        for i, header in enumerate(headers):
            column_values = [str(row[i]) if i < len(row) else '' for row in table_data]
            lengths = [len(val) for val in column_values]
            
            if lengths:
                structure['max_column_lengths'][header] = max(lengths)
                structure['min_column_lengths'][header] = min(lengths)
                structure['avg_column_lengths'][header] = sum(lengths) / len(lengths)
        
        return structure
    
    def calculate_data_quality_metrics(self, table_data: List[List[str]], headers: List[str]) -> Dict[str, Any]:
        """
        Calculate data quality metrics for the table.
        """
        if not table_data or not headers:
            return {}
        
        df = pd.DataFrame(table_data, columns=headers)
        
        quality_metrics = {
            'total_cells': len(df) * len(df.columns),
            'missing_cells': df.isnull().sum().sum(),
            'completeness': 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns))),
            'column_completeness': {},
            'duplicate_rows': len(df) - len(df.drop_duplicates()),
            'duplicate_percentage': (len(df) - len(df.drop_duplicates())) / len(df) if len(df) > 0 else 0
        }
        
        # Calculate completeness for each column
        for column in headers:
            if column in df.columns:
                missing_count = df[column].isnull().sum()
                total_count = len(df)
                quality_metrics['column_completeness'][column] = 1 - (missing_count / total_count) if total_count > 0 else 0
        
        # Convert numpy types to native Python types
        quality_metrics = self._convert_numpy_types(quality_metrics)
        
        return quality_metrics
    
    def extract_sample_values(self, table_data: List[List[str]], headers: List[str], max_samples: int = 5) -> Dict[str, List[str]]:
        """
        Extract sample values for each column.
        """
        if not table_data or not headers:
            return {}
        
        sample_values = {}
        df = pd.DataFrame(table_data, columns=headers)
        
        for column in headers:
            if column in df.columns:
                values = df[column].dropna().astype(str).unique()
                sample_values[column] = values[:max_samples].tolist()
        
        return sample_values
    
    async def learn_from_processed_file(
        self, 
        db: AsyncSession, 
        company_id: str, 
        table_data: List[List[str]], 
        headers: List[str], 
        field_mapping: Dict[str, str],
        confidence_score: int = 80,
        table_editor_settings: Optional[Dict[str, Any]] = None,
        carrier_name: Optional[str] = None,
        statement_date: Optional[str] = None
    ) -> bool:
        """
        Learn from a processed file and save the format information.
        """
        try:
            print(f"🎯 FormatLearningService: Learning from processed file for company {company_id}")
            print(f"🎯 FormatLearningService: Headers: {headers}")
            print(f"🎯 FormatLearningService: Field mapping: {field_mapping}")
            print(f"🎯 FormatLearningService: Table data length: {len(table_data)}")
            
            # Analyze the table
            table_structure = self.analyze_table_structure(table_data, headers)
            column_types = self.analyze_column_types(table_data, headers)
            column_patterns = self.extract_column_patterns(table_data, headers)
            sample_values = self.extract_sample_values(table_data, headers)
            data_quality_metrics = self.calculate_data_quality_metrics(table_data, headers)
            
            # Generate format signature
            format_signature = self.generate_format_signature(headers, table_structure)
            print(f"🎯 FormatLearningService: Generated format signature: {format_signature}")
            
            # Convert all data to JSON-serializable format
            table_structure = self._convert_numpy_types(table_structure)
            column_types = self._convert_numpy_types(column_types)
            column_patterns = self._convert_numpy_types(column_patterns)
            sample_values = self._convert_numpy_types(sample_values)
            data_quality_metrics = self._convert_numpy_types(data_quality_metrics)
            field_mapping = self._convert_numpy_types(field_mapping)
            
            # Enhanced table editor settings with carrier, date, and deletion info
            # CRITICAL: This stores ALL user corrections and edits so format learning remembers them
            enhanced_table_editor_settings = table_editor_settings or {}
            
            # Save corrected carrier name
            if carrier_name:
                enhanced_table_editor_settings['carrier_name'] = carrier_name
                enhanced_table_editor_settings['corrected_carrier_name'] = carrier_name  # Explicitly mark as corrected
                print(f"🎯 FormatLearningService: Saving corrected carrier name: {carrier_name}")
            
            # Save corrected statement date
            if statement_date:
                enhanced_table_editor_settings['statement_date'] = statement_date
                enhanced_table_editor_settings['corrected_statement_date'] = statement_date  # Explicitly mark as corrected
                print(f"🎯 FormatLearningService: Saving corrected statement date: {statement_date}")
            
            # Save table editor deletions and edits
            # These include deleted tables, deleted rows, and any manual adjustments
            if table_editor_settings:
                if 'deleted_tables' in table_editor_settings:
                    enhanced_table_editor_settings['deleted_tables'] = table_editor_settings['deleted_tables']
                    print(f"🎯 FormatLearningService: Saving deleted tables: {table_editor_settings['deleted_tables']}")
                
                if 'deleted_rows' in table_editor_settings:
                    enhanced_table_editor_settings['deleted_rows'] = table_editor_settings['deleted_rows']
                    print(f"🎯 FormatLearningService: Saving deleted rows: {len(table_editor_settings.get('deleted_rows', []))} rows")
                
                if 'table_deletions' in table_editor_settings:
                    enhanced_table_editor_settings['table_deletions'] = table_editor_settings['table_deletions']
                    print(f"🎯 FormatLearningService: Saving table deletions: {table_editor_settings['table_deletions']}")
                
                if 'row_deletions' in table_editor_settings:
                    enhanced_table_editor_settings['row_deletions'] = table_editor_settings['row_deletions']
                    print(f"🎯 FormatLearningService: Saving row deletions: {table_editor_settings['row_deletions']}")
            
            print(f"🎯 FormatLearningService: Final enhanced table editor settings keys: {list(enhanced_table_editor_settings.keys())}")
            
            # Create format learning record
            format_learning = schemas.CarrierFormatLearningCreate(
                company_id=company_id,
                format_signature=format_signature,
                headers=headers,
                header_patterns=None,  # Could be enhanced later
                column_types=column_types,
                column_patterns=column_patterns,
                sample_values=sample_values,
                table_structure=table_structure,
                data_quality_metrics=data_quality_metrics,
                field_mapping=field_mapping,
                table_editor_settings=enhanced_table_editor_settings,
                confidence_score=confidence_score,
                usage_count=1
            )
            
            # Save to database
            await with_db_retry(db, crud.save_carrier_format_learning, format_learning=format_learning)
            
            print(f"🎯 FormatLearningService: Successfully learned format for company {company_id}")
            return True
            
        except Exception as e:
            print(f"Error learning from processed file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def find_matching_format(
        self, 
        db: AsyncSession, 
        company_id: str, 
        headers: List[str], 
        table_structure: dict
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Find the best matching format for a new file with improved matching logic.
        """
        try:
            print(f"🎯 FormatLearningService: Finding matching format for company {company_id}")
            print(f"🎯 FormatLearningService: Headers: {headers}")
            print(f"🎯 FormatLearningService: Table structure: {table_structure}")
            print(f"🎯 FormatLearningService: Headers type: {type(headers)}")
            print(f"🎯 FormatLearningService: Headers length: {len(headers) if headers else 0}")
            
            best_match, score = await with_db_retry(
                db, 
                crud.find_best_matching_format, 
                company_id=company_id, 
                headers=headers, 
                table_structure=table_structure
            )
            
            print(f"🎯 FormatLearningService: Best match score: {score}")
            
            if best_match:
                print(f"🎯 FormatLearningService: Found matching format with signature: {best_match.format_signature}")
                print(f"🎯 FormatLearningService: Learned field mapping: {best_match.field_mapping}")
                print(f"🎯 FormatLearningService: Learned table editor settings: {best_match.table_editor_settings}")
                
                return {
                    'format_signature': best_match.format_signature,
                    'headers': best_match.headers,
                    'column_types': best_match.column_types,
                    'column_patterns': best_match.column_patterns,
                    'field_mapping': best_match.field_mapping,
                    'table_editor_settings': best_match.table_editor_settings,
                    'confidence_score': best_match.confidence_score,
                    'usage_count': best_match.usage_count
                }, score
            else:
                print(f"🎯 FormatLearningService: No matching format found")
            
            return None, 0.0
            
        except Exception as e:
            print(f"Error finding matching format: {e}")
            import traceback
            traceback.print_exc()
            return None, 0.0
    
    def find_matching_format_sync(
        self, 
        company_id: str, 
        headers: List[str], 
        table_structure: dict
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Synchronous version of find_matching_format for use in non-async contexts.
        """
        try:
            print(f"🎯 FormatLearningService: Finding matching format (sync) for company {company_id}")
            print(f"🎯 FormatLearningService: Headers: {headers}")
            print(f"🎯 FormatLearningService: Table structure: {table_structure}")
            
            # Import here to avoid circular imports
            from app.db import crud
            from app.utils.db_retry import with_db_retry_sync
            
            # Get all formats for this company
            formats = with_db_retry_sync(crud.get_carrier_formats_for_company, company_id=company_id)
            print(f"🎯 FormatLearningService: Found {len(formats)} saved formats for company")
            
            best_match = None
            best_score = 0.0
            
            for format_record in formats:
                # Calculate similarity score using improved logic
                header_similarity = crud.calculate_header_similarity(headers, format_record.headers)
                structure_similarity = crud.calculate_structure_similarity(table_structure, format_record.table_structure)
                
                # Combined score (weighted average) - header similarity is more important
                total_score = (header_similarity * 0.8) + (structure_similarity * 0.2)
                
                print(f"🎯 FormatLearningService: Comparing with saved format:")
                print(f"🎯 FormatLearningService:   Saved headers: {format_record.headers}")
                print(f"🎯 FormatLearningService:   Header similarity: {header_similarity}")
                print(f"🎯 FormatLearningService:   Structure similarity: {structure_similarity}")
                print(f"🎯 FormatLearningService:   Total score: {total_score}")
                
                # Lower threshold for better matching - 0.5 instead of 0.6
                if total_score > best_score and total_score > 0.5:  # Even more flexible threshold
                    best_score = total_score
                    best_match = format_record
                    print(f"🎯 FormatLearningService:   -> New best match with score {total_score}")
            
            if best_match:
                print(f"🎯 FormatLearningService: Found matching format with signature: {best_match.format_signature}")
                print(f"🎯 FormatLearningService: Learned field mapping: {best_match.field_mapping}")
                print(f"🎯 FormatLearningService: Learned table editor settings: {best_match.table_editor_settings}")
                
                return {
                    'format_signature': best_match.format_signature,
                    'headers': best_match.headers,
                    'column_types': best_match.column_types,
                    'column_patterns': best_match.column_patterns,
                    'field_mapping': best_match.field_mapping,
                    'table_editor_settings': best_match.table_editor_settings,
                    'confidence_score': best_match.confidence_score,
                    'usage_count': best_match.usage_count
                }, best_score
            else:
                print(f"🎯 FormatLearningService: No matching format found")
            
            return None, 0.0
            
        except Exception as e:
            print(f"Error finding matching format (sync): {e}")
            import traceback
            traceback.print_exc()
            return None, 0.0
    
    def validate_data_against_learned_format(
        self, 
        table_data: List[List[str]], 
        headers: List[str], 
        learned_format: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate new data against a learned format.
        """
        validation_results = {
            'overall_score': 0.0,
            'header_match_score': 0.0,
            'data_type_validation': {},
            'pattern_validation': {},
            'structure_validation': {},
            'warnings': [],
            'errors': []
        }
        
        # Validate headers
        if 'headers' in learned_format:
            header_similarity = self._calculate_header_similarity(headers, learned_format['headers'])
            validation_results['header_match_score'] = header_similarity
        
        # Validate data types
        if 'column_types' in learned_format:
            current_column_types = self.analyze_column_types(table_data, headers)
            for column, expected_type in learned_format['column_types'].items():
                if column in current_column_types:
                    current_type = current_column_types[column]
                    validation_results['data_type_validation'][column] = {
                        'expected': expected_type,
                        'actual': current_type,
                        'match': expected_type == current_type
                    }
                    
                    if expected_type != current_type:
                        validation_results['warnings'].append(
                            f"Column '{column}' expected type '{expected_type}' but found '{current_type}'"
                        )
        
        # Validate patterns
        if 'column_patterns' in learned_format:
            current_patterns = self.extract_column_patterns(table_data, headers)
            for column, expected_pattern in learned_format['column_patterns'].items():
                if column in current_patterns:
                    current_pattern = current_patterns[column]
                    validation_results['pattern_validation'][column] = {
                        'expected': expected_pattern,
                        'actual': current_pattern,
                        'match': expected_pattern == current_pattern
                    }
        
        # Calculate overall score
        scores = [validation_results['header_match_score']]
        scores.extend([
            v['match'] for v in validation_results['data_type_validation'].values()
        ])
        scores.extend([
            v['match'] for v in validation_results['pattern_validation'].values()
        ])
        
        if scores:
            validation_results['overall_score'] = sum(scores) / len(scores)
        
        return validation_results
    
    def _calculate_header_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """
        Calculate similarity between two header lists using improved matching.
        """
        if not headers1 or not headers2:
            return 0.0
        
        # Normalize headers
        headers1_normalized = [self._normalize_header(h) for h in headers1 if h]
        headers2_normalized = [self._normalize_header(h) for h in headers2 if h]
        
        if not headers1_normalized or not headers2_normalized:
            return 0.0
        
        # Calculate similarity using multiple methods
        exact_matches = 0
        fuzzy_matches = 0
        total_headers = max(len(headers1_normalized), len(headers2_normalized))
        
        # Find exact matches first
        used_headers2 = set()
        for h1 in headers1_normalized:
            for i, h2 in enumerate(headers2_normalized):
                if i not in used_headers2 and h1 == h2:
                    exact_matches += 1
                    used_headers2.add(i)
                    break
        
        # Find fuzzy matches for remaining headers
        remaining_headers1 = [h for i, h in enumerate(headers1_normalized) if i not in used_headers2]
        remaining_headers2 = [h for i, h in enumerate(headers2_normalized) if i not in used_headers2]
        
        for h1 in remaining_headers1:
            best_match_score = 0
            best_match_idx = -1
            
            for i, h2 in enumerate(remaining_headers2):
                if i not in used_headers2:
                    similarity = SequenceMatcher(None, h1, h2).ratio()
                    if similarity > best_match_score and similarity > 0.7:  # 70% similarity threshold
                        best_match_score = similarity
                        best_match_idx = i
            
            if best_match_idx >= 0:
                fuzzy_matches += 1
                used_headers2.add(best_match_idx)
        
        # Calculate weighted score
        exact_score = exact_matches / total_headers if total_headers > 0 else 0
        fuzzy_score = fuzzy_matches / total_headers if total_headers > 0 else 0
        
        # Weight exact matches higher than fuzzy matches
        total_score = (exact_score * 0.8) + (fuzzy_score * 0.2)
        
        return total_score
    
    def _normalize_header(self, header: str) -> str:
        """
        Normalize a header string for better matching.
        """
        if not header:
            return ""
        
        # Convert to lowercase and remove extra spaces
        normalized = header.lower().strip()
        
        # Remove common prefixes/suffixes that don't affect meaning
        normalized = re.sub(r'^(total|sum|amount|value|price|cost|fee|charge|commission|earned|paid|due|balance|net|gross)\s*', '', normalized)
        normalized = re.sub(r'\s*(total|sum|amount|value|price|cost|fee|charge|commission|earned|paid|due|balance|net|gross)$', '', normalized)
        
        # Remove punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    async def learn_from_user_corrections(
        self,
        db: AsyncSession,
        company_id: str,
        original_carrier: Optional[str],
        corrected_carrier: Optional[str],
        original_date: Optional[str],
        corrected_date: Optional[str],
        headers: List[str],
        table_structure: Dict[str, Any]
    ) -> bool:
        """
        Learn from user corrections to improve future auto-detection.
        """
        try:
            print(f"🎯 FormatLearningService: Learning from user corrections for company {company_id}")
            
            # Generate format signature for the corrected format
            format_signature = self.generate_format_signature(headers, table_structure)
            
            # Create correction learning record
            correction_data = {
                'company_id': company_id,
                'format_signature': format_signature,
                'corrections': {
                    'carrier_correction': {
                        'original': original_carrier,
                        'corrected': corrected_carrier,
                        'confidence_boost': 0.1 if corrected_carrier else 0
                    },
                    'date_correction': {
                        'original': original_date,
                        'corrected': corrected_date,
                        'confidence_boost': 0.1 if corrected_date else 0
                    }
                },
                'headers': headers,
                'table_structure': table_structure,
                'correction_timestamp': datetime.now().isoformat()
            }
            
            # Store correction for future learning
            # This could be stored in a separate corrections table or added to existing format learning
            print(f"🎯 FormatLearningService: Stored user corrections for format signature: {format_signature}")
            
            return True
            
        except Exception as e:
            print(f"Error learning from user corrections: {e}")
            return False
