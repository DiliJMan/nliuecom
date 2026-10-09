"""Clean-up for text pulled out of PDFs."""

from __future__ import annotations

import re
from collections import Counter

_WORD = re.compile(r"[A-Za-z]+")


# A hyphen after one of these is part of the word ("re-assignment"), not a line-break split.
_KEEP_HYPHEN_AFTER = {
    "re",
    "non",
    "self",
    "cross",
    "inter",
    "co",
    "anti",
    "multi",
    "pre",
    "post",
    "sub",
}


def join_wrapped(lines: list[str]) -> str:
    """Join wrapped lines, closing up words the PDF split across a line break.

    A trailing ' -' is always a split. A trailing '-' directly after a letter is a split too,
    unless the word fragment before it is a prefix that takes a hyphen.
    """
    out = ""
    for line in (ln.strip() for ln in lines):
        if not line:
            continue
        if not out:
            out = line
        elif out.endswith(" -"):
            out = out[:-2] + line
        elif out.endswith("-") and len(out) > 1 and out[-2].isalpha() and line[:1].islower():
            fragment = re.split(r"[\s(]", out[:-1])[-1].lower()
            out = out + line if fragment in _KEEP_HYPHEN_AFTER else out[:-1] + line
        else:
            out = f"{out} {line}"
    return out


def build_vocabulary(text: str, minimum: int = 2) -> set[str]:
    """Words that appear at least `minimum` times, lower-cased."""
    counts = Counter(w.lower() for w in _WORD.findall(text))
    return {w for w, n in counts.items() if n >= minimum}


def repair_kerning(text: str, vocabulary: set[str]) -> str:
    """Re-join words that the PDF split with a stray space ("infor mation").

    A pair is joined only when the joined word is common in the same document and at least
    one half is not a word on its own, so real word pairs ("to day") are left alone.
    """

    def fix(match: re.Match) -> str:
        left, right = match.group(1), match.group(2)
        joined = (left + right).lower()
        if joined in vocabulary and (
            left.lower() not in vocabulary or right.lower() not in vocabulary
        ):
            return left + right
        return match.group(0)

    # Two passes so words split in three pieces are caught.
    for _ in range(2):
        text = re.sub(r"\b([A-Za-z]{1,12}) ([A-Za-z]{2,12})\b", fix, text)
    return text
