#!/usr/bin/env python3
"""
Tests for web_ui.py module
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import pytz

# Add the backend directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from web_ui import get_timezone_from_config, get_localized_timestamp, ensure_compose_files_exist


class TestWebUIUtilities:
    """Test Web UI utility functions"""
    
    def test_get_localized_timestamp_format(self):
        """Test localized timestamp format"""
        # Mock datetime to return a specific time
        mock_datetime = datetime(2023, 5, 15, 14, 30, 45)
        
        with patch('web_ui.get_timezone_from_config') as mock_get_tz:
            mock_get_tz.return_value = pytz.timezone('Asia/Shanghai')
            
            with patch('web_ui.datetime') as mock_dt:
                mock_dt.now.return_value = mock_datetime.replace(tzinfo=pytz.timezone('Asia/Shanghai'))
                
                timestamp = get_localized_timestamp()
                
                # Should match the expected format YYYY_MM_DD_HH_MM
                assert len(timestamp) == 16  # YYYY_MM_DD_HH_MM format
                assert timestamp.count('_') == 4
    
    @patch('glob.glob')
    @patch('os.path.exists')
    def test_ensure_compose_files_exist_files_present(self, mock_exists, mock_glob):
        """Test ensure_compose_files_exist when files already exist"""
        mock_exists.return_value = True
        mock_glob.return_value = ['/app/compose/test.yaml']
        
        # Should not trigger file generation when files exist
        with patch('web_ui.get_containers') as mock_get_containers:
            ensure_compose_files_exist()
            
            # get_containers should not be called since files exist
            mock_get_containers.assert_not_called()
    
    @patch('subprocess.run')
    @patch('glob.glob')
    @patch('os.path.exists')
    def test_ensure_compose_files_exist_no_files(self, mock_exists, mock_glob, mock_subprocess):
        """Test ensure_compose_files_exist when no files exist"""
        mock_exists.return_value = True
        mock_glob.return_value = []  # No YAML files found
        
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        ensure_compose_files_exist()
        
        # Should call subprocess to run d2c.py
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ['python3', '/app/d2c.py']
        assert call_args[1]['env']['CRON'] == 'once'
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_ensure_compose_files_exist_directory_not_exists(self, mock_exists, mock_subprocess):
        """Test ensure_compose_files_exist when compose directory doesn't exist"""
        mock_exists.return_value = False
        
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        ensure_compose_files_exist()
        
        # Should call subprocess to run d2c.py when directory doesn't exist
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ['python3', '/app/d2c.py']
        assert call_args[1]['env']['CRON'] == 'once'


class TestWebUIConfiguration:
    """Test Web UI configuration handling"""
    
    def test_ensure_compose_files_exist_subprocess_failure(self):
        """Test ensure_compose_files_exist when subprocess fails"""
        with patch('subprocess.run') as mock_subprocess:
            with patch('os.path.exists', return_value=False):
                # Mock failed subprocess execution
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Error message"
                mock_subprocess.return_value = mock_result
                
                # Should not raise an exception
                ensure_compose_files_exist()
                
                mock_subprocess.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])