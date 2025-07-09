import pandas as pd
import numpy as np
import json
import os
import openpyxl
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime, timedelta
import re
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Comprehensive data processing engine for Power BI dashboard creation
    """
    
    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls', '.csv', '.json', '.txt']
        self.max_file_size = 100 * 1024 * 1024  # 100MB limit
        
    async def analyze_files(self, file_paths: List[str]) -> Dict:
        """
        Analyze uploaded files and extract metadata
        """
        try:
            analysis_results = {
                "files": [],
                "total_files": len(file_paths),
                "total_rows": 0,
                "columns": [],
                "numeric_columns": [],
                "date_columns": [],
                "text_columns": [],
                "data_types": {},
                "summary": "",
                "schema": {},
                "sample_data": {}
            }
            
            for file_path in file_paths:
                try:
                    file_analysis = await self._analyze_single_file(file_path)
                    analysis_results["files"].append(file_analysis)
                    
                    # Accumulate metadata
                    analysis_results["total_rows"] += file_analysis.get("row_count", 0)
                    
                    # Merge column information
                    file_columns = file_analysis.get("columns", [])
                    for col in file_columns:
                        if col not in analysis_results["columns"]:
                            analysis_results["columns"].append(col)
                    
                    # Merge data type information
                    analysis_results["data_types"].update(file_analysis.get("data_types", {}))
                    
                    # Categorize columns
                    analysis_results["numeric_columns"].extend(file_analysis.get("numeric_columns", []))
                    analysis_results["date_columns"].extend(file_analysis.get("date_columns", []))
                    analysis_results["text_columns"].extend(file_analysis.get("text_columns", []))
                    
                    # Store sample data
                    filename = Path(file_path).stem
                    analysis_results["sample_data"][filename] = file_analysis.get("sample_data", [])
                    
                except Exception as e:
                    logger.error(f"Error analyzing file {file_path}: {str(e)}")
                    analysis_results["files"].append({
                        "filename": Path(file_path).name,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Remove duplicates and create summary
            analysis_results["numeric_columns"] = list(set(analysis_results["numeric_columns"]))
            analysis_results["date_columns"] = list(set(analysis_results["date_columns"]))
            analysis_results["text_columns"] = list(set(analysis_results["text_columns"]))
            
            # Generate summary
            analysis_results["summary"] = self._generate_data_summary(analysis_results)
            
            # Create schema
            analysis_results["schema"] = self._create_data_schema(analysis_results)
            
            logger.info(f"Analyzed {len(file_paths)} files successfully")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in file analysis: {str(e)}")
            return self._get_empty_analysis()
    
    async def _analyze_single_file(self, file_path: str) -> Dict:
        """
        Analyze a single file and extract its metadata
        """
        file_path_obj = Path(file_path)
        file_extension = file_path_obj.suffix.lower()
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        file_size = file_path_obj.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
        
        # Read and analyze based on file type
        if file_extension in ['.xlsx', '.xls']:
            return await self._analyze_excel_file(file_path)
        elif file_extension == '.csv':
            return await self._analyze_csv_file(file_path)
        elif file_extension == '.json':
            return await self._analyze_json_file(file_path)
        elif file_extension == '.txt':
            return await self._analyze_text_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    async def _analyze_excel_file(self, file_path: str) -> Dict:
        """
        Analyze Excel file (.xlsx, .xls)
        """
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Analyze first sheet or sheet with most data
            main_sheet = sheet_names[0]
            if len(sheet_names) > 1:
                # Find sheet with most data
                max_rows = 0
                for sheet in sheet_names:
                    df_temp = pd.read_excel(file_path, sheet_name=sheet, nrows=1)
                    if len(df_temp.columns) > max_rows:
                        max_rows = len(df_temp.columns)
                        main_sheet = sheet
            
            # Read the main sheet
            df = pd.read_excel(file_path, sheet_name=main_sheet)
            
            return self._analyze_dataframe(df, Path(file_path).name, {"sheet_names": sheet_names, "main_sheet": main_sheet})
            
        except Exception as e:
            logger.error(f"Error analyzing Excel file: {str(e)}")
            raise e
    
    async def _analyze_csv_file(self, file_path: str) -> Dict:
        """
        Analyze CSV file
        """
        try:
            # Try different encodings and delimiters
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            delimiters = [',', ';', '\t', '|']
            
            df = None
            encoding_used = None
            delimiter_used = None
            
            for encoding in encodings:
                for delimiter in delimiters:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter, nrows=1000)
                        if df.shape[1] > 1:  # Successfully parsed multiple columns
                            encoding_used = encoding
                            delimiter_used = delimiter
                            break
                    except:
                        continue
                if df is not None:
                    break
            
            if df is None:
                # Fallback to default read_csv
                df = pd.read_csv(file_path)
                encoding_used = 'utf-8'
                delimiter_used = ','
            else:
                # Re-read full file with detected parameters
                df = pd.read_csv(file_path, encoding=encoding_used, delimiter=delimiter_used)
            
            metadata = {
                "encoding": encoding_used,
                "delimiter": delimiter_used
            }
            
            return self._analyze_dataframe(df, Path(file_path).name, metadata)
            
        except Exception as e:
            logger.error(f"Error analyzing CSV file: {str(e)}")
            raise e
    
    async def _analyze_json_file(self, file_path: str) -> Dict:
        """
        Analyze JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to DataFrame
            if isinstance(data, list):
                df = pd.json_normalize(data)
            elif isinstance(data, dict):
                # If dict has a key that contains list of records
                list_keys = [k for k, v in data.items() if isinstance(v, list)]
                if list_keys:
                    df = pd.json_normalize(data[list_keys[0]])
                else:
                    # Single record
                    df = pd.json_normalize([data])
            else:
                raise ValueError("Unsupported JSON structure")
            
            metadata = {
                "json_structure": "list" if isinstance(data, list) else "dict",
                "original_keys": list(data.keys()) if isinstance(data, dict) else None
            }
            
            return self._analyze_dataframe(df, Path(file_path).name, metadata)
            
        except Exception as e:
            logger.error(f"Error analyzing JSON file: {str(e)}")
            raise e
    
    async def _analyze_text_file(self, file_path: str) -> Dict:
        """
        Analyze text file (assuming delimited format)
        """
        try:
            # Try to detect if it's a delimited file
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            
            # Check for common delimiters
            delimiters = ['\t', ',', ';', '|']
            best_delimiter = None
            max_columns = 0
            
            for delimiter in delimiters:
                columns = len(first_lines[0].split(delimiter)) if first_lines else 0
                if columns > max_columns:
                    max_columns = columns
                    best_delimiter = delimiter
            
            if best_delimiter and max_columns > 1:
                # Treat as delimited file
                df = pd.read_csv(file_path, delimiter=best_delimiter, encoding='utf-8')
                metadata = {"delimiter": best_delimiter, "detected_as": "delimited"}
            else:
                # Treat as plain text - create simple analysis
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                return {
                    "filename": Path(file_path).name,
                    "file_type": "text",
                    "row_count": len(lines),
                    "columns": ["text_content"],
                    "data_types": {"text_content": "string"},
                    "numeric_columns": [],
                    "date_columns": [],
                    "text_columns": ["text_content"],
                    "sample_data": lines[:5],
                    "metadata": {"detected_as": "plain_text", "line_count": len(lines)}
                }
            
            return self._analyze_dataframe(df, Path(file_path).name, metadata)
            
        except Exception as e:
            logger.error(f"Error analyzing text file: {str(e)}")
            raise e
    
    def _analyze_dataframe(self, df: pd.DataFrame, filename: str, metadata: Dict = None) -> Dict:
        """
        Analyze a pandas DataFrame and extract metadata
        """
        try:
            # Basic info
            row_count = len(df)
            columns = list(df.columns)
            
            # Clean column names
            df.columns = [self._clean_column_name(col) for col in df.columns]
            clean_columns = list(df.columns)
            
            # Infer data types
            data_types = {}
            numeric_columns = []
            date_columns = []
            text_columns = []
            
            for col in df.columns:
                # Infer data type
                col_type = self._infer_column_type(df[col])
                data_types[col] = col_type
                
                if col_type in ['int', 'float']:
                    numeric_columns.append(col)
                elif col_type == 'datetime':
                    date_columns.append(col)
                else:
                    text_columns.append(col)
            
            # Get sample data
            sample_data = df.head(5).to_dict('records')
            
            # Generate statistics
            statistics = self._calculate_column_statistics(df)
            
            return {
                "filename": filename,
                "file_type": Path(filename).suffix,
                "row_count": row_count,
                "columns": clean_columns,
                "original_columns": columns,
                "data_types": data_types,
                "numeric_columns": numeric_columns,
                "date_columns": date_columns,
                "text_columns": text_columns,
                "sample_data": sample_data,
                "statistics": statistics,
                "metadata": metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing DataFrame: {str(e)}")
            raise e
    
    def _infer_column_type(self, series: pd.Series) -> str:
        """
        Infer the data type of a pandas Series
        """
        # Remove null values for analysis
        non_null_series = series.dropna()
        
        if len(non_null_series) == 0:
            return "string"
        
        # Check for numeric types
        if pd.api.types.is_numeric_dtype(non_null_series):
            if pd.api.types.is_integer_dtype(non_null_series):
                return "int"
            else:
                return "float"
        
        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(non_null_series):
            return "datetime"
        
        # Try to convert to datetime
        if non_null_series.dtype == 'object':
            try:
                pd.to_datetime(non_null_series.head(100))
                return "datetime"
            except:
                pass
            
            # Try to convert to numeric
            try:
                pd.to_numeric(non_null_series.head(100))
                if all(str(x).replace('.', '').replace('-', '').isdigit() for x in non_null_series.head(20) if pd.notna(x)):
                    return "float"
            except:
                pass
        
        # Check for boolean
        unique_values = set(str(x).lower() for x in non_null_series.unique()[:10])
        if unique_values.issubset({'true', 'false', '1', '0', 'yes', 'no'}):
            return "bool"
        
        return "string"
    
    def _clean_column_name(self, column_name: str) -> str:
        """
        Clean column names for Power BI compatibility
        """
        # Convert to string if not already
        column_name = str(column_name)
        
        # Remove or replace special characters
        cleaned = re.sub(r'[^\w\s]', '_', column_name)
        
        # Replace spaces with underscores
        cleaned = re.sub(r'\s+', '_', cleaned)
        
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        # Ensure it starts with a letter
        if cleaned and not cleaned[0].isalpha():
            cleaned = 'col_' + cleaned
        
        # Ensure it's not empty
        if not cleaned:
            cleaned = 'unnamed_column'
        
        return cleaned
    
    def _calculate_column_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate basic statistics for each column
        """
        statistics = {}
        
        for col in df.columns:
            col_stats = {
                "count": len(df[col]),
                "null_count": df[col].isnull().sum(),
                "unique_count": df[col].nunique(),
                "data_type": str(df[col].dtype)
            }
            
            # Add numeric statistics
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats.update({
                    "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                    "median": float(df[col].median()) if not pd.isna(df[col].median()) else None,
                    "std": float(df[col].std()) if not pd.isna(df[col].std()) else None,
                    "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                    "max": float(df[col].max()) if not pd.isna(df[col].max()) else None
                })
            
            # Add categorical statistics
            if df[col].dtype == 'object' or df[col].nunique() < 20:
                top_values = df[col].value_counts().head(5).to_dict()
                col_stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}
            
            statistics[col] = col_stats
        
        return statistics
    
    async def process_for_powerbi(self, file_paths: List[str], dashboard_plan: Dict) -> Dict:
        """
        Process files specifically for Power BI dashboard creation
        """
        try:
            logger.info("Processing data for Power BI")
            
            processed_tables = {}
            
            for file_path in file_paths:
                table_name = Path(file_path).stem
                
                # Read and clean data
                df = await self._read_and_clean_file(file_path)
                
                # Apply transformations based on dashboard plan
                df = self._apply_dashboard_transformations(df, dashboard_plan)
                
                # Prepare for Power BI
                table_data = self._prepare_table_for_powerbi(df, table_name)
                processed_tables[table_name] = table_data
            
            # Create relationships between tables if multiple files
            relationships = self._create_table_relationships(processed_tables) if len(processed_tables) > 1 else []
            
            result = {
                "tables": processed_tables,
                "relationships": relationships,
                "summary": f"Processed {len(processed_tables)} tables for Power BI",
                "total_rows": sum(table["row_count"] for table in processed_tables.values())
            }
            
            logger.info("Data processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing data for Power BI: {str(e)}")
            raise e
    
    async def _read_and_clean_file(self, file_path: str) -> pd.DataFrame:
        """
        Read file and apply basic cleaning
        """
        file_extension = Path(file_path).suffix.lower()
        
        # Read file based on type
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_extension == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8')
        elif file_extension == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
            df = pd.json_normalize(data if isinstance(data, list) else [data])
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Clean the DataFrame
        df = self._clean_dataframe(df)
        
        return df
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply comprehensive data cleaning
        """
        # Clean column names
        df.columns = [self._clean_column_name(col) for col in df.columns]
        
        # Remove completely empty rows and columns
        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Handle data type conversions
        for col in df.columns:
            # Try to convert to appropriate types
            if df[col].dtype == 'object':
                # Try numeric conversion
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                if not numeric_series.isna().all():
                    df[col] = numeric_series
                    continue
                
                # Try datetime conversion
                try:
                    datetime_series = pd.to_datetime(df[col], errors='coerce')
                    if not datetime_series.isna().all():
                        df[col] = datetime_series
                        continue
                except:
                    pass
        
        # Handle missing values
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                # Fill numeric nulls with 0 or median
                if df[col].isna().sum() / len(df) < 0.5:  # Less than 50% missing
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(0)
            elif df[col].dtype == 'object':
                # Fill text nulls with "Unknown"
                df[col] = df[col].fillna('Unknown')
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                # For datetime, forward fill or use a default date
                df[col] = df[col].fillna(method='ffill')
        
        return df
    
    def _apply_dashboard_transformations(self, df: pd.DataFrame, dashboard_plan: Dict) -> pd.DataFrame:
        """
        Apply transformations based on dashboard requirements
        """
        # Add calculated columns based on dashboard plan
        kpis = dashboard_plan.get("kpis", [])
        
        for kpi in kpis:
            field_name = kpi.get("field", "")
            calculation = kpi.get("calculation", "")
            kpi_name = kpi.get("name", "")
            
            if field_name in df.columns and calculation and kpi_name:
                try:
                    if calculation.upper() == "SUM":
                        df[f"{kpi_name}_Total"] = df[field_name].cumsum()
                    elif calculation.upper() == "AVERAGE":
                        df[f"{kpi_name}_Avg"] = df[field_name].rolling(window=5, min_periods=1).mean()
                    elif calculation.upper() == "COUNT":
                        df[f"{kpi_name}_Count"] = 1
                except Exception as e:
                    logger.warning(f"Failed to create calculated column {kpi_name}: {str(e)}")
        
        # Add time-based columns if datetime columns exist
        date_columns = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        
        for date_col in date_columns:
            try:
                df[f"{date_col}_Year"] = df[date_col].dt.year
                df[f"{date_col}_Month"] = df[date_col].dt.month
                df[f"{date_col}_Quarter"] = df[date_col].dt.quarter
                df[f"{date_col}_DayOfWeek"] = df[date_col].dt.day_name()
            except Exception as e:
                logger.warning(f"Failed to create time columns for {date_col}: {str(e)}")
        
        return df
    
    def _prepare_table_for_powerbi(self, df: pd.DataFrame, table_name: str) -> Dict:
        """
        Prepare DataFrame for Power BI import
        """
        # Convert DataFrame to Power BI compatible format
        schema = []
        for col in df.columns:
            data_type = self._map_pandas_to_powerbi_type(df[col].dtype)
            schema.append({
                "name": col,
                "type": data_type,
                "nullable": df[col].isna().any()
            })
        
        # Convert data to records
        rows = df.to_dict('records')
        
        # Clean the data for JSON serialization
        cleaned_rows = []
        for row in rows:
            cleaned_row = {}
            for key, value in row.items():
                if pd.isna(value):
                    cleaned_row[key] = None
                elif isinstance(value, (np.integer, np.floating)):
                    cleaned_row[key] = float(value) if np.isfinite(value) else None
                elif isinstance(value, np.bool_):
                    cleaned_row[key] = bool(value)
                elif isinstance(value, (pd.Timestamp, datetime)):
                    cleaned_row[key] = value.isoformat() if pd.notna(value) else None
                else:
                    cleaned_row[key] = str(value) if value is not None else None
            cleaned_rows.append(cleaned_row)
        
        return {
            "name": table_name,
            "schema": schema,
            "rows": cleaned_rows,
            "row_count": len(cleaned_rows),
            "column_count": len(schema)
        }
    
    def _map_pandas_to_powerbi_type(self, pandas_dtype) -> str:
        """
        Map pandas data types to Power BI data types
        """
        if pd.api.types.is_integer_dtype(pandas_dtype):
            return "int"
        elif pd.api.types.is_float_dtype(pandas_dtype):
            return "float"
        elif pd.api.types.is_bool_dtype(pandas_dtype):
            return "bool"
        elif pd.api.types.is_datetime64_any_dtype(pandas_dtype):
            return "datetime"
        else:
            return "string"
    
    def _create_table_relationships(self, tables: Dict) -> List[Dict]:
        """
        Create relationships between tables based on common columns
        """
        relationships = []
        table_names = list(tables.keys())
        
        for i, table1_name in enumerate(table_names):
            for table2_name in table_names[i+1:]:
                table1_columns = set(col["name"] for col in tables[table1_name]["schema"])
                table2_columns = set(col["name"] for col in tables[table2_name]["schema"])
                
                # Find common columns that could be keys
                common_columns = table1_columns.intersection(table2_columns)
                potential_keys = [col for col in common_columns if 
                                any(keyword in col.lower() for keyword in ['id', 'key', 'code', 'number'])]
                
                if potential_keys:
                    relationships.append({
                        "from_table": table1_name,
                        "to_table": table2_name,
                        "from_column": potential_keys[0],
                        "to_column": potential_keys[0],
                        "relationship_type": "many_to_one"
                    })
        
        return relationships
    
    def _generate_data_summary(self, analysis_results: Dict) -> str:
        """
        Generate a human-readable summary of the data analysis
        """
        total_files = analysis_results["total_files"]
        total_rows = analysis_results["total_rows"]
        total_columns = len(analysis_results["columns"])
        numeric_cols = len(analysis_results["numeric_columns"])
        date_cols = len(analysis_results["date_columns"])
        text_cols = len(analysis_results["text_columns"])
        
        summary = f"Analyzed {total_files} file(s) containing {total_rows:,} total rows and {total_columns} unique columns. "
        summary += f"Found {numeric_cols} numeric columns, {date_cols} date columns, and {text_cols} text columns. "
        
        if analysis_results["numeric_columns"]:
            summary += f"Key numeric fields: {', '.join(analysis_results['numeric_columns'][:3])}. "
        
        if analysis_results["date_columns"]:
            summary += f"Date fields: {', '.join(analysis_results['date_columns'][:2])}. "
        
        summary += "Data is ready for dashboard creation."
        
        return summary
    
    def _create_data_schema(self, analysis_results: Dict) -> Dict:
        """
        Create a unified schema from analysis results
        """
        schema = {}
        
        for col in analysis_results["columns"]:
            if col in analysis_results["data_types"]:
                schema[col] = {
                    "type": analysis_results["data_types"][col],
                    "category": "numeric" if col in analysis_results["numeric_columns"] else
                               "date" if col in analysis_results["date_columns"] else "text"
                }
        
        return schema
    
    def _get_empty_analysis(self) -> Dict:
        """
        Return empty analysis structure for error cases
        """
        return {
            "files": [],
            "total_files": 0,
            "total_rows": 0,
            "columns": [],
            "numeric_columns": [],
            "date_columns": [],
            "text_columns": [],
            "data_types": {},
            "summary": "No data could be analyzed",
            "schema": {},
            "sample_data": {}
        }
