// auth.js - دوال المصادقة
const API_BASE = '/api';

function getToken() { return localStorage.getItem('admin_token'); }
function setToken(token) { localStorage.setItem('admin_token', token); }
function removeToken() { localStorage.removeItem('admin_token'); }

async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(`${API_BASE}${endpoint}`, { method, headers, body: body ? JSON.stringify(body) : null });
    if (response.status === 401) { removeToken(); window.location.href = '/admin_web/index.html'; throw new Error('Unauthorized'); }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

function logout() { removeToken(); window.location.href = '/admin_web/index.html'; }
