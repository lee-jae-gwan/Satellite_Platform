from django.db import models

# Create your models here.
class SatelliteImage(models.Model):
    file = models.FileField(upload_to='satellite/')
    upload_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
    
