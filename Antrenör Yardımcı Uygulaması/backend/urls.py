from django.contrib import admin
from django.urls import path
from core.views import (
    giris_yap, 
    cikis_yap, 
    kayit_ol, 
    ogrenci_paneli, 
    profil_duzenle, 
    antrenor_paneli,
    egzersiz_kutuphanesi,
    egzersiz_sil,
    egzersiz_duzenle  
)

urlpatterns = [
    path('admin/', admin.site.urls),                    # Yönetici Paneli
    path('', giris_yap, name='giris_yap'),              # Ana Sayfa (Giriş)
    path('kayit/', kayit_ol, name='kayit_ol'),          # Kayıt Olma Sayfası
    path('cikis/', cikis_yap, name='cikis_yap'),        # Çıkış İşlemi  
    path('panel/', ogrenci_paneli, name='ogrenci_paneli'),      # Öğrenci Sayfası
    path('profil-duzenle/', profil_duzenle, name='profil_duzenle'), # Profil Düzenleme
    path('coach/', antrenor_paneli, name='antrenor_paneli'),    # Antrenör Sayfası 
    path('kutuphane/', egzersiz_kutuphanesi, name='egzersiz_kutuphanesi'),
    path('kutuphane/sil/<int:id>/', egzersiz_sil, name='egzersiz_sil'),
    path('kutuphane/duzenle/<int:id>/', egzersiz_duzenle, name='egzersiz_duzenle'),
]