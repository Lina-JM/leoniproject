from django.db import models 
from django.core.exceptions import ValidationError

def validate_excel_file(file):
    if not file.name.endswith(('.xls', '.xlsx')):
        raise ValidationError('Only Excel files are allowed (.xls, .xlsx)')

class FileUpload(models.Model):
    file1 = models.FileField(upload_to='uploads/', validators=[validate_excel_file])
    date1 = models.DateField(blank=False)  # Required date from user
    file2 = models.FileField(upload_to='uploads/', validators=[validate_excel_file])
    date2 = models.DateField(blank=False)  # Required date from user
    output = models.FileField(upload_to='outputs/', blank=True, null=True)


    def __str__(self):
        return f"Upload {self.id} - File1: {self.date1}, File2: {self.date2}"