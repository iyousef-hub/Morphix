"""File identification and intelligent context decisions; no Qt required."""
from collections import Counter
from pathlib import Path

PDF = {'.pdf'}
IMAGE = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff', '.gif', '.heic', '.heif', '.avif'}
VIDEO = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg', '.ts', '.mts', '.m2ts', '.wmv', '.flv'}
AUDIO = {'.mp3', '.wav', '.flac', '.m4a', '.m4b', '.ogg', '.oga', '.aac', '.aiff', '.aif', '.opus', '.wma', '.amr', '.caf', '.weba'}
OFFICE = {'.doc', '.docx', '.ppt', '.pptx', '.pps', '.ppsx', '.odt', '.odp', '.rtf'}
SHEET = {'.xls', '.xlsx', '.xlsm', '.ods', '.csv'}
ARCHIVE = {'.zip', '.7z', '.rar', '.tar', '.gz'}

# The header can override a misleading suffix for common formats.
def detect_extension(path):
    name = Path(path)
    ext = name.suffix.lower()
    try:
        with name.open('rb') as stream:
            h = stream.read(16)
        if h.startswith(b'%PDF-'): return '.pdf'
        if h.startswith(b'\x89PNG\r\n\x1a\n'): return '.png'
        if h.startswith(b'\xff\xd8\xff'): return '.jpg'
        if h.startswith((b'GIF87a', b'GIF89a')): return '.gif'
        if h.startswith(b'RIFF') and h[8:12] == b'WEBP': return '.webp'
    except (OSError, ValueError):
        pass
    return ext


def category_for(path):
    ext = detect_extension(path)
    for cat, extensions in [('pdf', PDF), ('image', IMAGE), ('video', VIDEO), ('audio', AUDIO), ('office', OFFICE), ('excel', SHEET), ('archive', ARCHIVE)]:
        if ext in extensions: return cat
    return 'other'


def selection_profile(paths):
    if not paths: return 'mixed'
    categories = {category_for(p) for p in paths}
    if categories == {'pdf', 'image'}:
        return 'pdf_image_mix'
    # Word / PowerPoint / Excel mixed with each other, images or PDFs.
    if len(categories) > 1 and categories <= {'office', 'excel', 'image', 'pdf'} and categories & {'office', 'excel'}:
        return 'docs_mix'
    if categories == {'excel'}:
        return 'excel_single' if len(paths) == 1 else 'excel_multi'
    if len(categories) == 1:
        category = next(iter(categories))
        if category in {'pdf', 'image', 'video', 'audio'}:
            return f'{category}_{"single" if len(paths) == 1 else "multi"}'
        if category == 'office': return 'office'
    return 'mixed'


def file_summary(paths, max_lines=4):
    """For wheel center: '6 PDF\n2 PNG\n1 JPEG', not just '9 files'."""
    counts = Counter('JPEG' if (ext := detect_extension(p).lstrip('.').upper()) in ('JPG', 'JPEG') else (ext or 'FILE') for p in paths)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    labels = [f'{count} {fmt}' for fmt, count in ranked[:max_lines]]
    if len(ranked) > max_lines:
        labels.append(f'+{len(ranked) - max_lines} types')
    return labels if labels else ['No files']


def preserve_selected_order(previous, current):
    """Keep surviving selections ordered; append newly highlighted files.

    Finder selection order is not guaranteed to represent click chronology.
    This preserves chronology only for changes observed while Morphix is open;
    the merge ordering dialog is the authoritative final choice.
    """
    chosen = list(dict.fromkeys(map(str, current)))
    chosen_set = set(chosen)
    remaining = [str(p) for p in previous if str(p) in chosen_set]
    existing = set(remaining)
    return remaining + [p for p in chosen if p not in existing]
