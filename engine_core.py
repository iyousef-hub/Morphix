"""Headless converter engine for crash-isolated Morphix workers.

GUI code MUST NOT be imported here. Keep operational functions in sync with
main.py until the next cleanup refactors main.py into a thin compatibility API.
"""
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

def parse_pages(value, total):
    result = []
    for part in value.replace(' ', '').split(','):
        if not part: continue
        bits = part.split('-')
        if len(bits) > 2: raise ValueError('Invalid page range')
        try:
            a = int(bits[0]); b = int(bits[-1])
        except ValueError: raise ValueError('Page ranges must be numbers, e.g. 1-3,5')
        if a < 1 or b > total or a > b:
            raise ValueError(f'Page range must be between 1 and {total}')
        result.extend(range(a-1, b))
    return list(dict.fromkeys(result))


def unique_path(folder, name):
    target = Path(folder) / name
    if not target.exists():
        return target
    stem, ext = target.stem, target.suffix
    n = 2
    while (Path(folder) / f'{stem}_{n}{ext}').exists():
        n += 1
    return Path(folder) / f'{stem}_{n}{ext}'


def run_command(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors='replace')
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-1500:])


def ensure_tool(name):
    if name == 'ffmpeg':
        # imageio-ffmpeg ships platform-specific FFmpeg executables in its wheels.
        # PyInstaller bundles that executable when built with the supplied spec.
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f'{name} is not available in this build.')
    return path


