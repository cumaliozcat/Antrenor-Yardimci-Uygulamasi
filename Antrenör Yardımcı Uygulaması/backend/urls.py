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
    egzersiz_duzenle,
    ogrenci_yonet,
    ogrenci_kontrol,
    mesaj_kutusu,  
    sohbet_odasi,
    yapay_zeka_sor,
    ogrenci_sil,      
    takimdan_ayril,
    antrenor_profil_duzenle,
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
    path('yonet/<int:ogrenci_id>/', ogrenci_yonet, name='ogrenci_yonet'),
    path('kontrol/<int:gorev_id>/', ogrenci_kontrol, name='ogrenci_kontrol'),
    path('mesajlar/', mesaj_kutusu, name='mesaj_kutusu'),
    path('sohbet/<int:user_id>/', sohbet_odasi, name='sohbet_odasi'),
    path('api/chatbot/', yapay_zeka_sor, name='yapay_zeka_sor'),
    path('ogrenci-sil/<int:ogrenci_id>/', ogrenci_sil, name='ogrenci_sil'),
    path('takimdan-ayril/', takimdan_ayril, name='takimdan_ayril'),
    path('profil-duzenle/', profil_duzenle, name='profil_duzenle'), # Mevcut
    path('koc-profil-duzenle/', antrenor_profil_duzenle, name='antrenor_profil_duzenle'),
]