"""Lossless parser/writer for Assetto Corsa setup .ini files.

The game stores each setup parameter in its own section:

    [PRESSURE_LF]
    VALUE=19

Some cars add metadata sections ([ABOUT], [CAR], [__EXT_PATCH]) and custom
sections created by CSP scripts. We never rebuild the file: we keep every line
and only replace the value token of the sections that actually change, so an
untouched setup round-trips byte-for-byte.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:;.*|//.*)?$")
VALUE_RE = re.compile(r"^(\s*VALUE\s*=\s*)(.*?)(\s*(?:;.*)?)$", re.IGNORECASE)
LINE_END_RE = re.compile(r"(\r\n|\n|\r)")


@dataclass
class SetupValue:
    section: str
    value: str
    line_index: int
    value_start: int
    value_end: int


@dataclass
class SetupFile:
    text: str
    values: dict[str, SetupValue] = field(default_factory=dict)
    sections: list[str] = field(default_factory=list)
    newline: str = "\r\n"

    @classmethod
    def parse(cls, text: str) -> "SetupFile":
        match = LINE_END_RE.search(text)
        newline = match.group(1) if match else "\r\n"
        lines = text.splitlines(keepends=True)
        values: dict[str, SetupValue] = {}
        sections: list[str] = []
        current: str | None = None

        for index, raw in enumerate(lines):
            line = raw.rstrip("\r\n")
            header = SECTION_RE.match(line)
            if header:
                current = header.group(1).strip().upper()
                sections.append(current)
                continue
            if current is None:
                continue
            value_match = VALUE_RE.match(line)
            if not value_match:
                continue
            # keep the first occurrence of a section
            if current in values:
                continue
            start, end = value_match.span(2)
            values[current] = SetupValue(
                section=current,
                value=value_match.group(2).strip(),
                line_index=index,
                value_start=start,
                value_end=end,
            )

        return cls(text=text, values=values, sections=sections, newline=newline)

    @classmethod
    def from_path(cls, path: str | "os.PathLike[str]") -> "SetupFile":  # type: ignore[name-defined]
        from pathlib import Path

        raw = Path(path).read_bytes()
        return cls.parse(raw.decode("utf-8-sig", errors="replace"))

    def get(self, section: str) -> str | None:
        item = self.values.get(section.upper())
        return item.value if item else None

    def get_float(self, section: str) -> float | None:
        raw = self.get(section)
        if raw is None:
            return None
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None

    def numeric(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for section, item in self.values.items():
            try:
                out[section] = float(item.value.replace(",", "."))
            except ValueError:
                continue
        return out

    def to_dict(self) -> dict[str, str]:
        return {section: item.value for section, item in self.values.items()}

    def with_values(self, changes: dict[str, str]) -> str:
        """Return a new text with the given sections' VALUE tokens replaced."""
        if not changes:
            return self.text

        lines = self.text.splitlines(keepends=True)
        for section, new_value in changes.items():
            item = self.values.get(section.upper())
            if item is None:
                continue
            raw = lines[item.line_index]
            ending = ""
            body = raw
            for ending_candidate in ("\r\n", "\n", "\r"):
                if body.endswith(ending_candidate):
                    ending = ending_candidate
                    body = body[: -len(ending_candidate)]
                    break
            # Recompute the span on the body without the line ending.
            match = VALUE_RE.match(body)
            if not match:
                continue
            body = body[: match.start(2)] + str(new_value) + body[match.end(2) :]
            lines[item.line_index] = body + ending

        return "".join(lines)

    def changed_sections(self, other: "SetupFile") -> dict[str, tuple[str, str]]:
        out: dict[str, tuple[str, str]] = {}
        for section, item in self.values.items():
            other_item = other.values.get(section)
            if other_item is not None and other_item.value != item.value:
                out[section] = (item.value, other_item.value)
        return out


def format_number(value: float, decimals: int = 0) -> str:
    if decimals <= 0:
        rounded = round(value)
        if abs(value - rounded) < 1e-9:
            return str(int(rounded))
    text = f"{value:.{max(decimals, 0)}f}".rstrip("0").rstrip(".")
    if text in ("-0", ""):
        return "0"
    return text
