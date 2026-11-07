# wiretap-py

Wiretap adds structured activity metadata to standard Python logging.

```python
from wiretap import Wiretap

logger, wiretap = Wiretap.get(__name__)

logger.info("Configuration loaded", extra=wiretap.snap("Configuration", "buzz"))
with wiretap.begin_scope("LoadWorkflow", "core", workflow_id=42) as activity:
    logger.debug(None, extra=activity.zero())
    logger.info("Working", extra=activity.tick())
    logger.info("Loaded {properties[workflow_id]}", extra=activity.last())
```

Use Wiretap's text or JSON formatter for message interpolation and structured output.
An omitted LAST is emitted automatically through the wiretap's logger.
Lifecycle findings are emitted as `BEEP` events with `focus="buzz"` and a `properties.beep_code` code.
Invalid sequences use ERROR; remarks use DEBUG. Each enabled finding is emitted once per activity.
