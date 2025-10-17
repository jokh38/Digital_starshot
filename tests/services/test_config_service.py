"""
Tests for ConfigurationService.

This module provides comprehensive testing for the configuration management
system used by the Starshot analyzer application.
"""

import unittest
import tempfile
import os
import configparser
from pathlib import Path

# Add src directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.config_service import (
    ConfigurationService,
    ConfigurationError,
    ValidationError
)


class TestConfigurationServiceDefaults(unittest.TestCase):
    """Test default configuration loading when file is missing."""

    def test_load_returns_defaults_when_file_missing(self):
        """Should return default config when config file does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ConfigurationService(
                config_path=os.path.join(tmpdir, 'nonexistent.ini')
            )
            config = service.load()

            self.assertIsNotNone(config)
            self.assertIn('network', config)
            self.assertIn('crop', config)
            self.assertIn('analysis', config)

    def test_default_network_configuration(self):
        """Should have sensible network defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ConfigurationService(
                config_path=os.path.join(tmpdir, 'nonexistent.ini')
            )
            config = service.load()

            self.assertEqual(config['network']['ip_address_app'], '192.168.1.100')

    def test_default_crop_configuration(self):
        """Should have sensible crop defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ConfigurationService(
                config_path=os.path.join(tmpdir, 'nonexistent.ini')
            )
            config = service.load()

            crop = config['crop']
            self.assertEqual(crop['crop_x'], 0)
            self.assertEqual(crop['crop_y'], 0)
            self.assertEqual(crop['crop_w'], 640)
            self.assertEqual(crop['crop_h'], 480)

    def test_default_analysis_configuration(self):
        """Should have sensible analysis defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ConfigurationService(
                config_path=os.path.join(tmpdir, 'nonexistent.ini')
            )
            config = service.load()

            analysis = config['analysis']
            self.assertAlmostEqual(analysis['dpmm_calibration'], 7.716666667)
            self.assertEqual(analysis['roi_size'], 200)
            self.assertEqual(analysis['min_contour_area'], 10)
            self.assertEqual(analysis['max_contour_area'], 500)
            self.assertEqual(analysis['ransac_threshold'], 2)