def execute(action, paths, out_dir, progress, options=None):
    options = options or {}
    import pymupdf as fitz
    from PIL import Image, ImageOps
    outputs = []
    def save_pdf(doc, name, optimize=False):
        out = unique_path(out_dir, name)
        if optimize:
            from compression_engine import save_pdf_compressed
            save_pdf_compressed(doc, out, strength=int(options.get('compression_strength', 45)),
                                grayscale=bool(options.get('pdf_grayscale', False)))
        else:
            doc.save(str(out), garbage=4, deflate=True, clean=False)
        outputs.append(out)
    def update(i, n):
        progress.emit(round(i / max(n, 1) * 100))
    import tools_engine
    tools_engine.register_heic()  # iPhone photos (HEIC) work in every image tool
    status = getattr(progress, 'status', None)
    if action == 'ppt_media':
        return tools_engine.ppt_media(paths, out_dir, progress.emit,
                                      max_height=options.get('ppt_height', '1080'),
                                      audio_format=options.get('ppt_audio', 'm4a'))
    if action == 'trim_media':
        return tools_engine.trim_media(paths, out_dir, progress.emit, start=options.get('trim_start', '0'),
                                       end=options.get('trim_end', ''), exact=bool(options.get('trim_exact', True)))
    if action == 'heic_jpg':
        return tools_engine.heic_to_jpg(paths, out_dir, progress.emit, quality=int(options.get('quality', 92)))
    if action == 'pdf_word':
        return tools_engine.pdf_to_word(paths, out_dir, progress.emit, status=status)
    if action == 'organize_pdf':
        return tools_engine.organize_pdf(paths[0], out_dir, options.get('pages') or [], progress.emit)
    if action == 'sign_pdf':
        return tools_engine.sign_pdf(paths, out_dir, progress.emit, signature=options['signature'],
                                     box=options['box'], pages=options.get('pages', 'current'),
                                     page_index=int(options.get('page_index', 0)))
    if action == 'sign_images':
        return tools_engine.sign_images(paths, out_dir, progress.emit, signature=options['signature'],
                                        box=options['box'])
    if action == 'download_ocr_model':
        import ocr_models
        return [ocr_models.download(options.get('kind', 'ocr_arabic'), progress.emit, status)]
    engine = options.get('ocr_engine', 'standard')
    if action in ('ocr_image_text', 'extract_pdf_text', 'ocr_pdf_text') and engine == 'accurate':
        import ocr_models
        return ocr_models.accurate_text(paths, out_dir, progress.emit, lang=options.get('ocr_lang', 'auto'),
                                        status=status)
    if action == 'ocr_image_text' and engine == 'formula':
        import ocr_models
        return ocr_models.formulas_to_latex(paths, out_dir, progress.emit, status=status)
    if action in ('zip_files', 'rar_files', 'tar_gz_files'):
        from core_ops import archive_files
        kind = {'rar_files':'rar', 'zip_files':'zip', 'tar_gz_files':'tar.gz'}[action]
        return archive_files(paths, out_dir, kind, progress.emit)
    if action == 'transcribe_media':
        from transcription_engine import transcribe_media
        return transcribe_media(paths, out_dir, progress.emit,
                                language=options.get('language', 'auto'),
                                quality=options.get('quality', 'accurate'),
                                formats=options.get('formats', ['txt', 'srt']),
                                status=getattr(progress, 'status', None),
                                ui_lang=options.get('ui_lang', 'en'),
                                clean_audio=bool(options.get('clean_audio', True)))
    if action == 'remove_bg':
        from background_engine import remove_background
        return remove_background(paths, out_dir, progress.emit, quality=options.get('bg_quality', 'standard'),
                                 background=options.get('background', 'transparent'),
                                 status=getattr(progress, 'status', None), ui_lang=options.get('ui_lang', 'en'))
    if action == 'download_bg_model':
        from background_engine import download_model as bg_download
        return [bg_download(options.get('bg_quality', 'standard'), progress.emit,
                            getattr(progress, 'status', None), ui_lang=options.get('ui_lang', 'en'))]
    docs = {'docs_merge_pdf': 'docs_merge_pdf', 'docs_pdf_each': 'docs_pdf_each',
            'xlsx_pdf_fit': 'excel_pdf_fit', 'xlsx_csv': 'excel_to_csv', 'xlsx_split': 'excel_split_sheets',
            'xlsx_merge': 'excel_merge', 'csv_xlsx': 'csv_to_excel'}
    if action in docs:
        import docs_engine
        return getattr(docs_engine, docs[action])(paths, out_dir, progress.emit,
                                                  ui_lang=options.get('ui_lang', 'en'))
    if action == 'download_speech_model':
        from transcription_engine import download_model
        folder = download_model(options.get('quality', 'accurate'), progress.emit,
                                getattr(progress, 'status', None), ui_lang=options.get('ui_lang', 'en'))
        return [folder]
    if action == 'ocr_image_text':
        from ocr_engine import extract_image_text
        return extract_image_text(paths, out_dir, progress.emit, dpi=int(options.get('ocr_dpi', 220)))
    if action in ('split_pdf', 'separate_pdf'):
        from page_ranges import extract_ranges
        ranges = options.get('page_ranges')
        if not ranges:
            raise ValueError('Choose page ranges before splitting the PDF')
        result = extract_ranges(paths[0], out_dir, ranges, separate=(action == 'separate_pdf'))
        progress.emit(100)
        return result
    if action == 'ocr_searchable_pdf':
        from ocr_engine import searchable_pdf
        return searchable_pdf(paths, out_dir, progress.emit,
                              dpi=int(options.get('ocr_dpi', 200)))
    if action in ('extract_pdf_text', 'ocr_pdf_text'):
        from ocr_engine import extract_pdf_text
        return extract_pdf_text(paths, out_dir, progress.emit,
                                force_ocr=(action == 'ocr_pdf_text'),
                                dpi=int(options.get('ocr_dpi', 220)))
    if action in ('merge_pdf', 'merge_optimize'):
        from pdf_merge import merge_documents
        dest = merge_documents(paths, progress)
        try:
            save_pdf(dest, 'merged.pdf', action == 'merge_optimize')
        finally:
            dest.close()
    elif action in ('optimize_pdf', 'rotate_pdf', 'pdf_png', 'pdf_png_zip', 'pdf_jpg_zip', 'crop_pdf', 'delete_pdf_pages', 'extract_pdf_pages'):
        for i, p in enumerate(paths, 1):
            with fitz.open(p) as doc:
                if doc.needs_pass:
                    raise RuntimeError(f'Password-protected PDF: {Path(p).name}')
                stem = Path(p).stem
                if action == 'optimize_pdf':
                    save_pdf(doc, stem + '_optimized.pdf', True)
                elif action == 'rotate_pdf':
                    for page in doc:
                        page.set_rotation((page.rotation + 90) % 360)
                    save_pdf(doc, stem + '_rotated.pdf')
                elif action == 'crop_pdf':
                    margin = float(options.get('margin_percent', 5)) / 100
                    for page in doc:
                        box = page.cropbox
                        dx, dy = box.width * margin, box.height * margin
                        if dx * 2 >= box.width or dy * 2 >= box.height:
                            raise ValueError('Crop margin is too large')
                        page.set_cropbox(fitz.Rect(box.x0+dx, box.y0+dy, box.x1-dx, box.y1-dy))
                    save_pdf(doc, stem + '_cropped.pdf')
                elif action in ('delete_pdf_pages', 'extract_pdf_pages'):
                    selected = parse_pages(options.get('pages', ''), len(doc))
                    if action == 'delete_pdf_pages':
                        selected = [j for j in range(len(doc)) if j not in selected]
                    if not selected:
                        raise ValueError('No pages remain in the output PDF')
                    result = fitz.open()
                    try:
                        for j in selected: result.insert_pdf(doc, from_page=j, to_page=j)
                        save_pdf(result, stem + ('_extracted.pdf' if action == 'extract_pdf_pages' else '_pages_removed.pdf'))
                    finally: result.close()
                elif action in ('pdf_png_zip', 'pdf_jpg_zip'):
                    fmt = 'png' if action == 'pdf_png_zip' else 'jpg'
                    scale = float(options.get('pdf_image_scale', 2.0))
                    if len(doc) == 1:
                        dest = unique_path(out_dir, f'{stem}_page_001.{fmt}')
                        pixels = doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                        if fmt == 'png':
                            pixels.save(str(dest))
                        else:
                            from PIL import Image as PILImage
                            with PILImage.frombytes('RGB', (pixels.width, pixels.height), pixels.samples) as raster:
                                raster.save(dest, format='JPEG', quality=88, optimize=True)
                        outputs.append(dest)
                    else:
                        dest = unique_path(out_dir, f'{stem}_{fmt}_pages.zip')
                        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED,
                                             compresslevel=6) as archive:
                            for idx, page in enumerate(doc, 1):
                                pixels = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                                if fmt == 'png':
                                    data = pixels.tobytes('png')
                                else:
                                    from PIL import Image as PILImage
                                    from io import BytesIO
                                    stream = BytesIO()
                                    with PILImage.frombytes('RGB', (pixels.width, pixels.height), pixels.samples) as raster:
                                        raster.save(stream, format='JPEG', quality=88, optimize=True)
                                    data = stream.getvalue()
                                archive.writestr(f'Page_{idx:03d}.{fmt}', data)
                        outputs.append(dest)
                else:
                    for idx, page in enumerate(doc):
                        out = unique_path(out_dir, f'{stem}_page_{idx + 1:03}.png')
                        page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(str(out))
                        outputs.append(out)
            update(i, len(paths))
    elif action in ('images_pdf', 'image_png', 'image_jpg', 'image_webp', 'image_resize', 'image_compress', 'image_rotate', 'image_grayscale', 'image_crop'):
        if action == 'images_pdf':
            from pdf_merge import merge_documents
            doc = merge_documents(paths, progress)
            try:
                save_pdf(doc, 'images_combined.pdf')
            finally:
                doc.close()
        else:
            ext = {'image_png': '.png', 'image_jpg': '.jpg', 'image_webp': '.webp',
                   'image_resize': '.png', 'image_compress': '.jpg', 'image_rotate': '.png',
                   'image_grayscale': '.png', 'image_crop': '.png'}[action]
            for i, p in enumerate(paths, 1):
                with Image.open(p) as original:
                    im = ImageOps.exif_transpose(original)
                    if action == 'image_resize':
                        size = int(options.get('max_pixels', 1920))
                        im.thumbnail((size, size), Image.Resampling.LANCZOS)
                    elif action == 'image_rotate':
                        im = im.rotate(-90, expand=True)
                    elif action == 'image_grayscale':
                        im = im.convert('L')
                    elif action == 'image_crop':
                        percent = float(options.get('crop_percent', 10)) / 100
                        w, h = im.size
                        dx, dy = int(w * percent), int(h * percent)
                        im = im.crop((dx, dy, w-dx, h-dy))
                    if ext == '.jpg' and action != 'image_compress':
                        im = im.convert('RGB')
                    elif ext != '.jpg' and action != 'image_grayscale' and im.mode not in ('RGB', 'RGBA'):
                        im = im.convert('RGBA')
                    suffix = {'image_resize':'_resized', 'image_compress':'_compressed',
                              'image_rotate':'_rotated', 'image_grayscale':'_grayscale',
                              'image_crop':'_cropped'}.get(action, '_converted')
                    out = unique_path(out_dir, Path(p).stem + suffix + ext)
                    if action == 'image_compress':
                        from compression_engine import save_image_compressed
                        save_image_compressed(im, out, quality=int(options.get('quality', 72)),
                                              resize_max=options.get('resize_max'))
                    else:
                        save_options = {'quality': 88, 'optimize': True} if ext in ('.jpg', '.webp') else {'optimize': True}
                        im.save(out, **save_options)
                    outputs.append(out)
                update(i, len(paths))
    elif action in ('join_video', 'video_mp4', 'video_mp3', 'audio_mp3', 'join_audio'):
        ffmpeg = ensure_tool('ffmpeg')
        if action == 'join_audio':
            # Sequential concatenation, preserving the selected-file order.
            # Normalize sample rates/channel layouts to support mixed input formats.
            cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y']
            for p in paths:
                cmd += ['-i', p]
            filters = []
            for i in range(len(paths)):
                filters.append(f'[{i}:a:0]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]')
            filters.append(''.join(f'[a{i}]' for i in range(len(paths))) +
                           f'concat=n={len(paths)}:v=0:a=1[outa]')
            out = unique_path(out_dir, 'merged_audio.mp3')
            cmd += ['-filter_complex', ';'.join(filters), '-map', '[outa]',
                    '-c:a', 'libmp3lame', '-q:a', '2', str(out)]
            run_command(cmd)
            outputs.append(out)
            progress.emit(100)
        elif action == 'join_video':
            # Normalize to matching video/audio streams, retaining audio when present.
            # Videos without audio get a silent stereo track.
            with tempfile.TemporaryDirectory(prefix='morphix_') as td:
                normalized = []
                for i, p in enumerate(paths, 1):
                    segment = Path(td) / f'segment_{i:04}.mp4'
                    probe = subprocess.run([ffmpeg, '-hide_banner', '-i', p],
                                           capture_output=True, text=True, errors='replace')
                    has_audio = 'Audio:' in probe.stderr
                    base = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', p]
                    if not has_audio:
                        base += ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']
                    base += ['-map', '0:v:0', '-map', '0:a:0' if has_audio else '1:a:0',
                             '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,'
                                    'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30',
                             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                             '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '44100',
                             '-ac', '2', '-b:a', '160k', '-shortest', str(segment)]
                    run_command(base)
                    normalized.append(segment)
                    update(i, len(paths) + 1)
                playlist = Path(td) / 'list.txt'
                playlist.write_text(''.join(f"file '{p.as_posix()}'\n" for p in normalized), encoding='utf-8')
                out = unique_path(out_dir, 'joined_video.mp4')
                run_command([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                             '-f', 'concat', '-safe', '0', '-i', str(playlist),
                             '-c', 'copy', str(out)])
                outputs.append(out)
                progress.emit(100)
        else:
            for i, p in enumerate(paths, 1):
                is_video = action == 'video_mp4'
                ext = '.mp4' if is_video else '.mp3'
                out = unique_path(out_dir, Path(p).stem + '_converted' + ext)
                if is_video:
                    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', p,
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                           '-c:a', 'aac', '-b:a', '160k', str(out)]
                else:
                    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', p,
                           '-vn', '-codec:a', 'libmp3lame', '-q:a', '3', str(out)]
                run_command(cmd)
                outputs.append(out)
                update(i, len(paths))
    elif action == 'office_pdf':
        from office_engine import office_to_pdf
        return office_to_pdf(paths, out_dir, progress.emit)
    else:
        raise RuntimeError('Unsupported action')
    return outputs

