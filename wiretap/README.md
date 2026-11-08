# wiretap-py

Wiretap adds structured activity metadata to standard Python logging.

```python
from wiretap import Wiretap
from wiretap.core.channel import INTERNAL, OFFICIAL

logger, wiretap = Wiretap.get(__name__)

logger.info("Configuration loaded", extra=wiretap.snap("Configuration", INTERNAL))
with wiretap.begin_scope("LoadWorkflow", OFFICIAL, workflow_id=42) as activity:
    logger.debug(None, extra=activity.zero())
    logger.info("Working", extra=activity.tick())
    logger.info("Loaded {properties[workflow_id]}", extra=activity.last())
```

Use Wiretap's text or JSON formatter for message interpolation and structured output.
`channel` is a field inside the `activity` metadata.

Channels are plain strings. `OFFICIAL` and `INTERNAL` are convenience constants
for `"official"` and `"internal"`; custom channels need no declaration:

```python
from wiretap import Wiretap

logger, wiretap = Wiretap.get(__name__)

with wiretap.begin_scope("Payment", "billing") as activity:
    logger.debug(None, extra=activity.zero())
    logger.info("Checking", extra=activity.tick("audit"))
    logger.info("Done", extra=activity.last())
```

`begin_scope` and `snap` accept any string channel. `zero`, `tick`, and `last`
inherit their scope's channel unless explicitly overridden.

An omitted LAST is emitted automatically through the wiretap's logger.
Lifecycle findings are emitted as `BEEP` events on the `INTERNAL` channel with a `properties.beep_code` code.
Invalid sequences use ERROR; remarks use DEBUG. Each enabled finding is emitted once per activity.
