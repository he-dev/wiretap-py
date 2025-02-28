from datetime import datetime

import pytest

from wiretap.json import JSONEncoderCache
from wiretap.json.encoders import UUIDEncoder, DateTimeEncoder


def test_get_encoder_for_uses_cached_encoder():
    encoders = [UUIDEncoder(), DateTimeEncoder()]

    encoder1 = JSONEncoderCache.get_encoder_for(encoders, datetime)
    encoder2 = JSONEncoderCache.get_encoder_for(encoders, datetime)

    assert encoder1 is encoders[1]
    assert encoder1 is encoder2
