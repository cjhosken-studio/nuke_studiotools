import os
import re

FRAME_RE = re.compile(r"(.*?)(\d+)(\.[^.]+)$")


def find_frame_range(directory):
    frames = []

    for fname in os.listdir(directory):
        match = FRAME_RE.match(fname)
        if not match:
            continue

        frame = int(match.group(2))
        frames.append(frame)

    if not frames:
        return None, None

    return min(frames), max(frames)


