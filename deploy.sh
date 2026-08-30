#!/usr/bin/env bash
# 安装本仓库运行所需的系统库与 Python 依赖。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT}/.venv"
REQ_FILE="${ROOT}/requirements.txt"
PYTHON_BIN="${PYTHON:-python3}"
USE_VENV=1
INSTALL_SYSTEM_DEPS=1
PIP_INDEX_URL="${PIP_INDEX_URL:-}"
PIP_EXTRA_INDEX_URL="${PIP_EXTRA_INDEX_URL:-}"
MIRROR=""

usage() {
  cat <<'EOF'
用法: ./deploy.sh [选项]

选项:
  --no-venv          不创建虚拟环境，直接用当前 Python 安装依赖
  --skip-system      跳过 apt 系统库（libportaudio2 等）
  --mirror <name>    使用国内 PyPI 镜像: tsinghua | aliyun | tencent
  --python <path>    指定 Python 解释器（默认 python3）
  -h, --help         显示帮助

环境变量:
  PYTHON             同 --python
  PIP_INDEX_URL      自定义 PyPI 源
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-venv) USE_VENV=0; shift ;;
    --skip-system) INSTALL_SYSTEM_DEPS=0; shift ;;
    --mirror)
      MIRROR="${2:-}"
      if [[ -z "${MIRROR}" ]]; then
        echo "错误: --mirror 需要参数 (tsinghua|aliyun|tencent)" >&2
        exit 1
      fi
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      if [[ -z "${PYTHON_BIN}" ]]; then
        echo "错误: --python 需要解释器路径" >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "未知参数: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "${MIRROR}" in
  "") ;;
  tsinghua) PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple" ;;
  aliyun) PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple" ;;
  tencent) PIP_INDEX_URL="https://mirrors.cloud.tencent.com/pypi/simple" ;;
  *)
    echo "错误: 不支持的镜像 '${MIRROR}'，可选 tsinghua|aliyun|tencent" >&2
    exit 1
    ;;
esac

if [[ ! -f "${REQ_FILE}" ]]; then
  echo "错误: 找不到 ${REQ_FILE}" >&2
  exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "错误: 找不到 Python 解释器: ${PYTHON_BIN}" >&2
  exit 1
fi

PY_VERSION="$("${PYTHON_BIN}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PY_MAJOR="$("${PYTHON_BIN}" -c 'import sys; print(sys.version_info[0])')"
PY_MINOR="$("${PYTHON_BIN}" -c 'import sys; print(sys.version_info[1])')"
if [[ "${PY_MAJOR}" -lt 3 || ( "${PY_MAJOR}" -eq 3 && "${PY_MINOR}" -lt 8 ) ]]; then
  echo "错误: 需要 Python >= 3.8，当前为 ${PY_VERSION}" >&2
  exit 1
fi

install_system_deps() {
  if [[ "${INSTALL_SYSTEM_DEPS}" -eq 0 ]]; then
    echo "==> 跳过系统依赖"
    return
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    echo "==> 未检测到 apt-get，请自行安装 PortAudio（sounddevice 依赖）"
    return
  fi

  local packages=(python3-venv python3-pip libportaudio2 libsndfile1 wget)
  echo "==> 检查系统依赖: ${packages[*]}"

  local missing=()
  local pkg
  for pkg in "${packages[@]}"; do
    if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
      missing+=("${pkg}")
    fi
  done

  if [[ ${#missing[@]} -eq 0 ]]; then
    echo "==> 系统依赖已就绪"
    return
  fi

  echo "==> 需要安装: ${missing[*]}"
  if command -v sudo >/dev/null 2>&1 && [[ "$(id -u)" -ne 0 ]]; then
    sudo apt-get update
    sudo apt-get install -y "${missing[@]}"
  elif [[ "$(id -u)" -eq 0 ]]; then
    apt-get update
    apt-get install -y "${missing[@]}"
  else
    echo "错误: 缺少系统包且无法使用 sudo。请手动安装: ${missing[*]}" >&2
    echo "或使用 --skip-system 跳过此步骤。" >&2
    exit 1
  fi
}

pip_args=()
if [[ -n "${PIP_INDEX_URL}" ]]; then
  pip_args+=(-i "${PIP_INDEX_URL}")
fi
if [[ -n "${PIP_EXTRA_INDEX_URL}" ]]; then
  pip_args+=(--extra-index-url "${PIP_EXTRA_INDEX_URL}")
fi

echo "==> 项目目录: ${ROOT}"
echo "==> Python: ${PYTHON_BIN} (${PY_VERSION})"
install_system_deps

if [[ "${USE_VENV}" -eq 1 ]]; then
  if [[ ! -d "${VENV_DIR}" ]]; then
    echo "==> 创建虚拟环境: ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  else
    echo "==> 复用虚拟环境: ${VENV_DIR}"
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  PYTHON_BIN="${VENV_DIR}/bin/python"
fi

echo "==> 升级 pip"
"${PYTHON_BIN}" -m pip install --upgrade pip setuptools wheel "${pip_args[@]}"

echo "==> 安装 Python 依赖"
"${PYTHON_BIN}" -m pip install -r "${REQ_FILE}" "${pip_args[@]}"

echo "==> 校验导入"
"${PYTHON_BIN}" - <<'PY'
import sherpa_onnx
import sounddevice
import numpy

print("sherpa-onnx:", getattr(sherpa_onnx, "__version__", "ok"))
print("sounddevice:", sounddevice.__version__)
print("numpy:", numpy.__version__)
PY

echo
echo "部署完成。"
if [[ "${USE_VENV}" -eq 1 ]]; then
  echo "激活虚拟环境:  source ${VENV_DIR}/bin/activate"
fi
echo "试运行:  ${PYTHON_BIN} ${ROOT}/speaker.py \"你好，这是语音合成测试\""
