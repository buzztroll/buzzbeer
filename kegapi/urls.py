import django.urls as djurls

import kegapi.views as views


urlpatterns = [
    djurls.path('scale/zero', views.ZeroScaleApi.as_view()),
    djurls.path('scale/calibrate', views.CalibrateScaleApi.as_view()),
    djurls.path('keg', views.KegApi.as_view()),
    djurls.path('keg/<str:id>', views.KegDetailsApi.as_view()),
]