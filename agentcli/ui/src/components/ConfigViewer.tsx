/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

'use client'

import { useState, useEffect } from 'react'
import { Settings, FileText, RefreshCw, AlertCircle, ChevronRight, ChevronDown, X } from 'lucide-react'
import { Button } from './ui/button'
import { ScrollArea } from './ui/scroll-area'

interface ConfigData {
  config_path: string
  content: string
}

interface ConfigViewerProps {
  isOpen: boolean
  onClose: () => void
}

interface ParsedConfig {
  name?: string
  system_prompt?: string
  provider?: {
    class?: string
    kwargs?: Record<string, any>
  }
  mcp_servers?: Array<Record<string, any>>
}

export function ConfigViewer({ isOpen, onClose }: ConfigViewerProps) {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['basic', 'provider']))

  const fetchConfig = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/config')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setConfig(data)
    } catch (error) {
      console.error('Error fetching config:', error)
      setError(error instanceof Error ? error.message : 'Failed to load configuration')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchConfig()
    }
  }, [isOpen])

  const parseYaml = (yamlContent: string): ParsedConfig | null => {
    try {
      // Simple YAML parsing for our specific structure
      const lines = yamlContent.split('\n')
      const result: ParsedConfig = {}
      
      let currentSection = ''
      let currentObject: any = result
      let mcpServers: Array<Record<string, any>> = []
      let currentMcpServer: Record<string, any> | null = null
      
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith('#')) continue
        
        if (trimmed.startsWith('name:')) {
          result.name = trimmed.split('name:')[1]?.trim().replace(/['"]/g, '')
        } else if (trimmed.startsWith('system_prompt:')) {
          result.system_prompt = trimmed.split('system_prompt:')[1]?.trim().replace(/['"]/g, '')
        } else if (trimmed === 'provider:') {
          currentSection = 'provider'
          result.provider = {}
          currentObject = result.provider
        } else if (trimmed === 'mcp_servers:') {
          currentSection = 'mcp_servers'
          mcpServers = []
        } else if (currentSection === 'provider') {
          if (trimmed.startsWith('class:')) {
            result.provider!.class = trimmed.split('class:')[1]?.trim().replace(/['"]/g, '')
          } else if (trimmed === 'kwargs:') {
            result.provider!.kwargs = {}
            currentObject = result.provider!.kwargs
          } else if (trimmed.includes(':') && currentObject === result.provider!.kwargs) {
            const [key, value] = trimmed.split(':')
            if (key && value) {
              currentObject[key.trim()] = value.trim().replace(/['"]/g, '')
            }
          }
        } else if (currentSection === 'mcp_servers') {
          if (trimmed.startsWith('- name:')) {
            if (currentMcpServer) mcpServers.push(currentMcpServer)
            currentMcpServer = { name: trimmed.split('name:')[1]?.trim().replace(/['"]/g, '') }
          } else if (currentMcpServer && trimmed.includes(':')) {
            const [key, value] = trimmed.split(':')
            if (key && value) {
              currentMcpServer[key.trim()] = value.trim().replace(/['"]/g, '')
            }
          }
        }
      }
      
      if (currentMcpServer) mcpServers.push(currentMcpServer)
      if (mcpServers.length > 0) result.mcp_servers = mcpServers
      
      return result
    } catch (e) {
      console.error('Failed to parse YAML:', e)
      return null
    }
  }

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const renderValue = (value: any): string => {
    if (typeof value === 'string') return value
    if (typeof value === 'number') return value.toString()
    if (typeof value === 'boolean') return value ? 'true' : 'false'
    return JSON.stringify(value)
  }

  if (!isOpen) return null

  const parsedConfig = config ? parseYaml(config.content) : null

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg h-[90vh] w-full max-w-4xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <Settings className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold">Agent Configuration</h2>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchConfig}
              disabled={isLoading}
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              title="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Info Banner */}
        <div className="px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <p className="text-xs text-blue-700 dark:text-blue-300">
            💡 This configuration is read-only. To modify it, edit the <code className="bg-blue-100 dark:bg-blue-800 px-1 py-0.5 rounded text-xs">.agent.yaml</code> file in your project directory and restart the agent.
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-muted-foreground">
                <RefreshCw className="h-4 w-4 animate-spin" />
                Loading configuration...
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
            </div>
          )}

          {config && parsedConfig && !isLoading && !error && (
            <ScrollArea className="h-full">
              <div className="p-6 space-y-6">
                {/* Basic Information */}
                <div className="space-y-3">
                  <button
                    onClick={() => toggleSection('basic')}
                    className="flex items-center gap-2 text-lg font-semibold hover:text-blue-600 transition-colors"
                  >
                    {expandedSections.has('basic') ? 
                      <ChevronDown className="h-4 w-4" /> : 
                      <ChevronRight className="h-4 w-4" />
                    }
                    Basic Information
                  </button>
                  {expandedSections.has('basic') && (
                    <div className="ml-6 space-y-2 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                      <div className="grid grid-cols-1 gap-3">
                        <div>
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Name:</span>
                          <span className="ml-2 text-sm">{parsedConfig.name || 'Not specified'}</span>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">System Prompt:</span>
                          <div className="ml-2 text-sm mt-1 p-2 bg-white dark:bg-gray-700 rounded border">
                            {parsedConfig.system_prompt || 'Not specified'}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Provider Configuration */}
                {parsedConfig.provider && (
                  <div className="space-y-3">
                    <button
                      onClick={() => toggleSection('provider')}
                      className="flex items-center gap-2 text-lg font-semibold hover:text-blue-600 transition-colors"
                    >
                      {expandedSections.has('provider') ? 
                        <ChevronDown className="h-4 w-4" /> : 
                        <ChevronRight className="h-4 w-4" />
                      }
                      Provider Configuration
                    </button>
                    {expandedSections.has('provider') && (
                      <div className="ml-6 space-y-3 bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                        <div>
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Class:</span>
                          <span className="ml-2 text-sm font-mono bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded">
                            {parsedConfig.provider.class || 'Not specified'}
                          </span>
                        </div>
                        {parsedConfig.provider.kwargs && Object.keys(parsedConfig.provider.kwargs).length > 0 && (
                          <div>
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-2">Parameters:</span>
                            <div className="ml-2 space-y-1">
                              {Object.entries(parsedConfig.provider.kwargs).map(([key, value]) => (
                                <div key={key} className="flex items-center gap-2">
                                  <span className="text-sm font-mono text-gray-600 dark:text-gray-400 min-w-0 flex-shrink-0">
                                    {key}:
                                  </span>
                                  <span className="text-sm bg-white dark:bg-gray-700 px-2 py-1 rounded border text-gray-900 dark:text-gray-100">
                                    {renderValue(value)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* MCP Servers */}
                {parsedConfig.mcp_servers && parsedConfig.mcp_servers.length > 0 && (
                  <div className="space-y-3">
                    <button
                      onClick={() => toggleSection('mcp')}
                      className="flex items-center gap-2 text-lg font-semibold hover:text-blue-600 transition-colors"
                    >
                      {expandedSections.has('mcp') ? 
                        <ChevronDown className="h-4 w-4" /> : 
                        <ChevronRight className="h-4 w-4" />
                      }
                      MCP Servers ({parsedConfig.mcp_servers.length})
                    </button>
                    {expandedSections.has('mcp') && (
                      <div className="ml-6 space-y-3">
                        {parsedConfig.mcp_servers.map((server, index) => (
                          <div key={index} className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                            <h4 className="font-medium text-sm mb-2">{server.name || `Server ${index + 1}`}</h4>
                            <div className="space-y-1 text-sm">
                              {Object.entries(server).filter(([key]) => key !== 'name').map(([key, value]) => (
                                <div key={key} className="flex items-center gap-2">
                                  <span className="text-gray-600 dark:text-gray-400 min-w-0 flex-shrink-0">
                                    {key}:
                                  </span>
                                  <span className="bg-white dark:bg-gray-700 px-2 py-1 rounded border">
                                    {renderValue(value)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Raw YAML Section */}
                <div className="space-y-3">
                  <button
                    onClick={() => toggleSection('raw')}
                    className="flex items-center gap-2 text-lg font-semibold hover:text-blue-600 transition-colors"
                  >
                    {expandedSections.has('raw') ? 
                      <ChevronDown className="h-4 w-4" /> : 
                      <ChevronRight className="h-4 w-4" />
                    }
                    Raw Configuration
                  </button>
                  {expandedSections.has('raw') && (
                    <div className="ml-6">
                      <pre className="text-xs font-mono bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg overflow-auto">
                        {config.content}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </ScrollArea>
          )}
        </div>


      </div>
    </div>
  )
} 