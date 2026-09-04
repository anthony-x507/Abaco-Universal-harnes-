'use strict'

module.exports = {
  name: 'propose_evolution',
  version: '1.0.0',
  description: 'Propose a plugin change. The signed core writes the file only after the user allows it.',

  get_tool_definition() {
    return {
      name: 'propose_evolution',
      description: 'Propose a JavaScript plugin change in the user runtime',
      parameters: {
        type: 'object',
        properties: {
          target_file: { type: 'string', description: 'Path relative to the runtime, e.g. plugins/web_search.js' },
          new_code: { type: 'string', description: 'Full new file contents' },
          reason: { type: 'string', description: 'Why this change is needed' },
        },
        required: ['target_file', 'new_code', 'reason'],
      },
    }
  },

  async execute(args, ctx) {
    const result = await ctx.corePost('/v1/runtime/evolve', {
      target_file: args.target_file,
      new_code: args.new_code,
      reason: args.reason || 'Proposed by the agent',
      agent: 'evolution',
    })
    if (!result.granted) {
      return result.reason || 'The user denied the change.'
    }
    return `Updated ${result.file}. The runtime reloaded that plugin.`
  },
}
