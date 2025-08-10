import torch
import nvdiffrast.torch as dr  # triggers build into torch_extensions cache
print("Torch:", torch.__version__, "CUDA:", torch.version.cuda)
from torch.utils.cpp_extension import get_default_build_root
print("torch_extensions cache:", get_default_build_root())
