# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Core utilities for Agent Development Kit (ADT) for Strands.
"""

from .template_generator import ServerTemplateGenerator

# Create a global instance for easy access
template_generator = ServerTemplateGenerator()

__all__ = ["template_generator", "ServerTemplateGenerator"] 