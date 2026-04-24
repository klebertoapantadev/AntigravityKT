const N8N_URL = process.env.N8N_WEBHOOK_URL;

export async function callN8nWebhook(path: string, data: any) {
  try {
    const response = await fetch(`${N8N_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`n8n error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error calling n8n:', error);
    throw error;
  }
}
