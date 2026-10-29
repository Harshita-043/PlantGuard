import sys, importlib
mods = ['torch','torchvision','transformers','onnxruntime','sam2','mobile_sam','cv2','fastapi','sqlalchemy','alembic','psycopg','jwt']
print('Python', sys.version.split('\n')[0])
for m in mods:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, '__version__', 'unknown')
        print(m, ver)
    except Exception as e:
        print(m, 'IMPORT_ERROR', e)
try:
    import onnxruntime as ort
    print('onnxruntime providers', ort.get_available_providers())
except Exception as e:
    print('onnxruntime providers error', e)

