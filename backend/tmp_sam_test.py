import traceback, sys
from app.ml.adapters.sam_adapter import Sam2LeafSegmentationAdapter

def main():
    try:
        adapter = Sam2LeafSegmentationAdapter()
        print('Adapter instantiated')
        loaded = adapter.load(target_device='cpu')
        print('Loaded:', loaded)
        print('Status:', adapter.loading_status)
    except Exception as e:
        print('Error:', e)
        traceback.print_exc()

if __name__ == '__main__':
    main()
