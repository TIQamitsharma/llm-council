const API_BASE = 'http://localhost:8001';

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export const api = {
  async listConversations(token) {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      headers: authHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to list conversations');
    return response.json();
  },

  async createConversation(token) {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error('Failed to create conversation');
    return response.json();
  },

  async getConversation(conversationId, token) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      headers: authHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to get conversation');
    return response.json();
  },

  async sendMessage(conversationId, content, token) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/message`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ content }),
    });
    if (!response.ok) throw new Error('Failed to send message');
    return response.json();
  },

  async sendMessageStream(conversationId, content, token, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) throw new Error('Failed to send message');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  async listApiKeys(token) {
    const response = await fetch(`${API_BASE}/api/user/keys`, {
      headers: authHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to list API keys');
    return response.json();
  },

  async saveApiKey(token, provider, key) {
    const response = await fetch(`${API_BASE}/api/user/keys`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ provider, key }),
    });
    if (!response.ok) throw new Error('Failed to save API key');
    return response.json();
  },

  async deleteApiKey(token, provider) {
    const response = await fetch(`${API_BASE}/api/user/keys/${provider}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to delete API key');
    return response.json();
  },

  async getCouncilConfig(token) {
    const response = await fetch(`${API_BASE}/api/user/council-config`, {
      headers: authHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to get council config');
    return response.json();
  },

  async saveCouncilConfig(token, councilModels, chairmanModel) {
    const response = await fetch(`${API_BASE}/api/user/council-config`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ council_models: councilModels, chairman_model: chairmanModel }),
    });
    if (!response.ok) throw new Error('Failed to save council config');
    return response.json();
  },
};
