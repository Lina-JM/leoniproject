from django.contrib import admin
from .models import FileUpload

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'file1', 'date1', 'file2', 'date2')