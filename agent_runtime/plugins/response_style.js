'use strict'

module.exports = {
  name: 'response_style',
  version: '1.0.0',
  description: 'Change replies between concise, detailed, and default styles',

  get_tool_definition() {
    return {
      name: 'set_response_style',
      description: 'Change the response style: concise, detailed, or default',
      parameters: {
        type: 'object',
        properties: {
          style: {
            type: 'string',
            enum: ['concise', 'detailed', 'default'],
            description: 'Response style',
          },
        },
        required: ['style'],
      },
    }
  },

  async execute(args, ctx) {
    const result = await ctx.corePost('/v1/response-style', { style: args.style })
    return `Response style changed to: ${result.style}`
  },
}
