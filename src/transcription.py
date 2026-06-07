from __future__ import annotations

from typing import Any, Literal


MLX_WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
FASTER_WHISPER_MODEL = "small.en"

AsrProvider = Literal["auto", "mlx_whisper", "faster_whisper"]


def transcribe_with_mlx(path: str, model: str = MLX_WHISPER_MODEL) -> dict[str, Any]:
    try:
        import mlx_whisper

        result = mlx_whisper.transcribe(path, path_or_hf_repo=model)
    except Exception as exc:  # noqa: BLE001 - model/runtime failures are UI-facing setup errors.
        return _failure("mlx_whisper", model, exc)

    text = str(result.get("text", "")).strip() if isinstance(result, dict) else ""
    if not text:
        return _failure("mlx_whisper", model, RuntimeError("MLX Whisper returned an empty transcript."))

    return {
        "ok": True,
        "provider": "mlx_whisper",
        "model": model,
        "text": text,
        "segments": result.get("segments", []) if isinstance(result, dict) else [],
        "language": result.get("language") if isinstance(result, dict) else None,
        "error": None,
        "fallback_errors": [],
    }


def transcribe_with_faster_whisper(path: str, model_size: str = FASTER_WHISPER_MODEL) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(path, beam_size=5, vad_filter=True)
        segments = list(segments_iter)
    except Exception as exc:  # noqa: BLE001 - model/runtime failures are UI-facing setup errors.
        return _failure("faster_whisper", model_size, exc)

    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
    if not text:
        return _failure("faster_whisper", model_size, RuntimeError("faster-whisper returned an empty transcript."))

    return {
        "ok": True,
        "provider": "faster_whisper",
        "model": model_size,
        "text": text,
        "segments": [
            {
                "start": getattr(segment, "start", None),
                "end": getattr(segment, "end", None),
                "text": segment.text,
            }
            for segment in segments
        ],
        "language": getattr(info, "language", None),
        "error": None,
        "fallback_errors": [],
    }


def transcribe_audio(
    path: str,
    provider: AsrProvider = "auto",
    mlx_model: str = MLX_WHISPER_MODEL,
    faster_model: str = FASTER_WHISPER_MODEL,
) -> dict[str, Any]:
    if provider == "mlx_whisper":
        return transcribe_with_mlx(path, mlx_model)
    if provider == "faster_whisper":
        return transcribe_with_faster_whisper(path, faster_model)
    if provider != "auto":
        return _failure(str(provider), "", RuntimeError(f"Unsupported ASR provider: {provider}"))

    primary = transcribe_with_mlx(path, mlx_model)
    if primary["ok"]:
        return primary

    backup = transcribe_with_faster_whisper(path, faster_model)
    backup["fallback_errors"] = [primary["error"]] if primary.get("error") else []
    return backup


def _failure(provider: str, model: str, exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "provider": provider,
        "model": model,
        "text": "",
        "segments": [],
        "language": None,
        "error": str(exc),
        "fallback_errors": [],
    }
