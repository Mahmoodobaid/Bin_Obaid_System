// ============================================================
// interactive.js - تجربة مستخدم تفاعلية ورسائل ذكية
// ============================================================

// --- المتغيرات العامة ---
let currentUser = null;
let pageGuideShown = false;
let lastInteractionTime = Date.now();

// --- تحميل بيانات المستخدم الحالي من الخادم ---
async function loadCurrentUser() {
    try {
        // استخدام apiRequest المعرفة في auth.js
        currentUser = await apiRequest('/admin/profile');
        return currentUser;
    } catch(e) {
        console.warn('تعذر تحميل بيانات المستخدم:', e);
        return null;
    }
}

// --- الحصول على تحية مناسبة حسب الوقت ---
function getGreeting() {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return 'صباح الخير';
    if (hour >= 12 && hour < 14) return 'سعيدة صباحاً';
    if (hour >= 14 && hour < 18) return 'مساء الخير';
    if (hour >= 18 && hour < 22) return 'مساء النور';
    return 'تهجدك مبارك';
}

// --- عرض رسالة ترحيب مخصصة في أعلى المحتوى الرئيسي ---
async function showWelcomeMessage() {
    const user = await loadCurrentUser();
    if (!user) return;
    
    const name = user.full_name || (user.email ? user.email.split('@')[0] : 'مديرنا');
    const greeting = getGreeting();
    const message = `${greeting}، ${name} 👋<br><small class="opacity-75">أهلاً بك في منظومة بن عبيد. نتمنى لك يوماً موفقاً!</small>`;
    
    // إزالة أي رسالة ترحيب سابقة
    const existingDiv = document.getElementById('dynamicWelcome');
    if (existingDiv) existingDiv.remove();
    
    const welcomeDiv = document.createElement('div');
    welcomeDiv.id = 'dynamicWelcome';
    welcomeDiv.className = 'alert alert-success rounded-4 shadow-sm mb-4 d-flex align-items-center';
    welcomeDiv.innerHTML = `
        <i class="fas fa-smile-wink fa-2x me-3"></i>
        <span>${message}</span>
        <button type="button" class="btn-close ms-auto" onclick="this.parentElement.remove()"></button>
    `;
    
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.prepend(welcomeDiv);
    }
}

// --- عرض دليل الصفحة (يظهر مرة واحدة لكل صفحة) ---
async function showPageGuide(pageName, description) {
    if (pageGuideShown) return;
    
    const user = await loadCurrentUser();
    const name = user ? (user.full_name || (user.email ? user.email.split('@')[0] : 'مديرنا')) : 'مديرنا';
    
    const guideDiv = document.createElement('div');
    guideDiv.className = 'alert alert-info rounded-4 shadow-sm mb-4 d-flex';
    guideDiv.innerHTML = `
        <i class="fas fa-info-circle fa-2x me-3"></i>
        <div class="flex-grow-1">
            <strong>📘 دليل ${pageName}</strong><br>
            <span>مرحباً بك يا ${name}، ${description}</span>
        </div>
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        const firstChild = mainContent.firstChild;
        if (firstChild && firstChild.id !== 'dynamicWelcome') {
            mainContent.insertBefore(guideDiv, firstChild);
        } else if (firstChild) {
            mainContent.insertBefore(guideDiv, firstChild.nextSibling);
        } else {
            mainContent.appendChild(guideDiv);
        }
    }
    
    pageGuideShown = true;
    
    // إخفاء تلقائي بعد 15 ثانية
    setTimeout(() => {
        if (guideDiv.parentNode) guideDiv.remove();
    }, 15000);
}

// --- عرض رسالة نجاح أو خطأ بشكل منبثق (باستخدام Bootstrap Toasts) ---
function showToast(message, type = 'success') {
    // إذا كانت showToast معرفة مسبقاً (من auth.js) استخدمها
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }
    
    // استخدام التنبيه العادي كخطة بديلة
    alert(message);
}

// --- عرض إشعار تفاعلي في الزاوية (يمكن تخصيصه) ---
function showNotification(title, message, icon = 'bell') {
    const container = document.querySelector('.toast-container') || (() => {
        const div = document.createElement('div');
        div.className = 'toast-container position-fixed top-0 start-0 p-3';
        document.body.appendChild(div);
        return div;
    })();
    
    const id = 'notification-' + Date.now();
    const html = `
        <div id="${id}" class="toast bg-white text-dark" role="alert" data-bs-autohide="true" data-bs-delay="5000">
            <div class="toast-header">
                <i class="fas fa-${icon} me-2 text-primary"></i>
                <strong class="me-auto">${title}</strong>
                <small>الآن</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    
    const el = document.getElementById(id);
    if (typeof bootstrap !== 'undefined') {
        new bootstrap.Toast(el).show();
    }
    el.addEventListener('hidden.bs.toast', () => el.remove());
}

// --- رسالة تحفيزية عشوائية (تظهر بعد فترة من النشاط) ---
const motivationalMessages = [
    "🌟 أنت تقوم بعمل رائع! استمر في الإدارة المتميزة.",
    "📊 البيانات منظمة بفضل جهودك، شكراً لك.",
    "💡 نصيحة: يمكنك استخدام النماذج لتسريع إدخال عروض الأسعار.",
    "🎯 تذكر أن تحديث المخزون بانتظام يحافظ على دقة النظام.",
    "🏆 أنت على الطريق الصحيح نحو النجاح!"
];

function showMotivationalMessage() {
    const now = Date.now();
    // تظهر كل 5 دقائق من التفاعل
    if (now - lastInteractionTime < 300000) return;
    lastInteractionTime = now;
    
    const randomMsg = motivationalMessages[Math.floor(Math.random() * motivationalMessages.length)];
    showNotification('رسالة تحفيزية', randomMsg, 'smile');
}

// --- تسجيل التفاعل مع الصفحة (لإظهار رسائل تحفيزية) ---
function trackInteraction() {
    lastInteractionTime = Date.now();
    // جدولة رسالة تحفيزية بعد 10 دقائق من آخر تفاعل
    setTimeout(showMotivationalMessage, 600000);
}

// --- ربط أحداث التفاعل لتتبع النشاط ---
function bindInteractionTracking() {
    const events = ['click', 'keypress', 'scroll', 'mousemove'];
    events.forEach(event => {
        document.addEventListener(event, () => {
            trackInteraction();
        });
    });
}

// --- تهيئة الصفحة: تحميل الترحيب وتتبع التفاعل ---
async function initInteractive() {
    // تحميل بيانات المستخدم أولاً
    await loadCurrentUser();
    
    // عرض رسالة الترحيب
    await showWelcomeMessage();
    
    // تفعيل تتبع التفاعل
    bindInteractionTracking();
    
    // عرض رسالة تحفيزية أولى بعد 5 دقائق
    setTimeout(showMotivationalMessage, 300000);
    
    console.log('✅ تم تهيئة التفاعلات الذكية.');
}

// --- تصدير الدوال للاستخدام العام (اختياري) ---
// يمكن استدعاء initInteractive() عند تحميل أي صفحة محمية
window.initInteractive = initInteractive;
window.showPageGuide = showPageGuide;
window.showNotification = showNotification;
