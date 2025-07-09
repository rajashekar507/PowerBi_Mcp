"""
Input validation utilities for AI Power BI Dashboard Generator
"""

import os
import re
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FileValidator:
    """Validates uploaded files for security and format compliance"""
    
    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        '.xls': ['application/vnd.ms-excel'],
        '.csv': ['text/csv', 'application/csv', 'text/plain'],
        '.json': ['application/json', 'text/json'],
        '.txt': ['text/plain'],
        '.png': ['image/png'],
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
        '.gif': ['image/gif'],
        '.bmp': ['image/bmp']
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB total
    
    # Security patterns to reject
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'<script',  # Script injection
        r'javascript:',  # JavaScript protocol
        r'vbscript:',  # VBScript protocol
        r'data:',  # Data URLs
        r'file://',  # File protocol
    ]
    
    @classmethod
    def validate_file(cls, file_path: str, original_filename: str) -> Tuple[bool, str]:
        """
        Validate a single uploaded file
        
        Args:
            file_path: Path to the uploaded file
            original_filename: Original filename from upload
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > cls.MAX_FILE_SIZE:
                return False, f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({cls.MAX_FILE_SIZE / 1024 / 1024}MB)"
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check file extension
            file_ext = Path(original_filename).suffix.lower()
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                return False, f"File extension '{file_ext}' is not allowed. Allowed extensions: {list(cls.ALLOWED_EXTENSIONS.keys())}"
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(original_filename)
            allowed_mimes = cls.ALLOWED_EXTENSIONS[file_ext]
            if mime_type and mime_type not in allowed_mimes:
                return False, f"MIME type '{mime_type}' is not allowed for extension '{file_ext}'"
            
            # Check for dangerous patterns in filename
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, original_filename, re.IGNORECASE):
                    return False, f"Filename contains dangerous pattern: {pattern}"
            
            # Additional security checks
            if not cls._is_safe_filename(original_filename):
                return False, "Filename contains invalid characters"
            
            return True, "File is valid"
            
        except Exception as e:
            logger.error(f"Error validating file {original_filename}: {e}")
            return False, f"Validation error: {str(e)}"
    
    @classmethod
    def validate_multiple_files(cls, files: List[Tuple[str, str]]) -> Tuple[bool, List[str]]:
        """
        Validate multiple uploaded files
        
        Args:
            files: List of (file_path, original_filename) tuples
            
        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []
        total_size = 0
        
        # Check total number of files
        if len(files) > 10:
            errors.append("Too many files. Maximum 10 files allowed per upload")
        
        for file_path, original_filename in files:
            # Validate individual file
            is_valid, error_msg = cls.validate_file(file_path, original_filename)
            if not is_valid:
                errors.append(f"{original_filename}: {error_msg}")
            else:
                total_size += os.path.getsize(file_path)
        
        # Check total size
        if total_size > cls.MAX_TOTAL_SIZE:
            errors.append(f"Total file size ({total_size / 1024 / 1024:.1f}MB) exceeds maximum allowed ({cls.MAX_TOTAL_SIZE / 1024 / 1024}MB)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _is_safe_filename(filename: str) -> bool:
        """Check if filename is safe (no path traversal, etc.)"""
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Check for empty or hidden files
        if not filename or filename.startswith('.'):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        if filename.upper().split('.')[0] in reserved_names:
            return False
        
        # Check for invalid characters
        invalid_chars = '<>:"|?*'
        if any(char in filename for char in invalid_chars):
            return False
        
        return True

class InputValidator:
    """Validates user input for chat messages and API requests"""
    
    MAX_MESSAGE_LENGTH = 10000
    MAX_CONVERSATION_HISTORY = 100
    
    @classmethod
    def validate_chat_message(cls, message: str) -> Tuple[bool, str]:
        """
        Validate chat message input
        
        Args:
            message: User's chat message
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not message or not message.strip():
            return False, "Message cannot be empty"
        
        if len(message) > cls.MAX_MESSAGE_LENGTH:
            return False, f"Message too long. Maximum {cls.MAX_MESSAGE_LENGTH} characters allowed"
        
        # Check for potential injection attacks
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, message, re.IGNORECASE | re.DOTALL):
                return False, "Message contains potentially dangerous content"
        
        return True, "Message is valid"
    
    @classmethod
    def validate_api_request(cls, request_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate API request data
        
        Args:
            request_data: Dictionary containing request data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate required fields
        if 'message' in request_data:
            is_valid, error = cls.validate_chat_message(request_data['message'])
            if not is_valid:
                errors.append(error)
        
        # Validate conversation_id if present
        if 'conversation_id' in request_data:
            conv_id = request_data['conversation_id']
            if not isinstance(conv_id, str) or not conv_id.strip():
                errors.append("Invalid conversation_id")
        
        # Validate file_ids if present
        if 'file_ids' in request_data:
            file_ids = request_data['file_ids']
            if not isinstance(file_ids, list):
                errors.append("file_ids must be a list")
            elif len(file_ids) > 10:
                errors.append("Too many file_ids. Maximum 10 allowed")
        
        return len(errors) == 0, errors

class ConfigValidator:
    """Validates configuration and environment variables"""
    
    REQUIRED_AI_KEYS = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    REQUIRED_POWERBI_KEYS = ['POWER_BI_TENANT_ID', 'POWER_BI_CLIENT_ID', 'POWER_BI_CLIENT_SECRET']
    
    @classmethod
    def validate_environment(cls) -> Tuple[bool, List[str]]:
        """
        Validate environment configuration
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for at least one AI API key
        has_ai_key = any(
            os.getenv(key) and os.getenv(key) != f"your_{key.lower()}_here" 
            for key in cls.REQUIRED_AI_KEYS
        )
        
        if not has_ai_key:
            errors.append("At least one AI API key (OpenAI or Anthropic) must be configured")
        
        # Check Power BI configuration (optional but recommended)
        powerbi_keys = [os.getenv(key) for key in cls.REQUIRED_POWERBI_KEYS]
        has_powerbi = all(key and key != f"your_{key.lower().replace('_', '_')}" for key in powerbi_keys)
        
        if not has_powerbi:
            errors.append("Power BI configuration is incomplete (optional but recommended for full functionality)")
        
        # Validate specific key formats
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and not openai_key.startswith('sk-'):
            errors.append("OpenAI API key should start with 'sk-'")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_cors_origins(cls, origins: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate CORS origins configuration
        
        Args:
            origins: List of allowed origins
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if "*" in origins:
            errors.append("CORS wildcard (*) should not be used in production")
        
        for origin in origins:
            if origin != "*" and not origin.startswith(('http://', 'https://')):
                errors.append(f"Invalid origin format: {origin}")
        
        return len(errors) == 0, errors