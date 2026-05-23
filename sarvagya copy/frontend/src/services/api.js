import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const checkHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
};

export const processPipeline = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    // Using multipart/form-data for file upload
    const response = await api.post('/api/v1/pipeline/run', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error processing pipeline:', error);
    throw error;
  }
};

export default api;
