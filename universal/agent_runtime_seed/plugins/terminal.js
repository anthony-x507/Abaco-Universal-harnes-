'use strict'

const { exec } = require('child_process')

module.exports = {
  name: 'terminal_access',
  version: '1.0.0',
  description: 'Run a shell command after the signed core asks the user',

  get_tool_definition() {
    return {
      name: 'terminal_access',
      description: 'Execute a command in the local terminal',
      parameters: {
        type: 'object',
        properties: {
          command: { type: 'string', description: 'Command to run' },
        },
        required: ['command'],
      },
    }
  },

  async execute(args, ctx) {
    const command = String(args.command || '').trim()
    if (!command) throw new Error('command is required')
    const permission = await ctx.corePost('/v1/permission/ask', {
      action: 'Run a terminal command',
      details: `Command: ${command}`,
      agent: 'terminal_access',
    })
    if (!permission.granted) {
      throw new Error(permission.reason || 'The user denied this command')
    }
    return new Promise((resolve, reject) => {
      exec(command, { timeout: 30000 }, (error, stdout, stderr) => {
        if (error) reject(error)
        else resolve(String(stdout || stderr || 'Command finished with no output'))
      })
    })
  },
}
