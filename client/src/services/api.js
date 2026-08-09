const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

export const fetchMeetingsList = async () => {
  const res = await fetch(`${API_URL}/meetings`);
  if (!res.ok) throw new Error('Failed to fetch meetings');
  return res.json();
};

export const fetchMeetingDetail = async (id) => {
  const res = await fetch(`${API_URL}/meetings/${id}`);
  if (!res.ok) throw new Error('Failed to fetch meeting detail');
  return res.json();
};

export const deleteMeeting = async (id) => {
  const res = await fetch(`${API_URL}/meetings/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete meeting');
  return res.json();
};

export const fetchModelsStatus = async () => {
  const res = await fetch(`${API_URL}/models`);
  if (!res.ok) throw new Error('Failed to fetch models status');
  return res.json();
};

export const activateModel = async (category, modelId, currentConfig) => {
  let updatedConfig = { ...currentConfig };
  if (category === 'asr') {
    if (modelId === 'openai-whisper') updatedConfig.asr_provider = 'openai-whisper';
    else {
      updatedConfig.asr_provider = 'faster-whisper';
      updatedConfig.asr_model = modelId;
    }
  } else if (category === 'summarizer') {
    updatedConfig.summarizer_model = modelId;
  } else if (category === 'llm') {
    updatedConfig.llm_model = modelId;
  }
  
  const res = await fetch(`${API_URL}/models/active`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updatedConfig)
  });
  if (!res.ok) throw new Error('Failed to activate model');
  return res.json();
};

export const startModelDownload = async (category, modelId) => {
  const res = await fetch(`${API_URL}/models/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_type: category, model_id: modelId })
  });
  if (!res.ok) throw new Error('Failed to trigger download');
  return res.json();
};

export const pollModelDownload = async (modelId) => {
  const encodedId = encodeURIComponent(modelId);
  const res = await fetch(`${API_URL}/models/download/${encodedId}`);
  if (!res.ok) throw new Error('Failed to poll download status');
  return res.json();
};

// Note: Streaming chat doesn't return a simple JSON, it returns a ReadableStream.
// So we export the raw fetch for chat, or handle streaming logic inside a custom fetch.
export const getChatStreamResponse = async (meetingId, question, history) => {
  const res = await fetch(`${API_URL}/meetings/${meetingId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history })
  });
  if (!res.ok) throw new Error('Failed to get response from local LLM');
  return res; // caller handles the stream reader
};

export const uploadMeetingFile = async (formData) => {
  const res = await fetch(`${API_URL}/process-meeting`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Processing failed');
  }
  return res.json();
};
