import os, json, hashlib, torch, onnxruntime as ort, sys
from safetensors.torch import load_file

model_paths = [
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\dino_disease\\dino_disease_classifier.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\dino_leaf_filter\\dino_leaf_filter.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\dino_leaf_filter\\dino_leaf_filter_v2.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\mobilesam\\mobile_sam.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_disease\\onnx\\dino_disease_fp32_224.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_disease\\onnx_int8\\dino_disease_dynamic_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_disease\\onnx_selective_int8\\dino_disease_mlp_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_leaf_filter\\onnx\\dino_leaf_filter_fp32_224.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_leaf_filter\\onnx_int8\\dino_leaf_filter_dynamic_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\segformer\\onnx\\segformer_fp32_512.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\segformer\\onnx_int8\\segformer_dynamic_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\sam2\\sam2.1_hiera_base_plus.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\outputs\\segformer_plantseg\\best_model\\model.safetensors",
]

results = []
for p in model_paths:
    info = {'path': p}
    try:
        size = os.path.getsize(p)
        info['size_bytes'] = size
    except Exception as e:
        info['size_error'] = str(e)
        results.append(info)
        continue
    # sha256
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    info['sha256'] = h.hexdigest()
    ext = os.path.splitext(p)[1].lower()
    info['format'] = ext
    # framework inference
    if ext in ['.pt', '.pth']:
        info['framework'] = 'pytorch'
    elif ext == '.safetensors':
        info['framework'] = 'pytorch (safetensors)'
    elif ext == '.onnx':
        info['framework'] = 'onnxruntime'
    else:
        info['framework'] = 'unknown'
    # pipeline stage guess
    name = os.path.basename(p).lower()
    if 'sam2' in name or 'sam' in name:
        info['pipeline_stage'] = 'segmentation (SAM)'
    elif 'leaf_filter' in name:
        info['pipeline_stage'] = 'leaf filter'
    elif 'disease' in name:
        info['pipeline_stage'] = 'disease classifier'
    elif 'segformer' in name:
        info['pipeline_stage'] = 'lesion segmentation'
    else:
        info['pipeline_stage'] = 'unknown'
    # precision
    if 'int8' in p.lower():
        if 'dynamic' in p.lower():
            info['precision'] = 'int8 dynamic'
        elif 'static' in p.lower() or 'selective' in p.lower():
            info['precision'] = 'int8 static'
        else:
            info['precision'] = 'int8'
    elif 'fp32' in p.lower() or p.lower().endswith('.pt'):
        info['precision'] = 'fp32'
    else:
        info['precision'] = 'unknown'
    # load test
    try:
        if ext in ['.pt', '.pth']:
            ckpt = torch.load(p, map_location='cpu')
            info['load_test'] = 'loaded pytorch checkpoint'
        elif ext == '.safetensors':
            ckpt = load_file(p)
            info['load_test'] = 'loaded safetensors'
        elif ext == '.onnx':
            sess = ort.InferenceSession(p)
            inputs = []
            for i in sess.get_inputs():
                shape = [dim if isinstance(dim, int) else 1 for dim in i.shape]
                inputs.append({'name': i.name, 'shape': shape, 'type': i.type})
            info['load_test'] = {'onnx_inputs': inputs}
        else:
            info['load_test'] = 'unsupported format'
    except Exception as e:
        info['load_test'] = f'error: {e}'
    results.append(info)

print(json.dumps(results, indent=2))

