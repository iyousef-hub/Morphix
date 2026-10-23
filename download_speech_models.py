"""One-time download of Morphix speech models (needs internet once).

    python download_speech_models.py            # accurate (large-v3-turbo)
    python download_speech_models.py fast       # small, faster
    python download_speech_models.py all
After this, Speech -> Text works without internet.
"""
import sys
import transcription_engine as te

wanted = sys.argv[1:] or [te.DEFAULT_QUALITY]
if wanted == ['all']:
    wanted = list(te.MODELS)
for quality in wanted:
    if quality not in te.MODELS:
        sys.exit(f'Unknown model "{quality}". Choose: {", ".join(te.MODELS)} or all')
    if te.model_dir(quality):
        print(f'✓ {te.MODELS[quality][2]} already installed: {te.model_dir(quality)}')
        continue
    print(f'Downloading {te.MODELS[quality][2]} ({te.MODELS[quality][1]}) …')
    print('✓ Installed:', te.download_model(quality, status_cb=print))
