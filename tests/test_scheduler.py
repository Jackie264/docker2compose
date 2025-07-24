#!/usr/bin/env python3
"""
Tests for scheduler.py module
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, mock_open, MagicMock
import signal

# Add the backend directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from scheduler import D2CScheduler


class TestD2CScheduler:
    """Test D2C scheduler functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('scheduler.D2CScheduler.setup_signal_handlers'):
            self.scheduler = D2CScheduler()
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        with patch('scheduler.D2CScheduler.setup_signal_handlers'):
            scheduler = D2CScheduler('/test/config.json')
            
            assert scheduler.config_file == '/test/config.json'
            assert scheduler.running is True
            assert scheduler.cron_utils is not None
    
    def test_load_config_success(self):
        """Test successful configuration loading"""
        test_config = {
            'CRON': '0 2 * * *',
            'NAS': 'debian',
            'TZ': 'Asia/Shanghai'
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
                cron_expr = self.scheduler.load_config()
                
                assert cron_expr == '0 2 * * *'
    
    def test_load_config_with_lowercase_key(self):
        """Test configuration loading with lowercase key"""
        test_config = {
            'cron': '*/5 * * * *',  # lowercase key
            'NAS': 'debian'
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
                cron_expr = self.scheduler.load_config()
                
                assert cron_expr == '*/5 * * * *'
    
    def test_load_config_missing_cron_key(self):
        """Test configuration loading when CRON key is missing"""
        test_config = {
            'NAS': 'debian',
            'TZ': 'Asia/Shanghai'
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
                cron_expr = self.scheduler.load_config()
                
                # Should use default value
                assert cron_expr == '*/5 * * * *'
    
    def test_load_config_file_error(self):
        """Test configuration loading when file read fails"""
        with patch('builtins.open', side_effect=IOError("File read error")):
            cron_expr = self.scheduler.load_config()
            
            # Should use default value when file read fails
            assert cron_expr == '*/5 * * * *'
    
    def test_load_config_invalid_json(self):
        """Test configuration loading with invalid JSON"""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="invalid json")):
                cron_expr = self.scheduler.load_config()
                
                # Should use default value when JSON is invalid
                assert cron_expr == '*/5 * * * *'
    
    def test_signal_handler_sets_running_false(self):
        """Test that signal handler sets running to False"""
        assert self.scheduler.running is True
        
        # Simulate receiving a signal
        self.scheduler.signal_handler(signal.SIGTERM, None)
        
        assert self.scheduler.running is False
    
    def test_signal_handler_with_different_signals(self):
        """Test signal handler with different signal types"""
        # Test SIGTERM
        self.scheduler.running = True
        self.scheduler.signal_handler(signal.SIGTERM, None)
        assert self.scheduler.running is False
        
        # Reset and test SIGINT
        self.scheduler.running = True
        self.scheduler.signal_handler(signal.SIGINT, None)
        assert self.scheduler.running is False
    
    @patch('signal.signal')
    def test_setup_signal_handlers(self, mock_signal):
        """Test signal handlers setup"""
        scheduler = D2CScheduler()
        
        # Verify that signal handlers were set up
        assert mock_signal.call_count >= 2
        
        # Check that SIGTERM and SIGINT handlers were registered
        calls = mock_signal.call_args_list
        signal_types = [call[0][0] for call in calls]
        
        assert signal.SIGTERM in signal_types
        assert signal.SIGINT in signal_types


class TestD2CSchedulerIntegration:
    """Integration tests for D2C scheduler"""
    
    def test_scheduler_with_cron_utils_integration(self):
        """Test scheduler integration with CronUtils"""
        test_config = {
            'CRON': '0　2　*　*　*',  # Full-width characters
        }
        
        with patch('scheduler.D2CScheduler.setup_signal_handlers'):
            scheduler = D2CScheduler()
            
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
                    cron_expr = scheduler.load_config()
                    
                    # Should be normalized by CronUtils
                    assert cron_expr == '0 2 * * *'
    
    def test_scheduler_debug_mode(self):
        """Test scheduler with debug mode enabled"""
        with patch('scheduler.D2CScheduler.setup_signal_handlers'):
            scheduler = D2CScheduler()
            
            # Verify debug mode is enabled by default
            assert scheduler.cron_utils.debug is True


if __name__ == '__main__':
    pytest.main([__file__])