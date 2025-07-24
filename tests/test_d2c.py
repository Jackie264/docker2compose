#!/usr/bin/env python3
"""
Tests for d2c.py module
"""

import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock
import sys

# Add the backend directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from d2c import (
    load_config, 
    ensure_config_file, 
    group_containers_by_network,
    convert_container_to_service
)


class TestLoadConfig:
    """Test configuration loading functionality"""
    
    def test_load_config_from_file(self):
        """Test loading configuration from config.json file"""
        test_config = {
            'NAS': 'zos',
            'CRON': '0 2 * * *',
            'NETWORK': 'false',
            'TZ': 'Europe/London'
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
                config = load_config()
                
                assert config['NAS'] == 'zos'
                assert config['CRON'] == '0 2 * * *'
                assert config['NETWORK'] == 'false'
                assert config['TZ'] == 'Europe/London'
    
    def test_load_config_file_not_exists(self):
        """Test loading configuration when config file doesn't exist"""
        with patch('os.path.exists', return_value=False):
            with patch.dict(os.environ, {
                'NAS': 'debian',
                'CRON': 'once',
                'NETWORK': 'true',
                'TZ': 'Asia/Shanghai'
            }):
                config = load_config()
                
                assert config['NAS'] == 'debian'
                assert config['CRON'] == 'once'
                assert config['NETWORK'] == 'true'
                assert config['TZ'] == 'Asia/Shanghai'
    
    def test_load_config_default_values(self):
        """Test loading configuration with default values"""
        with patch('os.path.exists', return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                config = load_config()
                
                assert config['NAS'] == 'debian'
                assert config['CRON'] == 'once'
                assert config['NETWORK'] == 'true'
                assert config['TZ'] == 'Asia/Shanghai'
    
    def test_load_config_file_read_error(self):
        """Test handling of file read errors"""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("File read error")):
                with patch.dict(os.environ, {'NAS': 'test_nas'}):
                    config = load_config()
                    
                    # Should fall back to environment variables
                    assert config['NAS'] == 'test_nas'


class TestEnsureConfigFile:
    """Test configuration file creation functionality"""
    
    def test_ensure_config_file_creates_directory(self):
        """Test that ensure_config_file creates the config directory"""
        with patch('os.path.exists') as mock_exists:
            with patch('os.makedirs') as mock_makedirs:
                with patch('builtins.open', mock_open()):
                    # First call for directory, second for file
                    mock_exists.side_effect = [False, False]
                    
                    ensure_config_file()
                    
                    mock_makedirs.assert_called_once_with('/app/config', exist_ok=True)
    
    def test_ensure_config_file_creates_default_config(self):
        """Test that ensure_config_file creates a default config file"""
        with patch('os.path.exists', return_value=False):
            with patch('os.makedirs'):
                with patch('builtins.open', mock_open()) as mock_file:
                    ensure_config_file()
                    
                    # Verify file was opened for writing
                    mock_file.assert_called_with('/app/config/config.json', 'w', encoding='utf-8')
    
    def test_ensure_config_file_handles_write_error(self):
        """Test handling of file write errors"""
        with patch('os.path.exists', return_value=False):
            with patch('os.makedirs'):
                with patch('builtins.open', side_effect=IOError("Write error")):
                    # Should not raise an exception
                    ensure_config_file()


class TestGroupContainersByNetwork:
    """Test container grouping functionality"""
    
    def test_group_containers_by_network_custom_network(self):
        """Test grouping containers by custom network"""
        containers = [
            {
                'Id': 'container1',
                'Name': '/app1',
                'HostConfig': {'NetworkMode': 'default'},
                'NetworkSettings': {
                    'Networks': {
                        'custom_network': {'IPAddress': '172.20.0.2'}
                    }
                }
            },
            {
                'Id': 'container2', 
                'Name': '/app2',
                'HostConfig': {'NetworkMode': 'default'},
                'NetworkSettings': {
                    'Networks': {
                        'custom_network': {'IPAddress': '172.20.0.3'}
                    }
                }
            }
        ]
        
        networks = {
            'custom_network': {'Driver': 'bridge'}
        }
        
        groups = group_containers_by_network(containers, networks)
        
        # Should have one group with both containers
        assert len(groups) == 1
        assert set(groups[0]) == {'container1', 'container2'}
    
    def test_group_containers_by_network_bridge_mode(self):
        """Test grouping containers with bridge network mode"""
        containers = [
            {
                'Id': 'container1',
                'Name': '/app1',
                'HostConfig': {'NetworkMode': 'bridge'},
                'NetworkSettings': {'Networks': {}}
            },
            {
                'Id': 'container2',
                'Name': '/app2', 
                'HostConfig': {'NetworkMode': 'bridge'},
                'NetworkSettings': {'Networks': {}}
            }
        ]
        
        networks = {}
        
        groups = group_containers_by_network(containers, networks)
        
        # Each bridge container should be in its own group
        assert len(groups) == 2
        assert ['container1'] in groups
        assert ['container2'] in groups
    
    def test_group_containers_by_network_host_mode(self):
        """Test grouping containers with host network mode"""
        containers = [
            {
                'Id': 'container1',
                'Name': '/app1',
                'HostConfig': {'NetworkMode': 'host'},
                'NetworkSettings': {'Networks': {}}
            }
        ]
        
        networks = {}
        
        groups = group_containers_by_network(containers, networks)
        
        # Host container should be in its own group
        assert len(groups) == 1
        assert groups[0] == ['container1']
    
    def test_group_containers_by_network_with_links(self):
        """Test grouping containers with links"""
        containers = [
            {
                'Id': 'container1',
                'Name': '/app1',
                'HostConfig': {
                    'NetworkMode': 'default',
                    'Links': ['/app2:app2']
                },
                'NetworkSettings': {'Networks': {}}
            },
            {
                'Id': 'container2',
                'Name': '/app2',
                'HostConfig': {'NetworkMode': 'default'},
                'NetworkSettings': {'Networks': {}}
            }
        ]
        
        networks = {}
        
        groups = group_containers_by_network(containers, networks)
        
        # Linked containers should be in the same group
        assert len(groups) == 1
        assert set(groups[0]) == {'container1', 'container2'}


class TestConvertContainerToService:
    """Test container to service conversion functionality"""
    
    def test_convert_container_basic_service(self):
        """Test basic container to service conversion"""
        container = {
            'Name': '/test-app',
            'Config': {
                'Image': 'nginx:latest',
                'Env': ['ENV_VAR=value', 'PATH=/usr/bin']
            },
            'HostConfig': {
                'RestartPolicy': {'Name': 'always'},
                'NetworkMode': 'bridge'
            },
            'NetworkSettings': {
                'Ports': {
                    '80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]
                }
            },
            'Mounts': []
        }
        
        with patch('d2c.load_config', return_value={
            'NAS': 'debian',
            'NETWORK': 'true'
        }):
            service = convert_container_to_service(container)
            
            assert service['container_name'] == 'test-app'
            assert service['image'] == 'nginx:latest'
            assert service['restart'] == 'always'
            assert service['network_mode'] == 'bridge'
            assert '8080:80/tcp' in service['ports']
            assert service['environment']['ENV_VAR'] == 'value'
            assert 'PATH' not in service['environment']  # PATH should be filtered out
    
    def test_convert_container_with_volumes(self):
        """Test container conversion with volume mounts"""
        container = {
            'Name': '/test-app',
            'Config': {
                'Image': 'nginx:latest',
                'Env': []
            },
            'HostConfig': {
                'RestartPolicy': {'Name': 'no'},
                'NetworkMode': 'default'
            },
            'NetworkSettings': {'Ports': {}},
            'Mounts': [
                {
                    'Type': 'bind',
                    'Source': '/host/path',
                    'Destination': '/container/path',
                    'RW': True
                },
                {
                    'Type': 'volume',
                    'Name': 'my-volume',
                    'Destination': '/data',
                    'RW': False
                }
            ]
        }
        
        with patch('d2c.load_config', return_value={
            'NAS': 'debian',
            'NETWORK': 'false'
        }):
            service = convert_container_to_service(container)
            
            assert '/host/path:/container/path' in service['volumes']
            assert 'my-volume:/data:ro' in service['volumes']
    
    def test_convert_container_host_network(self):
        """Test container conversion with host network mode"""
        container = {
            'Name': '/test-app',
            'Config': {
                'Image': 'nginx:latest',
                'Env': []
            },
            'HostConfig': {
                'RestartPolicy': {'Name': 'no'},
                'NetworkMode': 'host'
            },
            'NetworkSettings': {'Ports': {}},
            'Mounts': []
        }
        
        with patch('d2c.load_config', return_value={
            'NAS': 'debian',
            'NETWORK': 'true'
        }):
            service = convert_container_to_service(container)
            
            assert service['network_mode'] == 'host'
    
    def test_convert_container_restart_policy_on_failure(self):
        """Test container conversion with on-failure restart policy"""
        container = {
            'Name': '/test-app',
            'Config': {
                'Image': 'nginx:latest',
                'Env': []
            },
            'HostConfig': {
                'RestartPolicy': {
                    'Name': 'on-failure',
                    'MaximumRetryCount': 3
                },
                'NetworkMode': 'default'
            },
            'NetworkSettings': {'Ports': {}},
            'Mounts': []
        }
        
        with patch('d2c.load_config', return_value={
            'NAS': 'debian',
            'NETWORK': 'false'
        }):
            service = convert_container_to_service(container)
            
            assert service['restart'] == 'on-failure:3'


if __name__ == '__main__':
    pytest.main([__file__])