import os, json, hashlib, sys
import numpy as np
import onnxruntime as ort

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            h.update(data)
    return h.hexdigest()

def detect_quantization(model_path):
    # Load ONNX model and inspect node types for quantization patterns
    try:
        import onnx
        model = onnx.load(model_path)
        ops = [node.op_type for node in model.graph.node]
        if any(op.startswith('QLinear') for op in ops):
            return 'int8 static (QLinear)'
        if any(op in ('QuantizeLinear', 'DequantizeLinear') for op in ops):
            return 'int8 dynamic (QDQ)'
    except Exception:
        pass
    return 'fp32'
    # Look at node op types
    static_int8 = any(op.op_type.startswith('QLinear') for op in session.get_modelmeta().graph.node) if hasattr(session.get_modelmeta().graph, 'node') else False
    # onnxruntime does not expose graph nodes directly; fallback to inspecting model file via onnx
    try:
        import onnx
        model = onnx.load(session._model_path)
        ops = [node.op_type for node in model.graph.node]
        if any(op.startswith('QLinear') for op in ops):
            return 'int8 static (QLinear)'
        if any(op in ('QuantizeLinear', 'DequantizeLinear') for op in ops):
            return 'int8 dynamic (QDQ)'
    except Exception:
        pass
    return 'fp32'

def run_dummy(session):
    input_names = [inp.name for inp in session.get_inputs()]
    dummy_inputs = {}
    for inp in session.get_inputs():
        shape = [dim if isinstance(dim, int) else 1 for dim in inp.shape]
        dtype = np.float32 if inp.type.startswith('tensor(float') else np.int8
        dummy = np.zeros(shape, dtype=dtype)
        dummy_inputs[inp.name] = dummy
    outputs = session.run(None, dummy_inputs)
    return outputs

model_paths = [
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\sam2\\sam2.1_hiera_base_plus.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\mobilesam\\mobile_sam.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\dino_leaf_filter\\dino_leaf_filter.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\dino_leaf_filter\\dino_leaf_filter_v2.pt",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_leaf_filter\\onnx\\dino_leaf_filter_fp32_224.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_leaf_filter\\onnx_int8\\dino_leaf_filter_dynamic_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_disease\\onnx\\dino_disease_fp32_224.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_disease\\onnx_int8\\dino_disease_dynamic_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\dino_disease\\onnx_selective_int8\\dino_disease_mlp_int8.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\segformer\\onnx\\segformer_fp32_512.onnx",
    r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts\\optimized\\segformer\\onnx_int8\\segformer_dynamic_int8.onnx",
]

results = []
for path in model_paths:
    if not os.path.exists(path):
        results.append({"path": path, "error": "File not found"})
        continue
    try:
        sess = ort.InferenceSession(path, providers=['CPUExecutionProvider'])
        inputs = [{"name": i.name, "shape": i.shape, "type": i.type} for i in sess.get_inputs()]
        outputs = [{"name": o.name, "shape": o.shape, "type": o.type} for o in sess.get_outputs()]
        quant = detect_quantization(sess)
        # dummy run
        try:
            run_dummy(sess)
            dummy_status = "ok"
        except Exception as e:
            dummy_status = f"failed: {e}"
        results.append({"path": path, "sha256": sha256(path), "precision": quant, "inputs": inputs, "outputs": outputs, "dummy": dummy_status})
    except Exception as e:
        results.append({"path": path, "error": str(e)})

print(json.dumps(results, indent=2))

