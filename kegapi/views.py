import logging

import django.http as djhttp

import rest_framework as rest
import rest_framework.views as restview

import kegapi.models as models
import kegapi.serializers as serializers
import kegapi.exceptions as exceptions

import kegapi.scale_states as scale_states

_g_logger = logging.getLogger(__name__)


def _get_scale():
    try:
        s = models.Scales.objects.latest("creation_time")
        _g_logger.info("Found Scale")
        return s
    except models.Scales.DoesNotExist:
        _g_logger.info("There is no Scale")
        return None


class ZeroScaleApi(restview.APIView):
    def put(self, request, *args, **kwargs):
        scale_sm = scale_states.get_scale_sm_singleton()
        scale_db_obj = _get_scale()
        if scale_db_obj is None:
            scale_db_obj = models.Scales()
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
            if scale_db_obj is None:
                scale_db_obj = models.Scales()
            scale_sm.calibrate(scale_db_obj, known_weight=known_weight)
            serializer = serializers.ScaleSerializer(scale_db_obj, many=False)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except exceptions.StateTransitionException as ex:
            return djhttp.response.HttpResponseBadRequest(content=str(ex))


class KegApi(restview.APIView):

    # setup a new keg
    def post(self, request, *args, **kwargs):
        try:
            scale_db_obj = _get_scale()
            if scale_db_obj is None:
                return djhttp.response.HttpResponseBadRequest(
                    content="Before adding a keg you must calibrate your scale")
            scale_mgr = scale_states.get_scale_manager_singleton()
            new_keg = models.Kegs()
            new_keg.scale = scale_db_obj
            new_keg.full_weight_reading = scale_mgr.get_weight()
            new_keg.full_weight = scale_mgr.get_raw_weight()
            new_keg.save()
            serializer = serializers.KegSerializer(new_keg, many=False)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except Exception as ex:
            raise
            return djhttp.response.HttpResponseBadRequest(content=str(ex))

    # get list of all kegs
    def get(self, request, *args, **kwargs):
        try:
            all_kegs = models.Kegs.objects.all().order_by('-creation_time')
            serializer = serializers.KegSerializer(all_kegs, many=True)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except Exception as ex:
            return djhttp.response.HttpResponseBadRequest(content=str(ex))


class KegDetailsApi(restview.APIView):
    def get(self, request, id, *args, **kwargs):
        try:
            _g_logger.info(f"keg get {id}")
            keg = models.Kegs.objects.get(id=id)
            serializer = serializers.KegSerializer(keg, many=False)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except Exception as ex:
            return djhttp.response.HttpResponseBadRequest(content=str(ex))

