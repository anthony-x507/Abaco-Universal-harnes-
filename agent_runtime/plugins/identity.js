'use strict'

// Node stub. Node only proposes; the signed Python core is the source of truth
// for identity. There is no coreGet — only corePost.
module.exports = {
  name: 'identity',
  version: '1.0.0',
  description: 'Ask the signed core who this agent is. The core answers; Node does not decide.',

  get_tool_definition() {
    return {
      name: 'identity',
      description: 'Return the harness agent identity from the signed core.',
      parameters: { type: 'object', properties: {} },
    }
  },

  async execute(_args, ctx) {
    return JSON.stringify(await ctx.corePost('/v1/identity', {}))
  },
}
