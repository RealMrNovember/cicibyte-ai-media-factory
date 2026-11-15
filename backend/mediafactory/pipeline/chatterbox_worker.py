"""Runs inside the separate Chatterbox virtualenv (torch lives there, not in the app).

Usage:
  <chatterbox-python> chatterbox_worker.py --serve   one JSON request per stdin line, one JSON reply per stdout line;
                                                     the model loads once and stays in memory until stdin closes.
  <chatterbox-python> chatterbox_worker.py < req.json   a single request.
A request is {"text", "language", "out", "reference"?, "exaggeration"?, "cfg_weight"?, "threads"?}; the reply is
{"ok": true, "seconds": <audio length>} or {"ok": false, "error": "..."}.
Long text is synthesised in ~250 character chunks (the model is tuned for short passages) and joined.
A "reference" WAV clones that voice; its conditioning is computed once and cached.
"""

import json
import os
import re
import sys


def _chunks(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text) if p.strip()]
    chunks, buf = [], ""
    for p in parts:
        if buf and len(buf) + len(p) > 250:
            chunks.append(buf)
            buf = p
        else:
            buf = f"{buf} {p}".strip()
    return chunks + [buf] if buf else chunks


class Engine:
    def __init__(self, threads: int, device: str = "cpu") -> None:
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        torch.set_num_threads(threads)
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch, self.device = torch, device
        self.model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        self.default_conds = self.model.conds
        self.refs: dict[tuple[str, float], object] = {}

    def _condition(self, reference: str | None, exaggeration: float) -> None:
        if not reference:
            self.model.conds = self.default_conds
            return
        key = (reference, os.path.getmtime(reference))
        if key not in self.refs:
            self.model.prepare_conditionals(reference, exaggeration=exaggeration)
            self.refs = {key: self.model.conds}  # keep only the latest voice: conditioning is small but adds up
        self.model.conds = self.refs[key]

    def run(self, req: dict) -> dict:
        import torchaudio as ta

        torch, model = self.torch, self.model
        exaggeration = float(req.get("exaggeration", 0.5))
        self._condition(req.get("reference"), exaggeration)
        gap = torch.zeros(1, int(model.sr * 0.18))
        pieces = []
        with torch.inference_mode():
            for c in _chunks(req["text"]):
                wav = model.generate(c, language_id=req.get("language", "en"), exaggeration=exaggeration,
                                     cfg_weight=float(req.get("cfg_weight", 0.5)))  # fmt: skip
                pieces += [wav.detach().cpu(), gap]  # on the GPU the audio comes back as a CUDA tensor
        if not pieces:
            raise ValueError("no text to speak")
        wav = torch.cat(pieces[:-1], dim=-1)
        ta.save(req["out"], wav, model.sr, encoding="PCM_S", bits_per_sample=16)  # 16-bit PCM: readable by `wave`
        return {"ok": True, "seconds": wav.shape[-1] / model.sr}


def _safe(engine_box: list, req: dict) -> dict:
    try:
        if not engine_box:
            engine_box.append(Engine(int(req.get("threads", 8))))
        return engine_box[0].run(req)
    except Exception as exc:  # report, never hang the caller
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}


def main() -> None:
    box: list = []
    if "--serve" in sys.argv:
        for line in sys.stdin:
            if line.strip():
                print(json.dumps(_safe(box, json.loads(line))), flush=True)
        return
    print(json.dumps(_safe(box, json.loads(sys.stdin.read()))))


if __name__ == "__main__":
    main()
