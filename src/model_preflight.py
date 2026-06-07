from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import importlib.util
import json
from typing import Any
import urllib.request
from urllib.error import HTTPError, URLError


DEFAULT_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class PreflightResult:
    name: str
    ready: bool
    message: str
    action: str = ""
    provider: str | None = None
    model: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ready": self.ready,
            "message": self.message,
            "action": self.action,
            "provider": self.provider,
            "model": self.model,
            "details": self.details,
        }


def check_streamlit_audio_available() -> PreflightResult:
    try:
        streamlit = importlib.import_module("streamlit")
    except ImportError as exc:
        return PreflightResult(
            name="Streamlit audio input",
            ready=False,
            message="Streamlit is not installed, so microphone readiness cannot be checked.",
            action="pip install -r requirements.txt",
            details={"error": str(exc)},
        )

    if hasattr(streamlit, "audio_input"):
        version = getattr(streamlit, "__version__", "unknown")
        return PreflightResult(
            name="Streamlit audio input",
            ready=True,
            message=f"Streamlit audio input is available. Version: {version}.",
            details={"version": version},
        )

    version = getattr(streamlit, "__version__", "unknown")
    return PreflightResult(
        name="Streamlit audio input",
        ready=False,
        message=f"Streamlit is installed, but st.audio_input is unavailable. Version: {version}.",
        action="pip install 'streamlit>=1.40'",
        details={"version": version},
    )


def check_mlx_whisper_import() -> PreflightResult:
    return _check_runtime_import(
        module_name="mlx_whisper",
        display_name="MLX Whisper",
        install_action="pip install mlx-whisper mlx",
        runtime_action="Run the app from a normal macOS session with Apple Metal/GPU access, or use faster-whisper as the real ASR backup.",
        provider="mlx_whisper",
        model="mlx-community/whisper-large-v3-turbo",
    )


def check_faster_whisper_import() -> PreflightResult:
    return _check_runtime_import(
        module_name="faster_whisper",
        display_name="faster-whisper",
        install_action="pip install faster-whisper",
        runtime_action="Reinstall faster-whisper in the active virtual environment.",
        provider="faster_whisper",
        model="small.en",
    )


def check_ollama_model(
    base_url: str = "http://localhost:11434",
    model: str = "qwen3:8b",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> PreflightResult:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        payload = _get_json(url, timeout)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as setup guidance.
        return PreflightResult(
            name="Ollama model",
            ready=False,
            message=f"Ollama is not reachable at {base_url}.",
            action="ollama serve\nollama pull qwen3:8b",
            provider="ollama",
            model=model,
            details={"error": str(exc), "url": url},
        )

    available = _ollama_model_names(payload)
    if model in available:
        return PreflightResult(
            name="Ollama model",
            ready=True,
            message=f"Ollama model is available: {model}.",
            provider="ollama",
            model=model,
            details={"available_models": sorted(available), "url": url},
        )

    return PreflightResult(
        name="Ollama model",
        ready=False,
        message=f"Ollama is running, but {model} is not pulled.",
        action=f"ollama pull {model}",
        provider="ollama",
        model=model,
        details={"available_models": sorted(available), "url": url},
    )


def check_lm_studio_model(
    base_url: str = "http://localhost:1234/v1",
    model: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> PreflightResult:
    url = _lm_studio_models_url(base_url)
    try:
        payload = _get_json(url, timeout)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as setup guidance.
        return PreflightResult(
            name="LM Studio model",
            ready=False,
            message=f"LM Studio is not reachable at {base_url}.",
            action="Start LM Studio, load a local model, and enable the local server.",
            provider="lm_studio",
            model=model or None,
            details={"error": str(exc), "url": url},
        )

    available = _lm_studio_model_ids(payload)
    if not available:
        return PreflightResult(
            name="LM Studio model",
            ready=False,
            message="LM Studio is reachable, but no local model is exposed.",
            action="Load a model in LM Studio and start the local server.",
            provider="lm_studio",
            model=model or None,
            details={"url": url},
        )

    if model and model not in available:
        return PreflightResult(
            name="LM Studio model",
            ready=False,
            message=f"LM Studio is running, but {model} is not exposed.",
            action="Select one of the loaded LM Studio model IDs.",
            provider="lm_studio",
            model=model,
            details={"available_models": sorted(available), "url": url},
        )

    selected = model or sorted(available)[0]
    return PreflightResult(
        name="LM Studio model",
        ready=True,
        message=f"LM Studio model is available: {selected}.",
        provider="lm_studio",
        model=selected,
        details={"available_models": sorted(available), "url": url},
    )


def _check_runtime_import(
    module_name: str,
    display_name: str,
    install_action: str,
    runtime_action: str,
    provider: str,
    model: str,
) -> PreflightResult:
    if importlib.util.find_spec(module_name) is None:
        return PreflightResult(
            name=display_name,
            ready=False,
            message=f"{display_name} is not installed.",
            action=install_action,
            provider=provider,
            model=model,
        )

    try:
        importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - import can fail from native runtime setup.
        return PreflightResult(
            name=display_name,
            ready=False,
            message=f"{display_name} is installed, but it failed to import in this process.",
            action=runtime_action,
            provider=provider,
            model=model,
            details={"error": str(exc)},
        )

    return PreflightResult(
        name=display_name,
        ready=True,
        message=f"{display_name} can be imported.",
        provider=provider,
        model=model,
    )


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected JSON shape from {url}")
    return parsed


def _ollama_model_names(payload: dict[str, Any]) -> set[str]:
    models = payload.get("models", [])
    names: set[str] = set()
    if not isinstance(models, list):
        return names

    for item in models:
        if not isinstance(item, dict):
            continue
        for key in ("name", "model"):
            value = item.get(key)
            if isinstance(value, str) and value:
                names.add(value)
    return names


def _lm_studio_model_ids(payload: dict[str, Any]) -> set[str]:
    models = payload.get("data", [])
    names: set[str] = set()
    if not isinstance(models, list):
        return names

    for item in models:
        if not isinstance(item, dict):
            continue
        value = item.get("id")
        if isinstance(value, str) and value:
            names.add(value)
    return names


def _lm_studio_models_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/models"
    return f"{normalized}/v1/models"
