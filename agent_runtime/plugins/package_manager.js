'use strict'

module.exports = {
  name: 'package_manager',
  version: '1.0.0',
  description: 'Install pip, npm, or brew packages after the signed core asks the user',

  get_tool_definition() {
    return {
      name: 'package_manager',
      description: 'Install, uninstall, or list a package (pip, npm, brew)',
      parameters: {
        type: 'object',
        properties: {
          action: {
            type: 'string',
            enum: ['install', 'uninstall', 'list'],
            description: 'Action',
          },
          package: { type: 'string', description: 'Package name' },
          manager: {
            type: 'string',
            enum: ['pip', 'npm', 'brew'],
            description: 'Package manager',
          },
        },
        required: ['action', 'manager'],
      },
    }
  },

  async execute(args, ctx) {
    const data = await ctx.corePost('/v1/packages/run', {
      action: args.action,
      package: args.package,
      manager: args.manager,
    })
    if (!data.ok) {
      return data.error || 'Package action blocked.'
    }
    return `Package "${data.package || ''}" ${data.action}:\n${data.output || ''}`
  },
}
