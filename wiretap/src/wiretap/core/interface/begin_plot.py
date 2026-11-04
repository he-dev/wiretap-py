import contextlib
from typing import Iterator, Literal

from wiretap.util.plot import PlotAbout, PlotScope


@contextlib.contextmanager
def begin_plot(
        about: str,
        story: Literal["user", "buzz"],
        trace_id: str | None = None,
        parent_id: str | None = None,
        **kwargs
) -> Iterator[PlotAbout]:
    """
    Creates a plot scope and logs a closing event if no explicit last event occurred.

    Args:
        about: The name of the span. If None, the name will be derived from the calling frame. Usually the function name.
        story: The default story for events in this plot.
        trace_id: The trace ID to use for the span. If None, a random ID will be generated.
        parent_id: External parent span ID, used when there is no local parent plot.
        kwargs: Additional keyword arguments to be passed to each trace.

    Returns:
        The newly created span.
    """

    with PlotScope.push(
            about=about,
            story=story,
            state=kwargs,
            trace_id=trace_id,
            parent_id=parent_id,
    ) as plot:
        plot_about = PlotAbout(plot)
        try:
            yield plot_about
        except Exception:
            plot_about.last.once.log_error(
                message="{plot[about]} fails after {plot[duration_ms]} ms.",
                stack_level=5,
                **kwargs
            )
            raise
        else:
            plot_about.last.once.log_info(
                message="{plot[about]} completes in {plot[duration_ms]} ms.",
                stack_level=5,
                **kwargs
            )
