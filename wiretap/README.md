# wiretap-py

Wiretap adds structured activity metadata to standard Python logging.

```python
from wiretap import Wiretap
from wiretap.data.content import BASELINE, INTERNAL

logger, wiretap = Wiretap.get(__name__)

logger.info("Configuration loaded", extra=wiretap.snap("Configuration", INTERNAL))
with wiretap.begin_scope("LoadWorkflow", BASELINE, workflow_id=42) as activity:
    logger.debug(None, extra=activity.zero())
    logger.info("Working", extra=activity.tick())
    logger.info("Loaded {properties[workflow_id]}", extra=activity.last())
```

Use Wiretap's text or JSON formatter for message interpolation and structured output.
`BASELINE`, `INTERNAL`, `METADATA`, and `STRANGER` are property dictionaries
containing `{"content": "baseline"}`, `{"content": "internal"}`,
`{"content": "metadata"}`, and `{"content": "stranger"}`, respectively.
They can be imported from `wiretap` or `wiretap.data.content`.
Custom content values need no declaration:

```python
from wiretap import Wiretap

logger, wiretap = Wiretap.get(__name__)

with wiretap.begin_scope("Payment", {"content": "billing"}) as activity:
    logger.debug(None, extra=activity.zero())
    logger.info("Checking", extra=activity.tick({"content": "audit"}))
    logger.info("Done", extra=activity.last())
```

`begin_scope`, `snap`, `zero`, `tick`, and `last` accept property mappings and
keyword properties. Later mappings override earlier ones, and keywords win.
Events inherit their scope's properties unless explicitly overridden.

An omitted LAST is emitted automatically through the wiretap's logger.
Lifecycle findings are emitted as `BEEP` events with a `properties.beep_code` code.
Invalid sequences use ERROR; remarks use DEBUG. Each enabled finding is emitted once per activity.
