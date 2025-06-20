from django.contrib import admin
from django.urls import path
from myApp import views  
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('uploads/', views.uploads_table, name='upload_tables'), 
    path('delete/<int:upload_id>/', views.delete_upload, name='delete_upload'),  
    path('update/<int:upload_id>/', views.update_upload, name='update_upload'),
    path('download/<int:upload_id>/', views.download_output, name='download_output'),

]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
