/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

"use client"

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

interface TimelineProps {
  cycles: CycleEvent[]
  showGrid?: boolean
}

export function Timeline({ cycles, showGrid = false }: TimelineProps) {
  if (!cycles.length) return null

  // Calculate total timeline duration
  const allEvents = cycles.flatMap(c => [c, ...c.children])
  const totalDuration = Math.max(...allEvents.map(e => e.start + e.duration)) || 1

  const getBarColor = (eventName: string, role?: string) => {
    if (eventName.startsWith('Tool:')) return 'bg-green-600'
    if (role === 'assistant') return 'bg-blue-600'
    if (role === 'user') return 'bg-orange-600'
    return 'bg-gray-600'
  }

  return (
    <div className="space-y-6 p-4">
      {/* Timeline header with time markers */}
      <div className="relative w-full h-6 border-b border-border">
        {showGrid && [...Array(11)].map((_, idx) => {
          const timepoint = (idx / 10) * totalDuration
          return (
            <div key={idx} className="absolute flex flex-col items-center" style={{ left: `${idx * 10}%` }}>
              <div className="text-xs text-muted-foreground">{timepoint.toFixed(1)}s</div>
              <div className="w-px h-2 bg-border"></div>
            </div>
          )
        })}
      </div>

      {cycles.map((cycle, cycleIdx) => (
        <div key={cycleIdx} className="space-y-2">
          {/* Cycle header */}
          <div className="text-sm font-semibold text-foreground border-l-4 border-primary pl-2">
            {cycle.name}
          </div>

          {/* Cycle children events */}
          <div className="space-y-1 ml-4">
            {cycle.children.map((child, childIdx) => {
              const leftOffset = (child.start / totalDuration) * 100
              const widthPercent = (child.duration / totalDuration) * 100
              const barColor = getBarColor(child.name, child.role)

              return (
                <div key={childIdx} className="space-y-1">
                  {/* Event label */}
                  <div className="text-xs font-mono text-muted-foreground">
                    {child.name} {child.role && `(${child.role})`} — {child.duration.toFixed(6)}s
                  </div>

                  {/* Event timeline bar */}
                  <div className="relative w-full h-3 bg-muted/30 rounded overflow-hidden">
                    {/* Grid lines */}
                    {showGrid && [...Array(11)].map((_, idx) => (
                      <div
                        key={idx}
                        className="absolute top-0 h-full w-px bg-border/30"
                        style={{ left: `${idx * 10}%` }}
                      />
                    ))}

                    {/* Event bar */}
                    <div
                      className={`absolute top-0 h-full ${barColor} rounded transition-all`}
                      style={{ left: `${leftOffset}%`, width: `${widthPercent}%` }}
                      title={`${child.name}: ${child.start}s - ${(child.start + child.duration).toFixed(3)}s`}
                    />
                  </div>

                  {/* Optional message preview */}
                  {child.message && (
                    <div className="text-xs text-muted-foreground/70 italic ml-2">
                      "{child.message}"
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
} 