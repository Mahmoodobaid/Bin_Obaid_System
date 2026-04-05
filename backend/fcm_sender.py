# =====================================================
# fcm_sender.py - إرسال الإشعارات عبر FCM أو Google Cloud Messaging
# يدعم طريقتين: FCM Server Key (قديم) أو Service Account (credentials.json)
# الإصدار 2.0 - مع دعم متعدد الأجهزة ومعالجة الأخطاء
# =====================================================

import requests
import logging
import os
import json
from config import Config

logger = logging.getLogger(__name__)

FCM_SERVER_KEY = Config.FCM_SERVER_KEY
FCM_URL = "https://fcm.googleapis.com/fcm/send"
FCM_V1_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# محاولة تحميل credentials.json إذا كان موجوداً
USE_SERVICE_ACCOUNT = (FCM_SERVER_KEY is None or FCM_SERVER_KEY == "none" or FCM_SERVER_KEY.strip() == "")
service_account_credentials = None
project_id = None

if USE_SERVICE_ACCOUNT:
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        
        creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        if os.path.exists(creds_path):
            service_account_credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            # استخراج project_id من credentials.json
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
                project_id = creds_data.get('project_id')
            logger.info(f"✅ Loaded service account credentials from credentials.json, project_id: {project_id}")
        else:
            logger.warning("⚠️ credentials.json not found in backend directory. FCM notifications disabled.")
            USE_SERVICE_ACCOUNT = False
    except ImportError:
        logger.error("❌ google-auth library not installed. Install with: pip install google-auth google-auth-oauthlib")
        USE_SERVICE_ACCOUNT = False
    except Exception as e:
        logger.error(f"❌ Error loading credentials.json: {e}")
        USE_SERVICE_ACCOUNT = False


def get_access_token_from_service_account():
    """الحصول على access token من service account للـ FCM (v1 API)"""
    if not service_account_credentials:
        return None
    try:
        from google.auth.transport.requests import Request
        if service_account_credentials.expired:
            service_account_credentials.refresh(Request())
        return service_account_credentials.token
    except Exception as e:
        logger.error(f"Failed to get access token: {e}")
        return None


