"""
Media Processor — Thumbnail Generation Logic
Group A — Media Sharing Platform
Worker/Processor Developer: DMPT Dissanayake

This module handles the actual media processing:
  - Image thumbnail generation using Pillow
  - Video thumbnail extraction using ffmpeg (subprocess)
  - Placeholder generation for simulation / local testing
"""

import os
import logging
import subprocess
import tempfile
from typing import Tuple

logger = logging.getLogger(__name__)

# Default thumbnail dimensions (matches config.py THUMBNAIL_SIZE)
DEFAULT_THUMBNAIL_SIZE = (150, 150)


def generate_image_thumbnail(input_path: str, output_path: str,
                             size: Tuple[int, int] = DEFAULT_THUMBNAIL_SIZE) -> bool:
    """
    Generate a thumbnail from an image file using Pillow.

    Args:
        input_path:  Path to the source image file
        output_path: Path where the thumbnail JPEG will be saved
        size:        Tuple of (width, height) for the thumbnail

    Returns:
        True if the thumbnail was created successfully
    """
    try:
        from PIL import Image

        img = Image.open(input_path)
        img.thumbnail(size, Image.LANCZOS)

        # Convert to RGB if necessary (e.g. PNG with alpha)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(output_path, "JPEG", quality=85)
        logger.info(f"Image thumbnail created: {output_path} ({size[0]}x{size[1]})")
        return True

    except ImportError:
        logger.error("Pillow is not installed. Run: pip install Pillow")
        return False
    except Exception as e:
        logger.error(f"Image thumbnail generation failed: {e}")
        return False


def generate_video_thumbnail(input_path: str, output_path: str,
                             size: Tuple[int, int] = DEFAULT_THUMBNAIL_SIZE) -> bool:
    """
    Extract a single frame from a video file using ffmpeg and save it as
    a JPEG thumbnail.

    Requires ffmpeg to be installed and available on PATH.

    Args:
        input_path:  Path to the source video file
        output_path: Path where the thumbnail JPEG will be saved
        size:        Tuple of (width, height) for the thumbnail

    Returns:
        True if the thumbnail was created successfully
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",                          # overwrite output
            "-i", input_path,              # input file
            "-ss", "00:00:01",             # seek to 1 second
            "-vframes", "1",               # extract 1 frame
            "-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease",
            "-q:v", "5",                   # quality (lower = better)
            output_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )

        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"Video thumbnail created: {output_path}")
            return True
        else:
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.error(f"ffmpeg failed (code {result.returncode}): {stderr[:300]}")
            return False

    except FileNotFoundError:
        logger.error("ffmpeg is not installed or not on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out after 60 seconds")
        return False
    except Exception as e:
        logger.error(f"Video thumbnail generation failed: {e}")
        return False


def generate_placeholder_thumbnail(output_path: str, media_id: str,
                                   media_type: str = "image",
                                   size: Tuple[int, int] = DEFAULT_THUMBNAIL_SIZE) -> bool:
    """
    Generate a placeholder thumbnail image for simulation / local testing.
    Creates a coloured rectangle with the media ID rendered as text.

    This is used when the actual media file is not available (e.g. during
    simulation with mock S3).

    Args:
        output_path: Path where the placeholder JPEG will be saved
        media_id:    The media ID — drawn on the image as label text
        media_type:  'image' or 'video' — affects background colour
        size:        Tuple of (width, height)

    Returns:
        True if the placeholder was created successfully
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Choose background colour based on media type
        bg_color = (46, 125, 50) if media_type == "image" else (21, 101, 192)
        text_color = (255, 255, 255)

        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)

        # Draw media type label
        label = f"{'IMG' if media_type == 'image' else 'VID'}"
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            font = ImageFont.load_default()

        # Centre the label
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size[0] - tw) / 2, (size[1] - th) / 2 - 10),
                  label, fill=text_color, font=font)

        # Draw short ID below the label
        short_id = media_id[:8] if len(media_id) > 8 else media_id
        try:
            small_font = ImageFont.truetype("arial.ttf", 10)
        except (OSError, IOError):
            small_font = ImageFont.load_default()

        bbox2 = draw.textbbox((0, 0), short_id, font=small_font)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(((size[0] - tw2) / 2, (size[1] - th) / 2 + 12),
                  short_id, fill=text_color, font=small_font)

        img.save(output_path, "JPEG", quality=85)
        logger.info(f"Placeholder thumbnail created: {output_path}")
        return True

    except ImportError:
        logger.error("Pillow is not installed. Run: pip install Pillow")
        return False
    except Exception as e:
        logger.error(f"Placeholder thumbnail generation failed: {e}")
        return False


def generate_thumbnail(input_path: str, output_path: str,
                       media_type: str = "image",
                       media_id: str = "",
                       size: Tuple[int, int] = DEFAULT_THUMBNAIL_SIZE,
                       use_placeholder: bool = False) -> bool:
    """
    Main dispatcher — generate a thumbnail for the given media file.

    In simulation / local mode, if the input file does not exist or
    `use_placeholder` is True, a placeholder thumbnail is generated
    instead.

    Args:
        input_path:      Path to the source media file
        output_path:     Path where the thumbnail JPEG will be saved
        media_type:      'image' or 'video'
        media_id:        Media ID (used for placeholder labelling)
        size:            Tuple of (width, height)
        use_placeholder: If True, always generate a placeholder

    Returns:
        True if any form of thumbnail was created successfully
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # If real file is available and placeholder is not forced
    if not use_placeholder and os.path.exists(input_path):
        if media_type == "image":
            success = generate_image_thumbnail(input_path, output_path, size)
        elif media_type == "video":
            success = generate_video_thumbnail(input_path, output_path, size)
        else:
            logger.warning(f"Unknown media type '{media_type}', trying image handler")
            success = generate_image_thumbnail(input_path, output_path, size)

        if success:
            return True
        else:
            logger.warning("Real thumbnail generation failed, falling back to placeholder")

    # Fallback: generate a placeholder
    logger.info("Using placeholder thumbnail (simulation mode or fallback)")
    return generate_placeholder_thumbnail(output_path, media_id, media_type, size)
