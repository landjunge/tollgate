'use strict';

/**
 * Tollgate community node — chat / route / budget / invoke / search.
 * Secrets for providers stay in Tollgate; n8n only holds a consumer key.
 */
class Tollgate {
	constructor() {
		this.description = {
			displayName: 'Tollgate',
			name: 'tollgate',
			icon: 'file:tollgate.svg',
			group: ['transform'],
			version: 1,
			subtitle: '={{$parameter["operation"]}}',
			description:
				'API admission gateway: OpenAI chat, route, budget, invoke, Brave search',
			defaults: {
				name: 'Tollgate',
			},
			inputs: ['main'],
			outputs: ['main'],
			credentials: [
				{
					name: 'tollgateApi',
					required: true,
				},
			],
			requestDefaults: {
				baseURL: '={{$credentials.baseUrl}}',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
				},
			},
			properties: [
				{
					displayName: 'Operation',
					name: 'operation',
					type: 'options',
					noDataExpression: true,
					options: [
						{
							name: 'Chat',
							value: 'chat',
							description: 'OpenAI-compatible chat completions (admit + route + meter)',
							action: 'Chat via Tollgate',
						},
						{
							name: 'Route',
							value: 'route',
							description: 'Resolve intent → provider/model without calling',
							action: 'Route intent',
						},
						{
							name: 'Budget',
							value: 'budget',
							description: 'Consumer envelope + optional provider limits',
							action: 'Check budget',
						},
						{
							name: 'Invoke',
							value: 'invoke',
							description: 'Native admit + call + meter (any provider/op)',
							action: 'Invoke provider op',
						},
						{
							name: 'Search',
							value: 'search',
							description: 'Brave web search via gateway (invoke brave.search)',
							action: 'Web search',
						},
						{
							name: 'Health',
							value: 'health',
							description: 'GET /v1/health',
							action: 'Health check',
						},
					],
					default: 'chat',
				},

				// ── Chat ────────────────────────────────────────────
				{
					displayName: 'Model',
					name: 'model',
					type: 'string',
					default: 'tollgate/free',
					description: 'tollgate/free · tollgate/auto · or provider model id',
					displayOptions: { show: { operation: ['chat'] } },
				},
				{
					displayName: 'Prompt',
					name: 'prompt',
					type: 'string',
					typeOptions: { rows: 4 },
					default: '',
					required: true,
					description: 'User message (simple). For multi-turn use Messages JSON.',
					displayOptions: { show: { operation: ['chat'] } },
				},
				{
					displayName: 'System Prompt',
					name: 'system',
					type: 'string',
					typeOptions: { rows: 2 },
					default: '',
					displayOptions: { show: { operation: ['chat'] } },
				},
				{
					displayName: 'Max Tokens',
					name: 'maxTokens',
					type: 'number',
					default: 256,
					typeOptions: { minValue: 1 },
					displayOptions: { show: { operation: ['chat'] } },
				},
				{
					displayName: 'Temperature',
					name: 'temperature',
					type: 'number',
					default: 0.7,
					typeOptions: { minValue: 0, maxValue: 2, numberPrecision: 2 },
					displayOptions: { show: { operation: ['chat'] } },
				},
				{
					displayName: 'Prefer Free',
					name: 'preferFree',
					type: 'boolean',
					default: true,
					displayOptions: { show: { operation: ['chat'] } },
				},

				// ── Route ───────────────────────────────────────────
				{
					displayName: 'Intent',
					name: 'intent',
					type: 'options',
					options: [
						{ name: 'free_llm', value: 'free_llm' },
						{ name: 'llm', value: 'llm' },
						{ name: 'paid_llm', value: 'paid_llm' },
						{ name: 'search', value: 'search' },
						{ name: 'tts', value: 'tts' },
					],
					default: 'free_llm',
					displayOptions: { show: { operation: ['route'] } },
				},
				{
					displayName: 'Tokens Estimate',
					name: 'tokensEst',
					type: 'number',
					default: 1000,
					displayOptions: { show: { operation: ['route'] } },
				},

				// ── Budget ──────────────────────────────────────────
				{
					displayName: 'Provider (optional)',
					name: 'budgetProvider',
					type: 'string',
					default: '',
					description: 'If set, include provider-specific remaining limits',
					displayOptions: { show: { operation: ['budget'] } },
				},

				// ── Invoke ──────────────────────────────────────────
				{
					displayName: 'Provider',
					name: 'provider',
					type: 'string',
					default: 'opencode_zen',
					required: true,
					displayOptions: { show: { operation: ['invoke'] } },
				},
				{
					displayName: 'Op',
					name: 'op',
					type: 'string',
					default: 'chat',
					required: true,
					displayOptions: { show: { operation: ['invoke'] } },
				},
				{
					displayName: 'Arguments (JSON)',
					name: 'argumentsJson',
					type: 'json',
					default: '{\n  "message": "hi",\n  "max_tokens": 128\n}',
					displayOptions: { show: { operation: ['invoke'] } },
				},
				{
					displayName: 'Request Class',
					name: 'requestClass',
					type: 'options',
					options: [
						{ name: 'interactive', value: 'interactive' },
						{ name: 'batch', value: 'batch' },
						{ name: 'free', value: 'free' },
						{ name: 'system', value: 'system' },
					],
					default: 'batch',
					displayOptions: { show: { operation: ['invoke', 'search', 'chat'] } },
				},
				{
					displayName: 'Agent ID',
					name: 'agentId',
					type: 'string',
					default: 'n8n',
					displayOptions: { show: { operation: ['invoke', 'search', 'chat'] } },
				},

				// ── Search ──────────────────────────────────────────
				{
					displayName: 'Query',
					name: 'query',
					type: 'string',
					default: '',
					required: true,
					displayOptions: { show: { operation: ['search'] } },
				},
				{
					displayName: 'Count',
					name: 'count',
					type: 'number',
					default: 5,
					typeOptions: { minValue: 1, maxValue: 20 },
					displayOptions: { show: { operation: ['search'] } },
				},
			],
		};
	}

	async execute() {
		const items = this.getInputData();
		const returnData = [];
		const credentials = await this.getCredentials('tollgateApi');
		const baseUrl = String(credentials.baseUrl || 'http://127.0.0.1:8787').replace(
			/\/+$/,
			'',
		);
		const apiKey = String(credentials.apiKey || 'n8n');

		const headers = {
			Authorization: `Bearer ${apiKey}`,
			'X-Consumer-Key': apiKey,
			'Content-Type': 'application/json',
			Accept: 'application/json',
		};

		for (let i = 0; i < items.length; i++) {
			const operation = this.getNodeParameter('operation', i);
			let out;

			if (operation === 'health') {
				out = await this.helpers.httpRequest({
					method: 'GET',
					url: `${baseUrl}/v1/health`,
					headers,
					json: true,
				});
			} else if (operation === 'budget') {
				const provider = this.getNodeParameter('budgetProvider', i, '');
				const q = provider ? `?provider=${encodeURIComponent(provider)}` : '';
				out = await this.helpers.httpRequest({
					method: 'GET',
					url: `${baseUrl}/v1/budget${q}`,
					headers,
					json: true,
				});
			} else if (operation === 'route') {
				const intent = this.getNodeParameter('intent', i);
				const tokensEst = this.getNodeParameter('tokensEst', i, 1000);
				out = await this.helpers.httpRequest({
					method: 'POST',
					url: `${baseUrl}/v1/route`,
					headers,
					body: {
						intent,
						tokens_est: tokensEst,
						prefer_free: intent === 'free_llm',
					},
					json: true,
				});
			} else if (operation === 'chat') {
				const model = this.getNodeParameter('model', i);
				const prompt = this.getNodeParameter('prompt', i);
				const system = this.getNodeParameter('system', i, '');
				const maxTokens = this.getNodeParameter('maxTokens', i, 256);
				const temperature = this.getNodeParameter('temperature', i, 0.7);
				const preferFree = this.getNodeParameter('preferFree', i, true);
				const requestClass = this.getNodeParameter('requestClass', i, 'batch');
				const agentId = this.getNodeParameter('agentId', i, 'n8n');
				const messages = [];
				if (system) {
					messages.push({ role: 'system', content: system });
				}
				messages.push({ role: 'user', content: prompt });
				out = await this.helpers.httpRequest({
					method: 'POST',
					url: `${baseUrl}/v1/chat/completions`,
					headers,
					body: {
						model,
						messages,
						max_tokens: maxTokens,
						temperature,
						prefer_free: preferFree,
						request_class: requestClass,
						user: agentId,
					},
					json: true,
				});
				// Convenience fields for Set / IF nodes
				if (out && out.choices && out.choices[0] && out.choices[0].message) {
					out.text = out.choices[0].message.content;
				}
			} else if (operation === 'invoke') {
				const provider = this.getNodeParameter('provider', i);
				const op = this.getNodeParameter('op', i);
				let args = this.getNodeParameter('argumentsJson', i, {});
				if (typeof args === 'string') {
					try {
						args = JSON.parse(args || '{}');
					} catch {
						args = {};
					}
				}
				const requestClass = this.getNodeParameter('requestClass', i, 'batch');
				const agentId = this.getNodeParameter('agentId', i, 'n8n');
				out = await this.helpers.httpRequest({
					method: 'POST',
					url: `${baseUrl}/v1/invoke`,
					headers,
					body: {
						provider,
						op,
						arguments: args || {},
						request_class: requestClass,
						agent_id: agentId,
						job_id: `n8n-${i}`,
					},
					json: true,
				});
			} else if (operation === 'search') {
				const query = this.getNodeParameter('query', i);
				const count = this.getNodeParameter('count', i, 5);
				const requestClass = this.getNodeParameter('requestClass', i, 'batch');
				const agentId = this.getNodeParameter('agentId', i, 'n8n');
				out = await this.helpers.httpRequest({
					method: 'POST',
					url: `${baseUrl}/v1/invoke`,
					headers,
					body: {
						provider: 'brave',
						op: 'search',
						arguments: { query, count },
						request_class: requestClass,
						agent_id: agentId,
					},
					json: true,
				});
			} else {
				throw new Error(`Unknown operation: ${operation}`);
			}

			returnData.push({ json: out, pairedItem: { item: i } });
		}

		return [returnData];
	}
}

module.exports = { Tollgate };
