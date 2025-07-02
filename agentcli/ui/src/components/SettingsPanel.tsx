/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react'
import { Settings, Sliders, ChevronLeft, ChevronRight } from 'lucide-react'
import { Slider } from '@/components/ui/slider'
import { Separator } from '@/components/ui/separator'
import { AgentSettings } from '@/types/observability'

interface SettingsPanelProps {
  settings: AgentSettings
  onSettingsChange: (settings: AgentSettings) => void
  isOpen: boolean
  onToggle: (open: boolean) => void
}

export function SettingsPanel({ settings, onSettingsChange, isOpen, onToggle }: SettingsPanelProps) {
  const updateSetting = (key: keyof AgentSettings, value: number | string) => {
    onSettingsChange({
      ...settings,
      [key]: value
    })
  }

  return (
    <div className={`relative bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ${isOpen ? 'w-80' : 'w-12'} overflow-hidden`}>
      {/* Settings Icon (visible when collapsed) */}
      {!isOpen && (
        <div className="p-3 pt-4">
          <button
            onClick={() => onToggle(true)}
            className="w-6 h-6 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Open settings"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Settings Content (visible when expanded) */}
      {isOpen && (
        <div className="p-6 overflow-y-auto h-full relative">
          {/* Collapse button - floating to the right */}
          <button
            onClick={() => onToggle(false)}
            className="absolute top-4 right-4 w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 flex items-center justify-center transition-colors z-10"
            title="Collapse Settings"
          >
            <ChevronLeft className="h-3 w-3 text-gray-600 dark:text-gray-300" />
          </button>

          <div className="flex items-center gap-2 mb-6">
            <Settings className="h-4 w-4" />
            <h2 className="text-md font-semibold">Agent Settings</h2>
          </div>

          <div className="space-y-6">
            {/* Model Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Model ID</label>
              <textarea
                value={settings.model}
                onChange={(e) => updateSetting('model', e.target.value)}
                placeholder="Enter model ID (e.g., us.anthropic.claude-3-7-sonnet-20250219-v1:0)"
                className="w-full p-2 border border-input rounded-md bg-background text-sm resize-none min-h-[60px]"
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Enter the full model ID. Default is Claude 3.5 Sonnet.
              </p>
            </div>

            <Separator />

            {/* Temperature */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Temperature</label>
                <span className="text-sm text-muted-foreground">{settings.temperature}</span>
              </div>
              <Slider
                value={[settings.temperature]}
                onValueChange={(value) => updateSetting('temperature', value[0])}
                max={2}
                min={0}
                step={0.1}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Controls randomness. Lower values make responses more focused and deterministic.
              </p>
            </div>

            {/* Top P */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Top P</label>
                <span className="text-sm text-muted-foreground">{settings.top_p}</span>
              </div>
              <Slider
                value={[settings.top_p]}
                onValueChange={(value) => updateSetting('top_p', value[0])}
                max={1}
                min={0}
                step={0.05}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Nucleus sampling. Controls diversity by considering only the top P probability mass.
              </p>
            </div>

            {/* Top K */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Top K</label>
                <span className="text-sm text-muted-foreground">{settings.top_k}</span>
              </div>
              <Slider
                value={[settings.top_k]}
                onValueChange={(value) => updateSetting('top_k', value[0])}
                max={100}
                min={1}
                step={1}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Limits the number of highest probability tokens to consider.
              </p>
            </div>

            {/* Max Tokens */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Max Tokens</label>
                <span className="text-sm text-muted-foreground">{settings.max_tokens}</span>
              </div>
              <Slider
                value={[settings.max_tokens]}
                onValueChange={(value) => updateSetting('max_tokens', value[0])}
                max={4096}
                min={1}
                step={1}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Maximum number of tokens to generate in the response.
              </p>
            </div>

            <Separator />

            {/* Reset Button */}
            <button
              onClick={() => onSettingsChange({
                temperature: 0.7,
                top_p: 0.9,
                top_k: 50,
                max_tokens: 1024,
                model: "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
              })}
              className="w-full p-2 text-sm border border-input rounded-md hover:bg-accent transition-colors"
            >
              Reset to Defaults
            </button>
          </div>
        </div>
      )}
    </div>
  )
} 