# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

def extract_response_text(response) -> str:
    """Extract text content from various response formats."""
    if hasattr(response, 'message'):
        return str(response.message)
    elif hasattr(response, 'content'):
        if isinstance(response.content, list):
            # Handle list of content blocks (e.g., [{"text": "..."}])
            text_parts = []
            for item in response.content:
                if isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
                elif hasattr(item, 'text'):
                    text_parts.append(item.text)
                else:
                    text_parts.append(str(item))
            return ' '.join(text_parts)
        else:
            return str(response.content)
    elif hasattr(response, 'text'):
        return str(response.text)
    else:
        return str(response) 