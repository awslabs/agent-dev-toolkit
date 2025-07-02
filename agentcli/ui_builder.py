"""
UI Builder for Agent CLI

Handles building the Next.js UI project and serving it from the CLI.
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class UIBuilder:
    """Builds and manages the embedded UI project."""
    
    def __init__(self):
        self.ui_dir = Path(__file__).parent / "ui"
        self.build_dir = self.ui_dir / "out"
        self.static_dir = Path(__file__).parent / "static"
        
    def check_node_installed(self) -> bool:
        """Check if Node.js is installed."""
        try:
            result = subprocess.run(
                ["node", "--version"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            logger.info(f"Node.js version: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_npm_installed(self) -> bool:
        """Check if npm is installed."""
        try:
            result = subprocess.run(
                ["npm", "--version"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            logger.info(f"npm version: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def install_dependencies(self) -> bool:
        """Install npm dependencies."""
        if not self.ui_dir.exists():
            logger.error(f"UI directory not found: {self.ui_dir}")
            return False
            
        try:
            # Remove package-lock.json to avoid path issues in packaged environment
            package_lock = self.ui_dir / "package-lock.json"
            if package_lock.exists():
                logger.info("Removing package-lock.json for fresh install...")
                package_lock.unlink()
                
            result = subprocess.run(
                ["npm", "install"],
                cwd=self.ui_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e.stderr}")
            return False
    
    def build_ui(self) -> bool:
        """Build the Next.js project."""
        if not self.ui_dir.exists():
            logger.error(f"UI directory not found: {self.ui_dir}")
            return False
            
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=self.ui_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build UI: {e.stderr}")
            return False
    
    def copy_build_assets(self) -> bool:
        """Copy built assets to static directory."""
        if not self.build_dir.exists():
            logger.error(f"Build directory not found: {self.build_dir}")
            return False
            
        try:
            # Remove existing static directory
            if self.static_dir.exists():
                shutil.rmtree(self.static_dir)
            
            # Copy build output to static directory
            shutil.copytree(self.build_dir, self.static_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to copy build assets: {e}")
            return False
    
    def build_and_prepare(self) -> bool:
        """Complete build process: install deps, build, and copy assets."""
        # Check prerequisites
        if not self.check_node_installed():
            logger.warning("⚠️  Node.js not found. UI will not be available.")
            logger.warning("   Install Node.js from https://nodejs.org/")
            return False
            
        if not self.check_npm_installed():
            logger.warning("⚠️  npm not found. UI will not be available.")
            return False
        
        # Build process (remove verbose step messages)
        steps = [
            ("Installing dependencies", self.install_dependencies),
            ("Building UI", self.build_ui),
            ("Copying assets", self.copy_build_assets),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                logger.error(f"❌ Failed: {step_name}")
                return False
        
        return True
    
    def is_built(self) -> bool:
        """Check if UI is already built."""
        return (
            self.static_dir.exists() and 
            (self.static_dir / "index.html").exists()
        )
    
    def get_static_dir(self) -> Optional[Path]:
        """Get the static directory path if UI is built."""
        if self.is_built():
            return self.static_dir
        return None
    
    def start_dev_server(self, port: int = 3001) -> subprocess.Popen:
        """Start the Next.js development server."""
        if not self.ui_dir.exists():
            raise RuntimeError(f"UI directory not found: {self.ui_dir}")
            
        logger.info(f"🚀 Starting UI dev server on port {port}...")
        
        # Set environment variable for API proxy
        env = os.environ.copy()
        env["NODE_ENV"] = "development"
        
        return subprocess.Popen(
            ["npm", "run", "dev", "--", "-p", str(port)],
            cwd=self.ui_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

# Global instance
ui_builder = UIBuilder() 