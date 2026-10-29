import os, glob, json, hashlib
import numpy as np
import onnxruntime as ort

# Helper to compute SHA‑256 of a file
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# Detect simple quantization patterns via onnx ops
def detect_quantization(onnx_path):
    try:
        import onnx
        model = onnx.load(onnx_path)
        ops = [n.op_type for n in model.graph.node]
        if any(op.startswith("QLinear") for op in ops):
            return "int8 static (QLinear)"
        if any(op in ("QuantizeLinear", "DequantizeLinear") for op in ops):
            return "int8 dynamic (QDQ)"
    except Exception:
        pass
    return "fp32"

# Run a dummy inference (zeros) to ensure the session works
def run_dummy(session):
    dummy_inputs = {}
    for inp in session.get_inputs():
        shape = [d if isinstance(d, int) else 1 for d in inp.shape]
        dtype = np.float32 if inp.type.startswith("tensor(float") else np.int8
        dummy_inputs[inp.name] = np.zeros(shape, dtype=dtype)
    session.run(None, dummy_inputs)

# Find all ONNX models under artifacts
root = r"C:\\Users\\Asus\\PLANTGUARD AI\\artifacts"
onnx_files = glob.glob(os.path.join(root, "**", "*.onnx"), recursive=True)
results = []
for path in onnx_files:
    try:
        sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        inputs = [{"name": i.name, "shape": i.shape, "type": i.type} for i in sess.get_inputs()]
        outputs = [{"name": o.name, "shape": o.shape, "type": o.type} for o in sess.get_outputs()]
        quant = detect_quantization(path)
        try:
            run_dummy(sess)
            dummy = "ok"
        except Exception as e:
            dummy = f"failed: {e}"
        results.append({"path": path, "sha256": sha256(path), "precision": quant, "inputs": inputs, "outputs": outputs, "dummy": dummy})
    except Exception as e:
        results.append({"path": path, "error": str(e)})

print(json.dumps(results, indent=2))