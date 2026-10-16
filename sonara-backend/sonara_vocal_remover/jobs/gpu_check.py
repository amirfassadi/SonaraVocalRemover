"""Explicit GPU diagnostic: execute a CUDA kernel, then report visible memory."""
import json


def inspect_gpu(torch):
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable. Check the host driver, container GPU access and PyTorch wheel variant.')
    device = torch.device('cuda:0')
    # Device detection alone does not prove that this wheel can execute kernels.
    values = torch.ones((32, 32), device=device)
    result = values @ values
    torch.cuda.synchronize(device)
    if float(result[0, 0].item()) != 32.0:
        raise RuntimeError('CUDA matrix multiplication returned an unexpected result.')
    properties = torch.cuda.get_device_properties(device)
    free, total = torch.cuda.mem_get_info(device)
    return {'ready': True, 'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
            'device': properties.name, 'compute_capability': list(torch.cuda.get_device_capability(device)),
            'total_vram_gib': round(total / 1024**3, 2), 'free_vram_gib': round(free / 1024**3, 2),
            'kernel_test': 'passed', 'note': 'This is not a model-memory or inference benchmark.'}


def main():
    try:
        import torch
        result = inspect_gpu(torch)
    except Exception as exc:
        print(json.dumps({'ready': False, 'error': str(exc)}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