class TestConfigurationServiceLoading(unittest.TestCase):
    """Test loading configuration from file."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, 'config.ini')

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def create_test_config_file(self, **overrides):
        """Create a test configuration file with optional overrides."""
        config = configparser.ConfigParser()

        # Network section
        config.add_section('network')
        config.set('network', 'ip_address_app',
                   overrides.get('ip', '192.168.1.50'))

        # Crop section
        config.add_section('crop')
        config.set('crop', 'crop_x', str(overrides.get('crop_x', 10)))
        config.set('crop', 'crop_y', str(overrides.get('crop_y', 20)))
        config.set('crop', 'crop_w', str(overrides.get('crop_w', 800)))
        config.set('crop', 'crop_h', str(overrides.get('crop_h', 600)))

        # Analysis section
        config.add_section('analysis')
        config.set('analysis', 'dpmm_calibration',
                   str(overrides.get('dpmm', 7.716666667)))
        config.set('analysis', 'roi_size', str(overrides.get('roi_size', 200)))
        config.set('analysis', 'min_contour_area',
                   str(overrides.get('min_area', 10)))
        config.set('analysis', 'max_contour_area',
                   str(overrides.get('max_area', 500)))
        config.set('analysis', 'ransac_threshold',
                   str(overrides.get('ransac', 2)))

        with open(self.config_path, 'w') as f:
            config.write(f)

    def test_load_from_existing_file(self):
        """Should load configuration from existing file."""
        self.create_test_config_file(ip='10.0.0.1', crop_x=5)

        service = ConfigurationService(config_path=self.config_path)
        config = service.load()

        self.assertEqual(config['network']['ip_address_app'], '10.0.0.1')
        self.assertEqual(config['crop']['crop_x'], 5)

    def test_load_caches_configuration(self):
        """Should cache configuration after loading."""
        self.create_test_config_file()

        service = ConfigurationService(config_path=self.config_path)
        config1 = service.load()
        config2 = service.load()

        self.assertIs(config1, config2)


class TestConfigurationServiceValidation(unittest.TestCase):
    """Test configuration validation."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, 'config.ini')

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def test_validate_rejects_negative_crop_x(self):
        """Should reject negative crop_x values."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': -1,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_rejects_zero_crop_width(self):
        """Should reject zero or negative crop width."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 0,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_rejects_negative_crop_height(self):
        """Should reject negative crop height."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': -100
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_rejects_invalid_ip_address(self):
        """Should reject invalid IP address."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': 'not.an.ip.address.invalid'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_rejects_zero_dpmm(self):
        """Should reject zero dpmm_calibration."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 0,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_rejects_negative_roi_size(self):
        """Should reject negative roi_size."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': -50,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_accepts_valid_ipv4(self):
        """Should accept valid IPv4 addresses."""
        service = ConfigurationService(config_path=self.config_path)

        valid_ips = [
            '192.168.1.1',
            '10.0.0.1',
            '172.16.0.1',
            '127.0.0.1',
            '255.255.255.255',
            '0.0.0.0'
        ]

        for ip in valid_ips:
            config = {
                'network': {'ip_address_app': ip},
                'crop': {
                    'crop_x': 0,
                    'crop_y': 0,
                    'crop_w': 640,
                    'crop_h': 480
                },
                'analysis': {
                    'dpmm_calibration': 7.7,
                    'roi_size': 200,
                    'min_contour_area': 10,
                    'max_contour_area': 500,
                    'ransac_threshold': 2
                }
            }

            # Should not raise exception
            service.validate(config)

    def test_validate_accepts_valid_configuration(self):
        """Should accept valid configuration."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        # Should not raise exception
        service.validate(config)


class TestConfigurationServiceSave(unittest.TestCase):
    """Test saving configuration."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, 'config.ini')

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def test_save_creates_file(self):
        """Should create configuration file."""
        service = ConfigurationService(config_path=self.config_path)
        config = service.load()  # Get defaults
        service.save(config)

        self.assertTrue(os.path.exists(self.config_path))

    def test_save_preserves_values(self):
        """Should preserve configuration values after save and reload."""
        service = ConfigurationService(config_path=self.config_path)
        config = service.load()

        # Modify config
        config['network']['ip_address_app'] = '10.0.0.1'
        config['crop']['crop_x'] = 50

        # Save and reload
        service.save(config)
        service._cache = None  # Clear cache

        loaded_config = service.load()
        self.assertEqual(loaded_config['network']['ip_address_app'], '10.0.0.1')
        self.assertEqual(loaded_config['crop']['crop_x'], 50)

    def test_save_rejects_invalid_config(self):
        """Should reject saving invalid configuration."""
        service = ConfigurationService(config_path=self.config_path)

        invalid_config = {
            'network': {'ip_address_app': 'invalid'},
            'crop': {
                'crop_x': -1,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 10,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.save(invalid_config)


class TestConfigurationServiceGetSet(unittest.TestCase):
    """Test getting and setting individual configuration values."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, 'config.ini')

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def test_get_returns_value(self):
        """Should return configuration value."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        value = service.get('crop', 'crop_w')
        self.assertEqual(value, 640)

    def test_get_returns_network_ip(self):
        """Should return network IP address."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        value = service.get('network', 'ip_address_app')
        self.assertEqual(value, '192.168.1.100')

    def test_set_updates_value(self):
        """Should update configuration value."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        service.set('crop', 'crop_w', 800)
        value = service.get('crop', 'crop_w')
        self.assertEqual(value, 800)

    def test_set_validates_value(self):
        """Should validate value when setting."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        with self.assertRaises(ValidationError):
            service.set('crop', 'crop_w', -100)

    def test_set_and_save_persists_value(self):
        """Should persist value after set and save."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        service.set('network', 'ip_address_app', '10.0.0.5')
        service.save_current()

        service2 = ConfigurationService(config_path=self.config_path)
        service2.load()

        value = service2.get('network', 'ip_address_app')
        self.assertEqual(value, '10.0.0.5')

    def test_get_with_default(self):
        """Should support getting value with default."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        # This should get the actual value
        value = service.get('crop', 'crop_w', default=999)
        self.assertEqual(value, 640)


class TestConfigurationServiceMissingKeys(unittest.TestCase):
    """Test handling of missing configuration keys."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, 'config.ini')

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def test_get_missing_section_raises_error(self):
        """Should raise error when accessing missing section."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        with self.assertRaises(ConfigurationError):
            service.get('nonexistent', 'key')

    def test_get_missing_key_raises_error(self):
        """Should raise error when accessing missing key."""
        service = ConfigurationService(config_path=self.config_path)
        service.load()

        with self.assertRaises(ConfigurationError):
            service.get('crop', 'nonexistent_key')


class TestConfigurationServiceEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up temporary directory for test files."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmpdir.name, 'config.ini')

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def test_validate_rejects_min_area_greater_than_max_area(self):
        """Should reject configuration where min_area >= max_area."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 600,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        with self.assertRaises(ValidationError):
            service.validate(config)

    def test_validate_accepts_equal_min_max_area(self):
        """Should accept configuration where min_area == max_area."""
        service = ConfigurationService(config_path=self.config_path)
        config = {
            'network': {'ip_address_app': '192.168.1.1'},
            'crop': {
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 640,
                'crop_h': 480
            },
            'analysis': {
                'dpmm_calibration': 7.7,
                'roi_size': 200,
                'min_contour_area': 500,
                'max_contour_area': 500,
                'ransac_threshold': 2
            }
        }

        # Should not raise exception
        service.validate(config)


if __name__ == '__main__':
    unittest.main()
