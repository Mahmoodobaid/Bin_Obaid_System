# =====================================================
# image_optimizer.py - ضغط الصور تلقائياً للوصول إلى حجم 200KB أو أقل
# =====================================================

from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

DEFAULT_MAX_WIDTH = 1600
DEFAULT_MAX_HEIGHT = 1600
TARGET_SIZE_KB = 200
MIN_QUALITY = 30
START_QUALITY = 85
STEP_QUALITY = 5

def optimize_image_to_target(image_bytes, original_filename=None):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        max_w = DEFAULT_MAX_WIDTH
        max_h = DEFAULT_MAX_HEIGHT
        if img.width > max_w or img.height > max_h:
            ratio = min(max_w / img.width, max_h / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        quality = START_QUALITY
        optimized_bytes = None
        final_quality = quality
        
        while quality >= MIN_QUALITY:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            size_kb = len(output.getvalue()) / 1024
            
            if size_kb <= TARGET_SIZE_KB:
                optimized_bytes = output.getvalue()
                final_quality = quality
                break
            quality -= STEP_QUALITY
        
        if optimized_bytes is None:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=MIN_QUALITY, optimize=True)
            optimized_bytes = output.getvalue()
            final_quality = MIN_QUALITY
        
        final_size_kb = len(optimized_bytes) / 1024
        return optimized_bytes, 'image/jpeg', final_size_kb
        
    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        return image_bytes, 'image/jpeg', len(image_bytes)/1024

def optimize_image(image_bytes, original_filename=None, max_width=None, max_height=None, quality=None):
    if quality is not None:
        return image_bytes, 'image/jpeg'
    else:
        return optimize_image_to_target(image_bytes, original_filename)[:2]
