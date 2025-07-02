# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


class ServerTemplateGenerator:
    """Generates server code from master template."""
    
    def __init__(self):
        self.core_dir = Path(__file__).parent
        self.template_dir = self.core_dir
        # Enable autoescaping for HTML/XML templates to mitigate XSS risks (Bandit B701).
        # Code templates (e.g., .py.j2) are not auto-escaped to avoid corrupting generated code.
        # nosem: direct-use-of-jinja2 - Used for Python code generation, not HTML/user output
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=False)
        )
    
    def _read_utility_file(self, filename: str) -> str:
        """Read a utility file and return its content."""
        file_path = self.core_dir / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return f.read()
        return f"# {filename} not found"
    
    def generate_local_server(self) -> str:
        """Generate local development server code."""
        template = self.env.get_template('agent_server.py.j2')
        
        # Read utility files
        response_utils = self._read_utility_file('response_utils.py')
        trace_utils = self._read_utility_file('trace_utils.py')
        
        return template.render(  # nosem: direct-use-of-jinja2
            mode="local",
            response_utils=response_utils,
            trace_utils=trace_utils
        )
    
    def generate_container_server(self) -> str:
        """Generate container server code."""
        template = self.env.get_template('agent_server.py.j2')
        
        # Read utility files
        response_utils = self._read_utility_file('response_utils.py')
        trace_utils = self._read_utility_file('trace_utils.py')
        
        return template.render(  # nosem: direct-use-of-jinja2
            mode="container",
            response_utils=response_utils,
            trace_utils=trace_utils
        )
    
    def write_local_server(self, output_path: Path):
        """Write local server code to file."""
        code = self.generate_local_server()
        with open(output_path, 'w') as f:
            f.write(code)
    
    def write_container_server(self, output_path: Path):
        """Write container server code to file."""
        code = self.generate_container_server()
        with open(output_path, 'w') as f:
            f.write(code)


# Global instance
template_generator = ServerTemplateGenerator() 