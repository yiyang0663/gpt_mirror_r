from __future__ import annotations

from typing import Any


TEXT_BLOCK_TYPE = "text"
IMAGE_BLOCK_TYPE = "image_url"
FILE_BLOCK_TYPE = "file"
SUPPORTED_BLOCK_TYPES = {TEXT_BLOCK_TYPE, IMAGE_BLOCK_TYPE, FILE_BLOCK_TYPE}


def _normalize_text_block(item: Any):
    text = ""
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        text = item.get("text") or item.get("content") or ""

    normalized = str(text or "")
    if not normalized.strip():
        return None
    return {
        "type": TEXT_BLOCK_TYPE,
        "text": normalized,
    }


def _normalize_image_block(item: dict[str, Any]):
    image_payload = item.get("image_url")
    image_url = ""
    detail = ""

    if isinstance(image_payload, dict):
        image_url = str(image_payload.get("url") or "").strip()
        detail = str(image_payload.get("detail") or "").strip()
    elif isinstance(image_payload, str):
        image_url = image_payload.strip()

    if not image_url:
        image_url = str(item.get("url") or item.get("image") or "").strip()
    if not detail:
        detail = str(item.get("detail") or "").strip()

    if not image_url:
        return None

    normalized = {
        "type": IMAGE_BLOCK_TYPE,
        "image_url": {
            "url": image_url,
        },
    }
    if detail:
        normalized["image_url"]["detail"] = detail
    return normalized


def _normalize_file_block(item: dict[str, Any]):
    file_payload = item.get("file") if isinstance(item.get("file"), dict) else item

    filename = str(
        file_payload.get("filename")
        or file_payload.get("name")
        or file_payload.get("title")
        or ""
    ).strip()
    file_data = str(file_payload.get("file_data") or "").strip()
    file_id = str(file_payload.get("file_id") or "").strip()
    file_url = str(file_payload.get("file_url") or "").strip()
    mime_type = str(file_payload.get("mime_type") or file_payload.get("mime") or "").strip()
    size = file_payload.get("size")

    if not (file_data or file_id or file_url):
        return None

    normalized_file = {}
    if filename:
        normalized_file["filename"] = filename
    if mime_type:
        normalized_file["mime_type"] = mime_type
    if isinstance(size, int) and size >= 0:
        normalized_file["size"] = size
    if file_data:
        normalized_file["file_data"] = file_data
    if file_id:
        normalized_file["file_id"] = file_id
    if file_url:
        normalized_file["file_url"] = file_url

    return {
        "type": FILE_BLOCK_TYPE,
        "file": normalized_file,
    }


def normalize_chat_content_blocks(content: Any, fallback_text: str = ""):
    items = content
    if isinstance(items, str):
        items = [{"type": TEXT_BLOCK_TYPE, "text": items}]
    elif isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list):
        items = []

    normalized_blocks = []
    for item in items:
        if isinstance(item, str):
            normalized = _normalize_text_block(item)
        elif isinstance(item, dict):
            item_type = str(item.get("type") or "").strip().lower()
            if item_type in {"", TEXT_BLOCK_TYPE, "input_text", "output_text"}:
                normalized = _normalize_text_block(item)
            elif item_type in {IMAGE_BLOCK_TYPE, "input_image"}:
                normalized = _normalize_image_block(item)
            elif item_type in {FILE_BLOCK_TYPE, "input_file"}:
                normalized = _normalize_file_block(item)
            else:
                normalized = None
        else:
            normalized = None

        if normalized:
            normalized_blocks.append(normalized)

    if normalized_blocks:
        return normalized_blocks

    fallback_text = str(fallback_text or "")
    if fallback_text.strip():
        return [
            {
                "type": TEXT_BLOCK_TYPE,
                "text": fallback_text,
            }
        ]
    return []


def extract_text_from_content_blocks(content_blocks: Any):
    normalized_blocks = normalize_chat_content_blocks(content_blocks)
    text_parts = []
    for block in normalized_blocks:
        if block.get("type") == TEXT_BLOCK_TYPE:
            text_parts.append(str(block.get("text") or ""))
    return "".join(text_parts).strip()


def extract_file_names_from_content_blocks(content_blocks: Any):
    normalized_blocks = normalize_chat_content_blocks(content_blocks)
    file_names = []
    for block in normalized_blocks:
        if block.get("type") == FILE_BLOCK_TYPE:
            name = str((block.get("file") or {}).get("filename") or "").strip()
            if name:
                file_names.append(name)
    return file_names


def summarize_content_blocks(content_blocks: Any):
    text = extract_text_from_content_blocks(content_blocks)
    if text:
        return text

    normalized_blocks = normalize_chat_content_blocks(content_blocks)
    image_count = sum(1 for block in normalized_blocks if block.get("type") == IMAGE_BLOCK_TYPE)
    file_names = extract_file_names_from_content_blocks(normalized_blocks)

    attachment_names = []
    if image_count == 1:
        attachment_names.append("1 张图片")
    elif image_count > 1:
        attachment_names.append(f"{image_count} 张图片")

    if file_names:
        attachment_names.extend(file_names[:3])

    return "，".join(attachment_names).strip()
