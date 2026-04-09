// ============================================================
// firebase-init.js - تهيئة Firebase Cloud Messaging للواجهة
// ============================================================

// إعدادات مشروع Firebase (القيم الحقيقية)
const firebaseConfig = {
  apiKey: "AIzaSyDa0lpetC4RuB0XZjOjNnUvjQ8WJgQwRs8",
  authDomain: "bin-obaid-system.firebaseapp.com",
  projectId: "bin-obaid-system",
  storageBucket: "bin-obaid-system.firebasestorage.app",
  messagingSenderId: "798065209309",
  appId: "1:798065209309:web:07dd40e089709786671034"
};

// تهيئة Firebase
firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// مفتاح VAPID العام (تم الحصول عليه من Firebase Console > Cloud Messaging > Web Push certificates)
const VAPID_PUBLIC_KEY = "BOX-rVV7GiFdRouWy72STB9z-Ftd4zPznSuNIzz2N1YvkNa79YRNiCjw8WzyvcWh2bvH0_72KcgSOdpR2Wh0X7g";

// دالة لطلب إذن الإشعارات والحصول على توكن الجهاز
async function requestNotificationPermission() {
  try {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      console.log('✅ تم منح إذن الإشعارات.');
      const token = await messaging.getToken({ vapidKey: VAPID_PUBLIC_KEY });
      if (token) {
        console.log('🔑 FCM Token:', token);
        await saveTokenToServer(token);
        return token;
      } else {
        console.warn('⚠️ لم يتم الحصول على توكن التسجيل.');
      }
    } else {
      console.warn('⚠️ لم يتم منح إذن الإشعارات.');
    }
  } catch (err) {
    console.error('❌ خطأ في طلب إذن الإشعارات:', err);
  }
}

// دالة لحفظ التوكن في الخادم (Supabase عبر Flask API)
async function saveTokenToServer(token) {
  try {
    const res = await fetch('/api/fcm/register-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
      },
      body: JSON.stringify({ token })
    });
    if (res.ok) {
      console.log('✅ تم حفظ التوكن في الخادم بنجاح.');
    } else {
      console.error('⚠️ فشل حفظ التوكن:', await res.text());
    }
  } catch (err) {
    console.error('❌ خطأ في الاتصال بالخادم لحفظ التوكن:', err);
  }
}

// استقبال الإشعارات أثناء فتح التطبيق (في المقدمة)
messaging.onMessage((payload) => {
  console.log('📨 إشعار وارد:', payload);
  const title = payload.notification?.title || 'إشعار';
  const body = payload.notification?.body || '';
  
  // عرض الإشعار باستخدام دالة showToast إذا كانت موجودة
  if (typeof showToast === 'function') {
    showToast(`${title}\n${body}`, 'info');
  } else {
    alert(`${title}\n${body}`);
  }
});

// تصدير الدوال للاستخدام العام (اختياري)
window.requestNotificationPermission = requestNotificationPermission;
