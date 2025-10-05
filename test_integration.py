#!/usr/bin/env python3
"""
Simple test script to validate AAP Alarm integration configuration.
Run this in your Home Assistant environment to check for basic issues.
"""

import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def validate_integration():
    """Validate the integration files."""
    
    # Check if files exist
    base_path = Path("custom_components/aapalarm")
    required_files = [
        "__init__.py",
        "config_flow.py", 
        "const.py",
        "manifest.json",
        "strings.json",
        "translations/en.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not (base_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error("Missing required files: %s", missing_files)
        return False
    
    logger.info("All required files present")
    
    # Try to import the modules
    try:
        sys.path.insert(0, str(base_path.parent))
        
        from aapalarm.const import DOMAIN
        logger.info("Successfully imported const.py, domain: %s", DOMAIN)
        
        from aapalarm.config_flow import AAPAlarmConfigFlow
        logger.info("Successfully imported config_flow.py")
        
        # Check if config flow is properly registered
        if hasattr(AAPAlarmConfigFlow, 'domain'):
            logger.info("Config flow domain: %s", AAPAlarmConfigFlow.domain)
        else:
            logger.error("Config flow missing domain attribute")
            return False
            
    except Exception as e:
        logger.error("Import error: %s", e, exc_info=True)
        return False
    
    logger.info("Integration validation passed!")
    return True

if __name__ == "__main__":
    if validate_integration():
        print("✅ Integration validation passed!")
        sys.exit(0)
    else:
        print("❌ Integration validation failed!")
        sys.exit(1)