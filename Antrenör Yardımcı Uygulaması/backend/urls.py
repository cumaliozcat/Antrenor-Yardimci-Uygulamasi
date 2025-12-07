from django.contrib import admin
from django.urls import path
from core.views import ogrenci_paneli  # <-- Yeni eklediğimiz sayfa

urlpatterns = [
    path('admin/', admin.site.urls),     # Yönetici paneli linki
    path('', ogrenci_paneli),            # Ana sayfa (Boş bırakınca direkt açılır)
]