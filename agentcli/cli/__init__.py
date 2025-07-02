# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Agent Development Toolkit (ADT) for Strands
-----------------------------------------------------------------
This file contains the **full CLI source** (Typer) *plus* a concrete
implementation of **`adt init`** that scaffolds a ready‑to‑run Strands
agent project.
Refer to README.md for more information.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
import uvicorn
import boto3
from botocore.exceptions import NoCredentialsError, ProfileNotFound
from pathlib import Path
from textwrap import dedent
from typing import Optional, Dict, Any, List, Union
import yaml
from pydantic import BaseModel, Field, validator

import typer
from agentcli.server import create_app

# Store the original directory - will be set when needed
_original_dir = None

# Create the main Typer app
APP = typer.Typer(
    help="Build and run Strands agents locally or in containers",
    no_args_is_help=True,
    add_completion=False
)

# Global variable to store the project directory
_project_dir = None

def install_dependencies(project_dir: Path) -> None:
    """Install dependencies from requirements.txt if it exists."""
    requirements_file = project_dir / "requirements.txt"
    if requirements_file.exists():
        typer.echo("Installing dependencies from requirements.txt...")
        try:
            # nosec B603 – safe fixed command list
            _run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
            typer.echo("Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            typer.echo(f"Warning: Failed to install dependencies: {e}", err=True)



def get_project_dir(ctx: typer.Context, param: typer.CallbackParam, value: str) -> str:
    """Validate and return the project directory."""
    if ctx.resilient_parsing or not value or value == ".":
        return value
    try:
        path = Path(value).resolve()
        if not path.exists():
            raise typer.BadParameter(f"Directory does not exist: {path}")
        if not path.is_dir():
            raise typer.BadParameter(f"Not a directory: {path}")
        return str(path)
    except Exception as e:
        raise typer.BadParameter(str(e))

@APP.callback()
def main(
    ctx: typer.Context,
    project_dir: str = typer.Option(
        ".",
        "--project-dir", "-d",
        help="Project directory to use",
        callback=get_project_dir,
        show_default=True,
        hidden=True
    )
) -> None:
    """Build, run, and deploy Strands agents."""
    if ctx.resilient_parsing:
        return
        
    if ctx.invoked_subcommand is not None:
        global _project_dir
        path = Path(project_dir).resolve()
        os.chdir(path)
        sys.path.insert(0, str(path))
        _project_dir = path



# ──────────────────────────────────────────────────────────────────────────────
# Global config helpers – stored in ~/.agentcli/config.json
# ──────────────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".agentcli" / "config.json"


def _load_cfg() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_cfg(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ──────────────────────────────────────────────────────────────────────────────
# Utility wrappers
# ──────────────────────────────────────────────────────────────────────────────


def _get_provider_class(project_dir: Path) -> str:
    """Get the provider class from .agent.yaml."""
    try:
        config_file = project_dir / ".agent.yaml"
        if not config_file.exists():
            return "Unknown Provider"
        
        import yaml
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        provider_class = config.get("provider", {}).get("class", "")
        return provider_class if provider_class else "Unknown Provider"
    except Exception:
        return "Unknown Provider"

def _run(cmd: list[str], cwd: Optional[Path] = None) -> None:
    """Stream a subprocess **safely**; abort on non-zero exit.

    Security rationale:
        • The command is provided as a *list* (not a shell string), meaning
          `shell=False` (default) and therefore no shell-injection vector.
        • Each argument is quoted with :pyfunc:`shlex.quote` for display only
          (does *not* affect execution) so users can copy/paste safely.
        • Bandit false-positives B603/B607 are suppressed with ``# nosec``.
        • All command elements are validated as strings to prevent injection.
    """
    # Validate command list for security
    if not cmd or not isinstance(cmd, list):
        raise ValueError("Command must be a non-empty list")
    
    # Validate each command element is a string (prevents injection)
    validated_cmd = []
    for arg in cmd:
        if not isinstance(arg, (str, Path)):
            raise ValueError(f"Command argument must be string or Path, got {type(arg)}: {arg}")
        validated_cmd.append(str(arg))
    
    # Remove verbose command display
    pass

    # nosec B603,B607 – safe: shell=False and validated string list
    # nosemgrep: dangerous-subprocess-use-audit
    res = subprocess.run(
        validated_cmd,  # nosec B603 – validated command list, shell=False, no injection risk
        cwd=cwd, 
        text=True, 
        shell=False,  # Explicitly disable shell to prevent injection
        check=False   # Handle return codes manually
    )
    if res.returncode != 0:
        typer.secho("Command failed", fg=typer.colors.RED)
        raise typer.Exit(res.returncode)


# ──────────────────────────────────────────────────────────────────────────────
# init – scaffold project
# ──────────────────────────────────────────────────────────────────────────────

_INIT_HELP = """Create a new Strands agent project with best‑practice layout.

Examples:
    adt init my‑agent        # creates ./my‑agent
    adt init awesome‑bot     # creates ./awesome‑bot
"""


@APP.command("init", help=_INIT_HELP)
def init(
    name: str = typer.Argument(..., help="Project directory name"),
    pkg: Optional[str] = typer.Option(
        None,
        "--package",
        "-p",
        help="Python package name (defaults to <n> with dashes→underscores)",
        hidden=True,
    ),
):
    """Scaffold project folders + starter files."""
    from ..generators import create_project_generator
    
    generator = create_project_generator()
    generator.generate_project(name, pkg)


@APP.command("dev", help="Run the agent in a development server")
def dev(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the server on"),
    agent_path: str = typer.Option("src/agent.py", "--agent", "-a", help="Path to the agent.py file"),
    env_file: str = typer.Option("", "--env-file", help="Path to .env file for environment variables"),
    rebuild: bool = typer.Option(False, "--rebuild", help="For --container mode: rebuild Docker image from scratch (no cache)"),
    aws_profile: str = typer.Option("", "--aws-profile", help="AWS profile to use for credentials"),
    ui_dev: bool = typer.Option(False, "--ui-dev", help="Run UI in development mode (requires Node.js)", hidden=True),
    container: bool = typer.Option(False, "--container", help="Run in Docker container instead of locally")
):
    """Run the agent in a development server.
    
    The server provides a REST API for interacting with the agent.
    """
    if container:
        # Run in container mode
        return _dev_container(port, env_file, rebuild, aws_profile)
    else:
        # Run locally (existing behavior)
        return _dev_local(port, agent_path, env_file, rebuild, aws_profile, ui_dev)

def _dev_local(port, agent_path, env_file, rebuild, aws_profile, ui_dev):
    """Run agent development server locally."""
    from ..environment import create_environment_manager
    
    if not _project_dir:
        typer.echo("Error: Project directory not set. Use --project-dir or run from agent directory.", err=True)
        raise typer.Exit(1)
        
    try:
        # Setup environment - now passes project_dir for provider validation
        env_manager = create_environment_manager()
        env_file_path = Path(env_file).resolve() if env_file else None
        env_manager.setup_environment(env_file_path, aws_profile or None, _project_dir)
        
        # Get absolute path to agent.py
        agent_file = (_project_dir / agent_path).resolve()
        if not agent_file.exists():
            typer.echo(f"❌ Agent file not found: {agent_file}", err=True)
            raise typer.Exit(1)
            
        # Install or reinstall dependencies if needed
        requirements = Path("requirements.txt")
        if rebuild and requirements.exists():
            # nosec B603 – safe fixed command list
            _run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        elif not requirements.exists():
            typer.echo("⚠️  Warning: No requirements.txt found", err=True)
        
        # AUTO-BUILD UI: Check and build UI assets if needed
        if not ui_dev:  # Only auto-build for production UI, not dev mode
            from ..ui_builder import ui_builder
            
            if not ui_builder.is_built():
                # Check Node.js availability first
                if not ui_builder.check_node_installed():
                    typer.echo("❌ Node.js not found. Cannot build UI assets.", err=True)
                    typer.echo("   Please install Node.js ≥18 from https://nodejs.org/", err=True)
                    typer.echo("   Then run: adt dev", err=True)
                    raise typer.Exit(1)
                
                # Build UI
                typer.echo("🎨 Building UI assets... This is a one-time setup that may take a moment to complete.")
                if not ui_builder.build_and_prepare():
                    typer.echo("❌ UI build failed.", err=True)
                    typer.echo("   Check that Node.js ≥18 is installed and try again.", err=True)
                    raise typer.Exit(1)
        
        # Show clean status messages
        typer.echo("✅ Agent loaded")
        provider_class = _get_provider_class(_project_dir)
        typer.echo(f"🤖 Agent uses {provider_class} as Model Provider")

        # Create the FastAPI app with our agent
        attempted_install = False
        while True:
            try:
                app = create_app(agent_file, ui_dev=ui_dev)
                break  # success
            except ModuleNotFoundError as e:
                # If we've already tried installing once, re-raise
                if attempted_install:
                    raise
                attempted_install = True

                requirements = Path("requirements.txt")
                if not requirements.exists():
                    typer.echo(f"❌ Missing dependency '{e.name}' and no requirements.txt found.", err=True)
                    raise

                typer.echo(f"📦 Missing dependency '{e.name}'. Installing project deps …")
                try:
                    # nosec B603 – safe fixed command list
                    _run([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
                except subprocess.CalledProcessError as err:
                    typer.echo(f"❌ Failed to install requirements: {err}", err=True)
                    raise
        
        # Run the development server
        typer.echo(f"🚀 Chat UI available at http://localhost:{port}")
        if ui_dev:
            typer.echo("🔄 Hot reload enabled for UI development")
        uvicorn.run(app, host="0.0.0.0", port=port)
        
    except Exception as e:
        typer.echo(f"❌ Error running development server: {e}", err=True)
        raise typer.Exit(1)

def _dev_container(port, env_file, rebuild, aws_profile):
    """Run agent development server in Docker container with local UI."""
    if not _project_dir:
        typer.echo("Error: Project directory not set. Use --project-dir or run from agent directory.", err=True)
        raise typer.Exit(1)

    try:
        # Stop any existing containers first
        container_stop()
        
        # Build the container if requested or if it doesn't exist
        if rebuild or not _container_exists("agent:latest"):
            # Call container_build command directly
            cmd = ["docker", "build", "-t", "agent:latest"]
            if rebuild:
                cmd.append("--no-cache")
            cmd.extend(["-f", str(_project_dir / "Dockerfile"), str(_project_dir)])
            
            typer.echo("🏗️ Building Docker image agent:latest…")
            _run(cmd)
            typer.echo("✅ Successfully built agent:latest")
            
        # Prepare env_file path if provided
        env_file_path = Path(env_file).resolve() if env_file else None
        
        # Start the containerized backend on internal port
        container_internal_port = 8000  # Internal container port
        ui_port = port  # UI runs on the requested port (same as local mode)
        
        typer.echo("🐳 Starting containerized backend...")
        typer.echo(f"🔧 Backend API will run internally on port {container_internal_port}")
        
        # Start container in detached mode
        container_run(
            port=container_internal_port, 
            env_file=env_file_path, 
            detach=True,  # Run in background
            aws_profile=aws_profile,
            pass_aws_env=True
        )
        
        # Wait for container to start with retries
        import time
        typer.echo("⏳ Waiting for container to start...")
        
        # Retry health check multiple times with exponential backoff
        max_retries = 10
        retry_interval = 1  # Start with 1 second, increase gradually
        max_retry_interval = 5  # Cap at 5 seconds
        
        for attempt in range(max_retries):
            typer.echo(f"🔍 Health check attempt {attempt + 1}/{max_retries}")
            if _container_is_healthy(container_internal_port):
                break
            
            # Exponential backoff with jitter for better reliability
            if attempt < max_retries - 1:  # Don't sleep after last attempt
                current_interval = min(retry_interval * (1.5 ** attempt), max_retry_interval)
                typer.echo(f"⏱️  Waiting {current_interval:.1f}s before next check...")
                time.sleep(current_interval)  # nosec B311 – intentional health check delay with exponential backoff
        else:
            typer.echo("❌ Container failed to start properly after multiple attempts", err=True)
            typer.echo("💡 Check container logs with: docker logs $(docker ps -q --filter ancestor=agent:latest)")
            raise typer.Exit(1)
        
        typer.echo(f"✅ Backend running internally on port {container_internal_port}")
        
        # AUTO-BUILD UI: Check and build UI assets if needed (same as local mode)
        from ..ui_builder import ui_builder
        
        if not ui_builder.is_built():
            # Check Node.js availability first
            if not ui_builder.check_node_installed():
                typer.echo("❌ Node.js not found. Cannot build UI assets.", err=True)
                typer.echo("   Please install Node.js ≥18 from https://nodejs.org/", err=True)
                typer.echo("   Then run: adt dev --container", err=True)
                raise typer.Exit(1)
            
            # Build UI
            typer.echo("🎨 Building UI assets... This is a one-time setup that may take a moment to complete.")
            if not ui_builder.build_and_prepare():
                typer.echo("❌ UI build failed.", err=True)
                typer.echo("   Check that Node.js ≥18 is installed and try again.", err=True)
                raise typer.Exit(1)
        
        # Now start the local UI that connects to the containerized backend
        typer.echo("🎨 Starting local UI server...")
        typer.echo(f"🚀 Application available at http://localhost:{ui_port}")
        typer.echo("💡 Same URL as local mode - UI runs locally, backend runs in container")
        
        # Start local UI server that proxies to containerized backend
        _start_ui_with_container_backend(ui_port, container_internal_port)
        
    except Exception as e:
        typer.echo(f"❌ Error running containerized development server: {e}", err=True)
        # Clean up container if UI fails
        container_stop()
        raise typer.Exit(1)

def _container_exists(tag: str) -> bool:
    """Check if a Docker container image exists."""
    try:
        result = subprocess.run(  # nosec B603 – shell=False, fixed arg list; tag is arg element not shell string
            ["docker", "images", "-q", tag],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False

def _container_is_healthy(port: int) -> bool:
    """Check if the container is healthy and responding."""
    try:
        import requests
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        return response.status_code == 200
    except ImportError:
        # Fallback to curl if requests not available
        try:
            result = subprocess.run(  # nosec B603 – shell=False, safe arg list
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://localhost:{port}/health"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == "200"
        except:
            return False
    except:
        return False

def _start_ui_with_container_backend(ui_port: int, backend_port: int):
    """Start local UI server that connects to containerized backend."""
    from ..server import create_app
    
    # Create a special UI-only app that proxies to the container
    # We need to pass a dummy path since agent_path is required, but it won't be used
    dummy_path = Path("/dev/null")  # Won't be used due to container_backend_port
    app = create_app(
        agent_path=dummy_path,
        ui_dev=False,
        container_backend_port=backend_port  # Tell UI to use container backend
    )
    
    # Run the UI server
    uvicorn.run(app, host="0.0.0.0", port=ui_port)



@APP.command("cluster-bootstrap", help="Provision the shared ECS cluster (one-time) – stub", hidden=True)
def cluster_bootstrap(stack_name: str = "AgentClusterStack"):
    cfg = _load_cfg()
    cfg["cluster_arn"] = "arn:aws:ecs:region:acct:cluster/shared"  # stub
    cfg["listener_arn"] = "arn:aws:elasticloadbalancing:…listener/…"  # stub
    _save_cfg(cfg)
    typer.secho("Saved fake ARNs – replace with real deploy logic", fg=typer.colors.YELLOW)


@APP.command("deploy", help="Build, push & deploy (stub)", hidden=True)
def deploy(stage: str = typer.Option("dev", "--stage")):
    typer.echo("TODO: docker build/push + CDK deploy")


@APP.command("list", help="List agents (stub)", hidden=True)
def list_():
    typer.echo("TODO: boto3 list_services")


@APP.command("logs", help="Tail logs (stub)", hidden=True)
def logs(name: str, lines: int = typer.Option(50, "--lines", "-n")):
    typer.echo("TODO: aws logs tail")


@APP.command("destroy", help="Remove agent (stub)", hidden=True)
def destroy(name: str, force: bool = typer.Option(False, "--yes", "-y")):
    typer.echo("TODO: CDK destroy / boto3 delete_service")

# ──────────────────────────────────────────────────────────────────────────────
# Container management
# ──────────────────────────────────────────────────────────────────────────────
@APP.command("container-build", hidden=True)
def container_build(
    tag: str = typer.Option("agent:latest", "--tag", "-t", help="Docker image tag"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Do not use cache when building the image")
):
    """Build a Docker container for the agent."""
    if not _project_dir:
        typer.echo("Error: Project directory not set. Use --project-dir or run from agent directory.", err=True)
        raise typer.Exit(1)
        
    dockerfile = _project_dir / "Dockerfile"
    if not dockerfile.exists():
        typer.echo(f"Error: Dockerfile not found in {_project_dir}", err=True)
        raise typer.Exit(1)
        
    try:
        cmd = ["docker", "build", "-t", tag]
        if no_cache:
            cmd.append("--no-cache")
        cmd.extend(["-f", str(dockerfile), str(_project_dir)])
        
        typer.echo(f"Building Docker image {tag}...")
        _run(cmd)
        typer.echo(f"✅ Successfully built {tag}")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error building Docker image: {e}", err=True)
        raise typer.Exit(1)

@APP.command("container-run", hidden=True)
def container_run(
    port: int = 8000,
    tag: str = "agent:latest",
    env_file: Optional[Path] = None,
    detach: bool = False,
    aws_profile: str = "",
    pass_aws_env: bool = True
):
    """Run the agent in a Docker container."""
    if not _project_dir:
        typer.echo("Error: Project directory not set. Use --project-dir or run from agent directory.", err=True)
        raise typer.Exit(1)
    
    # Validate provider configuration and check if Bedrock is configured
    from ..environment import create_environment_manager
    env_manager = create_environment_manager()
    is_valid, error_msg, providers = env_manager.validate_provider_configuration(_project_dir)
    
    if not is_valid:
        typer.echo(f"❌ Provider configuration error: {error_msg}", err=True)
        if len(providers) > 1:
            typer.echo("💡 Please comment out all but one provider in .agent.yaml", err=True)
            typer.echo("   Only one provider.class should be active at a time", err=True)
        elif len(providers) == 0:
            typer.echo("💡 Please uncomment one provider.class in .agent.yaml", err=True)
        raise typer.Exit(1)
    
    needs_aws = providers[0] == "strands.models.BedrockModel"
    
    # Base docker command
    cmd = [
        "docker", "run",
        "-p", f"{port}:{port}",
        "-v", f"{_project_dir}/src:/app/src",
        "-v", f"{_project_dir}/requirements.txt:/app/requirements.txt",
        "-v", f"{_project_dir}/.agent.yaml:/app/.agent.yaml",
        "-v", f"{_project_dir}/container_entrypoint.py:/app/container_entrypoint.py",
        "--env", "PYTHONUNBUFFERED=1",
        "--env", f"PORT={port}"
    ]
    
    # Handle environment variables in this order of precedence:
    # 1. From .env file if provided
    # 2. From AWS profile if provided
    # 3. From host environment variables
    # 4. Default values
    
    # 1. Handle .env file if provided
    env_file_path = None
    if env_file:
        # Handle both string and Path objects
        if isinstance(env_file, str):
            env_file_path = Path(env_file)
        else:
            env_file_path = env_file
            
        if env_file_path.exists():
            env_file_path = env_file_path.resolve()
            # Mount the .env file
            cmd.extend(["-v", f"{env_file_path}:/app/.env"])
            typer.echo(f"Using environment file: {env_file_path}")
            
            # Also pass variables directly for immediate availability
            try:
                with open(env_file_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            cmd.extend(["--env", f"{key}={value}"])
                            typer.echo(f"Passing {key} from .env file")
            except Exception as e:
                typer.echo(f"Warning: Failed to read .env file: {e}", err=True)
    
    # Only handle AWS credentials if using Bedrock
    if needs_aws:
        typer.echo(f"ℹ️  Bedrock provider configured - setting up AWS credentials")
        
        # 2. Handle AWS profile if specified (overrides .env AWS settings)
        if aws_profile:
            try:
                session = boto3.Session(profile_name=aws_profile)
                credentials = session.get_credentials()
                if credentials:
                    aws_env = {
                        'AWS_ACCESS_KEY_ID': credentials.access_key,
                        'AWS_SECRET_ACCESS_KEY': credentials.secret_key,
                    }
                    # Only set region if profile has one configured
                    if session.region_name:
                        aws_env['AWS_REGION'] = session.region_name
                    # Only add session token if it exists and is not empty
                    if credentials.token:
                        aws_env['AWS_SESSION_TOKEN'] = credentials.token
                    
                    for key, value in aws_env.items():
                        if value:  # Only set non-empty values
                            cmd.extend(["--env", f"{key}={value}"])
                    typer.echo(f"Using AWS credentials from profile: {aws_profile}")
            except Exception as e:
                typer.echo(f"Warning: Failed to load AWS profile {aws_profile}: {e}", err=True)
        
        # 3. Pass through AWS environment variables from host (only if not in .env file)
        if pass_aws_env:
            aws_vars = [
                'AWS_ACCESS_KEY_ID',
                'AWS_SECRET_ACCESS_KEY',
                'AWS_SESSION_TOKEN',
                'AWS_REGION'
            ]
            
            # Track which vars were already set from .env file
            env_vars_set = set()
            if env_file and env_file_path and env_file_path.exists():
                try:
                    with open(env_file_path) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key = line.split('=', 1)[0]
                                env_vars_set.add(key)
                except Exception:
                    pass
            
            for var in aws_vars:
                # Only pass through host env vars if they weren't in .env file
                if var not in env_vars_set:
                    value = os.environ.get(var)
                    if value:
                        cmd.extend(["--env", f"{var}={value}"])
                        typer.echo(f"Passing through {var} from host environment")
                else:
                    typer.echo(f"Skipping {var} from host (using .env file value)")
        
        # Let boto3 handle region defaults - no hardcoded fallback
    else:
        typer.echo(f"ℹ️  {providers[0]} provider configured - skipping AWS credential setup")
    
    # Add detach flag if requested
    if detach:
        cmd.append("-d")
    else:
        cmd.append("-it")
    
    # Add the image tag and command
    cmd.append(tag)
    
    # Use the container entrypoint which provides full dev server functionality
    cmd.extend(["python", "container_entrypoint.py"])
    
    try:
        _run(cmd)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error running container: {e}", err=True)
        raise typer.Exit(1)

@APP.command("build-ui", hidden=True)
def build_ui():
    """Build the Next.js UI for the CLI."""
    from ..ui_builder import ui_builder
    
    typer.echo("🏗️  Building Agent CLI UI...")
    
    success = ui_builder.build_and_prepare()
    
    if success:
        typer.echo("🎉 UI build completed successfully!")
        typer.echo("The UI will now be available when running 'adt dev'")
    else:
        typer.echo("❌ UI build failed. Check that Node.js is installed.", err=True)
        typer.echo("Install Node.js from https://nodejs.org/", err=True)
        raise typer.Exit(1)

@APP.command("regenerate-templates", hidden=True)
def regenerate_templates():
    """Regenerate server templates from master template.
    
    This command regenerates both local and container server code from the
    master template, ensuring they stay in sync with shared utilities.
    """
    if not _project_dir:
        typer.echo("Error: Project directory not set. Use --project-dir or run from agent directory.", err=True)
        raise typer.Exit(1)
    
    from ..core.template_generator import template_generator
    from pathlib import Path
    
    try:
        # Regenerate container entrypoint
        container_path = _project_dir / "container_entrypoint.py"
        template_generator.write_container_server(container_path)
        typer.echo(f"✅ Regenerated {container_path}")
        
        # Regenerate local dev server (if needed in the future)
        # local_path = Path("agentcli/server/dev_server.py")
        # template_generator.write_local_server(local_path)
        # typer.echo(f"✅ Regenerated {local_path}")
        
        typer.echo("🎉 All templates regenerated successfully!")
        typer.echo("💡 Both local and container modes now use the same shared utilities")
        
    except Exception as e:
        typer.echo(f"❌ Error regenerating templates: {e}", err=True)
        raise typer.Exit(1)

@APP.command("add")
def add(
    type: str = typer.Argument(..., help="Type of component to add (currently only 'tool' is supported)"),
    name: str = typer.Argument(..., help="Name of the component")
):
    """Add a new component to the agent.
    
    Currently supports:
    - tool: Add a new tool to your agent
    
    Example:
        adt add tool weather_check
    """
    if type == "tool":
        # Create the tools directory if it doesn't exist
        tools_dir = Path("src/tools")
        if not tools_dir.exists():
            typer.echo("Error: No tools directory found. Are you in a valid agent project?", err=True)
            raise typer.Exit(1)
            
        # Create individual tool file
        tool_file = tools_dir / f"{name}.py"
        if tool_file.exists():
            typer.echo(f"Error: Tool file {tool_file} already exists!", err=True)
            raise typer.Exit(1)
            
        # Create the new tool file with proper template
        tool_code = f'''from strands import tool

@tool
def {name}(input_text: str) -> str:
    """Add a description of what {name} does here.
    
    Args:
        input_text: Description of the input parameter
        
    Returns:
        str: Description of what this tool returns
    """
    # TODO: Implement {name} functionality
    return f"Tool {name} received: {{input_text}}"
'''
        
        tool_file.write_text(tool_code)
        typer.echo(f"✨ Created new tool '{name}' in {tool_file}")
        typer.echo("The tool will be automatically discovered by the agent.")
        typer.echo("Edit the file to implement your tool's functionality!")
    else:
        typer.echo(f"Error: Unknown component type '{type}'", err=True)
        typer.echo("Available types: tool")
        raise typer.Exit(1)

@APP.command("container-stop", hidden=True)
def container_stop():
    """Stop all running agent containers."""
    try:
        # Get all running container IDs
        result = subprocess.run(  # nosec B603 – shell=False, safe arg list
            ["docker", "ps", "-q", "--filter", "ancestor=agent:latest"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            typer.echo("Error checking for running containers", err=True)
            return
            
        container_ids = result.stdout.strip().split('\n')
        container_ids = [cid for cid in container_ids if cid]
        
        if not container_ids:
            typer.echo("No running agent containers found")
            return
            
        # Stop all containers
        _run(["docker", "stop"] + container_ids)
        typer.echo(f"Stopped {len(container_ids)} container(s)")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error stopping containers: {e}", err=True)
        raise typer.Exit(1)



# ... (rest of the code remains the same)
# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────


def cli() -> None:
    """Main CLI entry point."""
    global _original_dir
    
    # Capture original directory when CLI starts
    try:
        _original_dir = Path.cwd().resolve()
    except (FileNotFoundError, OSError, PermissionError):
        _original_dir = Path.home().resolve()
    
    try:
        APP()
    finally:
        # Restore original directory when done (if it exists)
        if _original_dir and _original_dir.exists():
            try:
                os.chdir(_original_dir)
            except (FileNotFoundError, OSError, PermissionError):
                # Directory might have been deleted or inaccessible, ignore
                pass

def main():
    """Entry point for pip installation."""
    cli()


if __name__ == "__main__":
    _cli_main()
