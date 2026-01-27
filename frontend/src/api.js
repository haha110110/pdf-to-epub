import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getStatus = (projectId) => api.get(`/projects/${projectId}/status`);
export const uploadPDF = (formData) => api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
});

export const getProjects = () => api.get('/projects');
export const deleteProject = (projectId) => api.delete(`/projects/${projectId}`);
export const updateProjectMetadata = (projectId, payload) => api.patch(`/projects/${projectId}/metadata`, payload);

export const getContent = (projectId) => api.get(`/projects/${projectId}/content`);
export const saveContent = (projectId, content) => api.put(`/projects/${projectId}/content`, { content });

export const buildEpub = (projectId) => api.post(`/projects/${projectId}/build`);

export const getDownloadUrl = (projectId) => `/api/projects/${projectId}/download`;
export const getSourcePackageUrl = (projectId) => `/api/projects/${projectId}/package`;

export default api;
