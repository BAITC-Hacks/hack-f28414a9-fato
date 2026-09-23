from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def _transcribe(path: Path) -> tuple[list[dict[str, Any]], str, str]:
    from faster_whisper import WhisperModel

    model_name = os.getenv("WHISPER_MODEL", "small")
    model = WhisperModel(
        model_name,
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    )
    segments, info = model.transcribe(str(path), beam_size=5, vad_filter=True, word_timestamps=False)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    return rows, info.language or "unknown", model_name


def _diarize(path: Path, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    if os.getenv("ENABLE_DIARIZATION", "false").lower() != "true":
        for item in segments:
            item["speaker"] = "Говорящий 1"
        return segments, "Диаризация отключена; весь текст помечен как «Говорящий 1»."
    try:
        import torch
        from pyannote.audio import Pipeline

        token = os.getenv("HF_TOKEN")
        kwargs = {"use_auth_token": token} if token else {}
        pipeline = Pipeline.from_pretrained(os.getenv("DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1"), **kwargs)
        if pipeline is None:
            raise RuntimeError("модель pyannote не загружена")
        if os.getenv("WHISPER_DEVICE", "cpu").startswith("cuda"):
            pipeline.to(torch.device("cuda"))
        diarization = pipeline(str(path))
        turns = [(turn.start, turn.end, speaker) for turn, _, speaker in diarization.itertracks(yield_label=True)]
        for item in segments:
            mid = (item["start"] + item["end"]) / 2
            candidates = [(min(end, item["end"]) - max(start, item["start"]), speaker)
                          for start, end, speaker in turns if start <= mid <= end]
            item["speaker"] = max(candidates, default=(0, "SPEAKER_00"))[1]
        labels = sorted({x["speaker"] for x in segments})
        mapping = {label: f"Говорящий {i + 1}" for i, label in enumerate(labels)}
        for item in segments:
            item["speaker"] = mapping[item["speaker"]]
        return segments, "Диаризация выполнена локальной моделью pyannote.audio."
    except Exception as exc:
        for item in segments:
            item["speaker"] = "Говорящий 1"
        return segments, f"Диаризация недоступна; назначен один говорящий. Детали: {exc}"


def _extract_tasks(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Deliberately conservative MVP: capture explicit assignment language and preserve
    # the source phrase so a human can review inferred names and dates.
    pattern = re.compile(
        r"\b(поручаю|поручить|нужно|надо|необходимо|сделай(?:те)?|подготовь(?:те)?|"
        r"отправь(?:те)?|проверь(?:те)?|обеспечь(?:те)?|жауапты|тапсыр(?:ма|ыңыз)?|"
        r"дайында(?:ңыз)?|жаса(?:ңыз)?|жібер(?:іңіз)?)\b", re.I
    )
    deadline = re.compile(r"(?:до|к|дедлайн\s*[:—-]?|срок\s*[:—-]?|дейін|мерзімі\s*[:—-]?)\s*([^,.;\n]{2,35})", re.I)
    tasks = []
    for segment in segments:
        text = segment["text"].strip()
        if not pattern.search(text):
            continue
        responsible = "Не определён"
        match = re.search(r"(?:^|[,;]\s*|поручаю\s+)([А-ЯЁӘІҢҒҮҰҚӨҺA-Z][а-яёәіңғүұқөһa-z-]+(?:\s+[А-ЯЁӘІҢҒҮҰҚӨҺA-Z][а-яёәіңғүұқөһa-z-]+)?)\s*[,—:]", text)
        if match:
            responsible = match.group(1).strip()
        due_match = deadline.search(text)
        due = due_match.group(1).strip() if due_match else "Не указан"
        task = re.sub(r"^(?:ну|так|значит)[,\s]+", "", text, flags=re.I)
        task = re.sub(r"\s+", " ", task)
        tasks.append({"task": task, "responsible": responsible, "deadline": due,
                      "source": text, "speaker": segment.get("speaker", "Говорящий 1"),
                      "timestamp": segment.get("start", 0)})
    return tasks


def process_recording(path: Path, filename: str) -> dict[str, Any]:
    segments, language, model_name = _transcribe(path)
    if not segments:
        raise RuntimeError("В записи не распознана речь")
    segments, diarization_status = _diarize(path, segments)
    transcript = " ".join(s["text"] for s in segments)
    tasks = _extract_tasks(segments)
    summary = transcript[:700].rstrip()
    if len(transcript) > 700:
        summary += "…"
    return {
        "filename": filename, "language": language, "model": model_name,
        "summary": summary or "Краткое содержание не сформировано.",
        "transcript": segments, "tasks": tasks,
        "diarization_status": diarization_status,
        "notes": ["Саммари в MVP — начальные 700 символов транскрипта.",
                  "Поручения выделяются по ключевым словам; ответственного и срок проверьте вручную."],
    }

