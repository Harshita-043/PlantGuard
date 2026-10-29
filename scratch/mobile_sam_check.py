import importlib, sys
mods = ['mobile_sam']
for m in mods:
    try:
        mod = importlib.import_module(m)
        print(m, 'imported', getattr(mod, '__file__', ''))
    except Exception as e:
        print(m, 'IMPORT_ERROR', e)

