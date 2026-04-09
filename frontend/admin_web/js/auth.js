// ============================================================
// auth.js - نظام المصادقة والتواصل مع الخادم
// ============================================================

// --- الإعدادات الأساسية ---
// اكتشاف عنوان الخادم تلقائياً: إذا كنا في بيئة تطوير محلية (localhost) نستخدم نفس المنفذ،
// وإذا كنا على خادم منشور نستخدم المسار النسبي '/api'
const API_BASE_URL = (() => {
  const host = window.location.hostname;
  // إذا كان التطبيق يعمل على localhost أو ضمن WebView يصل إلى ملف محلي (file://)
  if (host === 'localhost' || host === '127.0.0.1' || window.location.protocol === 'file:') {
    return 'http://localhost:5000/api'; // غيّر المنفذ إذا كان مختلفاً
  }
  // في حالة النشر على خادم حقيقي، نستخدم نفس النطاق
  return '/api';
})();

// --- إدارة التوكن ---
function getToken() {
  return localStorage.getItem('admin_token');
}

function setToken(token) {
  localStorage.setItem('admin_token', token);
}

function removeToken() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('user_data'); // تنظيف أي بيانات مستخدم مخزنة
}

// --- دالة الطلب العامة (apiRequest) ---
async function apiRequest(endpoint, method = 'GET', body = null) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    method,
    headers,
  };

  if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, config);

    // التعامل مع انتهاء الجلسة أو عدم الصلاحية
    if (response.status === 401) {
      removeToken();
      // منع التوجيه المتكرر إذا كنا بالفعل في صفحة تسجيل الدخول
      if (!window.location.pathname.includes('index.html')) {
        window.location.href = 'index.html';
      }
      throw new Error('انتهت الجلسة، الرجاء تسجيل الدخول مجدداً');
    }

    // إذا كان الرد غير ناجح (4xx, 5xx) نرمي خطأ يحتوي على رسالة الخادم إن وجدت
    if (!response.ok) {
      let errorMessage = `خطأ ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || errorMessage;
      } catch (e) {
        // إذا لم يكن الرد JSON، نستخدم نص الحالة
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    // للردود التي لا تحتوي على جسم (مثل 204 No Content)
    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error(`API Request Failed [${method} ${endpoint}]:`, error);
    throw error; // نعيد رمي الخطأ ليلتقطه المستدعي
  }
}

// --- دوال المصادقة المحددة ---

/**
 * تسجيل الدخول (للإدارة أو العملاء)
 * @param {string} phone رقم الهاتف
 * @param {string} password كلمة المرور
 * @returns {Promise<Object>} بيانات المستخدم والتوكن
 */
async function login(phone, password) {
  const result = await apiRequest('/auth/login-with-phone', 'POST', { phone, password });
  if (result.access_token) {
    setToken(result.access_token);
    // يمكن تخزين بيانات المستخدم للاستخدام في الواجهات
    if (result.user) {
      localStorage.setItem('user_data', JSON.stringify(result.user));
    }
  }
  return result;
}

/**
 * طلب إعادة تعيين كلمة المرور
 * @param {string} phone رقم الهاتف
 */
async function requestPasswordReset(phone) {
  return await apiRequest('/auth/request-password-reset', 'POST', { phone });
}

/**
 * تسجيل الخروج
 */
function logout() {
  removeToken();
  window.location.href = 'index.html';
}

/**
 * التحقق من صحة التوكن الحالي (للصفحات المحمية)
 * @returns {Promise<boolean>} true إذا كان التوكن صالحاً
 */
async function checkAuth() {
  const token = getToken();
  if (!token) return false;

  try {
    // نستخدم نقطة نهاية خفيفة للتحقق
    await apiRequest('/admin/check', 'GET');
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * حماية الصفحة: إذا لم يكن المستخدم مسجلاً دخول، يتم توجيهه لصفحة تسجيل الدخول
 */
async function requireAuth() {
  const isAuthenticated = await checkAuth();
  if (!isAuthenticated) {
    window.location.href = 'index.html';
  }
  return isAuthenticated;
}

// --- دوال مساعدة للإشعارات (Toast) - يمكن استدعاؤها من أي مكان إذا لم تكن معرفة مسبقاً ---
if (typeof window.showToast === 'undefined') {
  window.showToast = function(message, type = 'success') {
    // إذا كانت الصفحة تستخدم Bootstrap، نحاول إنشاء toast مؤقت
    if (typeof bootstrap !== 'undefined') {
      const container = document.querySelector('.toast-container') || (() => {
        const div = document.createElement('div');
        div.className = 'toast-container position-fixed top-0 start-0 p-3';
        document.body.appendChild(div);
        return div;
      })();

      const id = 'toast-' + Date.now();
      const bg = type === 'success' ? 'bg-success' : (type === 'danger' ? 'bg-danger' : 'bg-warning');
      const icon = type === 'success' ? 'fa-check-circle' : (type === 'danger' ? 'fa-exclamation-circle' : 'fa-info-circle');
      const txt = type === 'success' ? 'نجاح' : (type === 'danger' ? 'خطأ' : 'تنبيه');

      const html = `
        <div id="${id}" class="toast ${bg} text-white" role="alert" data-bs-autohide="true" data-bs-delay="4000">
          <div class="toast-header ${bg} text-white">
            <i class="fas ${icon} me-2"></i>
            <strong class="me-auto">${txt}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
          </div>
          <div class="toast-body">${message}</div>
        </div>
      `;
      container.insertAdjacentHTML('beforeend', html);
      const el = document.getElementById(id);
      new bootstrap.Toast(el).show();
      el.addEventListener('hidden.bs.toast', () => el.remove());
    } else {
      alert(message);
    }
  };
}
