'use strict'

module.exports = {
  name: 'tor_browser',
  version: '1.0.0',
  description: 'Permission-gated Tor fetch via the signed core. Not a marketplace.',

  get_tool_definition() {
    return {
      name: 'tor_browser',
      description: 'Fetch a URL over Tor after the user allows it. Search uses DuckDuckGo over Tor. Saves text into app data only.',
      parameters: {
        type: 'object',
        properties: {
          action: {
            type: 'string',
            enum: ['navegar', 'buscar', 'descargar'],
            description: 'navegar, buscar, or descargar',
          },
          url: { type: 'string', description: 'http(s) URL, including .onion hosts' },
          query: { type: 'string', description: 'Search query for buscar' },
          timeout: { type: 'integer', description: 'Seconds, max 60' },
        },
        required: ['action'],
      },
    }
  },

  async execute(args, ctx) {
    return JSON.stringify(
      await ctx.corePost('/v1/browse/tor', {
        action: args.action,
        url: args.url || '',
        query: args.query || '',
        timeout: args.timeout || 30,
      }),
    )
  },
}
