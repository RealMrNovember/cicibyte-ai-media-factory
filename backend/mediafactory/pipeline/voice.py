"""Voice choice from the Studio: one voice per language, shared speed and pitch."""

from pydantic import BaseModel, Field, field_validator

from mediafactory.pipeline.tts import DEFAULT_VOICE, VOICE_CATALOG


class VoiceSettings(BaseModel):
    en: str = DEFAULT_VOICE["en"]
    tr: str = DEFAULT_VOICE["tr"]
    speed: float = Field(default=1.0, ge=0.8, le=1.3)
    pitch: int = Field(default=0, ge=-4, le=4, description="semitones")

    @field_validator("en", "tr")
    @classmethod
    def _known(cls, v: str, info) -> str:
        voice = VOICE_CATALOG.get(v)
        if voice is None or voice["language"] != info.field_name:
            raise ValueError(f"unknown {info.field_name} voice {v!r}")
        return v

    @property
    def length_scale(self) -> float:
        return 1.0 / self.speed
