The Qwen2.5-Omni is able to run on the AMD ROCm GPU include Radeon and Instinct. 

ROCm is an open-source software platform optimized to extract HPC and AI workload performance from AMD Instinct accelerators and AMD Radeon GPUs while maintaining compatibility with industry software frameworks. For more information, see [What is ROCm](https://rocm.docs.amd.com/en/latest/what-is-rocm.html)? 

The ROCm stack could be deployed by python virtualenv or container. Let's use the two ways to run Qwen2.5-Omni on AMD Radeon GPU and Instinct GPU on Ubuntu24.04.

| Env               | GPU |
| :---------------- | :------: |
| Conda             |   AMD Radeon PRO W7900  |
| Container         |   AMD Instinct MI300X   |

# Prerequisite

## Download the model

```shell
huggingface-cli login --token <your HF token>
huggingface-cli download  Qwen/Qwen2.5-Omni-7B --local-dir Qwen/Qwen2.5-Omni-7B
```

## Install the AMD GPU driver
You should install the GPU driver for both ways. Please follow the instructions from https://rocm.docs.amd.com/projects/install-on-linux/en/latest/install/quick-start.html to install it.

For ubuntu24.04

```shell
sudo apt update
sudo apt install "linux-headers-$(uname -r)" "linux-modules-extra-$(uname -r)"
sudo apt install python3-setuptools python3-wheel
sudo usermod -a -G render,video $LOGNAME # Add the current user to the render and video groups
wget https://repo.radeon.com/amdgpu-install/6.3.3/ubuntu/noble/amdgpu-install_6.3.60303-1_all.deb
sudo apt install ./amdgpu-install_6.3.60303-1_all.deb
sudo apt update
sudo apt install amdgpu-dkms
```

(you should install the driver according which Linux version of yours)

# WAY-1 Run with conda on Radeon PRO W7900
Create the conda env and install the PyTorch of ROCm

```shell
yes | conda create -t qomni python=3.11
conda activate qomni
pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.3
```

Clone the repo and install the packages for the demo

```shell
https://github.com/QwenLM/Qwen2.5-Omni.git
cd Qwen2.5-Omni
pip install -r requirements_web_demo.txt

# It's highly recommended to use `[decord]` feature for faster video loading.
pip install qwen-omni-utils[decord]
```

Run the webui demo

(Please use the real path of Qwen2.5-Omni-7B to replace [mode_path] in the command)

```shell
python web_demo.py -c <model_path>

```

Then open the webui by http://127.0.0.1:7860 in browser. (You may set the permission in browser to use microphone and camera)


# WAY-2 Run with container on MI300X

The Qwen2.5-Omni could be accelerated by flash-attention_2(FA2). AMD provides the out-of-box docker images with PyTorch and FA2 pre-installed.

Pull the docker image from https://hub.docker.com/r/rocm/vllm-dev

```shell
docker pull rocm/vllm-dev:main
```

Start the container

```shell
docker run -it --network=host --device=/dev/kfd --device=/dev/dri \
--group-add=video --ipc=host --cap-add=SYS_PTRACE \
--security-opt seccomp=unconfined --shm-size 8G \
-v $HOME:/ws -w /ws \
rocm/vllm-dev:main
```

Check the environment

```shell
# pip list | grep torch
torch                   2.4.0a0+git7cecbf6
torchvision             0.19.0a0+fab8488

# pip list | grep flash_attn
flash_attn                        2.7.2
```

Check out the repo and install the dependency

```shell
git clone https://github.com/QwenLM/Qwen2.5-Omni.git
cd Qwen2.5-Omni
pip install -r requirements_web_demo.txt
```

Use HIP_VISIBLE_DEVICES to set which GPU to run the demo.

(Please use the real path of Qwen2.5-Omni-7B to replace [mode_path] in the command)

```shell
HIP_VISIBLE_DEVICES=7 python web_demo.py -c [model_path] --flash-attn2
```

The model will be loaded with FA2. Then test it in browser as WAY-1.


# Reference

[https://rocm.docs.amd.com/projects/radeon/en/latest/index.html](https://rocm.docs.amd.com/en/latest/)

[https://github.com/QwenLM/Qwen2.5-Omni/](https://github.com/QwenLM/Qwen2.5-Omni/blob/main/README.md)

