# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Environment and credential management for ADT"""

import os
import boto3
import yaml
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import typer

@dataclass
class AWSCredentials:
    """AWS credential information."""
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    region: Optional[str] = None
    profile: Optional[str] = None
    source: str = "unknown"

class EnvironmentManager:
    """Manages environment variables and AWS credentials."""
    
    def __init__(self):
        self.aws_env_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY', 
            'AWS_SESSION_TOKEN',
            'AWS_REGION',
            'AWS_PROFILE'
        ]
    
    def get_configured_providers(self, project_dir: Path) -> List[str]:
        """Get all configured (uncommented) providers from agent config."""
        config_file = project_dir / ".agent.yaml"
        if not config_file.exists():
            return []
        
        try:
            with open(config_file) as f:
                content = f.read()
            
            # Custom YAML loader that detects duplicate keys
            class StrictLoader(yaml.SafeLoader):
                def construct_mapping(self, node, deep=False):
                    mapping = {}
                    for key_node, value_node in node.value:
                        key = self.construct_object(key_node, deep=deep)
                        if key in mapping:
                            raise yaml.constructor.ConstructorError(
                                f"Duplicate key '{key}' found in YAML", key_node.start_mark
                            )
                        value = self.construct_object(value_node, deep=deep)
                        mapping[key] = value
                    return mapping
            
            # Parse the YAML with duplicate key detection
            config = yaml.load(content, Loader=StrictLoader)
            
            # Look for provider.class in the config
            provider_section = config.get("provider", {})
            
            # Check if there's a single provider.class defined
            if isinstance(provider_section, dict) and "class" in provider_section:
                return [provider_section["class"]]
            
            return []
            
        except yaml.constructor.ConstructorError as e:
            if "Duplicate key" in str(e):
                typer.echo(f"❌ Invalid YAML: {e}", err=True)
                typer.echo("💡 You have duplicate keys in .agent.yaml (likely multiple uncommented provider.class lines)", err=True)
                typer.echo("   Please comment out all but one provider section", err=True)
            else:
                typer.echo(f"❌ YAML parsing error: {e}", err=True)
            return []
        except Exception as e:
            typer.echo(f"Warning: Could not parse agent config: {e}", err=True)
            return []

    def validate_provider_configuration(self, project_dir: Path) -> Tuple[bool, str, List[str]]:
        """
        Validate that exactly one provider is configured.
        Returns: (is_valid, error_message, configured_providers)
        """
        providers = self.get_configured_providers(project_dir)
        
        if len(providers) == 0:
            return False, "No provider configured in .agent.yaml", providers
        elif len(providers) == 1:
            return True, "", providers
        else:
            return False, f"Multiple providers configured: {', '.join(providers)}", providers

    def is_bedrock_provider_configured(self, project_dir: Path) -> bool:
        """Check if the agent is configured to use Bedrock provider."""
        is_valid, error_msg, providers = self.validate_provider_configuration(project_dir)
        
        if not is_valid:
            typer.echo(f"❌ Provider configuration error: {error_msg}", err=True)
            if len(providers) > 1:
                typer.echo("💡 Please comment out all but one provider in .agent.yaml", err=True)
                typer.echo("   Only one provider.class should be active at a time", err=True)
            elif len(providers) == 0:
                typer.echo("💡 Please uncomment one provider.class in .agent.yaml", err=True)
            return False  # Fail safely - don't proceed with ambiguous config
        
        # Check if the single configured provider is Bedrock
        return providers[0] == "strands.models.BedrockModel"
    
    def load_env_file(self, env_file_path: Path) -> Dict[str, str]:
        """Load environment variables from a .env file."""
        env_vars = {}
        
        if not env_file_path.exists():
            typer.echo(f"❌ Environment file not found: {env_file_path}", err=True)
            typer.echo("💡 Check the file path or create the .env file", err=True)
            raise typer.Exit(1)
        
        try:
            with open(env_file_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                        else:
                            typer.echo(f"Warning: Invalid line {line_num} in {env_file_path}: {line}", err=True)
            
            return env_vars
            
        except Exception as e:
            typer.echo(f"Error reading environment file {env_file_path}: {e}", err=True)
            return {}
    
    def get_aws_credentials(self, profile: Optional[str] = None, env_file_vars: Optional[Dict[str, str]] = None) -> AWSCredentials:
        """Get AWS credentials from various sources in order of precedence."""
        
        # HIGHEST PRIORITY: If AWS profile is explicitly provided, use it (no fallback)
        if profile:
            # Check if AWS environment variables would override the profile
            env_vars_present = bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
            env_file_aws_present = bool(env_file_vars and 'AWS_ACCESS_KEY_ID' in env_file_vars and 'AWS_SECRET_ACCESS_KEY' in env_file_vars)
            
            if env_vars_present:
                typer.echo(f"⚠️  AWS profile '{profile}' specified but environment variables AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are present", err=True)
                typer.echo("💡 Environment variables take precedence over profiles in AWS SDK", err=True)
                typer.echo("💡 Either unset the environment variables or remove --aws-profile to use env vars", err=True)
                raise typer.Exit(1)
            
            if env_file_aws_present:
                typer.echo(f"⚠️  AWS profile '{profile}' specified but .env file contains AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY", err=True)
                typer.echo("💡 Environment file AWS credentials take precedence over profiles in AWS SDK", err=True)
                typer.echo("💡 Either remove AWS credentials from .env file or remove --aws-profile to use .env credentials", err=True)
                raise typer.Exit(1)
            
            profile_creds = self._get_credentials_from_profile(profile)
            return profile_creds
        
        # SECOND PRIORITY: If env file is provided, ONLY use env file (fail if no AWS creds)
        if env_file_vars is not None:
            if 'AWS_ACCESS_KEY_ID' in env_file_vars and 'AWS_SECRET_ACCESS_KEY' in env_file_vars:
                return AWSCredentials(
                    access_key_id=env_file_vars['AWS_ACCESS_KEY_ID'],
                    secret_access_key=env_file_vars['AWS_SECRET_ACCESS_KEY'],
                    session_token=env_file_vars.get('AWS_SESSION_TOKEN'),
                    region=env_file_vars.get('AWS_REGION'),
                    source="env_file"
                )
            else:
                # Env file explicitly provided but doesn't contain AWS credentials - FAIL HARD
                typer.echo("❌ Environment file provided but contains no AWS credentials", err=True)
                typer.echo("💡 Add AWS credentials to your .env file:", err=True)
                typer.echo("   AWS_ACCESS_KEY_ID=your_access_key", err=True)
                typer.echo("   AWS_SECRET_ACCESS_KEY=your_secret_key", err=True)
                raise typer.Exit(1)
        
        # Nothing explicitly provided - use default resolution chain
        
        # 1. Try environment variables
        env_creds = self._get_credentials_from_env()
        if env_creds.access_key_id and env_creds.secret_access_key:
            return env_creds
        
        # 2. Try default AWS credentials (boto3 chain)
        default_creds = self._get_credentials_from_boto3()
        if default_creds.access_key_id:
            return default_creds
        
        # 3. Return empty credentials
        return AWSCredentials(source="none_found")
    
    def _get_credentials_from_env(self) -> AWSCredentials:
        """Get credentials from environment variables."""
        return AWSCredentials(
            access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            session_token=os.getenv('AWS_SESSION_TOKEN'),
            region=os.getenv('AWS_REGION'),
            source="environment_variables"
        )
    
    def _get_credentials_from_profile(self, profile: str) -> AWSCredentials:
        """Get credentials from AWS profile."""
        try:
            session = boto3.Session(profile_name=profile)
            credentials = session.get_credentials()
            
            if credentials:
                return AWSCredentials(
                    access_key_id=credentials.access_key,
                    secret_access_key=credentials.secret_key,
                    session_token=credentials.token,
                    region=session.region_name,
                    profile=profile,
                    source=f"aws_profile_{profile}"
                )
            else:
                # Profile exists but has no credentials
                typer.echo(f"❌ AWS profile '{profile}' found but contains no credentials", err=True)
                typer.echo(f"💡 Configure the profile: aws configure --profile {profile}", err=True)
                raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"❌ Failed to load AWS profile '{profile}': {e}", err=True)
            typer.echo(f"💡 Check if profile exists: aws configure list-profiles", err=True)
            typer.echo(f"💡 Create the profile: aws configure --profile {profile}", err=True)
            raise typer.Exit(1)
    
    def _get_credentials_from_boto3(self) -> AWSCredentials:
        """Get credentials from boto3 default chain."""
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if credentials:
                return AWSCredentials(
                    access_key_id=credentials.access_key,
                    secret_access_key=credentials.secret_key,
                    session_token=credentials.token,
                    region=session.region_name,
                    source="boto3_default"
                )
        except Exception as e:
            typer.echo(f"Warning: Failed to get default AWS credentials: {e}", err=True)
        
        return AWSCredentials(source="boto3_failed")
    
    def validate_aws_credentials(self, credentials: AWSCredentials) -> bool:
        """Validate AWS credentials by making a simple API call."""
        if not credentials.access_key_id or not credentials.secret_access_key:
            return False
        
        try:
            session = boto3.Session(
                aws_access_key_id=credentials.access_key_id,
                aws_secret_access_key=credentials.secret_access_key,
                aws_session_token=credentials.session_token,
                region_name=credentials.region
            )
            
            # Try to get caller identity
            sts = session.client('sts')
            sts.get_caller_identity()
            return True
            
        except Exception as e:
            typer.echo(f"Warning: AWS credentials validation failed: {e}", err=True)
            return False
    
    def setup_environment(
        self, 
        env_file: Optional[Path] = None,
        aws_profile: Optional[str] = None,
        project_dir: Optional[Path] = None
    ) -> Dict[str, str]:
        """Setup environment variables for the application."""
        env_vars = {}
        
        # Load from .env file if provided
        file_vars = {}
        if env_file:
            file_vars = self.load_env_file(env_file)
            env_vars.update(file_vars)
            
            # Apply to current environment
            for key, value in file_vars.items():
                os.environ[key] = value
        
        # Validate provider configuration and check if Bedrock is configured
        needs_aws = True
        if project_dir:
            is_valid, error_msg, providers = self.validate_provider_configuration(project_dir)
            
            if not is_valid:
                typer.echo(f"❌ Provider configuration error: {error_msg}", err=True)
                if len(providers) > 1:
                    typer.echo("💡 Please comment out all but one provider in .agent.yaml", err=True)
                    typer.echo("   Only one provider.class should be active at a time", err=True)
                    typer.echo(f"   Currently active: {', '.join(providers)}", err=True)
                elif len(providers) == 0:
                    typer.echo("💡 Please uncomment one provider.class in .agent.yaml", err=True)
                raise typer.Exit(1)
            
            # Check if the single configured provider is Bedrock
            needs_aws = providers[0] == "strands.models.BedrockModel"
            
            # Remove verbose provider messages - keep logic only
            pass
        
        if not needs_aws:
            return env_vars
        
        # Get AWS credentials (existing logic for Bedrock)
        # Pass env file vars only if env file was provided
        env_file_vars = file_vars if env_file else None
        aws_creds = self.get_aws_credentials(aws_profile, env_file_vars)
        
        if aws_creds.access_key_id:
            # Validate credentials - fail fast on validation errors
            if not self.validate_aws_credentials(aws_creds):
                typer.echo(f"❌ AWS credentials validation failed (source: {aws_creds.source})", err=True)
                
                # Provide specific guidance based on credential source
                if aws_creds.source == "env_file":
                    typer.echo(f"💡 Check AWS credentials in: {env_file}", err=True)
                elif aws_creds.source == "environment_variables":
                    typer.echo("💡 Check AWS environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)", err=True)
                elif aws_creds.source.startswith("aws_profile"):
                    typer.echo(f"💡 Check AWS profile configuration: aws configure --profile {aws_profile}", err=True)
                elif aws_creds.source == "boto3_default":
                    typer.echo("💡 Check default AWS credentials: aws configure", err=True)
                else:
                    typer.echo("💡 Check AWS credential configuration", err=True)
                
                # typer.echo("💡 Verify credentials have sufficient permissions for AWS Bedrock", err=True)
                raise typer.Exit(1)
        else:
            # No AWS credentials found - this only happens when no explicit options were provided
            typer.echo("⚠️  No AWS credentials found for Bedrock provider", err=True)
            typer.echo("💡 Set up AWS credentials:")
            typer.echo("   1. Create a .env file with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            typer.echo("   2. Use AWS CLI: aws configure")
            typer.echo("   3. Set environment variables directly")
        
        return env_vars
    
    def get_docker_env_args(
        self, 
        env_file: Optional[Path] = None,
        aws_profile: Optional[str] = None
    ) -> List[str]:
        """Get Docker environment arguments for container runs."""
        args = []
        
        # Add env file if provided
        if env_file and env_file.exists():
            env_vars = self.load_env_file(env_file)
            for key, value in env_vars.items():
                args.extend(["--env", f"{key}={value}"])
        
        # Add AWS credentials
        # Load env file vars if provided for Docker
        env_file_vars = {}
        if env_file and env_file.exists():
            env_file_vars = self.load_env_file(env_file)
        aws_creds = self.get_aws_credentials(aws_profile, env_file_vars)
        if aws_creds.access_key_id:
            args.extend(["--env", f"AWS_ACCESS_KEY_ID={aws_creds.access_key_id}"])
            args.extend(["--env", f"AWS_SECRET_ACCESS_KEY={aws_creds.secret_access_key}"])
            
            if aws_creds.session_token:
                args.extend(["--env", f"AWS_SESSION_TOKEN={aws_creds.session_token}"])
            
            if aws_creds.region:
                args.extend(["--env", f"AWS_REGION={aws_creds.region}"])
        
        return args

    # ----------------------------------------
    # Helper functions
    # ----------------------------------------

    def _clear_aws_env_vars(self):
        """Remove AWS credential-related variables from current environment."""
        for var in self.aws_env_vars:
            if var in os.environ:
                os.environ.pop(var, None)

    def _export_creds_to_env(self, creds: 'AWSCredentials'):
        """Export provided credentials to environment variables for child processes."""
        os.environ['AWS_ACCESS_KEY_ID'] = creds.access_key_id or ''
        os.environ['AWS_SECRET_ACCESS_KEY'] = creds.secret_access_key or ''
        if creds.session_token:
            os.environ['AWS_SESSION_TOKEN'] = creds.session_token
        if creds.region:
            os.environ['AWS_REGION'] = creds.region

def create_environment_manager() -> EnvironmentManager:
    """Create and return an environment manager instance."""
    return EnvironmentManager() 