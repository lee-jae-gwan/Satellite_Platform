from rest_framework import serializers
from .models import SatelliteImage

class SatelliteImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SatelliteImage
        fields = ['id','file','upload_at']

        