def send_push_notification_v1(tokens, title, body, data=None):
    """
    إرسال إشعار عبر FCM v1 API (باستخدام service account).
    مناسبة عند عدم وجود FCM_SERVER_KEY أو قيمتها "none".
    """
    if not USE_SERVICE_ACCOUNT or not service_account_credentials or not project_id:
        logger.warning("Service account not available, cannot send via v1 API")
        return None
    
    access_token = get_access_token_from_service_account()
    if not access_token:
        logger.error("Failed to get access token for FCM v1")
        return None
    
    url = FCM_V1_URL.format(project_id=project_id)
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    results = []
    if isinstance(tokens, str):
        tokens = [tokens]
    
    for token in tokens:
        if not token:
            continue
            
        message = {
            'message': {
                'token': token,
                'notification': {
                    'title': title,
                    'body': body,
                },
                'android': {
                    'priority': 'HIGH',
                    'notification': {
                        'sound': 'default',
                        'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                    }
                },
                'apns': {
                    'headers': {
                        'apns-priority': '10',
                    },
                    'payload': {
                        'aps': {
                            'sound': 'default',
                        }
                    }
                }
            }
        }
        
        # إضافة البيانات الإضافية إذا وجدت
        if data:
            message['message']['data'] = data
        
        try:
            response = requests.post(url, json=message, headers=headers, timeout=10)
            if response.status_code == 200:
                results.append({'success': True, 'token': token[:10] + '...'})
                logger.info(f"✅ FCM v1 notification sent to {token[:10]}...")
            else:
                error_msg = response.json().get('error', {}).get('message', response.text)
                results.append({'error': error_msg, 'token': token[:10] + '...'})
                logger.warning(f"❌ FCM v1 failed for {token[:10]}...: {error_msg}")
        except Exception as e:
            results.append({'error': str(e), 'token': token[:10] + '...'})
            logger.error(f"❌ FCM v1 request error: {e}")
    
    return results


def send_push_notification_legacy(tokens, title, body, data=None):
    """
    إرسال إشعار عبر FCM legacy API (باستخدام Server Key)
    """
    if not FCM_SERVER_KEY or FCM_SERVER_KEY == "none":
        logger.warning("FCM_SERVER_KEY not set or is 'none', cannot send legacy notification")
        return None
    
    headers = {
        'Authorization': f'key={FCM_SERVER_KEY}',
        'Content-Type': 'application/json',
    }
    
    results = []
    if isinstance(tokens, str):
        tokens = [tokens]
    
    for token in tokens:
        if not token:
            continue
            
        payload = {
            'to': token,
            'notification': {
                'title': title,
                'body': body,
                'sound': 'default',
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            },
            'priority': 'high',
        }
        
        if data:
            payload['data'] = data
        
        try:
            response = requests.post(FCM_URL, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success', 0) > 0:
                    results.append({'success': True, 'token': token[:10] + '...'})
                    logger.info(f"✅ FCM legacy notification sent to {token[:10]}...")
                else:
                    error = result.get('results', [{}])[0].get('error', 'Unknown error')
                    results.append({'error': error, 'token': token[:10] + '...'})
                    logger.warning(f"❌ FCM legacy failed for {token[:10]}...: {error}")
            else:
                results.append({'error': f'HTTP {response.status_code}', 'token': token[:10] + '...'})
                logger.warning(f"❌ FCM legacy HTTP error {response.status_code} for {token[:10]}...")
        except Exception as e:
            results.append({'error': str(e), 'token': token[:10] + '...'})
            logger.error(f"❌ FCM legacy request error: {e}")
    
    return results


def send_push_notification(tokens, title, body, data=None):
    """
    الواجهة الرئيسية: تختار تلقائياً الطريقة المناسبة.
    إذا كان FCM_SERVER_KEY موجوداً وليس "none" تستخدم legacy API.
    وإلا تحاول استخدام service account (credentials.json).
    """
    if not tokens:
        logger.warning("No tokens provided for notification")
        return None
    
    # إذا كان هناك FCM_SERVER_KEY حقيقي (ليس none)
    if FCM_SERVER_KEY and FCM_SERVER_KEY != "none":
        return send_push_notification_legacy(tokens, title, body, data)
    else:
        # استخدام service account (credentials.json)
        return send_push_notification_v1(tokens, title, body, data)


def send_to_customers(title, body, data=None):
    """
    إرسال إشعار لجميع العملاء (يتم جلب التوكنات من قاعدة البيانات)
    """
    try:
        from models import UserModel
        customers = UserModel.get_all_customers()
        tokens = [c.get('fcm_token') for c in customers if c.get('fcm_token')]
        
        if tokens:
            logger.info(f"📢 Sending notification to {len(tokens)} customers")
            return send_push_notification(tokens, title, body, data)
        else:
            logger.warning("No customer FCM tokens found")
            return None
    except Exception as e:
        logger.error(f"Error in send_to_customers: {e}")
        return None


def send_to_single_device(fcm_token, title, body, data=None):
    """
    إرسال إشعار لجهاز واحد
    """
    if not fcm_token:
        logger.warning("No FCM token provided")
        return None
    return send_push_notification(fcm_token, title, body, data)


def test_fcm_connection():
    """
    اختبار اتصال FCM (يرسل إشعار تجريبي)
    """
    if USE_SERVICE_ACCOUNT:
        token = get_access_token_from_service_account()
        if token:
            logger.info("✅ FCM v1 connection test: SUCCESS (access token obtained)")
            return True
        else:
            logger.error("❌ FCM v1 connection test: FAILED (no access token)")
            return False
    elif FCM_SERVER_KEY and FCM_SERVER_KEY != "none":
        logger.info("✅ FCM legacy connection test: Server key configured")
        return True
    else:
        logger.error("❌ FCM connection test: No configuration found")
        return False