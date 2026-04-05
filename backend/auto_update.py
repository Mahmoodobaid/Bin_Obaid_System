# =====================================================
# auto_update.py - نظام التحديث التلقائي لتطبيق بن عبيد (OTA)
# الإصدار 2.0 - مع دعم GitHub Releases، التخزين المؤقت، وتحليلات الإصدارات
# =====================================================

import os
import logging
import requests
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, send_file
from functools import wraps
import re

logger = logging.getLogger(__name__)
update_bp = Blueprint('update', __name__)

# إعدادات GitHub
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Mahmoodobaid/Bin_Obaid_System')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', None)
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# إعدادات التخزين المؤقت
CACHE_DURATION_SECONDS = int(os.getenv('UPDATE_CACHE_SECONDS', 300))
VERSIONS_LOG_FILE = 'versions_log.json'

# التخزين المؤقت
_cache = {}
_cache_expiry = {}


def cached(ttl_seconds=CACHE_DURATION_SECONDS):
    """ديكوراتور لتخزين نتائج الدوال مؤقتاً"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            now = datetime.utcnow()
            if key in _cache and _cache_expiry.get(key, now) > now:
                return _cache[key]
            result = func(*args, **kwargs)
            _cache[key] = result
            _cache_expiry[key] = now + timedelta(seconds=ttl_seconds)
            return result
        return wrapper
    return decorator


def invalidate_update_cache():
    """مسح التخزين المؤقت للإصدارات"""
    global _cache, _cache_expiry
    keys_to_delete = [k for k in _cache.keys() if k.startswith('get_latest_release')]
    for k in keys_to_delete:
        del _cache[k]
        del _cache_expiry[k]
    logger.info("Update cache invalidated")


def parse_version(version_str: str) -> tuple:
    """
    تحويل سلسلة الإصدار إلى tuple للمقارنة.
    يدعم: 'v1.2.3' أو '1.2.3' أو '1.2.3-beta'
    """
    if version_str.startswith('v'):
        version_str = version_str[1:]
    parts = re.split(r'[-.]', version_str)
    numeric_parts = []
    for p in parts:
        try:
            numeric_parts.append(int(p))
        except ValueError:
            break
    return tuple(numeric_parts)


def is_newer_version(current: str, latest: str) -> bool:
    """مقارنة إصدارين، تعيد True إذا كان latest أحدث من current"""
    current_tuple = parse_version(current)
    latest_tuple = parse_version(latest)
    return latest_tuple > current_tuple


@cached(ttl_seconds=CACHE_DURATION_SECONDS)
def get_latest_release():
    """
    استدعاء GitHub API لجلب أحدث إصدار.
    تعيد: (version, download_url, release_notes, published_at)
    أو (None, None, None, None) في حالة الخطأ
    """
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN and GITHUB_TOKEN != 'ضع_هنا_توكن_جيت_هب':
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            version = data.get('tag_name', '')
            
            # البحث عن APK asset
            download_url = None
            for asset in data.get('assets', []):
                if asset['name'].endswith('.apk'):
                    download_url = asset['browser_download_url']
                    break
            
            release_notes = data.get('body', '')
            published_at = data.get('published_at', '')
            
            logger.info(f"Latest release: {version}")
            return version, download_url, release_notes, published_at
        
        elif response.status_code == 404:
            logger.warning(f"No releases found for repo: {GITHUB_REPO}")
            return None, None, None, None
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return None, None, None, None
            
    except requests.exceptions.Timeout:
        logger.error("GitHub API timeout")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Failed to fetch latest release: {str(e)}")
        return None, None, None, None


def register_user_version(user_id: str, version: str, device_info: str = None):
    """تسجيل إصدار التطبيق الذي يستخدمه المستخدم (للإحصائيات)"""
    try:
        log = {}
        if os.path.exists(VERSIONS_LOG_FILE):
            with open(VERSIONS_LOG_FILE, 'r', encoding='utf-8') as f:
                log = json.load(f)
        
        if user_id not in log:
            log[user_id] = []
        
        log[user_id].append({
            'version': version,
            'device_info': device_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # الاحتفاظ بآخر 10 إدخالات فقط
        if len(log[user_id]) > 10:
            log[user_id] = log[user_id][-10:]
        
        with open(VERSIONS_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save version log: {e}")


def get_version_adoption_stats():
    """إحصائيات عن اعتماد الإصدارات (كم مستخدم يستخدم كل إصدار)"""
    try:
        if not os.path.exists(VERSIONS_LOG_FILE):
            return {}
        
        with open(VERSIONS_LOG_FILE, 'r', encoding='utf-8') as f:
            log = json.load(f)
        
        stats = {}
        for user_id, entries in log.items():
            if entries:
                latest_version = entries[-1]['version']
                stats[latest_version] = stats.get(latest_version, 0) + 1
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get version stats: {e}")
        return {}


# ===================== نقاط النهاية (Endpoints) =====================

@update_bp.route('/version', methods=['GET'])
def get_version():
    """
    نقطة نهاية عامة (لا تحتاج مصادقة) لإرجاع أحدث إصدار ومعلومات التحميل.
    يمكن تمرير ?current_version=1.0.0 للتحقق إذا كان هناك تحديث.
    """
    version, download_url, release_notes, published_at = get_latest_release()
    
    if not version:
        return jsonify({
            'error': 'Unable to fetch latest version',
            'message': 'يرجى المحاولة لاحقاً'
        }), 503

    current = request.args.get('current_version', '')
    update_available = False
    if current:
        update_available = is_newer_version(current, version)

    response = {
        'version': version,
        'download_url': download_url,
        'release_notes': release_notes,
        'published_at': published_at,
        'update_available': update_available
    }
    return jsonify(response), 200


@update_bp.route('/version/check', methods=['POST'])
def check_version():
    """
    نقطة نهاية لتسجيل إصدار المستخدم والتحقق من التحديث.
    الجسم: { "current_version": "1.0.0", "device_info": "optional" }
    """
    data = request.get_json()
    if not data or 'current_version' not in data:
        return jsonify({'error': 'current_version مطلوب'}), 400

    current_version = data['current_version']
    device_info = data.get('device_info', '')
    
    # تسجيل الإصدار (إذا كان هناك user_id من التوكن)
    auth_header = request.headers.get('Authorization')
    user_id = None
    if auth_header and auth_header.startswith('Bearer '):
        try:
            from auth import decode_token
            token = auth_header.split(' ')[1]
            payload = decode_token(token)
            if payload:
                user_id = payload.get('user_id')
        except:
            pass
    
    if user_id:
        register_user_version(user_id, current_version, device_info)

    # جلب أحدث إصدار
    version, download_url, release_notes, _ = get_latest_release()
    if not version:
        return jsonify({'error': 'Unable to fetch latest version'}), 503

    update_available = is_newer_version(current_version, version)
    
    return jsonify({
        'current_version': current_version,
        'latest_version': version,
        'update_available': update_available,
        'download_url': download_url if update_available else None,
        'release_notes': release_notes if update_available else None
    }), 200


@update_bp.route('/download/latest', methods=['GET'])
def download_latest():
    """إعادة توجيه مباشر إلى رابط تحميل أحدث APK"""
    version, download_url, _, _ = get_latest_release()
    if not download_url:
        return jsonify({'error': 'No APK found in latest release'}), 404
    return redirect(download_url, code=302)


@update_bp.route('/download/proxy', methods=['GET'])
def download_proxy():
    """
    بديل: يقوم الخادم بتنزيل APK وإعادته كـ attachment.
    مفيد إذا كان المستخدمون لا يستطيعون الوصول مباشرة إلى GitHub.
    """
    version, download_url, _, _ = get_latest_release()
    if not download_url:
        return jsonify({'error': 'No APK available'}), 404
    
    try:
        response = requests.get(download_url, stream=True, timeout=30)
        if response.status_code == 200:
            return send_file(
                response.raw,
                mimetype='application/vnd.android.package-archive',
                as_attachment=True,
                download_name=f'binobeid_{version}.apk'
            )
        else:
            return jsonify({'error': 'Failed to download APK from GitHub'}), 502
    except Exception as e:
        logger.error(f"Proxy download error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@update_bp.route('/admin/update/refresh-cache', methods=['POST'])
def refresh_cache():
    """نقطة نهاية للمسؤول لمسح التخزين المؤقت يدوياً"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from auth import decode_token
        token = auth_header.split(' ')[1]
        payload = decode_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
    except:
        return jsonify({'error': 'Auth failed'}), 500
    
    invalidate_update_cache()
    return jsonify({'message': 'Update cache cleared successfully'}), 200


@update_bp.route('/admin/update/stats', methods=['GET'])
def version_stats():
    """نقطة نهاية للمسؤول لعرض إحصائيات اعتماد الإصدارات"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from auth import decode_token
        token = auth_header.split(' ')[1]
        payload = decode_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
    except:
        return jsonify({'error': 'Auth failed'}), 500
    
    stats = get_version_adoption_stats()
    return jsonify(stats), 200


@update_bp.route('/version/force-update', methods=['GET'])
def force_update_info():
    """
    نقطة نهاية خاصة لإجبار التحديث: تعيد إصدار إجباري إذا كان هناك تحديث حرج.
    """
    force_version = os.getenv('FORCE_UPDATE_VERSION', '')
    if not force_version:
        return jsonify({'force_update': False}), 200
    
    version, download_url, release_notes, _ = get_latest_release()
    
    return jsonify({
        'force_update': True,
        'required_version': force_version,
        'latest_version': version,
        'download_url': download_url,
        'message': 'يجب تحديث التطبيق للاستمرار في الخدمة'
    }), 200