/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

"use client"
import React from 'react'
import { Timeline } from '@/components/Timeline'
import { X } from 'lucide-react'
import { MessageTrace } from '../types/observability'
import { ScrollArea } from './ui/scroll-area'

// Recursive event types respecting cycle -> children
interface ChildEvent {
  name: string
  role?: string
  start: number
  duration: number
  message?: string
}

interface CycleEvent extends ChildEvent {
  children: ChildEvent[]
}

interface TimelineModalProps {
  traces: any[]
  isOpen: boolean
  onClose: () => void
}

export const TimelineModal: React.FC<TimelineModalProps> = ({ traces, isOpen, onClose }) => {
  if (!isOpen) return null

  // Show a message if there are no new traces
  if (!Array.isArray(traces) || traces.length === 0) {
    return (
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 relative">
          <button onClick={onClose} className="absolute top-2 right-2 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200">×</button>
          <p className="text-muted-foreground">No new trace events for this message.</p>
        </div>
      </div>
    )
  }

  // base_time = earliest start_time among cycles
  const baseTime = Math.min(...traces.map((t: any) => t.start_time))

  // Debug logging
  console.log('🔍 Raw traces timestamps:', traces.map((t: any) => ({
    name: t.name,
    start_time: t.start_time,
    duration: t.duration,
    children: t.children?.map((c: any) => ({
      name: c.name,
      start_time: c.start_time,
      duration: c.duration
    }))
  })))
  console.log('📍 Base time:', baseTime)

  const cyclesEvents: CycleEvent[] = traces
    .sort((a: any, b: any) => a.start_time - b.start_time)
    .map((cycle: any, index: number) => {
      const children: ChildEvent[] = (cycle.children || [])
        .sort((a: any, b: any) => (a.start_time || 0) - (b.start_time || 0))
        .map((child: any): ChildEvent => {
          const role = child.message?.role || child.metadata?.tool_name || ''
          const messagePreview = (() => {
            if (child.message?.content) {
              const first = child.message.content[0]
              if (typeof first === 'object' && 'text' in first) return first.text.slice(0, 60)
              if (typeof first === 'object' && 'toolResult' in first) return JSON.stringify(first.toolResult.status)
            }
            return ''
          })()
          return {
            name: child.name,
            role,
            start: Number(((child.start_time || 0) - baseTime).toFixed(6)),
            duration: Number((child.duration || 0).toFixed(6)),
            message: messagePreview
          }
        })

      return {
        name: `Cycle ${index + 1}`,
        role: '',
        start: Number(((cycle.start_time || 0) - baseTime).toFixed(6)),
        duration: Number((cycle.duration || 0).toFixed(6)),
        message: '',
        children
      }
    })

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg max-h-[80vh] w-[90vw] p-6 overflow-y-auto relative">
        <h2 className="text-lg font-semibold mb-4">Timeline Events (delta only)</h2>
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
        >
          ×
        </button>

        <div className="mb-6">
          <Timeline cycles={cyclesEvents} showGrid={true} />
        </div>

        <pre className="text-xs bg-muted p-4 rounded max-h-[60vh] overflow-y-auto whitespace-pre-wrap">
{JSON.stringify(cyclesEvents, null, 2)}
        </pre>
      </div>
    </div>
  )
} 