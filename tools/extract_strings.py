import ast, sys, pathlib, json
root = pathlib.Path(__file__).resolve().parents[1]
found = {}
def lit(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str): return node.value
    return None
for f in root.glob('*.py'):
    tree = ast.parse(f.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
            if name in ('tr', '_t') and node.args:
                v = lit(node.args[0])
                if v: found.setdefault(v, set()).add(f.name)
            if name == 'trl' and len(node.args) > 1:
                v = lit(node.args[1])
                if v: found.setdefault(v, set()).add(f.name)
# data tables translated at display
import importlib
sys.path.insert(0, str(root))
src = (root/'quickwheel.py').read_text()
mod = ast.parse(src)
for node in mod.body:
    if isinstance(node, ast.Assign) and node.targets[0].id in ('PROFILES','WHEEL_LABELS'):
        d = ast.literal_eval(node.value)
        for k,v in d.items(): found.setdefault(v[0], set()).add('quickwheel tables')
for node in ast.parse((root/'main.py').read_text()).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0],'id','')=='ACTIONS':
        for v in ast.literal_eval(node.value).values(): found.setdefault(v,set()).add('ACTIONS')
for node in ast.parse((root/'hub_panel.py').read_text()).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0],'id','') in ('SHAPE_LABELS','POSITION_LABELS'):
        for v in ast.literal_eval(node.value).values(): found.setdefault(v,set()).add('hub')
for node in ast.parse((root/'wheel_preferences.py').read_text()).body:
    if isinstance(node, ast.ClassDef):
        for b in node.body:
            if isinstance(b, ast.Assign) and getattr(b.targets[0],'id','')=='PAGES':
                for v in ast.literal_eval(b.value): found.setdefault(v,set()).add('prefs')
for node in ast.parse((root/'compression_dialog.py').read_text()).body:
    if isinstance(node, ast.ClassDef):
        for b in node.body:
            if isinstance(b, ast.Assign) and getattr(b.targets[0],'id','')=='PRESETS':
                for v,_ in ast.literal_eval(b.value): found.setdefault(v,set()).add('compress')
te_src = ast.parse((root/'transcription_engine.py').read_text())
for node in te_src.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0],'id','')=='MODELS':
        for v in ast.literal_eval(node.value).values(): found.setdefault(v[2],set()).add('models')
for t in ['Text (.txt)','Text + times','Subtitles (.srt)','WebVTT']: found.setdefault(t,set()).add('fmt')
STRINGS = found

