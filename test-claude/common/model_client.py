"""Model clients for the Claude re-runs.

AnthropicClient sends one streamed Messages API request with no tools.
ReplayClient returns a recorded answer without calling anything; it is for testing the harness.
Both return a Reply.
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_env(path=REPO / ".env"):
    """Set variables from a KEY=VALUE file. A variable already set in the environment is left alone."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and value and not os.environ.get(key):
            os.environ[key] = value

# US dollars per million tokens (input, output).
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-fable-5-2": (8.0, 40.0),
}

# Raw Messages API stream events. The SDK's stream helper also yields its own
# convenience events (for example "text" and "thinking"); those are not logged.
RAW_EVENT_TYPES = {
    "message_start",
    "content_block_start",
    "content_block_delta",
    "content_block_stop",
    "message_delta",
    "message_stop",
    "ping",
    "error",
}


@dataclass
class Reply:
    text: str
    thinking: list
    content: list
    stop_reason: str
    stop_details: object
    usage: dict
    model_returned: str
    message_id: str
    request_id: str
    wall_s: float
    events: list = field(default_factory=list)

    @property
    def block_types(self):
        counts = {}
        for block in self.content:
            kind = block.get("type", "?")
            counts[kind] = counts.get(kind, 0) + 1
        return counts

    @property
    def tool_blocks(self):
        return {k: v for k, v in self.block_types.items() if "tool" in k}

    @property
    def tool_free(self):
        return not self.tool_blocks


def cost_usd(model, usage):
    """Cost of one response from its usage record, or None if the model has no listed price."""
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    tokens_in = (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
    )
    tokens_out = usage.get("output_tokens") or 0
    return round((tokens_in * price_in + tokens_out * price_out) / 1_000_000, 4)


def request_body(model, system, messages, effort, max_tokens):
    """The request settings, as sent. No tools, no sampling parameters, no fallbacks."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": effort},
    }


class AnthropicClient:
    def __init__(self):
        import anthropic  # imported here so the scorer and the replay test need no SDK

        load_env()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env at the repo root and fill it in.")
        self.sdk_version = anthropic.__version__
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    def count_tokens(self, model, system, messages):
        return self.client.messages.count_tokens(model=model, system=system, messages=messages).input_tokens

    def send(self, model, system, messages, effort, max_tokens):
        body = request_body(model, system, messages, effort, max_tokens)
        events = []
        request_id = None
        start = time.time()
        with self.client.messages.stream(**body) as stream:
            for event in stream:
                if getattr(event, "type", None) in RAW_EVENT_TYPES and hasattr(event, "to_dict"):
                    events.append(event.to_dict())
            final = stream.get_final_message()
            request_id = stream.request_id
        wall_s = round(time.time() - start, 1)

        message = final.to_dict()
        content = message.get("content", [])
        return Reply(
            text="".join(b.get("text", "") for b in content if b.get("type") == "text"),
            thinking=[b.get("thinking", "") for b in content if b.get("type") == "thinking"],
            content=content,
            stop_reason=message.get("stop_reason"),
            stop_details=message.get("stop_details"),
            usage=message.get("usage", {}),
            model_returned=message.get("model"),
            message_id=message.get("id"),
            request_id=request_id,
            wall_s=wall_s,
            events=events,
        )


class ReplayClient:
    """Returns a fixed answer text. Used to test the runner and log writer without an API call."""

    sdk_version = "replay"

    def __init__(self, answer_text):
        self.answer_text = answer_text

    def count_tokens(self, model, system, messages):
        return 0

    def send(self, model, system, messages, effort, max_tokens):
        content = [{"type": "text", "text": self.answer_text}]
        return Reply(
            text=self.answer_text,
            thinking=[],
            content=content,
            stop_reason="end_turn",
            stop_details=None,
            usage={"input_tokens": 0, "output_tokens": 0},
            model_returned="replay",
            message_id=None,
            request_id=None,
            wall_s=0.0,
            events=[{"type": "replay"}],
        )
