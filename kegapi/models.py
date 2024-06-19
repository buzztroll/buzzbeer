import uuid

import django.db.models as djmodels


SCALE_STATE_NONE = "N"
SCALE_STATE_ZEROED = "Z"
SCALE_STATE_CALIBRATED = "C"

KEG_STATE_NONE = "N"
KEG_STATE_RUNNING = "R"
KEG_STATE_STOPPED = "S"


class Scales(djmodels.Model):
    ScaleStatesMap = {
        SCALE_STATE_NONE: 'NONE',
        SCALE_STATE_ZEROED: 'ZEROED',
        SCALE_STATE_CALIBRATED: 'CALIBRATED',
    }
    state = djmodels.CharField(
        max_length=1,
        choices=ScaleStatesMap,
        default=SCALE_STATE_NONE,
    )
    creation_time = djmodels.DateTimeField(
        auto_now_add=True, auto_now=False, blank=True, db_index=True)
    zero_offset = djmodels.FloatField(default=0.0)
    known_weight_reading = djmodels.FloatField(default=0.0)
    known_weight = djmodels.FloatField(default=0.0)


class Kegs(djmodels.Model):
    id = djmodels.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creation_time = djmodels.DateTimeField(
        auto_now_add=True, auto_now=False, blank=True, db_index=True)
    scale = djmodels.ForeignKey(Scales, on_delete=djmodels.CASCADE)
    full_weight_reading = djmodels.FloatField()
    full_weight = djmodels.FloatField()
