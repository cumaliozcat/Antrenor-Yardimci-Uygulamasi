from django.contrib import admin
from .models import Profil, Gorev, Odul, KazanilanOdul

# Modelleri admin panelinde görünür yapıyoruz
admin.site.register(Profil)
admin.site.register(Gorev)
admin.site.register(Odul)
admin.site.register(KazanilanOdul)

