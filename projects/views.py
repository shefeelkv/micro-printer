import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Project, CustomFont

@csrf_exempt
def project_list_create(request):
    """API endpoint to list all saved projects or create a new one."""
    if request.method == 'GET':
        projects = Project.objects.all()
        data = [{
            'id': str(p.id),
            'name': p.name,
            'updated_at': p.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'settings': p.settings
        } for p in projects]
        return JsonResponse({'projects': data})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            name = body.get('name', 'Untitled Project')
            html_content = body.get('html_content', '')
            settings = body.get('settings', {})
            
            project = Project.objects.create(
                name=name,
                html_content=html_content,
                settings=settings
            )
            return JsonResponse({
                'status': 'success',
                'id': str(project.id),
                'name': project.name,
                'message': 'Project saved successfully!'
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@csrf_exempt
def project_detail(request, project_id):
    """API endpoint to retrieve, update, or delete a single project."""
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'GET':
        return JsonResponse({
            'id': str(project.id),
            'name': project.name,
            'html_content': project.html_content,
            'settings': project.settings
        })

    elif request.method in ['POST', 'PUT']:
        try:
            body = json.loads(request.body)
            project.name = body.get('name', project.name)
            project.html_content = body.get('html_content', project.html_content)
            project.settings = body.get('settings', project.settings)
            project.save()
            return JsonResponse({
                'status': 'success',
                'id': str(project.id),
                'name': project.name,
                'message': 'Project updated successfully!'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    elif request.method == 'DELETE':
        project.delete()
        return JsonResponse({'status': 'success', 'message': 'Project deleted successfully!'})

@csrf_exempt
def upload_font(request):
    """API endpoint to upload a custom TTF font file."""
    if request.method == 'POST':
        font_file = request.FILES.get('ttf_file')
        font_name = request.POST.get('font_name', '').strip()

        if not font_file:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)
        
        if not font_file.name.endswith('.ttf'):
            return JsonResponse({'status': 'error', 'message': 'Only TrueType Font (.ttf) files are supported.'}, status=400)

        if not font_name:
            # Fallback to the file base name (slugified)
            font_name = font_file.name.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ').title()

        try:
            # Check if font with same name already exists
            existing_font = CustomFont.objects.filter(name=font_name).first()
            if existing_font:
                # Overwrite the file
                existing_font.ttf_file = font_file
                existing_font.save()
                font = existing_font
            else:
                font = CustomFont.objects.create(name=font_name, ttf_file=font_file)
            
            # Try to register it immediately in ReportLab to verify validity
            from pdf_engine.font_manager import register_font_family
            register_font_family(font.name)

            return JsonResponse({
                'status': 'success',
                'font_name': font.name,
                'message': f"Font '{font.name}' uploaded and registered successfully!"
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)
