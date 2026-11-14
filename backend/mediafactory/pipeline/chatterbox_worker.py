"""Runs inside the separate Chatterbox virtualenv (torch lives there, not in the app).

Usage: <chatterbox-python> chatterbox_worker.py  < {"text": ..., "language": "tr", "out": "/path.wav", ...}
Prints {"ok": true, "seconds": <audio length>} or {"ok": false, "error": "..."} on stdout.
Long text is synthesised sentence by sentence (the model is tuned for short passages) and joined.
"""

import json
import re
import sys


def main() -> None:
    req = json.loads(sys.stdin.read())
    try:
        import torch
        import torchaudio as ta
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        torch.set_num_threads(int(req.get("threads", 8)))
        model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
        parts = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", req["text"]) if p.strip()]
        chunks, buf = [], ""
        for p in parts:  # group short sentences into ~250 character chunks
            if buf and len(buf) + len(p) > 250:
                chunks.append(buf)
                buf = p
            else:
                buf = f"{buf} {p}".strip()
        if buf:
            chunks.append(buf)
        gap = torch.zeros(1, int(model.sr * 0.18))
        pieces = []
        for c in chunks:
            kw = {"language_id": req.get("language", "en"), "exaggeration": float(req.get("exaggeration", 0.5)),
                  "cfg_weight": float(req.get("cfg_weight", 0.5))}  # fmt: skip
            if req.get("reference"):
                kw["audio_prompt_path"] = req["reference"]
            pieces += [model.generate(c, **kw), gap]
        wav = torch.cat(pieces[:-1], dim=-1)
        ta.save(req["out"], wav, model.sr, encoding="PCM_S", bits_per_sample=16)  # 16-bit PCM: readable by the wave module
        print(json.dumps({"ok": True, "seconds": wav.shape[-1] / model.sr}))
    except Exception as exc:  # report, never hang the caller
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}))


if __name__ == "__main__":
    main()
