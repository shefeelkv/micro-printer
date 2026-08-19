from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

import editor.views as editor_views
import projects.views as projects_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Editor workspace URL mappings
    path('', editor_views.index, name='index'),
    path('upload-file/', editor_views.upload_file, name='upload_file'),
    path('generate-pdf/', editor_views.generate_pdf_view, name='generate_pdf'),
    path('diagnostic-pdf/', editor_views.diagnostic_pdf_view, name='diagnostic_pdf'),
    
    # Projects / templates API URL mappings
    path('projects/', projects_views.project_list_create, name='project_list_create'),
    path('projects/<uuid:project_id>/', projects_views.project_detail, name='project_detail'),
    path('upload-font/', projects_views.upload_font, name='upload_font'),
]

# Serve media upload files (e.g. custom TTF fonts) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
