import os
import re
import pandas as pd
from django.core.files import File
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import FileUpload
from .forms import ExcelFileUploadForm
from .utils import generate_output
from datetime import date
from django.utils import timezone
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.contrib import messages
from django.views.decorators.cache import never_cache 

def parse_week_string(week_str):
    try:
        year, week = map(int, week_str.split("-W"))
        return year, week
    except Exception:
        raise ValueError("Date input must be in the format 'YYYY-Www' (e.g. 2025-W21)")

def week_to_date(year, week):
    try:
        return date.fromisocalendar(year, week, 1)
    except Exception:
        raise ValueError(f"Invalid year/week combination: year={year}, week={week}")

def extract_week_from_filename(filename):
    match = re.search(r'KW[\s_]*(\d{1,2})', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def validate_excel_headers(file1, file2):
    """Validate that both Excel files have identical headers"""
    try:
        df1 = pd.read_excel(file1, nrows=0)
        df2 = pd.read_excel(file2, nrows=0)
        
        if list(df1.columns) != list(df2.columns):
            mismatched = set(df1.columns).symmetric_difference(set(df2.columns))
            raise ValueError(f"Header mismatch detected.")
            
        return True
    except Exception as e:
        if "Header mismatch" in str(e):
            raise  # Re-raise the original header mismatch error
        raise ValueError(f"Error reading Excel files: {str(e)}")

@never_cache
def index(request):
    if request.method == 'POST':
        form = ExcelFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file1 = request.FILES.get('file1')
            file2 = request.FILES.get('file2')

            try:
                current_year = timezone.now().year
                file1_week = extract_week_from_filename(file1.name) if file1 else None
                file2_week = extract_week_from_filename(file2.name) if file2 else None

                date1_str = request.POST.get('date1')
                date2_str = request.POST.get('date2')

                # Parse dates
                date1 = None
                if date1_str:
                    year1, week1 = parse_week_string(date1_str)
                    date1 = week_to_date(year1, week1)
                elif file1_week:
                    date1 = week_to_date(current_year, file1_week)

                date2 = None
                if date2_str:
                    year2, week2 = parse_week_string(date2_str)
                    date2 = week_to_date(year2, week2)
                elif file2_week:
                    date2 = week_to_date(current_year, file2_week)

                # Validate dates
                if not date1 or not date2:
                    raise ValueError("Missing date input and unable to extract week number from filenames.")
                if date1 <= date2:
                    raise ValueError("KW(X) must be later than KW(X-N)")

                # Validate headers
                validate_excel_headers(file1, file2)

                # Save the form
                instance = form.save(commit=False)
                instance.date1 = date1
                instance.date2 = date2
                instance.save()

                # Generate output
                output_path, output_filename = generate_output(
                    instance.file1.path,
                    instance.file2.path,
                    instance
                )

                with open(output_path, 'rb') as f:
                    instance.output.save(output_filename, File(f), save=True)

                # Store results in session
                request.session['extracted_data'] = pd.read_excel(output_path).to_dict(orient='records')
                messages.success(request, "Files compared successfully!")
                return redirect('upload_tables')

            except ValueError as e:
                error_type = "validation_error"
                if "Header mismatch" in str(e):
                    error_type = "header_error"
                elif "KW(X) must be later" in str(e):
                    error_type = "date_error"

                initial_date1 = f"{current_year}-W{file1_week:02d}" if not date1_str and file1_week else date1_str or ''
                initial_date2 = f"{current_year}-W{file2_week:02d}" if not date2_str and file2_week else date2_str or ''

                return render(request, "index.html", {
                    'form': form,
                    'uploaded_files': FileUpload.objects.all().order_by('-id'),
                    'error': str(e),
                    'error_type': error_type,
                    'date1_initial': initial_date1,
                    'date2_initial': initial_date2
                })
            except Exception as e:
                initial_date1 = f"{current_year}-W{file1_week:02d}" if not date1_str and file1_week else date1_str or ''
                initial_date2 = f"{current_year}-W{file2_week:02d}" if not date2_str and file2_week else date2_str or ''

                return render(request, "index.html", {
                    'form': form,
                    'uploaded_files': FileUpload.objects.all().order_by('-id'),
                    'error': f"An unexpected error occurred: {str(e)}",
                    'error_type': "system_error",
                    'date1_initial': initial_date1,
                    'date2_initial': initial_date2
                })
    else:
        form = ExcelFileUploadForm()

    return render(request, "index.html", {
        'form': form,
        'uploaded_files': FileUpload.objects.all().order_by('-id'),
        'date1_initial': '',
        'date2_initial': ''
    })

@never_cache  
def uploads_table(request):
    uploaded_files = FileUpload.objects.all().order_by('-id')
    return render(request, 'upload_tables.html', {
        'uploaded_files': uploaded_files,
        'extracted_data': request.session.get('extracted_data', [])
    })

def delete_upload(request, upload_id):
    upload = get_object_or_404(FileUpload, id=upload_id)
    
    # Delete associated files
    for file_field in [upload.file1, upload.file2, upload.output]:
        if file_field:
            path = os.path.join(settings.MEDIA_ROOT, str(file_field))
            if os.path.exists(path):
                os.remove(path)
    
    upload.delete()
    messages.success(request, "Upload deleted successfully!")
    return redirect('upload_tables')

def update_upload(request, upload_id):
    file_record = get_object_or_404(FileUpload, id=upload_id)
    current_year = timezone.now().year
    
    if request.method == 'POST':
        try:
            changed = False
            
            # Handle file updates
            if 'file1' in request.FILES:
                file_record.file1 = request.FILES['file1']
                changed = True
                
            if 'file2' in request.FILES:
                file_record.file2 = request.FILES['file2']
                changed = True
            
            # Handle date updates
            new_date1 = None
            new_date2 = None
            
            if request.POST.get('date1'):
                year1, week1 = parse_week_string(request.POST['date1'])
                new_date1 = week_to_date(year1, week1)
                if new_date1 != file_record.date1:
                    file_record.date1 = new_date1
                    changed = True
                    
            if request.POST.get('date2'):
                year2, week2 = parse_week_string(request.POST['date2'])
                new_date2 = week_to_date(year2, week2)
                if new_date2 != file_record.date2:
                    file_record.date2 = new_date2
                    changed = True
            
            # Validate dates
            if file_record.date1 and file_record.date2 and file_record.date1 <= file_record.date2:
                raise ValueError("KW(X) must be later than KW(X-N)")
            
            # Validate headers if files were changed
            if changed and ('file1' in request.FILES or 'file2' in request.FILES):
                file1 = request.FILES['file1'] if 'file1' in request.FILES else file_record.file1
                file2 = request.FILES['file2'] if 'file2' in request.FILES else file_record.file2
                validate_excel_headers(file1, file2)
            
            if changed:
                file_record.save()
                
                # Regenerate output
                output_path, output_filename = generate_output(
                    file_record.file1.path,
                    file_record.file2.path,
                    file_record
                )
                with open(output_path, 'rb') as f:
                    file_record.output.save(output_filename, File(f), save=True)
                
                messages.success(request, "Upload updated successfully!")
            else:
                messages.info(request, "No changes detected.")
            
            return redirect('upload_tables')

        except ValueError as e:
            date1_initial = request.POST.get('date1', 
                f"{current_year}-W{file_record.date1.isocalendar()[1]:02d}" if file_record.date1 else '')
            date2_initial = request.POST.get('date2', 
                f"{current_year}-W{file_record.date2.isocalendar()[1]:02d}" if file_record.date2 else '')
            
            error_type = "validation_error"
            if "Header mismatch" in str(e):
                error_type = "header_error"
            elif "KW(X) must be later" in str(e):
                error_type = "date_error"
            
            return render(request, 'update_upload.html', {
                'file': file_record,
                'error': str(e),
                'error_type': error_type,
                'date1_initial': date1_initial,
                'date2_initial': date2_initial,
            })
        except Exception as e:
            date1_initial = request.POST.get('date1', 
                f"{current_year}-W{file_record.date1.isocalendar()[1]:02d}" if file_record.date1 else '')
            date2_initial = request.POST.get('date2', 
                f"{current_year}-W{file_record.date2.isocalendar()[1]:02d}" if file_record.date2 else '')
            
            return render(request, 'update_upload.html', {
                'file': file_record,
                'error': f"An unexpected error occurred: {str(e)}",
                'error_type': "system_error",
                'date1_initial': date1_initial,
                'date2_initial': date2_initial,
            })

    # GET request - show current values
    return render(request, 'update_upload.html', {
        'file': file_record,
        'date1_initial': (
            f"{current_year}-W{file_record.date1.isocalendar()[1]:02d}" 
            if file_record.date1 else ''
        ),
        'date2_initial': (
            f"{current_year}-W{file_record.date2.isocalendar()[1]:02d}" 
            if file_record.date2 else ''
        ),
    })

def download_output(request, upload_id):
    file_record = get_object_or_404(FileUpload, id=upload_id)

    if not file_record.output:
        messages.error(request, "No output file available for download.")
        return redirect('upload_tables')

    output_path = file_record.output.path

    if file_record.date1 and file_record.date2:
        kw1 = file_record.date1.isocalendar()[1]
        kw2 = file_record.date2.isocalendar()[1]
        custom_filename = f"Comparison_Sitz_Rechts_VE_from_KW{kw1}_to_KW{kw2}.xlsx"
    else:
        custom_filename = "Comparison_Output.xlsx"

    try:
        with open(output_path, 'rb') as f:
            response = HttpResponse(
                f.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{smart_str(custom_filename)}"'
            return response
    except Exception as e:
        messages.error(request, f"Error preparing file for download: {str(e)}")
        return redirect('upload_tables')