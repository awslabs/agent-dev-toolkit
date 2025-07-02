/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

"use client"
import React, { useEffect, useRef, useState } from 'react'
// Sanitize dynamically generated SVG before injection
import DOMPurify from 'dompurify'
import { X } from 'lucide-react'
import { MessageTrace } from '../types/observability'
import { ScrollArea } from './ui/scroll-area'

interface ChildEvent {
  name: string
  role?: string
  start: number
  duration: number
  message?: string
  metadata?: any
}

interface CycleEvent extends ChildEvent {
  children: ChildEvent[]
}

interface SequenceDiagramModalProps {
  traces: any[]
  userMessage?: string | null
  isOpen: boolean
  onClose: () => void
}

export const SequenceDiagramModal: React.FC<SequenceDiagramModalProps> = ({ traces, userMessage, isOpen, onClose }) => {
  if (!isOpen) return null

  const diagramRef = useRef<HTMLDivElement>(null)
  const [isMermaidLoaded, setMermaidLoaded] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)

  // Load Mermaid script from the public folder
  useEffect(() => {
    // Check if mermaid is already available globally
    if ((window as any).mermaid) {
      setMermaidLoaded(true)
      return
    }

    const basePath = process.env.NODE_ENV === 'production' ? '/static' : ''
    const scriptSrc = `${basePath}/mermaid.min.js`.replace('//', '/')
    const script = document.createElement('script')
    script.src = scriptSrc
    script.onload = () => {
      (window as any).mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' })
      setMermaidLoaded(true)
    }
    script.onerror = () => console.error('Mermaid script could not be loaded.')
    document.body.appendChild(script)

    // Cleanup script on component unmount
    return () => {
      const existingScript = document.querySelector(`script[src='${scriptSrc}']`)
      if (existingScript) {
        document.body.removeChild(existingScript)
      }
    }
  }, [])

  const cycles = (() => {
    if (!Array.isArray(traces) || traces.length === 0) {
      return []
    }
    const baseTime = Math.min(...traces.map((t: any) => t.start_time))
    return traces.map((cycle: any, index: number) => ({
      name: `Cycle ${index + 1}`,
      role: '',
      start: Number(((cycle.start_time||0)-baseTime).toFixed(6)),
      duration: Number((cycle.duration||0).toFixed(6)),
      message:'',
      children: (cycle.children||[]).map((child:any) => ({
        name: child.name,
        role: child.message?.role||child.metadata?.tool_name||'',
        start: Number(((child.start_time||0)-baseTime).toFixed(6)),
        duration: Number((child.duration||0).toFixed(6)),
        message: (()=>{
          if(child.message?.content){
            const first=child.message.content[0]
            if(typeof first==='object'&&'text'in first) return first.text.slice(0,60)
            if(typeof first==='object'&&'toolResult'in first) return JSON.stringify(first.toolResult.status)
          }
          return ''
        })()
      }))
    }))
  })()

  // Render a message if there are no cycles to display
  if (cycles.length === 0) {
    return (
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 relative">
          <button onClick={onClose} className="absolute top-2 right-2 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200">×</button>
          <p className="text-muted-foreground">No new trace events for this message.</p>
        </div>
      </div>
    )
  }

  const sanitizeText = (text: string): string => {
    if (!text) return ""
    
    return text
      // Replace problematic characters
      .replace(/["\n\r]/g, " ")
      .replace(/[<>]/g, "")
      .replace(/[{}[\]]/g, "")
      .replace(/[|\\]/g, "")
      .replace(/[#%&*+]/g, "")
      .replace(/\s+/g, " ")
      .trim()
  }

  const generateMermaidCode = (data: CycleEvent[]): string => {
    const lines = ["sequenceDiagram"]
    lines.push("    participant User")
    lines.push("    participant Assistant")
    lines.push("    participant Tool")
    lines.push("")

    // Add the initial user message if available
    if (userMessage) {
      const sanitized = sanitizeText(userMessage)
      const truncatedMessage = sanitized.length > 50 
        ? sanitized.slice(0, 50) + "..."
        : sanitized
      lines.push(`    User->>+Assistant: ${truncatedMessage}`)
      lines.push("")
    }

    data.forEach((cycle, cycleIndex) => {
      lines.push(`    Note over Assistant: ${cycle.name} starts at t=${cycle.start.toFixed(3)}s`)
      
      cycle.children.forEach((child) => {
        const { name, role, start, duration, message } = child
        
        if (name.includes("Tool:")) {
          const toolName = name.split(":")[1]?.trim() || "unknown"
          
          // Try to extract tool inputs from the child data
          let toolInputs = ""
          if (child.metadata?.toolInput) {
            try {
              const inputs = typeof child.metadata.toolInput === 'string' 
                ? JSON.parse(child.metadata.toolInput) 
                : child.metadata.toolInput
              const inputStr = Object.entries(inputs)
                .map(([key, value]) => `${key}: ${value}`)
                .join(", ")
              toolInputs = inputStr.length > 30 
                ? inputStr.slice(0, 30) + "..."
                : inputStr
            } catch (e) {
              toolInputs = "..."
            }
          }
          
          const toolMessage = toolInputs 
            ? `Call ${toolName}(${sanitizeText(toolInputs)})`
            : `Call ${toolName}`
          
          lines.push(`    Assistant->>+Tool: ${toolMessage}<br/>[start: ${start.toFixed(3)}s]`)
          
          // Handle tool response
          const responseMsg = sanitizeText(message || "")
          const truncatedResponse = responseMsg.length > 50 
            ? responseMsg.slice(0, 50) + "..."
            : responseMsg
          
          lines.push(`    Tool-->>-Assistant: ${truncatedResponse}<br/>[duration: ${duration.toFixed(3)}s]`)
        } else if (role === "assistant" && name.includes("stream_messages")) {
          const msg = sanitizeText(message || "")
          const truncatedMsg = msg.length > 50 
            ? msg.slice(0, 50) + "..."
            : msg
          
          // Only deactivate Assistant on the final response
          if (cycleIndex === data.length - 1) {
            lines.push(`    Assistant-->>-User: ${truncatedMsg}<br/>[start: ${start.toFixed(3)}s, duration: ${duration.toFixed(3)}s]`)
          } else {
            lines.push(`    Assistant-->>User: ${truncatedMsg}<br/>[start: ${start.toFixed(3)}s, duration: ${duration.toFixed(3)}s]`)
          }
        } else if (name.includes("Recursive call")) {
          lines.push(`    Note over Assistant: Recursive call<br/>[start: ${start.toFixed(3)}s, duration: ${duration.toFixed(3)}s]`)
        }
      })
      lines.push("")
    })
    
    return lines.join("\n")
  }

  const mermaidCode = generateMermaidCode(cycles)

  // Copy Mermaid code to clipboard
  const copyMermaidCode = async () => {
    try {
      await navigator.clipboard.writeText(mermaidCode)
      setCopiedCode(true)
      setTimeout(() => setCopiedCode(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  // Render diagram when dependencies are ready
  useEffect(() => {
    const renderDiagram = async () => {
      if (isMermaidLoaded && diagramRef.current) {
        try {
          const mermaid = (window as any).mermaid
          const { svg } = await mermaid.render(`mermaid-diag-${Date.now()}`, mermaidCode)
          
          // Use DOMParser for safer SVG parsing instead of innerHTML
          const parser = new DOMParser()
          const doc = parser.parseFromString(
            DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true } }),
            'image/svg+xml'
          )
          
          // Check for parsing errors
          const parserErrors = doc.getElementsByTagName('parsererror')
          if (parserErrors.length > 0) {
            throw new Error('Invalid SVG content')
          }
          
          // Clear existing content and append sanitized SVG
          diagramRef.current.replaceChildren()
          const svgElement = doc.documentElement
          if (svgElement && svgElement.tagName === 'svg') {
            diagramRef.current.appendChild(document.importNode(svgElement, true))
          } else {
            throw new Error('No valid SVG element found')
          }
        } catch (error) {
          // Safe fallback for error messages
          if (diagramRef.current) {
            diagramRef.current.textContent = 'Error rendering diagram.'
          }
          console.error(error)
        }
      }
    }
    renderDiagram()
  }, [isMermaidLoaded, mermaidCode])

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg max-h-[80vh] w-[90vw] p-6 overflow-y-auto relative">
        <h2 className="text-lg font-semibold mb-4">Sequence Diagram</h2>
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200">×</button>

        <div ref={diagramRef} className="mermaid-container bg-white p-4 rounded min-h-[200px] flex justify-center items-center relative">
          {!isMermaidLoaded && "Loading Mermaid..."}
          
          {/* Copy Mermaid Code Link - Bottom Right */}
          <button
            onClick={copyMermaidCode}
            className="absolute bottom-2 right-2 text-xs text-blue-500 hover:text-blue-700 underline bg-white/80 px-2 py-1 rounded shadow-sm"
          >
            {copiedCode ? 'Copied!' : 'copy mermaidjs code'}
          </button>
        </div>
      </div>
    </div>
  )
} 