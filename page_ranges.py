"""PDF page-range validation and extraction; independent of Qt."""
from pathlib import Path


def validate_ranges(ranges, page_count, *, allow_overlap=False):
    if not isinstance(page_count, int) or page_count < 1:
        raise ValueError('PDF contains no pages')
    if not ranges:
        raise ValueError('Choose at least one range')
    normalized = []
    seen = set()
    for start, end in ranges:
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError('Page boundaries must be whole numbers')
        if start < 1 or end > page_count or start > end:
            raise ValueError(f'Use ranges from 1 to {page_count}, with Start <= End')
        pages = set(range(start, end + 1))
        if not allow_overlap and (seen & pages):
            raise ValueError('Page ranges overlap; each page should belong to one part')
        seen.update(pages)
        normalized.append((start, end))
    return normalized


def extract_ranges(pdf_path, out_dir, ranges, *, separate=False):
    import pymupdf
    from core_ops import unique_path
    source = Path(pdf_path)
    with pymupdf.open(source) as doc:
        if not doc.is_pdf or doc.needs_pass:
            raise ValueError('Select an unprotected PDF')
        pairs = validate_ranges(ranges, len(doc))
        if not separate and len(pairs) != 1:
            raise ValueError('Extract Range requires exactly one range')
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        result_paths = []
        for index, (first, last) in enumerate(pairs, 1):
            with pymupdf.open() as part:
                part.insert_pdf(doc, from_page=first - 1, to_page=last - 1)
                suffix = f'_part_{index:02d}_pages_{first:03d}-{last:03d}' if separate else f'_pages_{first:03d}-{last:03d}'
                output = unique_path(target_dir, source.stem + suffix + '.pdf')
                part.save(output, garbage=4, deflate=True)
                result_paths.append(output)
        return result_paths
