import inspect
from dataclasses import dataclass

from wiretap.meta import trim_path


FRAME_INDEX_CALLER = 1


@dataclass(frozen=True)
class Caller:
    func: str
    file: str
    line: int

    @staticmethod
    def from_current_frame(frame_offset: int) -> "Caller":
        # meta: Uses Python frame inspection to capture where the public API was called.
        frame = inspect.currentframe()
        try:
            steps = FRAME_INDEX_CALLER + frame_offset
            for _ in range(steps):
                if frame is None:
                    break
                frame = frame.f_back

            return Caller(
                func=frame.f_code.co_name if frame is not None else "<unknown>",
                file=trim_path(frame.f_code.co_filename) if frame is not None else "<unknown>",
                line=frame.f_lineno if frame is not None else 0
            )
        finally:
            del frame
