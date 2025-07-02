/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

"use client"
import React, { useState } from 'react'
import { PanelRightClose, PanelRightOpen, X, BarChart3, Clock, Zap, MessageSquare, Activity, ChevronRight } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { Separator } from './ui/separator'
import { MessageTrace } from '../types/observability'
import { TimelineModal } from './TimelineModal'
import { SequenceDiagramModal } from './SequenceDiagramModal'

interface MetricsPanelProps {
  selectedTrace?: MessageTrace
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    trace?: MessageTrace
  }>
  onClose: () => void
  isOpen: boolean
  onToggle: (open: boolean) => void
}

export function MetricsPanel({ selectedTrace, messages, onClose, isOpen, onToggle }: MetricsPanelProps) {
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const formatTokens = (tokens: number) => {
    if (tokens < 1000) return tokens.toString()
    return `${(tokens / 1000).toFixed(1)}k`
  }

  // Find the corresponding user message for the selected trace
  const getUserMessage = () => {
    if (!selectedTrace) return null
    
    // Find the assistant message with this trace
    const assistantMessageIndex = messages.findIndex(msg => 
      msg.role === 'assistant' && msg.trace?.message_id === selectedTrace.message_id
    )
    
    if (assistantMessageIndex === -1) return null
    
    // Find the most recent user message before this assistant message
    for (let i = assistantMessageIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return messages[i].content
      }
    }
    
    return null
  }

  const userMessage = getUserMessage()

  // Modal state for JSON visualizer
  const [showJsonModal, setShowJsonModal] = useState(false)
  const [showTimelineModal, setShowTimelineModal] = useState(false)
  const [showSequenceModal, setShowSequenceModal] = useState(false)

  // Recursive renderer for expandable JSON using <details>
  const renderJsonDetails = (data: any): React.ReactNode => {
    if (data === null || data === undefined) return String(data)
    if (typeof data !== 'object') {
      return <span className="text-blue-600">{String(data)}</span>
    }
    if (Array.isArray(data)) {
      return (
        <div className="pl-4 space-y-1">
          {data.map((item, idx) => {
            const isPrimitive = item === null || typeof item !== 'object'
            if (isPrimitive) {
              return (
                <div key={idx} className="ml-2 text-sm">
                  <span className="text-purple-600">[{idx}]: </span>{renderJsonDetails(item)}
                </div>
              )
            }
            return (
              <details key={idx} className="ml-2">
                <summary className="cursor-pointer text-sm text-purple-600">[{idx}]</summary>
                <div className="pl-4">{renderJsonDetails(item)}</div>
              </details>
            )
          })}
        </div>
      )
    }
    return (
      <div className="pl-2 space-y-1">
        {Object.entries(data).map(([k, v]) => {
          const isPrimitive = v === null || typeof v !== 'object'
          if (isPrimitive) {
            return (
              <div key={k} className="ml-2 text-sm">
                <span className="text-purple-600">{k}: </span>{renderJsonDetails(v)}
              </div>
            )
          }
          return (
            <details key={k} className="ml-2">
              <summary className="cursor-pointer text-sm text-purple-600">{k}</summary>
              <div className="pl-4">{renderJsonDetails(v)}</div>
            </details>
          )
        })}
      </div>
    )
  }

  return (
    <div className={`fixed top-0 right-0 h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 transition-all duration-300 ${isOpen ? 'w-80' : 'w-12'} z-30 overflow-hidden`}>
      {/* Observability Icon (visible when collapsed) */}
      {!isOpen && (
        <div className="p-3 pt-4">
          <button
            onClick={() => onToggle(true)}
            className="w-6 h-6 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Open observability"
          >
            <Activity className="h-4 w-4" />
          </button>
          {selectedTrace && (
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse mt-2 mx-auto" />
          )}
        </div>
      )}

      {/* Metrics Content (visible when expanded) */}
      {isOpen && (
        <>
          {!selectedTrace ? (
            <div className="p-6 relative">
              {/* Collapse button - floating to the right */}
              <button
                onClick={() => onToggle(false)}
                className="absolute top-6 right-6 w-5 h-5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-colors z-10"
                title="Collapse Observability"
              >
                <ChevronRight className="h-3 w-3 text-muted-foreground" />
              </button>

              <div className="flex items-center gap-2 mb-6">
                <BarChart3 className="h-4 w-4" />
                <h2 className="text-md font-semibold">Observability</h2>
              </div>
              
              <div className="text-center text-muted-foreground py-12">
                <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">Click on a message to view its trace data</p>
              </div>
            </div>
          ) : (
            <div className="overflow-y-auto h-full">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 relative">
                {/* Collapse button - floating to the right */}
                <button
                  onClick={() => onToggle(false)}
                  className="absolute top-6 right-6 w-5 h-5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-colors z-10"
                  title="Collapse Observability"
                >
                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                </button>

                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Trace Details</h2>
                </div>
                <div className="flex gap-4">
                  <button
                    onClick={() => setShowTimelineModal(true)}
                    className="text-xs text-blue-500 hover:underline"
                  >
                    Timeline
                  </button>
                  <button
                    onClick={() => setShowSequenceModal(true)}
                    className="text-xs text-blue-500 hover:underline"
                  >
                    Event Loop
                  </button>
                </div>
              </div>

              <div className="p-6">
                <Tabs defaultValue="overview" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="tools">Tools</TabsTrigger>
                    <TabsTrigger value="summary">Metrics</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" className="space-y-4">
                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 border border-border rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          <span className="text-xs font-medium">Duration</span>
                        </div>
                        <p className="text-lg font-semibold">
                          {selectedTrace.total_duration_ms > 0 ? formatDuration(selectedTrace.total_duration_ms) : 'N/A'}
                        </p>
                      </div>
                      
                      <div className="p-3 border border-border rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <Zap className="h-4 w-4 text-muted-foreground" />
                          <span className="text-xs font-medium">Tokens</span>
                        </div>
                        <p className="text-lg font-semibold">
                          {selectedTrace.total_tokens.total_tokens > 0 ? formatTokens(selectedTrace.total_tokens.total_tokens) : 'N/A'}
                        </p>
                      </div>
                    </div>

                    <Separator />

                    {/* Token Breakdown */}
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Token Usage</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Prompt</span>
                          <span>{selectedTrace.total_tokens.prompt_tokens}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Completion</span>
                          <span>{selectedTrace.total_tokens.completion_tokens}</span>
                        </div>
                        <div className="flex justify-between text-sm font-medium border-t border-border pt-2">
                          <span>Total</span>
                          <span>{selectedTrace.total_tokens.total_tokens}</span>
                        </div>
                      </div>
                    </div>

                    <Separator />

                    {/* Agent Details */}
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">Agent Details</h3>
                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="text-muted-foreground">Model Provider:</span>
                          <br />
                          <span className="font-mono text-xs break-all">{selectedTrace.agent_attributes['gen_ai.request.model']}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Cycles</span>
                          <span>{selectedTrace.cycles?.length || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">LLM Calls</span>
                          <span>{selectedTrace.llm_calls?.length || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Tool Calls</span>
                          <span>{selectedTrace.tool_calls?.length || 0}</span>
                        </div>
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="tools" className="space-y-4">
                    <h3 className="text-sm font-medium">Tool Executions</h3>
                    {selectedTrace.tool_calls.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No tools were called</p>
                    ) : (
                      <div className="space-y-3">
                        {selectedTrace.tool_calls.map((tool, index) => (
                          <div key={index} className="p-3 border border-border rounded-lg">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-sm font-medium">{tool.tool_name}</span>
                              <span className="text-xs text-muted-foreground">
                                {formatDuration(tool.duration_ms)}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mb-1">Parameters:</p>
                            <pre className="text-xs bg-muted p-2 rounded mb-2 max-h-20 overflow-y-auto">
                              {JSON.stringify(tool.parameters, null, 2)}
                            </pre>
                            <p className="text-xs text-muted-foreground mb-1">Result:</p>
                            <pre className="text-xs bg-muted p-2 rounded max-h-20 overflow-y-auto">
                              {JSON.stringify(tool.result, null, 2)}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="summary" className="space-y-4">
                    <h3 className="text-sm font-medium">Full Trace Metrics</h3>
                    {selectedTrace.metrics_summary ? (
                      <div className="p-3 border border-border rounded-lg max-h-[70vh] overflow-y-auto text-xs">
                        {renderJsonDetails(selectedTrace.metrics_summary)}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No summary metrics available.</p>
                    )}
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          )}
        </>
      )}

      {showTimelineModal && selectedTrace && (
        <TimelineModal
          traces={selectedTrace.debug_info?.new_traces || []}
          isOpen={true}
          onClose={() => setShowTimelineModal(false)}
        />
      )}

      {showSequenceModal && selectedTrace && (
        <SequenceDiagramModal
          traces={selectedTrace.debug_info?.new_traces || []}
          isOpen={true}
          onClose={()=>setShowSequenceModal(false)}
          userMessage={userMessage}
        />
      )}
    </div>
  )
} 