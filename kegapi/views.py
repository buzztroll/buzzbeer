import logging

import django.http as djhttp

import rest_framework as rest
import rest_framework.views as restview

import kegapi.models as models
import kegapi.serializers as serializers
import kegapi.exceptions as exceptions

import kegapi.scale_states as scale_states

import django.template.loader as djtemplateloader


_g_logger = logging.getLogger(__name__)


def _float_preceision(f, dps):
    p = dps * 10
    x = int(f * p)
    return x / float(p)


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
            new_keg.full_weight = scale_mgr.get_raw_weight()
            new_keg.save()
            serializer = serializers.KegSerializer(new_keg, many=False)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except Exception as ex:
            _g_logger.exception("Keg post failed")
            return djhttp.response.HttpResponseBadRequest(content=str(ex))

    # get list of all kegs
    def get(self, request, *args, **kwargs):
        try:
            all_kegs = models.Kegs.objects.all().order_by('-creation_time')
            serializer = serializers.KegSerializer(all_kegs, many=True)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except Exception as ex:
            _g_logger.exception("Keg get failed")
            return djhttp.response.HttpResponseBadRequest(content=str(ex))


class KegDetailsApi(restview.APIView):
    def get(self, request, id, *args, **kwargs):
        try:
            _g_logger.info(f"keg get {id}")
            keg = models.Kegs.objects.get(id=id)
            serializer = serializers.KegSerializer(keg, many=False)
            return djhttp.JsonResponse(serializer.data, safe=False, status=rest.status.HTTP_200_OK)
        except Exception as ex:
            _g_logger.exception("Keg detail failed")
            return djhttp.response.HttpResponseBadRequest(content=str(ex))


def gauge(request):
    context = {}
    scale_db_obj = _get_scale()
    if scale_db_obj is None:
        context['scale_exists'] = False
    else:
        context['scale_exists'] = True
        scale_mgr = scale_states.get_scale_manager_singleton()
        try:
            k = models.Kegs.objects.latest("creation_time")
            full = k.full_weight
            oz = scale_mgr.get_weight()
            _g_logger.info(f"full weight {full} {oz}")
            total_beers = full / 12.0
            beers_consumed = (full - oz) / 12.0
            beers_left = total_beers - beers_consumed
            context['weight_oz'] = _float_preceision(oz, 1)
            context['total_beers'] = _float_preceision(total_beers, 1)
            context['beers_consumed'] = _float_preceision(beers_consumed, 1)
            context['beers_left'] = _float_preceision(beers_left, 1)
            context['keg_exists'] = True
        except models.Kegs.DoesNotExist:
            context['keg_exists'] = False

    template = djtemplateloader.get_template("gauge.html")
    return djhttp.HttpResponse(template.render(context, request))


def calibrate(request):
    if request.method == "POST":
        if "zero_it" in request.POST:
            scale_sm = scale_states.get_scale_sm_singleton()
            scale_db_obj = _get_scale()
            if scale_db_obj is None:
                scale_db_obj = models.Scales()
            scale_sm.zero(scale_db_obj)
        elif "calibrate_it" in request.POST:
            known_weight = float(request.POST['calibration_value'])
            _g_logger.info(f"setting calibration to {known_weight}")
            scale_sm = scale_states.get_scale_sm_singleton()
            scale_db_obj = _get_scale()
            scale_sm.calibrate(scale_db_obj, known_weight=known_weight)

    template = djtemplateloader.get_template("calibrate.html")
    context = {}
    scale_db_obj = _get_scale()
    if scale_db_obj is None:
        context['scale_exists'] = False
    else:
        context['scale_exists'] = True
        context['creation_time'] = scale_db_obj.creation_time
        context['zero_offset'] = scale_db_obj.zero_offset
        context['known_weight'] = scale_db_obj.known_weight
        context['known_weight_reading'] = scale_db_obj.known_weight_reading
        context['scale_state'] = scale_db_obj.state

    return djhttp.HttpResponse(template.render(context, request))


def newkeg(request):
    context = {}

    scale_db_obj = _get_scale()
    if scale_db_obj is None:
        context['scale_exists'] = False
    else:
        context['scale_exists'] = True
        if request.method == "POST":
            scale_mgr = scale_states.get_scale_manager_singleton()
            scale_mgr.new_full()
            k = models.Kegs()
            k.scale = scale_db_obj
            k.full_weight = scale_mgr.get_full_weight()
            k.save()

    try:
        k = models.Kegs.objects.latest("creation_time")
        context['creation_time'] = k.creation_time
        context['weight'] = k.full_weight
        context['keg_exists'] = True
    except models.Kegs.DoesNotExist:
        _g_logger.info("no keg found")
        context['keg_exists'] = False

    template = djtemplateloader.get_template("newkeg.html")
    return djhttp.HttpResponse(template.render(context, request))