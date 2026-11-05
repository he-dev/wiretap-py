# wiretap-py

Wiretap adds structured plot metadata to standard Python logging.

```python
from wiretap import Storyline

logger, storyline = Storyline.logger(__name__)

logger.info("Configuration loaded", extra=storyline.snap("Configuration", "buzz"))
with storyline.begin_plot("LoadWorkflow", "core", workflow_id=42) as plot:
    logger.debug(None, extra=plot.zero())
    logger.info("Working", extra=plot.tick())
    logger.info("Loaded {samples[workflow_id]}", extra=plot.last())
```

Use Wiretap's text or JSON formatter for message interpolation and structured output.
An omitted LAST is emitted automatically through the storyline's logger.
Lifecycle findings are emitted as `BEEP` events with `story="buzz"` and a `samples.beep_code` code.
Invalid sequences use ERROR; remarks use DEBUG. Each enabled finding is emitted once per plot scope.
