#!/usr/bin/env python3
"""
Tests for cron_utils.py module
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import patch

# Add the backend directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from cron_utils import CronUtils


class TestCronUtils:
    """Test CRON utilities functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cron_utils = CronUtils()
    
    def test_normalize_cron_expression_basic(self):
        """Test basic CRON expression normalization"""
        # Test normal expression
        result = self.cron_utils.normalize_cron_expression("0 2 * * *")
        assert result == "0 2 * * *"
        
        # Test with extra spaces
        result = self.cron_utils.normalize_cron_expression("0  2   *  *  *")
        assert result == "0 2 * * *"
    
    def test_normalize_cron_expression_full_width_chars(self):
        """Test normalization of full-width characters"""
        # Test full-width space
        result = self.cron_utils.normalize_cron_expression("0　2　*　*　*")
        assert result == "0 2 * * *"
        
        # Test full-width asterisk
        result = self.cron_utils.normalize_cron_expression("0 2 ＊ ＊ ＊")
        assert result == "0 2 * * *"
        
        # Test full-width question mark
        result = self.cron_utils.normalize_cron_expression("0 2 ？ * *")
        assert result == "0 2 ? * *"
    
    def test_normalize_cron_expression_empty_or_none(self):
        """Test normalization of empty or None expressions"""
        assert self.cron_utils.normalize_cron_expression("") == ""
        assert self.cron_utils.normalize_cron_expression(None) is None
    
    def test_set_debug_mode(self):
        """Test setting debug mode"""
        assert self.cron_utils.debug is False
        
        self.cron_utils.set_debug(True)
        assert self.cron_utils.debug is True
        
        self.cron_utils.set_debug(False)
        assert self.cron_utils.debug is False
    
    def test_log_debug_when_enabled(self):
        """Test debug logging when debug mode is enabled"""
        self.cron_utils.set_debug(True)
        
        with patch('sys.stderr') as mock_stderr:
            self.cron_utils.log_debug("Test message")
            # Check that something was written to stderr
            mock_stderr.write.assert_called()
    
    def test_log_debug_when_disabled(self):
        """Test debug logging when debug mode is disabled"""
        self.cron_utils.set_debug(False)
        
        with patch('sys.stderr') as mock_stderr:
            self.cron_utils.log_debug("Test message")
            # Check that nothing was written to stderr
            mock_stderr.write.assert_not_called()


class TestCronUtilsValidation:
    """Test CRON expression validation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cron_utils = CronUtils()
    
    def test_valid_5_field_cron_expressions(self):
        """Test validation of valid 5-field CRON expressions"""
        valid_expressions = [
            "0 2 * * *",      # Every day at 2 AM
            "*/5 * * * *",    # Every 5 minutes
            "0 0 1 * *",      # First day of every month
            "0 9-17 * * 1-5", # Business hours on weekdays
            "30 2 * * 0",     # Every Sunday at 2:30 AM
        ]
        
        for expr in valid_expressions:
            # The normalize function should handle these without errors
            result = self.cron_utils.normalize_cron_expression(expr)
            assert result is not None
            assert len(result.split()) == 5
    
    def test_normalize_complex_expressions(self):
        """Test normalization of complex CRON expressions"""
        # Test with commas
        result = self.cron_utils.normalize_cron_expression("0 2，4，6 * * *")
        assert "," in result  # Should convert full-width comma to half-width
        
        # Test with ranges
        result = self.cron_utils.normalize_cron_expression("0 2－6 * * *")
        assert "-" in result  # Should convert full-width dash to half-width
    
    def test_normalize_preserves_valid_expressions(self):
        """Test that normalization preserves already valid expressions"""
        valid_expr = "0 */2 * * *"
        result = self.cron_utils.normalize_cron_expression(valid_expr)
        assert result == valid_expr


if __name__ == '__main__':
    pytest.main([__file__])