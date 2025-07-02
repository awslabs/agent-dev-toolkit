/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface TraceAttributes {
  'gen_ai.system': string
  'agent.name': string
  'gen_ai.agent.name': string
  'gen_ai.prompt': string
  'gen_ai.completion': string
  'system_prompt': string
  'gen_ai.request.model': string
  'gen_ai.event.start_time': string
  'gen_ai.event.end_time': string
  'gen_ai.usage.prompt_tokens': number
  'gen_ai.usage.completion_tokens': number
  'gen_ai.usage.total_tokens': number
}

export interface CycleSpan {
  cycle_id: string
  prompt: string
  completion: string
  tool_results?: any[]
  start_time: string
  end_time: string
  duration_ms: number
}

export interface LLMSpan {
  model: string
  prompt: string
  completion: string
  usage: TokenUsage
  start_time: string
  end_time: string
  duration_ms: number
}

export interface ToolSpan {
  tool_name: string
  parameters: Record<string, any>
  result: any
  start_time: string
  end_time: string
  duration_ms: number
}

export interface MessageTrace {
  message_id: string
  agent_attributes: TraceAttributes
  cycles: CycleSpan[]
  llm_calls: LLMSpan[]
  tool_calls: ToolSpan[]
  total_duration_ms: number
  total_tokens: TokenUsage
  has_real_traces?: boolean
  raw_traces?: any[]
  debug_info?: any
  metrics_summary?: any
}

export interface AgentSettings {
  temperature: number
  top_p: number
  top_k: number
  max_tokens: number
  model: string
} 