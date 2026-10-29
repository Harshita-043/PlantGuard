import importlib, sys
mods = ["sam2", "mobile_sam"]
for m in mods:
    try:
        lib = importlib.import_module(m)
        print(m, "imported from", getattr(lib, "__file__", "built-in"))
    except Exception as e:
        print(m, "IMPORT_ERROR", e)

