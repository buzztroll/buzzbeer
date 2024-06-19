import rest_framework.serializers as serializers

import kegapi.models as models


class ScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Scales
        fields = ['state', 'creation_time', 'zero_offset', 'known_weight_reading', 'known_weight']
