// =====================================================
// update_service.dart - التحقق من التحديثات وتنزيل APK
// =====================================================

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:open_file/open_file.dart';
import 'package:permission_handler/permission_handler.dart';
import '../api_service.dart';
import '../utils/constants.dart';

class UpdateService {
  static final ApiService _api = ApiService();

  // التحقق من وجود تحديث
  static Future<bool> checkForUpdate() async {
    try {
      final latest = await _api.getLatestVersion();
      final latestVersion = latest['version'];
      final currentVersion = Constants.currentVersion;
      
      return _isNewerVersion(latestVersion, currentVersion);
    } catch (e) {
      print('Error checking update: $e');
      return false;
    }
  }

  // الحصول على معلومات التحديث
  static Future<Map<String, dynamic>> getUpdateInfo() async {
    return await _api.getLatestVersion();
  }

  // تنزيل وتثبيت التحديث
  static Future<bool> downloadAndInstall(BuildContext context, String downloadUrl) async {
    // طلب إذن التخزين (لأندرويد)
    if (Platform.isAndroid) {
      final status = await Permission.storage.request();
      if (!status.isGranted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('يلزم إذن الوصول إلى التخزين لتثبيت التحديث')),
        );
        return false;
      }
    }

    // طلب إذن تثبيت التطبيقات (لأندرويد 8+)
    if (Platform.isAndroid) {
      final status = await Permission.requestInstallPackages.request();
      if (!status.isGranted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('يلزم إذن تثبيت التطبيقات لتثبيت التحديث')),
        );
        return false;
      }
    }

    // عرض مربع حوار التحميل
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => const _DownloadDialog(),
    );

    try {
      // تنزيل الملف
      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/bin_obeid_update.apk');
      
      final response = await http.get(Uri.parse(downloadUrl));
      await file.writeAsBytes(response.bodyBytes);
      
      // إغلاق مربع الحوار
      // ignore: use_build_context_synchronously
      Navigator.pop(context);
      
      // فتح الملف للتثبيت
      final result = await OpenFile.open(file.path);
      return result.type == ResultType.done;
    } catch (e) {
      // إغلاق مربع الحوار في حالة الخطأ
      // ignore: use_build_context_synchronously
      Navigator.pop(context);
      print('Download error: $e');
      return false;
    }
  }

  // عرض مربع حوار التحديث
  static Future<void> showUpdateDialog(BuildContext context) async {
    final updateInfo = await getUpdateInfo();
    final latestVersion = updateInfo['version'];
    final releaseNotes = updateInfo['release_notes'];
    final downloadUrl = updateInfo['download_url'];
    final isForceUpdate = updateInfo['force_update'] ?? false;

    if (downloadUrl == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('لا يوجد رابط تحميل متاح')),
      );
      return;
    }

    showDialog(
      context: context,
      barrierDismissible: !isForceUpdate,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            const Icon(Icons.system_update, color: Colors.blue),
            const SizedBox(width: 8),
            Text('تحديث متاح v$latestVersion'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('يتوفر إصدار جديد من التطبيق:'),
            const SizedBox(height: 8),
            if (releaseNotes != null && releaseNotes.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('ما الجديد؟', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(releaseNotes, style: const TextStyle(fontSize: 12)),
                  ],
                ),
              ),
            if (isForceUpdate)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text(
                  'هذا التحديث إلزامي للاستمرار في استخدام التطبيق',
                  style: TextStyle(color: Colors.red, fontSize: 12),
                ),
              ),
          ],
        ),
        actions: [
          if (!isForceUpdate)
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('لاحقاً'),
            ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final success = await downloadAndInstall(context, downloadUrl);
              if (!success && context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('فشل تحميل التحديث، يرجى المحاولة لاحقاً')),
                );
              }
            },
            child: const Text('تحديث الآن'),
          ),
        ],
      ),
    );
  }

  // مقارنة الإصدارات
  static bool _isNewerVersion(String latest, String current) {
    try {
      final latestParts = latest.replaceAll('v', '').split('.');
      final currentParts = current.replaceAll('v', '').split('.');
      
      for (int i = 0; i < latestParts.length; i++) {
        final latestNum = int.tryParse(latestParts[i]) ?? 0;
        final currentNum = i < currentParts.length ? int.tryParse(currentParts[i]) ?? 0 : 0;
        
        if (latestNum > currentNum) return true;
        if (latestNum < currentNum) return false;
      }
      return false;
    } catch (e) {
      return latest != current;
    }
  }
}

// مربع حوار التحميل
class _DownloadDialog extends StatelessWidget {
  const _DownloadDialog();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          const Text('جاري تحميل التحديث...'),
          const SizedBox(height: 8),
          Text(
            'يرجى الانتظار',
            style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
          ),
        ],
      ),
    );
  }
}