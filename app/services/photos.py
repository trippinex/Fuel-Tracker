"""Photo upload validation.

Single source of truth for size cap, allowed extensions, and magic-byte
verification. Replaces the standard library ``imghdr`` (deprecated in
Python 3.11, slated for removal in 3.13) with a small inline detector.
"""

import os
from typing import Optional, Tuple

ALLOWED_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


def _detect_image_type(header: bytes) -> Optional[str]:
    """Sniff the leading bytes of a file to identify a known image format.

    Returns 'jpeg', 'png', 'webp', or None if no match.
    """
    if len(header) < 12:
        return None
    if header[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'
    return None


def validate_photo(file_storage) -> Tuple[Optional[str], Optional[str]]:
    """Validate an uploaded image file.

    Returns:
        (extension, error_message)
        - On success:   (".jpg", None) — extension includes the leading dot
        - On failure:   (None, "human-readable error")
        - On no file:   (None, None) — nothing was uploaded, no error
    """
    if not file_storage or not file_storage.filename:
        return None, None

    # 1. Size cap
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_PHOTO_BYTES:
        return None, 'Photo must be smaller than 5 MB.'

    # 2. Extension check
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        return None, 'Photo must be a JPG, PNG, or WebP image.'

    # 3. Magic-bytes check — defends against a renamed file
    header = file_storage.read(512)
    file_storage.seek(0)
    detected = _detect_image_type(header)
    if detected not in ('jpeg', 'png', 'webp'):
        return None, 'Photo content does not match a supported image type.'

    return ext, None
