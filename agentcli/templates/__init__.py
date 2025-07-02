"""Template engine for AgentCLI project generation."""

from pathlib import Path
from typing import Dict, Any, Optional
import jinja2
from dataclasses import dataclass, field

@dataclass
class ProjectConfig:
    """Configuration for project generation."""
    name: str
    pkg_name: str
    
    # Model configuration
    model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    region: str = "us-west-2"
    temperature: float = 0.3
    top_p: float = 0.9
    max_tokens: int = 2048
    
    # Deployment configuration
    stage: str = "dev"
    cpu: int = 1024
    memory: int = 2048
    
    # Package versions
    strands_version: str = "0.1.0"
    strands_tools_version: str = "0.1.0"
    boto3_version: str = "1.28.0"
    pyyaml_version: str = "6.0"
    pydantic_version: str = "2.0.0"
    fastapi_version: str = "0.68.0"
    uvicorn_version: str = "0.15.0"
    multipart_version: str = "0.0.5"
    dotenv_version: str = "1.0.0"
    
    # Tool defaults
    tool_name: str = "sample_tool"
    tool_description: str = "A sample tool that echoes back the input with a greeting"
    tool_response_prefix: str = "Hello! You said"
    
    @property
    def default_region(self) -> str:
        return self.region

class TemplateEngine:
    """Jinja2-based template engine for project generation."""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent
        # nosem: direct-use-of-jinja2 - Used for Python code generation, not HTML/user output
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render_template(self, template_name: str, config: ProjectConfig) -> str:
        """Render a template with the given configuration."""
        # Special handling for container entrypoint - use generated code
        if template_name == "container_entrypoint.py.j2":
            from ..core.template_generator import template_generator
            return template_generator.generate_container_server()
        
        template = self.env.get_template(template_name)
        return template.render(**config.__dict__)  # nosem: direct-use-of-jinja2
    
    def get_template_mapping(self) -> Dict[str, str]:
        """Get mapping of template files to target paths."""
        return {
            "agent.py.j2": "src/agent.py",
            "tools_init.py.j2": "src/tools/__init__.py",
            "sample_tool.py.j2": "src/tools/sample_tool.py",
            "mcp_client.py.j2": "src/mcp_client.py",
            "mcp_tools.py.j2": "src/mcp_tools.py",
            "requirements.txt.j2": "requirements.txt",
            "agent_config.yaml.j2": ".agent.yaml",
            "env_example.j2": ".env.example",
            "Dockerfile.j2": "Dockerfile",
            "container_entrypoint.py.j2": "container_entrypoint.py",
        }
    


def create_template_engine() -> TemplateEngine:
    """Create and return a template engine instance."""
    return TemplateEngine() 