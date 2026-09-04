'use strict'

module.exports = {
  name: 'wallet',
  version: '1.0.0',
  description: 'Store card aliases. The signed core encrypts them and never charges a merchant.',

  get_tool_definition() {
    return {
      name: 'wallet',
      description: 'Save, list, delete, or simulate a purchase with a stored card. Purchases always go through the signed core.',
      parameters: {
        type: 'object',
        properties: {
          action: {
            type: 'string',
            enum: ['guardar', 'listar', 'eliminar', 'comprar'],
            description: 'guardar, listar, eliminar, or comprar',
          },
          card_name: { type: 'string', description: 'Card alias' },
          card_number: { type: 'string', description: 'Card number (never logged)' },
          expiry: { type: 'string', description: 'MM/YY' },
          cvv: { type: 'string', description: 'CVV' },
          amount: { type: 'number', description: 'Amount for a simulated purchase' },
          merchant: { type: 'string', description: 'Merchant label' },
        },
        required: ['action'],
      },
    }
  },

  async execute(args, ctx) {
    const action = String(args.action || '')
    if (action === 'listar') {
      const data = await ctx.corePost('/v1/wallet/list', {})
      return JSON.stringify(data)
    }
    if (action === 'guardar') {
      return JSON.stringify(
        await ctx.corePost('/v1/wallet/cards', {
          card_name: args.card_name,
          card_number: args.card_number,
          expiry: args.expiry,
          cvv: args.cvv,
        }),
      )
    }
    if (action === 'eliminar') {
      return JSON.stringify(await ctx.corePost('/v1/wallet/cards/delete', { card_name: args.card_name }))
    }
    if (action === 'comprar') {
      return JSON.stringify(
        await ctx.corePost('/v1/wallet/purchase', {
          card_name: args.card_name,
          amount: args.amount,
          merchant: args.merchant,
        }),
      )
    }
    return 'Unknown action. Use guardar, listar, eliminar, or comprar.'
  },
}
