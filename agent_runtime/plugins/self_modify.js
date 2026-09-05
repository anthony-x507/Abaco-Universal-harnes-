'use strict'

module.exports = {
  name: 'self_modify',
  version: '1.0.0',
  description: 'Propose a non-core file change; Python signs and writes',

  get_tool_definition() {
    return {
      name: 'self_modify',
      description: 'Change agent plugin code after the user allows it',
      parameters: {
        type: 'object',
        properties: {
          file_path: { type: 'string', description: 'File to change' },
          new_content: { type: 'string', description: 'New file contents' },
          reason: { type: 'string', description: 'Why this change is needed' },
        },
        required: ['file_path', 'new_content', 'reason'],
      },
    }
  },

  async execute(args, ctx) {
    const data = await ctx.corePost('/v1/self-modify/run', {
      file_path: args.file_path,
      new_content: args.new_content,
      reason: args.reason,
    })
    if (!data.ok) {
      return data.error || 'Change blocked.'
    }
    return `Updated ${data.file || args.file_path}`
  },
}
