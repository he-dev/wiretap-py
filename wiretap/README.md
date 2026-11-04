# wiretap-py

Wiretap adds structured plot metadata to standard Python logging.

```python
from wiretap import Storyline

logger, storyline = Storyline.logger(__name__)

logger.info("Configuration loaded", extra=storyline.snap("Configuration", "buzz"))
with storyline.begin_plot("LoadWorkflow", "core", workflow_id=42) as plot:
    logger.debug(None, extra=plot.zero())
    logger.info("Working", extra=plot.tick())
    logger.info("Loaded {context[workflow_id]}", extra=plot.last())
```

Use Wiretap's text or JSON formatter for message interpolation and structured output.
An omitted LAST is emitted automatically through the storyline's logger.
Event diagnostics are stored in `plot.diagnostics.errors` and `plot.diagnostics.remarks`.
