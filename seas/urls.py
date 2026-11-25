from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from core import views
from django.conf import settings
from django.views.static import serve
from django.urls import re_path

urlpatterns=[path('',views.home),path('api/state',views.state),path('api/login',views.sign_in),path('api/logout',views.sign_out),path('api/config',views.config),path('api/experts',views.experts),path('api/evaluations/<str:ident>',views.evaluation),path('api/evaluations/<str:ident>/finalize',views.finish),path('api/evaluations/<str:ident>/duplicate',views.duplicate),path('api/evaluations/<str:ident>/pdf',views.pdf),path('admin/',admin.site.urls),path('accounts/password_reset/',auth.PasswordResetView.as_view(),name='password_reset'),path('accounts/password_reset/done/',auth.PasswordResetDoneView.as_view(),name='password_reset_done'),path('accounts/reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(),name='password_reset_confirm'),path('accounts/reset/done/',auth.PasswordResetCompleteView.as_view(),name='password_reset_complete')]
urlpatterns += [re_path(r'^static/(?P<path>.*)$',serve,{'document_root':settings.STATICFILES_DIRS[0]})]
