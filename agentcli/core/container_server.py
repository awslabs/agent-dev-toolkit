


# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""

Template Variables:
- mode: "local" or "container" 
"""


#!/usr/bin/env python3
"""
Standalone container entrypoint for running Strands agents.
This script creates a simple FastAPI server without any agentcli dependencies.

Generated from agentcli/core/agent_server.py.j2 - DO NOT EDIT MANUALLY
"""


import os
import sys
import uvicorn
import importlib.util
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel


# Add the app directory to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')




# === GENERATED UTILITIES (from agentcli/core/) ===

# response_utils.py
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

# trace_utils.py  
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import time
from typing import Dict, Any, Optional, List

# --- Global state -----------------------------------------------------------------
# Per-agent snapshot table keyed by id(agent) → last cumulative counters seen.
_agent_snapshots: dict[int, Dict[str, Any]] = {}

# Running totals for the current UI session (reset when chat window reloads)
_session_totals = {
    'inputTokens': 0,
    'outputTokens': 0,
    'totalTokens': 0,
    'cycles': 0,
    'latencyMs': 0
}

def extract_strands_trace_data(agent_response, message_id: str = None, *, agent=None) -> Optional[Dict[str, Any]]:
    """Extract trace data from Strands agent response using get_summary()."""
    
    # Check if it's a Strands AgentResult object with metrics
    if not hasattr(agent_response, 'metrics'):
        print("❌ No metrics found in agent response")
        return None
    
    try:
        # Get current summary
        summary = agent_response.metrics.get_summary()
        
        # Generate message ID if not provided
        if not message_id:
            message_id = f"msg_{int(time.time() * 1000000)}"
        
        per_message_data = calculate_per_message_metrics(summary, agent)
        
        # Inject raw metrics summary for downstream debug output
        per_message_data['metrics_summary'] = summary
        
        # Convert to UI format
        return convert_to_ui_format(agent_response, per_message_data, message_id, agent=agent)
        
    except Exception as e:
        print(f"❌ Error extracting trace data: {e}")
        return None

def calculate_per_message_metrics(current_summary: Dict[str, Any], agent_obj) -> Dict[str, Any]:
    """Calculate per-message metrics by tracking deltas from previous state.

    When the caller does not provide a persistent ``agent_obj`` (``agent_obj is None``)
    we treat the supplied usage numbers as already per-message and skip the snapshot
    bookkeeping that enables cumulative-to-delta conversion for long-lived agents.
    """
    
    global _agent_snapshots, _session_totals
    
    # Current cumulative numbers ----
    curr_usage = current_summary.get('accumulated_usage', {})
    curr_cycles = current_summary.get('total_cycles', 0)
    curr_latency = current_summary.get('accumulated_metrics', {}).get('latencyMs', 0)

    # If we were not given the agent object, treat values as already per-message.
    if agent_obj is None:
        delta_usage = curr_usage
        delta_cycles = curr_cycles
        delta_latency = curr_latency
    else:
        key = id(agent_obj)
        prev_snapshot = _agent_snapshots.get(key, None)

        if prev_snapshot is None:
            # first call on this agent
            delta_usage = curr_usage
            delta_cycles = curr_cycles
            delta_latency = curr_latency
        else:
            prev_cycles_val = prev_snapshot['cycles']
            delta_usage = {
                'inputTokens': max(0, curr_usage.get('inputTokens', 0) - prev_snapshot['inputTokens']),
                'outputTokens': max(0, curr_usage.get('outputTokens', 0) - prev_snapshot['outputTokens']),
                'totalTokens': max(0, curr_usage.get('totalTokens', 0) - prev_snapshot['totalTokens'])
            }
            delta_cycles = max(0, curr_cycles - prev_cycles_val)
            delta_latency = max(0, curr_latency - prev_snapshot['latencyMs'])

        # Save snapshot back only when we have an agent object (persistent path)
        if agent_obj is not None:
            _agent_snapshots[key] = {
                'inputTokens': curr_usage.get('inputTokens', 0),
                'outputTokens': curr_usage.get('outputTokens', 0),
                'totalTokens': curr_usage.get('totalTokens', 0),
                'cycles': curr_cycles,
                'latencyMs': curr_latency
            }

    # ---------------- session totals ----------------
    _session_totals['inputTokens'] += delta_usage.get('inputTokens', 0)
    _session_totals['outputTokens'] += delta_usage.get('outputTokens', 0)
    _session_totals['totalTokens'] += delta_usage.get('totalTokens', 0)
    _session_totals['cycles'] += delta_cycles
    _session_totals['latencyMs'] += delta_latency

    token_delta = delta_usage
    new_cycles = delta_cycles
    latency_delta = delta_latency
    
    # Determine previous cycle index for slicing traces
    if agent_obj is None:
        prev_cycles_index = 0
    else:
        prev_cycles_index = prev_snapshot['cycles'] if 'prev_snapshot' in locals() and prev_snapshot else 0

    # Get only the new traces (cycles) for this message
    all_traces = current_summary.get('traces', [])
    new_traces = all_traces[prev_cycles_index:curr_cycles] if prev_cycles_index < len(all_traces) else []
    
    # Extract message content and tool calls from traces
    message_contents = []
    tool_calls = []
    
    for trace in new_traces:
        for child in trace.get('children', []):
            # Extract assistant messages
            if child.get('name') == 'stream_messages' and child.get('message', {}).get('role') == 'assistant':
                content = child.get('message', {}).get('content', [])
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        message_contents.append(item['text'])
                    # Extract tool use from assistant message
                    elif isinstance(item, dict) and 'toolUse' in item:
                        tool_use = item['toolUse']
                        tool_id = tool_use.get('toolUseId', '')
                        tool_name = tool_use.get('name', 'unknown')
                        tool_input = tool_use.get('input', {})
                        
                        # Find the corresponding tool result
                        tool_result = ""
                        for other_child in trace.get('children', []):
                            if 'Tool:' in other_child.get('name', '') and other_child.get('metadata', {}).get('toolUseId') == tool_id:
                                # Extract tool result
                                if other_child.get('message', {}).get('content'):
                                    for result_item in other_child['message']['content']:
                                        if isinstance(result_item, dict) and 'toolResult' in result_item:
                                            result_content = result_item['toolResult'].get('content', [])
                                            for content_item in result_content:
                                                if isinstance(content_item, dict) and 'text' in content_item:
                                                    tool_result = content_item['text']
                                break
                        
                        tool_calls.append({
                            'id': tool_id,
                            'name': tool_name,
                            'parameters': tool_input,
                            'result': tool_result
                        })
    
    # Get tool usage for this message
    tool_usage = current_summary.get('tool_usage', {})
    
    # Note: no per-agent snapshot update when ``agent_obj`` is None
    
    return {
        'token_delta': token_delta,
        'new_cycles': new_cycles,
        'latency_ms': latency_delta,
        'message_contents': message_contents,
        'tool_calls': tool_calls,
        'tool_usage': tool_usage,
        'new_traces': new_traces,
        'metrics_summary': current_summary
    }

def convert_to_ui_format(agent_response, per_message_data: Dict[str, Any], message_id: str, *, agent=None) -> Dict[str, Any]:
    """Convert per-message data to UI-compatible format."""
    
    # Extract response text
    response_text = str(agent_response) if agent_response else ""
    
    # Get actual model from agent, fallback to hardcoded value
    actual_model = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # fallback
    agent_name = "Strands Agent"
    
    if agent:
        if hasattr(agent, 'model') and agent.model:
            # Extract model ID from the model object with error handling
            model_obj = agent.model
            try:
                if hasattr(model_obj, 'model_id'):
                    actual_model = str(model_obj.model_id)
                elif hasattr(model_obj, 'model'):
                    actual_model = str(model_obj.model)
                elif hasattr(model_obj, 'model_name'):
                    actual_model = str(model_obj.model_name)
                elif hasattr(model_obj, '_model_id'):
                    actual_model = str(model_obj._model_id)
                elif hasattr(model_obj, '__dict__') and 'model_id' in model_obj.__dict__:
                    actual_model = str(model_obj.__dict__['model_id'])
                else:
                    # Safe extraction from model class name
                    try:
                        class_name = model_obj.__class__.__name__
                        if 'Bedrock' in class_name:
                            actual_model = "BedrockModel"
                        elif 'Anthropic' in class_name:
                            actual_model = "AnthropicModel"
                        elif 'OpenAI' in class_name:
                            actual_model = "OpenAIModel"
                        else:
                            actual_model = class_name
                    except (AttributeError, TypeError):
                        actual_model = "Unknown Model"
            except (AttributeError, TypeError, ValueError):
                # Fallback if any attribute access or str() conversion fails
                actual_model = "Unknown Model"
        if hasattr(agent, 'name') and agent.name:
            agent_name = agent.name
        elif hasattr(agent, '__class__'):
            agent_name = agent.__class__.__name__
    
    current_time = time.time()
    
    # Build cycles from per-message traces
    cycles = []
    llm_calls = []
    tool_calls = []
    
    for i, trace in enumerate(per_message_data['new_traces']):
        cycle_id = trace.get('id', f'cycle_{i+1}')
        cycle_name = trace.get('name', f'Cycle {i+1}')
        
        # Get completion text for this cycle
        completion_text = ""
        for child in trace.get('children', []):
            if child.get('name') == 'stream_messages' and child.get('message', {}).get('role') == 'assistant':
                content = child.get('message', {}).get('content', [])
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        completion_text += item['text'] + " "
        
        cycle = {
            "cycle_id": cycle_id,
            "prompt": "User message",
            "completion": completion_text.strip() or response_text,
            "start_time": trace.get('start_time', current_time),
            "end_time": trace.get('end_time', current_time + 1),
            "duration_ms": int(trace.get('duration', 1) * 1000) if trace.get('duration') else 1000,
            "spans": []
        }
        cycles.append(cycle)
        
        # Create LLM call for this cycle
        llm_calls.append({
            "call_id": f"llm_{cycle_id}",
            "model": actual_model,
            "start_time": cycle['start_time'],
            "end_time": cycle['end_time'],
            "duration_ms": cycle['duration_ms'],
            "prompt": "User message",
            "completion": completion_text.strip() or response_text,
            "tokens": {
                "prompt_tokens": per_message_data['token_delta']['inputTokens'] // max(1, per_message_data['new_cycles']),
                "completion_tokens": per_message_data['token_delta']['outputTokens'] // max(1, per_message_data['new_cycles']),
                "total_tokens": per_message_data['token_delta']['totalTokens'] // max(1, per_message_data['new_cycles'])
            }
        })
    
    # Convert tool calls
    for i, tool_data in enumerate(per_message_data['tool_calls']):
        tool_calls.append({
            "tool_id": tool_data.get('id', f"tool_{i+1}"),
            "tool_name": tool_data['name'],
            "start_time": current_time,
            "end_time": current_time + 0.1,
            "duration_ms": 100,
            "parameters": tool_data.get('parameters', {}),
            "result": tool_data.get('result', '')
        })
    
    print(f"🎯 Per-message: {per_message_data['new_cycles']} cycles, {per_message_data['token_delta']['totalTokens']} tokens, {len(tool_calls)} tool calls")
    
    return {
        "message_id": message_id,
        "trace_id": f"trace_{int(current_time * 1000000)}",
        "has_real_traces": True,
        "response_text": response_text,
        "message_text": "",
        
        # UI-compatible format
        "agent_attributes": {
            "gen_ai.system": "strands-agents",
            "agent.name": agent_name,
            "gen_ai.agent.name": agent_name,
            "gen_ai.request.model": actual_model,
            "gen_ai.usage.prompt_tokens": per_message_data['token_delta']['inputTokens'],
            "gen_ai.usage.completion_tokens": per_message_data['token_delta']['outputTokens'],
            "gen_ai.usage.total_tokens": per_message_data['token_delta']['totalTokens'],
            "mode": "local"
        },
        "cycles": cycles,
        "llm_calls": llm_calls,
        "tool_calls": tool_calls,
        "total_duration_ms": per_message_data['latency_ms'],
        "total_tokens": {
            "prompt_tokens": per_message_data['token_delta']['inputTokens'],
            "completion_tokens": per_message_data['token_delta']['outputTokens'],
            "total_tokens": per_message_data['token_delta']['totalTokens']
        },
        "metrics_summary": per_message_data.get('metrics_summary'),
        
        # Debug info
        "debug_info": {
            "new_cycles": per_message_data['new_cycles'],
            "message_contents": per_message_data['message_contents'],
            "new_traces": per_message_data['new_traces'],
            "metrics_summary": per_message_data.get('metrics_summary')
        }
    }

def reset_metrics_state():
    """Reset the global metrics state (useful for testing or new sessions)."""
    global _agent_snapshots, _session_totals
    _agent_snapshots.clear()
    _session_totals.clear()
    print("🔄 Reset metrics state")

def get_trace_data(agent_response, message: str, response_text: str, model_name: str, mode: str = "local", real_tool_calls: list = None) -> Optional[Dict[str, Any]]:
    """Get trace data from agent response."""
    
    # Generate a unique message ID
    message_id = f"msg_{hash(message) % 100000}_{int(time.time() * 1000)}"
    
    # Extract trace data
    trace_data = extract_strands_trace_data(agent_response, message_id)
    
    if trace_data:
        print("✅ Using REAL Strands trace data with per-message metrics")
        # Update with the actual message text
        trace_data['message_text'] = message
        return trace_data
    else:
        print("❌ No real Strands trace data found")
        return None

def extract_direct_metrics_from_response(agent_response, message_id: str = None) -> Optional[Dict[str, Any]]:
    """Extract metrics directly from agent response without delta tracking.
    
    This is useful for temporary agents where global delta tracking doesn't work.
    """
    
    # Check if it's a Strands AgentResult object with metrics
    if not hasattr(agent_response, 'metrics'):
        print("❌ No metrics found in agent response")
        return None
    
    try:
        # Get current summary
        summary = agent_response.metrics.get_summary()
        
        # Generate message ID if not provided
        if not message_id:
            message_id = f"msg_{int(time.time() * 1000000)}"
        
        # Extract metrics directly (no delta calculation)
        current_usage = summary.get('accumulated_usage', {})
        current_cycles = summary.get('total_cycles', 0)
        current_latency = summary.get('accumulated_metrics', {}).get('latencyMs', 0)
        all_traces = summary.get('traces', [])
        
        # Use all traces from this response (since it's a fresh agent)
        new_traces = all_traces
        
        # Extract message content and tool calls from traces
        message_contents = []
        tool_calls = []
        
        for trace in new_traces:
            for child in trace.get('children', []):
                # Extract assistant messages
                if child.get('name') == 'stream_messages' and child.get('message', {}).get('role') == 'assistant':
                    content = child.get('message', {}).get('content', [])
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            message_contents.append(item['text'])
                        # Extract tool use from assistant message
                        elif isinstance(item, dict) and 'toolUse' in item:
                            tool_use = item['toolUse']
                            tool_id = tool_use.get('toolUseId', '')
                            tool_name = tool_use.get('name', 'unknown')
                            tool_input = tool_use.get('input', {})
                            
                            # Find the corresponding tool result
                            tool_result = ""
                            for other_child in trace.get('children', []):
                                if 'Tool:' in other_child.get('name', '') and other_child.get('metadata', {}).get('toolUseId') == tool_id:
                                    # Extract tool result
                                    if other_child.get('message', {}).get('content'):
                                        for result_item in other_child['message']['content']:
                                            if isinstance(result_item, dict) and 'toolResult' in result_item:
                                                result_content = result_item['toolResult'].get('content', [])
                                                for content_item in result_content:
                                                    if isinstance(content_item, dict) and 'text' in content_item:
                                                        tool_result = content_item['text']
                                        break
                            
                            tool_calls.append({
                                'id': tool_id,
                                'name': tool_name,
                                'parameters': tool_input,
                                'result': tool_result
                            })
        
        # Build direct metrics (no delta calculation)
        direct_metrics = {
            'token_delta': {
                'inputTokens': current_usage.get('inputTokens', 0),
                'outputTokens': current_usage.get('outputTokens', 0),
                'totalTokens': current_usage.get('totalTokens', 0)
            },
            'new_cycles': current_cycles,
            'latency_ms': current_latency,
            'message_contents': message_contents,
            'tool_calls': tool_calls,
            'tool_usage': summary.get('tool_usage', {}),
            'new_traces': new_traces,
            'metrics_summary': summary
        }
        
        # Convert to UI format
        return convert_to_ui_format(agent_response, direct_metrics, message_id)
        
    except Exception as e:
        print(f"❌ Error extracting direct metrics: {e}")
        return None 


# settings_handler removed – YAML-only configuration


# === END GENERATED UTILITIES ===

class AgentRequest(BaseModel):
    message: str


def load_agent():
    """Load the agent from the agent.py file."""
    agent_path = Path("/app/src/agent.py")
    
    print(f"🔍 Checking for agent file at: {agent_path}")
    print(f"🔍 File exists: {agent_path.exists()}")
    
    if not agent_path.exists():
        print(f"❌ Agent file not found at {agent_path}")
        print(f"📂 Contents of /app/src: {list(Path('/app/src').iterdir()) if Path('/app/src').exists() else 'Directory not found'}")
        raise ImportError(f"Agent file not found: {agent_path}")
    
    spec = importlib.util.spec_from_file_location("agent", agent_path)
    if not spec or not spec.loader:
        raise ImportError("Could not create module spec for agent")
    
    agent_module = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(agent_module)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ImportError(f"Failed to execute agent module: {e}")
    
    agent = getattr(agent_module, "agent", None)
    if not agent:
        available_objects = [attr for attr in dir(agent_module) if not attr.startswith('_')]
        raise ImportError(f"No 'agent' object found. Available objects: {available_objects}")
    
    print(f"✅ Successfully loaded agent: {type(agent)}")
    return agent



def create_app():
    """Create a standalone FastAPI app for the agent."""

    app = FastAPI(
        title="Strands Agent Server",
        description="Containerized Strands agent server",
        version="1.0.0"
    )
    
    # Enable CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    
    # Container mode - load agent and create endpoints
    try:
        agent = load_agent()
        
        # nosem: useless-inner-function
        @app.post("/chat")
        async def chat_endpoint(request: AgentRequest):
            """Chat with the agent."""
            try:
                message = request.message
                
                if not message:
                    raise HTTPException(status_code=400, detail="Message is required")
                
                # Guard: drop any message objects that have an empty content list
                try:
                    if hasattr(agent, 'messages') and isinstance(agent.messages, list):
                        agent.messages = [m for m in agent.messages if m.get('content')]
                except Exception:
                    # Fail-open: never block the request because of cleanup errors
                    pass
                
                # Direct agent call
                response = agent(message)
                
                # Extract response content
                response_text = extract_response_text(response)
                
                # Extract trace data
                if hasattr(response, '_is_temporary_agent') and response._is_temporary_agent:
                    trace_data = extract_direct_metrics_from_response(response)
                else:
                    trace_data = extract_strands_trace_data(response, agent=agent)
                
                return {
                    "response": response.message if hasattr(response, 'message') else str(response),
                    "trace": trace_data
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=str(e))
                
    except Exception as e:
        print(f"❌ Failed to load agent: {e}")
        
        # nosem: useless-inner-function
        @app.post("/chat")
        async def chat_endpoint_error(request: AgentRequest):
            raise HTTPException(status_code=500, detail=f"Agent failed to load: {str(e)}")
        
        agent = None
    
    # nosem: useless-inner-function
    @app.get("/health")
    async def health_check():
        try:
            if 'agent' in locals() and agent is not None:
                return {
                    "status": "healthy", 
                    "mode": "container",
                    "agent_loaded": True,
                    "agent_type": str(type(agent))
                }
            else:
                return {
                    "status": "unhealthy", 
                    "mode": "container",
                    "error": "Agent failed to load"
                }
        except NameError:
            return {
                "status": "unhealthy", 
                "mode": "container",
                "error": "Agent variable not defined"
            }
    
    # nosem: useless-inner-function
    @app.get("/info")
    async def agent_info():
        try:
            if 'agent' not in locals() or agent is None:
                return {
                    "error": "Agent failed to load",
                    "description": "Containerized Strands agent (failed to initialize)",
                    "status": "error"
                }
        except NameError:
            return {
                "error": "Agent failed to load",
                "description": "Containerized Strands agent (failed to initialize)",
                "status": "error"
            }
        
        agent_name = "Agent"
        if hasattr(agent, 'name'):
            agent_name = agent.name
        elif hasattr(agent, '__class__'):
            agent_name = agent.__class__.__name__
        
        # Extract model info properly with error handling
        model_info = "unknown"
        if hasattr(agent, 'model') and agent.model:
            model_obj = agent.model
            try:
                if hasattr(model_obj, 'model_id'):
                    model_info = str(model_obj.model_id)
                elif hasattr(model_obj, 'model'):
                    model_info = str(model_obj.model)
                elif hasattr(model_obj, 'model_name'):
                    model_info = str(model_obj.model_name)
                elif hasattr(model_obj, '_model_id'):
                    model_info = str(model_obj._model_id)
                elif hasattr(model_obj, '__dict__') and 'model_id' in model_obj.__dict__:
                    model_info = str(model_obj.__dict__['model_id'])
                else:
                    try:
                        class_name = model_obj.__class__.__name__
                        if 'Bedrock' in class_name:
                            model_info = "BedrockModel"
                        elif 'Anthropic' in class_name:
                            model_info = "AnthropicModel"
                        elif 'OpenAI' in class_name:
                            model_info = "OpenAIModel"
                        else:
                            model_info = class_name
                    except (AttributeError, TypeError):
                        model_info = "Unknown Model"
            except (AttributeError, TypeError, ValueError):
                model_info = "Unknown Model"
                    
        return {
            "name": agent_name,
            "description": "Containerized Strands agent",
            "model": model_info,
            "system_prompt": getattr(agent, 'system_prompt', None)
        }
    
    # nosem: useless-inner-function
    @app.get("/config")
    async def agent_config():
        """Get the agent configuration from .agent.yaml."""
        try:
            # In container mode, look for .agent.yaml in /app
            config_path = Path("/app/.agent.yaml")
            
            if not config_path.exists():
                raise HTTPException(status_code=404, detail="Agent configuration file (.agent.yaml) not found")
            
            # Read and return the YAML content as text
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            return {
                "config_path": str(config_path),
                "content": config_content
            }
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Agent configuration file not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading configuration: {str(e)}")
    
    # nosem: useless-inner-function
    @app.get("/")
    async def root():
        return {
            "message": "Strands Agent Server (Container Mode)",
            "version": "1.0.0",
            "endpoints": {
                "chat": "POST /chat",
                "health": "GET /health", 
                "info": "GET /info",
                "config": "GET /config"
            }
        }
    
    return app
    


def main():
    """Main entrypoint for containerized agent server."""
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🐳 Starting Strands Agent Server on {host}:{port}")
    
    try:
        app = create_app()
        print(f"✅ App created successfully")
        print(f"🌐 Server available at http://localhost:{port}")
        
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 
 