# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Embedded UI assets for the agent development server.
This contains a modern React-like interface built with vanilla JS and Tailwind CSS.
"""

# Modern chat interface HTML with embedded CSS and JavaScript
CHAT_UI_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Chat Interface</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#eff6ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
        .message-enter {
            animation: messageSlideIn 0.3s ease-out;
        }
        @keyframes messageSlideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .typing-indicator {
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .prose pre {
            background: #1e293b;
            color: #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
        }
        .prose code {
            background: #f1f5f9;
            color: #1e293b;
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 0.875rem;
        }
        .prose pre code {
            background: transparent;
            color: #e2e8f0;
            padding: 0;
        }
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
    <div id="app" class="flex flex-col h-screen max-w-4xl mx-auto">
        <!-- Header -->
        <div class="bg-white/80 backdrop-blur-sm border-b border-gray-200 p-4 shadow-sm">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                    <i data-lucide="bot" class="w-6 h-6 text-white"></i>
                </div>
                <div>
                    <h1 class="text-xl font-semibold text-gray-900" id="agent-title">Agent Chat</h1>
                    <p class="text-sm text-gray-500">AI Assistant powered by Strands</p>
                </div>
                <div class="ml-auto flex items-center space-x-2">
                    <div class="flex items-center space-x-1 text-sm text-gray-500">
                        <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>Connected</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Messages Container -->
        <div id="messages-container" class="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
            <!-- Welcome message will be inserted here -->
        </div>

        <!-- Input Area -->
        <div class="bg-white/80 backdrop-blur-sm border-t border-gray-200 p-4">
            <div class="flex space-x-4">
                <input 
                    type="text" 
                    id="message-input"
                    placeholder="Type your message..."
                    class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    disabled
                />
                <button 
                    id="send-button"
                    class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    disabled
                >
                    <i data-lucide="send" class="w-5 h-5"></i>
                </button>
            </div>
            <p class="text-xs text-gray-500 mt-2">
                Press Enter to send • Shift+Enter for new line
            </p>
        </div>
    </div>

    <script>
        class ChatInterface {
            constructor() {
                this.messages = [];
                this.isLoading = false;
                this.messageInput = document.getElementById('message-input');
                this.sendButton = document.getElementById('send-button');
                this.messagesContainer = document.getElementById('messages-container');
                
                this.init();
            }

            init() {
                // Initialize Lucide icons
                lucide.createIcons();
                
                // Add welcome message
                this.addMessage('agent', 'Hello! I\\'m your AI assistant. How can I help you today?');
                
                // Set up event listeners
                this.messageInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.sendMessage();
                    }
                });
                
                this.sendButton.addEventListener('click', () => this.sendMessage());
                
                // Enable input
                this.messageInput.disabled = false;
                this.sendButton.disabled = false;
                this.messageInput.focus();
                
                // Auto-detect agent name from page title or use default
                this.detectAgentInfo();
            }

            detectAgentInfo() {
                // Try to get agent info from the backend
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        if (data.agent_name) {
                            document.getElementById('agent-title').textContent = data.agent_name + ' Agent';
                        }
                    })
                    .catch(() => {
                        // Fallback to default
                        console.log('Could not detect agent info, using defaults');
                    });
            }

            addMessage(type, content, isLoading = false) {
                const messageId = Date.now().toString();
                const message = {
                    id: messageId,
                    type,
                    content,
                    timestamp: new Date(),
                    isLoading
                };
                
                this.messages.push(message);
                this.renderMessage(message);
                this.scrollToBottom();
                
                return messageId;
            }

            updateMessage(messageId, content, isLoading = false) {
                const message = this.messages.find(m => m.id === messageId);
                if (message) {
                    message.content = content;
                    message.isLoading = isLoading;
                    this.renderMessages();
                }
            }

            renderMessage(message) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} message-enter`;
                messageDiv.id = `message-${message.id}`;
                
                const isUser = message.type === 'user';
                const bgClass = isUser ? 'bg-blue-500 text-white' : 'bg-white/80 backdrop-blur-sm text-gray-900 shadow-sm border border-gray-200';
                
                messageDiv.innerHTML = `
                    <div class="max-w-[80%] rounded-lg p-4 ${bgClass}">
                        <div class="flex items-start space-x-3">
                            <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? 'bg-blue-600' : 'bg-gradient-to-r from-blue-500 to-indigo-600'}">
                                <i data-lucide="${isUser ? 'user' : 'bot'}" class="w-4 h-4 text-white"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                ${message.isLoading ? this.renderLoadingContent() : this.renderMessageContent(message)}
                                <div class="flex items-center justify-between mt-2">
                                    <span class="text-xs ${isUser ? 'text-blue-100' : 'text-gray-400'}">
                                        ${message.timestamp.toLocaleTimeString()}
                                    </span>
                                    ${!isUser && !message.isLoading ? this.renderCopyButton(message.id) : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                this.messagesContainer.appendChild(messageDiv);
                lucide.createIcons();
            }

            renderLoadingContent() {
                return `
                    <div class="flex items-center space-x-2 typing-indicator">
                        <div class="flex space-x-1">
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                        </div>
                        <span class="text-sm text-gray-500">Thinking...</span>
                    </div>
                `;
            }

            renderMessageContent(message) {
                const isUser = message.type === 'user';
                if (isUser) {
                    return `<p class="whitespace-pre-wrap">${this.escapeHtml(message.content)}</p>`;
                } else {
                    // For agent messages, render as markdown
                    const htmlContent = marked.parse(message.content);
                    return `<div class="prose prose-sm max-w-none">${htmlContent}</div>`;
                }
            }

            renderCopyButton(messageId) {
                return `
                    <button 
                        onclick="chatInterface.copyMessage('${messageId}')"
                        class="p-1 rounded hover:bg-gray-100 transition-colors"
                        title="Copy message"
                    >
                        <i data-lucide="copy" class="w-3 h-3 text-gray-400"></i>
                    </button>
                `;
            }

            renderMessages() {
                this.messagesContainer.innerHTML = '';
                this.messages.forEach(message => this.renderMessage(message));
            }

            async sendMessage() {
                const content = this.messageInput.value.trim();
                if (!content || this.isLoading) return;

                // Add user message
                this.addMessage('user', content);
                this.messageInput.value = '';
                this.isLoading = true;
                this.updateInputState();

                // Add loading message
                const loadingMessageId = this.addMessage('agent', '', true);

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ message: content }),
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const data = await response.json();
                    const agentContent = this.parseAgentResponse(data.response);
                    
                    this.updateMessage(loadingMessageId, agentContent, false);

                } catch (error) {
                    console.error('Error sending message:', error);
                    this.updateMessage(
                        loadingMessageId, 
                        'Sorry, I encountered an error. Please try again.\\n\\n**Error:** ' + error.message, 
                        false
                    );
                } finally {
                    this.isLoading = false;
                    this.updateInputState();
                    this.messageInput.focus();
                }
            }

            parseAgentResponse(response) {
                // Handle different response formats
                if (typeof response === 'string') {
                    return response;
                }
                
                if (response && typeof response === 'object') {
                    // Handle Strands agent response format
                    if (response.role === 'assistant' && Array.isArray(response.content)) {
                        return response.content
                            .map(item => item.text || item.content || String(item))
                            .join('\\n');
                    }
                    
                    // Handle other object formats
                    if (response.message) {
                        return response.message;
                    }
                    
                    if (response.content) {
                        return Array.isArray(response.content) 
                            ? response.content.join('\\n')
                            : String(response.content);
                    }
                    
                    // Fallback to JSON string with formatting
                    return '```json\\n' + JSON.stringify(response, null, 2) + '\\n```';
                }
                
                return String(response);
            }

            updateInputState() {
                this.messageInput.disabled = this.isLoading;
                this.sendButton.disabled = this.isLoading;
                
                if (this.isLoading) {
                    this.sendButton.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>';
                } else {
                    this.sendButton.innerHTML = '<i data-lucide="send" class="w-5 h-5"></i>';
                }
                lucide.createIcons();
            }

            copyMessage(messageId) {
                const message = this.messages.find(m => m.id === messageId);
                if (message) {
                    navigator.clipboard.writeText(message.content).then(() => {
                        // Visual feedback
                        const button = document.querySelector(`#message-${messageId} button`);
                        const originalContent = button.innerHTML;
                        button.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-green-500"></i>';
                        lucide.createIcons();
                        
                        setTimeout(() => {
                            button.innerHTML = originalContent;
                            lucide.createIcons();
                        }, 2000);
                    });
                }
            }

            scrollToBottom() {
                setTimeout(() => {
                    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
                }, 100);
            }

            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        }

        // Initialize the chat interface when the page loads
        let chatInterface;
        document.addEventListener('DOMContentLoaded', () => {
            chatInterface = new ChatInterface();
        });
    </script>
</body>
</html>
''' 