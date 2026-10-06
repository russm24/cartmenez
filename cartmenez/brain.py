"""Claude in character: decides what to say and which sound byte to play."""

import json
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from .config import Config

PERSONA = """\
You are the voice of a webcam kiosk sitting on a laptop. You play Eric Cartman \
from South Park: a loud, bossy, self-important ten-year-old who thinks he is the \
smartest and most important person in any room. Everything you say is spoken \
aloud through a speaker to whoever just walked up, so it must sound like him.

How he talks:
- Whiny, indignant, theatrical. Swings between sugary fake-polite ("Well hellooo \
there, friend") and outraged ("That is SO not cool!").
- Always has a scheme. Tries to recruit, bribe or boss the visitor into it.
- Demands respect for his authority, insists he is "big-boned", gets distracted \
by snacks (Cheesy Poofs, KFC, Mom's cooking).
- Uses kid phrasing: "you guys", "seriously", "sweet", "screw you guys, I'm going \
home" when someone walks off or bores him.

Keep it fun for strangers at a public kiosk:
- PG-13 at most. No slurs, nothing about race, religion, ethnicity, gender, \
sexuality, disability or body size of the visitor. Roast their ideas and \
choices, never who they are.
- If someone is upset, a child, or asks for real help, drop the act just enough \
to be kind and brief.

Spoken-output rules:
- 1-3 short sentences per reply (under ~40 words). No stage directions, emoji, \
asterisks or markdown; only words he would actually say out loud.
- End most turns with a question or a demand so the visitor has something to \
say back.

Sound bytes: you may optionally trigger ONE clip per reply from this list. Use \
them sparingly (maybe one reply in three) and only when it lands as a joke. Use \
"none" otherwise.
{catalog}

Events in square brackets (like [A person walked up]) come from the camera \
system, not from the visitor. Set end_conversation to true when the visitor says \
goodbye, walks away, or you've clearly wrapped up.\
"""


class Reply(BaseModel):
    say: str
    sound: str = "none"
    sound_timing: Literal["before", "after"] = "after"
    end_conversation: bool = False


FALLBACK = Reply(say="Whatever, I don't have to talk to you. Screw you guys, I'm going home.", end_conversation=True)


class CartmanBrain:
    def __init__(self, cfg: Config, sound_names: list[str], sound_catalog: str):
        self.cfg = cfg
        self.client = anthropic.Anthropic()
        self.system = PERSONA.format(catalog=sound_catalog)
        self.schema = {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "say": {"type": "string", "description": "Exactly what to speak aloud."},
                    "sound": {"type": "string", "enum": sound_names + ["none"]},
                    "sound_timing": {"type": "string", "enum": ["before", "after"]},
                    "end_conversation": {"type": "boolean"},
                },
                "required": ["say", "sound", "sound_timing", "end_conversation"],
                "additionalProperties": False,
            },
        }
        self.messages: list[dict] = []

    def reset(self) -> None:
        self.messages = []

    def respond(self, user_text: str) -> Reply:
        self.messages.append({"role": "user", "content": user_text})
        try:
            response = self.client.beta.messages.create(
                model=self.cfg.model,
                max_tokens=2000,
                system=self.system,
                messages=self.messages,
                output_config={"effort": self.cfg.effort, "format": self.schema},
                # Re-route to a fallback model if a safety classifier declines.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.RateLimitError:
            print("[claude] rate limited")
            self.messages.pop()
            return FALLBACK
        except anthropic.APIStatusError as e:
            print(f"[claude] API error {e.status_code}: {e.message}")
            self.messages.pop()
            return FALLBACK
        except anthropic.APIConnectionError as e:
            print(f"[claude] connection error: {e}")
            self.messages.pop()
            return FALLBACK

        if response.stop_reason == "refusal":
            self.messages.pop()
            return Reply(say="Yeah, I'm not doing that. Ask me something else, hippie.")

        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            reply = Reply.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[claude] could not parse reply ({e}): {text!r}")
            self.messages.pop()
            return FALLBACK

        # Append the full content (incl. thinking blocks) unchanged so history stays append-only.
        self.messages.append({"role": "assistant", "content": response.content})
        return reply
