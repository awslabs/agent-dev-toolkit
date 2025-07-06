/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Copy, Check, Bot, User, Loader2, FileText, Settings } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { SettingsPanel } from '@/components/SettingsPanel'
import { MetricsPanel } from '@/components/MetricsPanel'
import { ConfigViewer } from '@/components/ConfigViewer'
import { AgentSettings, MessageTrace } from '../types/observability'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  trace?: MessageTrace
}

interface AgentInfo {
  name: string
  description?: string
  model?: string
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agentInfo, setAgentInfo] = useState<AgentInfo>({ name: 'Agent Playground' })
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [selectedTrace, setSelectedTrace] = useState<MessageTrace | undefined>()
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settings, setSettings] = useState<AgentSettings>({
    temperature: 0.7,
    top_p: 0.9,
    top_k: 50,
    max_tokens: 1024,
    model: "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
  })
  const [isMetricsPanelOpen, setIsMetricsPanelOpen] = useState(false)
  const [isConfigViewerOpen, setIsConfigViewerOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Fetch agent info on mount
  useEffect(() => {
    fetchAgentInfo()
  }, [])

  const fetchAgentInfo = async () => {
    try {
      const response = await fetch('/info')
      if (response.ok) {
        const data = await response.json()
        const agentData = {
          name: data.name || 'Agent',
          description: data.description,
          model: data.model
        }
        setAgentInfo(agentData)
        
        // Update settings with the actual model from agent
        if (data.model && data.model !== 'unknown') {
          setSettings(prev => ({ ...prev, model: data.model }))
        }
      }
    } catch (error) {
      console.error('Failed to fetch agent info:', error)
    }
  }

  const generateMockTrace = (messageId: string, userMessage: string, assistantResponse: string): MessageTrace => {
    const startTime = new Date().toISOString()
    const endTime = new Date(Date.now() + Math.random() * 2000 + 500).toISOString()
    const duration = new Date(endTime).getTime() - new Date(startTime).getTime()
    
    // Use the actual agent model, fallback to settings.model if not available
    const actualModel = agentInfo.model && agentInfo.model !== 'unknown' ? agentInfo.model : settings.model
    
    return {
      message_id: messageId,
      agent_attributes: {
        'gen_ai.system': 'strands-agents',
        'agent.name': agentInfo.name,
        'gen_ai.agent.name': agentInfo.name,
        'gen_ai.prompt': userMessage,
        'gen_ai.completion': assistantResponse,
        'system_prompt': 'You are a helpful AI assistant',
        'gen_ai.request.model': actualModel,
        'gen_ai.event.start_time': startTime,
        'gen_ai.event.end_time': endTime,
        'gen_ai.usage.prompt_tokens': Math.floor(userMessage.length / 4),
        'gen_ai.usage.completion_tokens': Math.floor(assistantResponse.length / 4),
        'gen_ai.usage.total_tokens': Math.floor((userMessage.length + assistantResponse.length) / 4)
      },
      cycles: [
        {
          cycle_id: `cycle-${Date.now()}`,
          prompt: `System: You are a helpful AI assistant\n\nUser: ${userMessage}`,
          completion: assistantResponse,
          start_time: startTime,
          end_time: endTime,
          duration_ms: duration
        }
      ],
      llm_calls: [
        {
          model: actualModel,
          prompt: `System: You are a helpful AI assistant\n\nUser: ${userMessage}`,
          completion: assistantResponse,
          usage: {
            prompt_tokens: Math.floor(userMessage.length / 4),
            completion_tokens: Math.floor(assistantResponse.length / 4),
            total_tokens: Math.floor((userMessage.length + assistantResponse.length) / 4)
          },
          start_time: startTime,
          end_time: endTime,
          duration_ms: duration
        }
      ],
      tool_calls: [],
      total_duration_ms: duration,
      total_tokens: {
        prompt_tokens: Math.floor(userMessage.length / 4),
        completion_tokens: Math.floor(assistantResponse.length / 4),
        total_tokens: Math.floor((userMessage.length + assistantResponse.length) / 4)
      }
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages((prev: Message[]) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: 'ui-session',
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Handle different response formats
      let assistantContent = ''
      let traceData: MessageTrace | undefined
      
      if (typeof data === 'string') {
        assistantContent = data
      } else if (data.response && data.trace) {
        // New format with trace data
        if (typeof data.response === 'object' && data.response.role === 'assistant' && data.response.content) {
          if (Array.isArray(data.response.content)) {
            assistantContent = data.response.content
              .filter((item: any) => item.text)
              .map((item: any) => item.text)
              .join('\n')
          } else {
            assistantContent = data.response.content
          }
        } else if (typeof data.response === 'string') {
          assistantContent = data.response
        } else {
          assistantContent = JSON.stringify(data.response, null, 2)
        }
        traceData = data.trace
      } else if (data.role === 'assistant' && data.content) {
        // Direct assistant response
        if (Array.isArray(data.content)) {
          assistantContent = data.content
            .filter((item: any) => item.type === 'text')
            .map((item: any) => item.text)
            .join('\n')
        } else {
          assistantContent = data.content
        }
      } else if (data.response && typeof data.response === 'object') {
        // Nested response object (Strands format)
        const response = data.response
        if (response.role === 'assistant' && response.content) {
          if (Array.isArray(response.content)) {
            assistantContent = response.content
              .filter((item: any) => item.text)
              .map((item: any) => item.text)
              .join('\n')
          } else {
            assistantContent = response.content
          }
        } else {
          assistantContent = JSON.stringify(response, null, 2)
        }
      } else if (data.response && typeof data.response === 'string') {
        assistantContent = data.response
      } else if (data.message) {
        assistantContent = data.message
      } else {
        assistantContent = JSON.stringify(data, null, 2)
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
        trace: traceData || generateMockTrace((Date.now() + 1).toString(), userMessage.content, assistantContent)
      }

      setMessages((prev: Message[]) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        timestamp: new Date()
      }
      setMessages((prev: Message[]) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const copyToClipboard = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(messageId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleMessageClick = (message: Message) => {
    if (message.trace) {
      setSelectedTrace(message.trace)
      setIsMetricsPanelOpen(true)
    }
  }

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      {/* Centering container for the chat panel */}
      <main className="flex-1 flex justify-center items-center p-2 overflow-hidden">
        {/* The actual chat panel with max-width and controlled height */}
        <div className="w-full max-w-[1000px] h-full flex flex-col bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto px-6 space-y-0 custom-scrollbar ">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground py-12">
                <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium mb-2">Agent Development Toolkit for Strands - Playground</p>
                <p className="text-sm">Start a conversation by typing a message below.</p>
              </div>
            )}
            
            {messages.map((message: Message) => (
              <div
                key={message.id}
                className="flex gap-4 items-start hover:bg-gray-50 dark:hover:bg-gray-700/50 -mx-6 px-6 pb-2 pt-8 transition-colors border-b border-gray-200 dark:border-gray-700 last:border-none"
                onClick={() => handleMessageClick(message)}
              >
                {/* Avatar */}
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  {message.role === 'user' ? (
                    <User className="h-4 w-4" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                </div>
                
                {/* Message Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">
                      {message.role === 'user' ? 'User' : 'Agent'}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                    
                  </div>
                  
                  <div className="prose prose-sm max-w-none dark:prose-invert flex flex-col gap-4 justify-start items-start">
                    {message.role === 'assistant' ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          code: ({ node, inline, className, children, ...props }: any) => {
                            const match = /language-(\w+)/.exec(className || '')
                            return !inline ? (
                              <pre className="bg-gray-900 text-gray-100 rounded p-3 overflow-x-auto">
                                <code {...props}>{children}</code>
                              </pre>
                            ) : (
                              <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm" {...props}>
                                {children}
                              </code>
                            )
                          }
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <p className="whitespace-pre-wrap text-gray-900 dark:text-gray-100">{message.content}</p>
                    )}
                    {message.trace && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedTrace(message.trace)
                          setIsMetricsPanelOpen(true)
                        }}
                        className="text-xs bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:hover:bg-blue-800 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-sm transition-colors"
                      >
                        View trace →
                      </button>
                    )}
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      copyToClipboard(message.content, message.id)
                    }}
                    className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-muted-foreground hover:text-foreground"
                    title="Copy message"
                  >
                    {copiedId === message.id ? (
                      <div className="flex items-center gap-1">
                        <Check className="h-3 w-3 text-green-500" />
                        <span>Copied</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1">
                        <Copy className="h-3 w-3" />
                        <span>Copy</span>
                      </div>
                    )}
                  </button>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex gap-4 items-start -mx-6 px-6 py-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{agentInfo.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-border bg-white dark:bg-gray-800 p-6">
            <div className="flex gap-3">
              <Button
                onClick={() => setIsConfigViewerOpen(true)}
                size="icon"
                variant="ghost"
                className="h-12 w-12 shrink-0"
                title="Configuration"
              >
                <Settings className="h-4 w-4" />
              </Button>
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  ref={inputRef}
                  onKeyDown={handleKeyPress}
                  placeholder={`Send a message to ${agentInfo.name}...`}
                  disabled={isLoading}
                  className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
              </div>
              <Button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                size="icon"
                className="h-12 w-12 shrink-0"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </main>

      {/* Right Panel - Metrics */}
      <MetricsPanel 
        selectedTrace={selectedTrace} 
        messages={messages}
        onClose={() => setSelectedTrace(undefined)}
        isOpen={isMetricsPanelOpen}
        onToggle={setIsMetricsPanelOpen}
      />

      {/* Config Viewer Modal */}
      <ConfigViewer 
        isOpen={isConfigViewerOpen}
        onClose={() => setIsConfigViewerOpen(false)}
      />
    </div>
  )
} 