// =====================================================
// firebase_messaging.dart - تهيئة واستقبال إشعارات FCM
// =====================================================

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../api_service.dart';

class FirebaseMessagingService {
  static final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  static final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();

  // تهيئة الإشعارات المحلية
  static Future<void> initialize() async {
    // تهيئة الإشعارات المحلية للأندرويد
    const AndroidInitializationSettings androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const DarwinInitializationSettings iosSettings = DarwinInitializationSettings();
    const InitializationSettings settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await _localNotifications.initialize(settings);

    // طلب إذن الإشعارات
    await _requestPermission();

    // الحصول على التوكن
    await _getToken();

    // معالجة الإشعارات
    _setupForegroundHandler();
    _setupBackgroundHandler();
    _setupTerminatedHandler();
  }

  // طلب إذن الإشعارات
  static Future<void> _requestPermission() async {
    final settings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );
    print('Notification permission status: ${settings.authorizationStatus}');
  }

  // الحصول على التوكن وتسجيله في الخادم
  static Future<void> _getToken() async {
    final token = await _firebaseMessaging.getToken();
    if (token != null) {
      print('FCM Token: $token');
      await _registerToken(token);
    }
  }

  static Future<void> _registerToken(String token) async {
    try {
      final api = ApiService();
      await api.registerFCMToken(token);
    } catch (e) {
      print('Failed to register FCM token: $e');
    }
  }

  // معالجة الإشعارات عندما يكون التطبيق في المقدمة
  static void _setupForegroundHandler() {
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('Got a message whilst in the foreground!');
      _showLocalNotification(message);
    });
  }

  // معالجة الإشعارات عندما يكون التطبيق في الخلفية
  static void _setupBackgroundHandler() {
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  }

  // معالجة الإشعارات عند فتح التطبيق من الإشعار
  static void _setupTerminatedHandler() {
    FirebaseMessaging.instance.getInitialMessage().then((RemoteMessage? message) {
      if (message != null) {
        _handleMessage(message);
      }
    });

    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      _handleMessage(message);
    });
  }

  // عرض إشعار محلي
  static void _showLocalNotification(RemoteMessage message) {
    final notification = message.notification;
    if (notification == null) return;

    const AndroidNotificationDetails androidDetails = AndroidNotificationDetails(
      'bin_obeid_channel',
      'إشعارات بن عبيد',
      channelDescription: 'قناة إشعارات التطبيق',
      importance: Importance.high,
      priority: Priority.high,
    );
    const DarwinNotificationDetails iosDetails = DarwinNotificationDetails();
    const NotificationDetails details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      notification.title,
      notification.body,
      details,
    );
  }

  // معالجة الضغط على الإشعار
  static void _handleMessage(RemoteMessage message) {
    final data = message.data;
    final productSku = data['product_sku'];
    
    if (productSku != null && productSku.isNotEmpty) {
      // توجيه المستخدم إلى صفحة المنتج
      // يمكن استخدام Navigator عبر GlobalKey
      print('Open product: $productSku');
    }
  }
}

// معالج الإشعارات في الخلفية
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  print("Handling a background message: ${message.messageId}");
}

// تحديث التوكن (يتم استدعاؤه عند تغيير التوكن)
Future<void> refreshFCMToken() async {
  FirebaseMessaging.instance.onTokenRefresh.listen((newToken) async {
    print('FCM Token refreshed: $newToken');
    await FirebaseMessagingService._registerToken(newToken);
  });
}