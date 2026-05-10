from django.contrib import admin
from .models import Profil, Gorev, Odul, KazanilanOdul, Egzersiz

# Mevcut modelleri admin panelinde görünür yapıyoruz
admin.site.register(Profil)
admin.site.register(Gorev)
admin.site.register(Odul)
admin.site.register(KazanilanOdul)

# Egzersiz modelini özel görünümüyle kaydediyoruz
# İŞTE EKSİK OLAN SATIR BURASIYDI:
@admin.register(Egzersiz)
class EgzersizAdmin(admin.ModelAdmin):
    # Admin panelinde yan yana hangi sütunların görüneceğini belirliyoruz
    list_display = ('isim', 'olusturan', 'id')
    # Arama çubuğu ekliyoruz (Egzersiz adına göre arama yapmak için)
    search_fields = ('isim',)