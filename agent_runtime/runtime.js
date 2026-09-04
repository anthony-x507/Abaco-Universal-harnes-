'use strict'

const fs = require('fs')
const path = require('path')
const express = require('express')
const axios = require('axios')

const CORE_URL = (process.env.UNIVERSAL_CORE_URL || 'http://127.0.0.1:43124').replace(/\/$/, '')
const PORT = Number(process.env.UNIVERSAL_RUNTIME_PORT || 43126)
const RUNTIME_DIR = process.env.UNIVERSAL_RUNTIME_DIR
  ? path.resolve(process.env.UNIVERSAL_RUNTIME_DIR)
  : path.join(process.env.HOME || '', 'Library', 'Application Support', 'Universal', 'agent_runtime')
const PLUGINS_DIR = path.join(RUNTIME_DIR, 'plugins')

const app = express()
app.use(express.json({ limit: '2mb' }))

const plugins = {}

function loadPlugins() {
  for (const key of Object.keys(plugins)) delete plugins[key]
  if (!fs.existsSync(PLUGINS_DIR)) fs.mkdirSync(PLUGINS_DIR, { recursive: true })
  for (const file of fs.readdirSync(PLUGINS_DIR)) {
    if (!file.endsWith('.js')) continue
    const full = path.join(PLUGINS_DIR, file)
    try {
      delete require.cache[require.resolve(full)]
      const plugin = require(full)
      if (plugin && plugin.name) plugins[plugin.name] = plugin
    } catch (error) {
      console.error(`plugin load failed ${file}: ${error.message}`)
    }
  }
}

async function corePost(pathname, body) {
  const response = await axios.post(`${CORE_URL}${pathname}`, body, { timeout: 80000 })
  return response.data
}

async function callLlm(messages, tools) {
  return corePost('/v1/llm/complete', { messages, tools })
}

function toolDefinitions() {
  return Object.values(plugins)
    .map((plugin) => {
      if (typeof plugin.get_tool_definition !== 'function') return null
      return plugin.get_tool_definition()
    })
    .filter(Boolean)
}

const MAX_ITERATIONS = 10
const REPEAT_LIMIT = 3
const LIMIT_MESSAGE =
  'The agent could not finish this task within the tool-call limit. Try a simpler question.'
const REPEAT_NUDGE =
  'You already called this tool repeatedly. Give a final answer now from the tool results you have. Do not call tools again.'

async function runAgentLoop(prompt, history) {
  const messages = [...(history || []), { role: 'user', content: prompt }]
  const tools = toolDefinitions()
  let response = ''
  let lastNames = ''
  let streak = 0
  for (let iteration = 0; iteration < MAX_ITERATIONS; iteration += 1) {
    const llm = await callLlm(messages, tools)
    const calls = llm.tool_calls || []
    if (!calls.length) {
      response = llm.content || ''
      break
    }
    messages.push({
      role: 'assistant',
      content: llm.content || null,
      tool_calls: calls.map((call, index) => ({
        id: call.id || `call_${index}`,
        type: 'function',
        function: {
          name: call.name,
          arguments:
            typeof call.arguments === 'string' ? call.arguments || '{}' : JSON.stringify(call.arguments || {}),
        },
      })),
    })
    for (const call of calls) {
      const plugin = plugins[call.name]
      let content = ''
      if (!plugin || typeof plugin.execute !== 'function') {
        content = `Plugin "${call.name}" not found`
      } else {
        try {
          let args = {}
          try {
            args = typeof call.arguments === 'string' ? JSON.parse(call.arguments || '{}') : call.arguments || {}
          } catch {
            args = { raw: call.arguments }
          }
          content = await plugin.execute(args, { corePost, runtimeDir: RUNTIME_DIR })
          if (typeof content !== 'string') content = JSON.stringify(content)
        } catch (error) {
          content = error.message || String(error)
        }
      }
      messages.push({ role: 'tool', tool_call_id: call.id || call.name, content })
    }
    const names = calls.map((call) => call.name || '').join(',')
    streak = names && names === lastNames ? streak + 1 : 1
    lastNames = names
    if (streak >= REPEAT_LIMIT) {
      messages.push({ role: 'user', content: REPEAT_NUDGE })
      const finalLlm = await callLlm(messages, [])
      response = (finalLlm && finalLlm.content) || LIMIT_MESSAGE
      break
    }
  }
  return response || LIMIT_MESSAGE
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', product: 'Universal runtime', plugins: Object.keys(plugins) })
})

app.get('/list_plugins', (_req, res) => {
  res.json({
    plugins: Object.values(plugins).map((plugin) => ({
      name: plugin.name,
      version: plugin.version || '1.0.0',
      description: plugin.description || '',
    })),
  })
})

app.post('/think', async (req, res) => {
  try {
    const prompt = String(req.body?.prompt || '')
    const history = Array.isArray(req.body?.history) ? req.body.history : []
    const response = await runAgentLoop(prompt, history)
    res.json({ status: 'success', response })
  } catch (error) {
    res.status(500).json({ status: 'error', error: error.message })
  }
})

app.post('/reload', (_req, res) => {
  loadPlugins()
  res.json({ status: 'reloaded', plugins: Object.keys(plugins) })
})

app.post('/evolve', async (req, res) => {
  try {
    const result = await corePost('/v1/runtime/evolve', {
      target_file: req.body?.target_file,
      new_code: req.body?.new_code,
      reason: req.body?.reason || 'Proposed by the runtime',
      agent: 'evolution',
    })
    res.json(result)
  } catch (error) {
    const status = error.response?.status || 500
    res.status(status).json({
      status: 'error',
      error: error.response?.data?.detail || error.message,
    })
  }
})

loadPlugins()
app.listen(PORT, '127.0.0.1', () => {
  console.log(`Universal runtime listening on http://127.0.0.1:${PORT}`)
})
