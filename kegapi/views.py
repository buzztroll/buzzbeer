import logging

import django.http as djhttp

import rest_framework as rest
import rest_framework.views as restview

import kegapi.models as models
import kegapi.serializers as serializers
import kegapi.exceptions as exceptions

import kegapi.scale_states as scale_states

_g_logger = logging.getLogger(__name__)


def _get_latest_keg():
    try:
        obj = models.Kegs.objects.latest("creation_time")
        _g_logger.info("Found keg")
        return obj
    except models.Kegs.DoesNotExist:
        k = models.Kegs()
        _g_logger.info("There is no Keg")
        return k


def _get_scale():
    try:
        s = models.Scales.objects.latest("creation_time")
        _g_logger.info("Found Scale")
        return s
    except models.Scales.DoesNotExist:
        s = models.Scales()
        _g_logger.info("There is no Scale")
        return s


class ZeroKegApi(restview.APIView):
    def put(self, request, *args, **kwargs):
        scale_sm = scale_states.get_scale_sm_singleton()
        scale_db_obj = _get_scale()
        scale_sm.zero(scale_db_obj)
        serializer = serializers.ScaleSerializer(scale_db_obj, many=False)
        return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)


class CalibrateScaleApi(restview.APIView):
    def put(self, request, *args, **kwargs):
        try:
            known_weight = request.data.get("weight")
            if known_weight is None:
                return djhttp.response.HttpResponseBadRequest(content="You must provide a known weight")
            _g_logger.info(f"incoming known weight is {known_weight}")
            scale_sm = scale_states.get_scale_sm_singleton()
            scale_db_obj = _get_scale()
            scale_sm.calibrate(scale_db_obj, known_weight=known_weight)
            serializer = serializers.ScaleSerializer(scale_db_obj, many=False)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except exceptions.StateTransitionException as ex:
            return djhttp.response.HttpResponseBadRequest(content=str(ex))