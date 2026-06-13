<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

const props = defineProps<{
  message: string
  isUser?: boolean
}>()

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

// Custom renderer for code highlighting
const renderer = new marked.Renderer()
renderer.code = function(code: string, infostring: string | undefined): string {
  const lang = infostring || ''
  let highlighted: string
  if (lang && hljs.getLanguage(lang)) {
    try {
      highlighted = hljs.highlight(code, { language: lang }).value
    } catch {
      highlighted = hljs.highlightAuto(code).value
    }
  } else {
    highlighted = hljs.highlightAuto(code).value
  }
  return `<pre><code class="hljs">${highlighted}</code></pre>`
}

marked.use({ renderer })

const bgClass = computed(() =>
  props.isUser ? 'message-user ml-auto' : 'message-assistant'
)

const textClass = computed(() =>
  props.isUser ? 'text-white' : 'text-gray-100'
)

// Render markdown to HTML
const renderedContent = computed(() => {
  if (props.isUser) {
    // User messages are plain text
    return escapeHtml(props.message)
  }
  // Assistant messages are markdown
  return marked.parse(props.message) as string
})

// Escape HTML for user messages
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}
</script>

<template>
  <div
    :class="[bgClass, textClass]"
    class="p-4 max-w-[80%] break-words message-bubble"
  >
    <!-- User message: plain text -->
    <div v-if="isUser" class="whitespace-pre-wrap">{{ message }}</div>

    <!-- Assistant message: rendered markdown -->
    <div v-else v-html="renderedContent" class="markdown-content"></div>
  </div>
</template>

<style>
/* Markdown content styles */
.markdown-content {
  line-height: 1.6;
}

.markdown-content p {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

.markdown-content p:first-child {
  margin-top: 0;
}

.markdown-content p:last-child {
  margin-bottom: 0;
}

.markdown-content h1, .markdown-content h2, .markdown-content h3 {
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.markdown-content h1 { font-size: 1.5rem; }
.markdown-content h2 { font-size: 1.25rem; }
.markdown-content h3 { font-size: 1.125rem; }

.markdown-content ul, .markdown-content ol {
  margin-left: 1.5rem;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

.markdown-content li {
  margin-top: 0.25rem;
  margin-bottom: 0.25rem;
}

.markdown-content code {
  background-color: #1e293b;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.875em;
}

.markdown-content pre {
  background-color: #1e293b;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin-top: 0.75rem;
  margin-bottom: 0.75rem;
}

.markdown-content pre code {
  background-color: transparent;
  padding: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.markdown-content blockquote {
  border-left: 3px solid #3b82f6;
  padding-left: 1rem;
  margin-left: 0;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
  color: #9ca3af;
}

.markdown-content a {
  color: #60a5fa;
  text-decoration: underline;
}

.markdown-content a:hover {
  color: #93c5fd;
}

.markdown-content table {
  border-collapse: collapse;
  margin-top: 0.75rem;
  margin-bottom: 0.75rem;
  width: 100%;
}

.markdown-content th, .markdown-content td {
  border: 1px solid #374151;
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.markdown-content th {
  background-color: #1e293b;
  font-weight: 600;
}

/* Message bubble styles */
.message-bubble {
  border-radius: 1rem;
}

.message-user {
  background-color: #3b82f6;
  border-bottom-right-radius: 0.25rem;
}

.message-assistant {
  background-color: #1e293b;
  border-bottom-left-radius: 0.25rem;
}
</style>
