from django.db import models


class UploadedFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    query = models.CharField(max_length=200)
