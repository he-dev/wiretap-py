from wiretap import begin_plot, snap


def log_v13():
    snap("log_info", "buzz").log_info("Message without plot.")
    with begin_plot(about="outer", story="user", foo="bar") as outer:
        outer.zero.log_debug(None)
        with begin_plot("inner", "user") as inner:
            # inner.zero.log_debug(None)
            inner.tick.log_info(None)
            inner.last.log_info("That's it in {plot[duration_ms]} ms.", bar="baz")
    snap("enough", "buzz").log_info("That's it.")
