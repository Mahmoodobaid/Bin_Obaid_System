// ============================================================
// firebase-messaging-sw.js - Service Worker لاستقبال الإشعارات في الخلفية
// ============================================================

// استيراد مكتبات Firebase (الإصدار المتوافق مع Service Worker)
importScripts('https://www.gstatic.com/firebasejs/9.6.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.6.1/firebase-messaging-compat.js');

// إعدادات مشروع Firebase (نفس القيم المستخدمة في firebase-init.js)
const firebaseConfig = {
  apiKey: "AIzaSyDa0lpetC4RuB0XZjOjNnUvjQ8WJgQwRs8",
  authDomain: "bin-obaid-system.firebaseapp.com",
  projectId: "bin-obaid-system",
  storageBucket: "bin-obaid-system.firebasestorage.app",
  messagingSenderId: "798065209309",
  appId: "1:798065209309:web:07dd40e089709786671034"
};

// تهيئة Firebase في نطاق Service Worker
firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// التعامل مع الإشعارات التي تصل أثناء إغلاق التطبيق أو في الخلفية
messaging.onBackgroundMessage((payload) => {
  console.log('[SW] تلقى إشعار خلفية:', payload);

  const notificationTitle = payload.notification?.title || 'بن عبيد';
  const notificationOptions = {
    body: payload.notification?.body || 'لديك إشعار جديد',
    icon: '/favicon.ico', // يمكنك تغيير مسار الأيقونة حسب رغبتك
    badge: '/favicon.ico',
    vibrate: [200, 100, 200],
    data: payload.data || {}
  };

  // عرض الإشعار للمستخدم
  self.registration.showNotification(notificationTitle, notificationOptions);
});

// (اختياري) التعامل مع النقر على الإشعار
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // إذا كانت هناك نافذة مفتوحة، ركز عليها وانتقل للمسار
      for (let client of windowClients) {
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus();
        }
      }
      // وإلا افتح نافذة جديدة
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
