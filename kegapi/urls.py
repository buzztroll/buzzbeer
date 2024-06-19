import django.urls as djurls

import kegapi.views as views


urlpatterns = [
    djurls.path('scale/zero', views.ZeroKegApi.as_view()),
    djurls.path('scale/calibrate', views.CalibrateScaleApi.as_view()),
]