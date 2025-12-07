from django.db import models
from django.contrib.auth.models import User
import datetime

# 1. KULLANICI PROFİLİ
class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    boy = models.IntegerField(help_text="Santimetre cinsinden (Örn: 180)", verbose_name="Boy (cm)")
    kilo = models.FloatField(help_text="Kilogram cinsinden (Örn: 85.5)", verbose_name="Kilo (kg)")
    yildiz_bakiyesi = models.IntegerField(default=0, verbose_name="Yıldız Bakiyesi")
    
    class Meta:
        verbose_name = "Öğrenci Profili"
        verbose_name_plural = "Öğrenci Profilleri"
    
    def __str__(self):
        return f"{self.user.username} - {self.yildiz_bakiyesi} Yıldız"

# 2. GÖREVLER
class Gorev(models.Model):
    TUR_SECENEKLERI = (
        ('ANTREMAN', 'Antrenman'),
        ('BESLENME', 'Beslenme'),
    )
    
    ogrenci = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gorevler', verbose_name="Öğrenci")
    tarih = models.DateField(default=datetime.date.today, verbose_name="Tarih")
    baslik = models.CharField(max_length=200, verbose_name="Başlık")
    aciklama = models.TextField(verbose_name="Açıklama")
    tur = models.CharField(max_length=10, choices=TUR_SECENEKLERI, verbose_name="Tür")
    yapildi_mi = models.BooleanField(default=False, verbose_name="Tamamlandı mı?")

    class Meta:
        verbose_name = "Görev"
        verbose_name_plural = "Görev Listesi"

    def __str__(self):
        return f"{self.baslik} - {self.ogrenci.username}"

# 3. ÖDÜL SİSTEMİ
class Odul(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Ödül Adı")
    bedel = models.IntegerField(verbose_name="Yıldız Bedeli")
    resim = models.ImageField(upload_to='oduller/', blank=True, verbose_name="Görsel")

    class Meta:
        verbose_name = "Ödül"
        verbose_name_plural = "Ödül Kataloğu"

    def __str__(self):
        return self.isim

# 4. KAZANILAN ÖDÜLLER
class KazanilanOdul(models.Model):
    ogrenci = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Öğrenci")
    odul = models.ForeignKey(Odul, on_delete=models.CASCADE, verbose_name="Kazanılan Ödül")
    kazanilma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Kazanılma Tarihi")
    teslim_edildi = models.BooleanField(default=False, verbose_name="Teslim Edildi mi?")

    class Meta:
        verbose_name = "Kazanılan Ödül"
        verbose_name_plural = "Kazanılan Ödüller"

    def __str__(self):
        return f"{self.ogrenci.username} -> {self.odul.isim}"