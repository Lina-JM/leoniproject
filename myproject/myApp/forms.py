from django import forms
from .models import FileUpload
from django.utils.safestring import mark_safe

class ExcelFileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['file1', 'file2', 'date1', 'date2']
        widgets = {
            'date1': forms.DateInput(
                attrs={'type': 'week', 'class': 'form-control'},
                format='%Y-W%W'
            ),
            'date2': forms.DateInput(
                attrs={'type': 'week', 'class': 'form-control'},
                format='%Y-W%W'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date1'].input_formats = ['%Y-W%W']
        self.fields['date2'].input_formats = ['%Y-W%W']

    def clean_file1(self):
        file = self.cleaned_data.get('file1')
        if file and not file.name.endswith(('.xls', '.xlsx')):
            raise forms.ValidationError(mark_safe('<span style="color:red">BOOM(X-N) must be an Excel file (.xls or .xlsx)</span>'))
        return file

    def clean_file2(self):
        file = self.cleaned_data.get('file2')
        if file and not file.name.endswith(('.xls', '.xlsx')):
            raise forms.ValidationError(mark_safe('<span style="color:red">BOOM(X-N) must be an Excel file (.xls or .xlsx)</span>'))
        return file

    def clean(self):
        # Only file validation remains
        return super().clean()