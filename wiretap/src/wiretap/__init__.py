from .util.activity import DOMAIN, SYSTEM
from .util.buzz import configure
from .core.interface.begin_scope import begin_scope, log_envelope
from .core.interface.log_event import log_info, log_debug, log_warning, log_error

# core: Star import for convenience.
__all__ = [
    "begin_scope",
    "log_envelope",
    "log_info",
    "log_debug",
    "log_warning",
    "log_error",
    "DOMAIN",
    "SYSTEM",
    "configure"
]
