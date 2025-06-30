import io
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import FileUpload
from .utils import clean_value, build_data_dict
from datetime import date

class FileUploadTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create sample Excel files content (minimal valid content)
        self.file_content = (
            b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x9f\x8a\x9b'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00'
            b'\x00[Content_Types].xml\xae\x91\xcbn\x83\x10\x86\xef\xfb\x0f'
        )
        self.file1 = SimpleUploadedFile("file1.xlsx", self.file_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.file2 = SimpleUploadedFile("file2.xlsx", self.file_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_index_get(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_file_upload_post_invalid_dates(self):
        response = self.client.post(reverse('index'), {
            'date1': '2025-W20',
            'date2': '2025-W21',
            'file1': self.file1,
            'file2': self.file2,
        }, follow=True)
        # Since date1 <= date2 is invalid, expect error message
        self.assertContains(response, "KW(X) must be later than KW(X-N)")

    def test_clean_value(self):
        self.assertEqual(clean_value('  abc\xa0 '), 'ABC')

    def test_build_data_dict(self):
        import pandas as pd
        data = {
            'Component No.': ['A1', 'B2', None],
            'Customer Part No': ['C1', 'D2', 'E3'],
            'Req. Qty': [10, 20, 30],
            'Description': ['desc1', 'desc2', 'desc3']
        }
        df = pd.DataFrame(data)
        result = build_data_dict(df, component_col=0, customer_col=1, quantity_col=2, description_col=3)
        self.assertIn(('A1', 'C1'), result)
        self.assertIn(('B2', 'D2'), result)
        self.assertNotIn((None, 'E3'), result)

    def test_delete_upload(self):
        upload = FileUpload.objects.create(
            file1=self.file1,
            file2=self.file2,
            date1=date(2025, 5, 19),
            date2=date(2025, 5, 12)
        )
        response = self.client.post(reverse('delete_upload', args=[upload.id]), follow=True)
        self.assertRedirects(response, reverse('upload_tables'))
        self.assertFalse(FileUpload.objects.filter(id=upload.id).exists())

    def test_update_upload(self):
        upload = FileUpload.objects.create(
            file1=self.file1,
            file2=self.file2,
            date1=date(2025, 5, 19),
            date2=date(2025, 5, 12)
        )
        response = self.client.post(reverse('update_upload', args=[upload.id]), {
            'date1': '2025-W22',
            'date2': '2025-W21',
            'file1': self.file1,
            'file2': self.file2,
        }, follow=True)
        self.assertRedirects(response, reverse('upload_tables'))

    def test_download_output(self):
        upload = FileUpload.objects.create(
            file1=self.file1,
            file2=self.file2,
            date1=date(2025, 5, 19),
            date2=date(2025, 5, 12)
        )
        upload.output.save('output.xlsx', self.file1)
        response = self.client.get(reverse('download_output', args=[upload.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_api_get(self):
        response = self.client.get(reverse('api-uploads'))
        self.assertEqual(response.status_code, 200)

    def test_api_post(self):
        response = self.client.post(reverse('api-uploads'), {
            'file1': self.file1,
            'file2': self.file2,
            'date1': '2025-05-19',
            'date2': '2025-05-12',
        }, format='multipart')
        self.assertIn(response.status_code, [200, 201])
