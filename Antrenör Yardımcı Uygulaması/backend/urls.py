from django.contrib import admin
from django.urls import path
from core.views import ogrenci_paneli, giris_yap, cikis_yap
from core.views import ogrenci_paneli, giris_yap, cikis_yap, profil_duzenle

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', giris_yap, name='giris_yap'),
    path('panel/', ogrenci_paneli, name='ogrenci_paneli'),
    path('profil-duzenle/', profil_duzenle, name='profil_duzenle'), 
    path('cikis/', cikis_yap, name='cikis_yap'),
]