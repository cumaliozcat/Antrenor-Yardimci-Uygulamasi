from django.db import models
from django.contrib.auth.models import User
import datetime

# --- 1. ANTRENÖR PROFİLİ (EN ÜSTTE OLMALI) ---
# Profil modeli buna bağlanacağı için Python önce bunu okumalı.
class AntrenorProfil(models.Model):
    UZMANLIKLAR = (
        ('FITNESS', 'Fitness & Vücut Geliştirme'),
        ('PILATES', 'Pilates & Yoga'),
        ('KILO_VERME', 'Kilo Verme & Diyet'),
        ('KONDISYON', 'Atletik Performans & Kondisyon'),
        ('REHAB', 'Fizik Tedavi & Rehabilitasyon'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='antrenor_profili', verbose_name="Antrenör")
    yas = models.IntegerField(verbose_name="Yaş")
    uzmanlik_alani = models.CharField(max_length=20, choices=UZMANLIKLAR, verbose_name="Uzmanlık Alanı")

    class Meta:
        verbose_name = "Antrenör Profili"
        verbose_name_plural = "Antrenör Profilleri"

    def __str__(self):
        return f"Coach: {self.user.username}"


# --- 2. ÖĞRENCİ PROFİLİ ---
# AntrenorProfil artık yukarıda tanımlı olduğu için hata vermez.
class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil', verbose_name="Kullanıcı")
    
    
    antrenor = models.ForeignKey(AntrenorProfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='ogrenciler', verbose_name="Antrenörü")
    
    boy = models.IntegerField(help_text="Santimetre (Örn: 180)", verbose_name="Boy (cm)")
    kilo = models.FloatField(help_text="Kilogram (Örn: 85.5)", verbose_name="Kilo (kg)")
    yas = models.IntegerField(default=18, verbose_name="Yaş")
    yildiz_bakiyesi = models.IntegerField(default=0, verbose_name="Yıldız Bakiyesi")
    
    class Meta:
        verbose_name = "Öğrenci Profili"
        verbose_name_plural = "Öğrenci Profilleri"
    
    def __str__(self):
        return f"Öğrenci: {self.user.username}"


# --- 3. DAVET SİSTEMİ ---
class Davet(models.Model):
    DURUMLAR = (
        ('BEKLIYOR', 'Bekliyor'),
        ('KABUL', 'Kabul Edildi'),
        ('RED', 'Reddedildi'),
    )
    
    gonderen = models.ForeignKey(AntrenorProfil, on_delete=models.CASCADE, verbose_name="Antrenör")
    alici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gelen_davetler', verbose_name="Öğrenci")
    durum = models.CharField(max_length=10, choices=DURUMLAR, default='BEKLIYOR', verbose_name="Durum")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Gönderilme Tarihi")

    class Meta:
        verbose_name = "Antrenör Daveti"
        verbose_name_plural = "Antrenör Davetleri"

    def __str__(self):
        return f"{self.gonderen.user.username} -> {self.alici.username} ({self.durum})"


# --- 4. GÖREVLER ---
class Gorev(models.Model):
    TUR_SECENEKLERI = (
        ('ANTREMAN', 'Antrenman'),
        ('BESLENME', 'Beslenme'),
    )
    DURUM_SECENEKLERI = (
        ('ATANDI', 'Atandı (Yapılmayı Bekliyor)'),
        ('ONAY_BEKLIYOR', 'Öğrenci Bitirdi (Hoca Onayı Bekliyor)'),
        ('TAMAMLANDI', 'Onaylandı ve Bitti'),
    )
    
    ogrenci = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gorevler', verbose_name="Öğrenci")
    tarih = models.DateField(default=datetime.date.today, verbose_name="Tarih")
    baslik = models.CharField(max_length=200, verbose_name="Başlık")
    aciklama = models.TextField(verbose_name="Açıklama")
    tur = models.CharField(max_length=10, choices=TUR_SECENEKLERI, verbose_name="Tür")
    durum = models.CharField(max_length=15, choices=DURUM_SECENEKLERI, default='ATANDI', verbose_name="Durum")
    yapildi_mi = models.BooleanField(default=False, verbose_name="Genel Tamamlanma") 

    class Meta:
        verbose_name = "Görev"
        verbose_name_plural = "Görev Listesi"

    def __str__(self):
        return f"{self.baslik} - {self.ogrenci.username} ({self.durum})"


# --- 5. ÖDÜL SİSTEMİ ---
class Odul(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Ödül Adı")
    bedel = models.IntegerField(verbose_name="Yıldız Bedeli")
    resim = models.ImageField(upload_to='oduller/', blank=True, verbose_name="Görsel")

    class Meta:
        verbose_name = "Ödül"
        verbose_name_plural = "Ödül Kataloğu"

    def __str__(self):
        return self.isim


# --- 6. KAZANILAN ÖDÜLLER ---
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
    # --- 7. EGZERSİZ KÜTÜPHANESİ (YENİ) ---
class Egzersiz(models.Model):
    olusturan = models.ForeignKey(AntrenorProfil, on_delete=models.CASCADE, related_name='egzersizler', verbose_name="Antrenör")
    isim = models.CharField(max_length=150, verbose_name="Egzersiz Adı")
    aciklama = models.TextField(verbose_name="Nasıl Yapılır?", blank=True)
    video_link = models.URLField(blank=True, null=True, verbose_name="Video Linki (Opsiyonel)")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Egzersiz"
        verbose_name_plural = "Egzersiz Kütüphanesi"

    def __str__(self):
        return f"{self.isim} ({self.olusturan.user.username})"
    # --- 8. ANTRENMAN DETAYLARI (YENİ) ---
class AntrenmanHareket(models.Model):   
    gorev = models.ForeignKey(Gorev, on_delete=models.CASCADE, related_name='hareketler')
    egzersiz = models.ForeignKey('Egzersiz', on_delete=models.CASCADE)
    set_sayisi = models.CharField(max_length=50, verbose_name="Set")
    tekrar_sayisi = models.CharField(max_length=50, verbose_name="Tekrar")
    yapildi_mi = models.BooleanField(default=False, verbose_name="Yapıldı")

    def __str__(self):
        return f"{self.egzersiz.isim} - {self.gorev.baslik}"
    
    # --- 9. MESAJLAŞMA SİSTEMİ  ---
class Mesaj(models.Model):
    gonderen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gonderilen_mesajlar')
    alici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alinan_mesajlar')
    icerik = models.TextField(verbose_name="Mesaj İçeriği")
    tarih = models.DateTimeField(auto_now_add=True)
    okundu_mu = models.BooleanField(default=False)

    class Meta:
        ordering = ['tarih'] 
        verbose_name = "Mesaj"
        verbose_name_plural = "Mesajlar"

    def __str__(self):
        return f"{self.gonderen} -> {self.alici}: {self.icerik[:20]}"