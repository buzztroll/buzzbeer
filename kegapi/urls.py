import django.urls as djurls

import kegapi.views as views


urlpatterns = [
    djurls.path('api/scale/zero', views.ZeroScaleApi.as_view()),
    djurls.path('api/scale/calibrate', views.CalibrateScaleApi.as_view()),
    djurls.path('api', views.KegApi.as_view()),
    djurls.path('api/<str:id>', views.KegDetailsApi.as_view()),
    djurls.path('gauge', views.gauge, name='gauge'),
    djurls.path('calibrate', views.calibrate, name='calibrate'),
    djurls.path('newkeg', views.newkeg, name='newkeg'),
]