from django.shortcuts import render, redirect
from .models import Gorev, Profil
import datetime

def ogrenci_paneli(request):
    aktif_kullanici = request.user
    bugun = datetime.date.today()

    if not aktif_kullanici.is_authenticated:
        return render(request, 'ogrenci_paneli.html', {'hata': 'Lütfen giriş yapın'})

    # --- KAYDETME İŞLEMİ (POST) ---
    if request.method == "POST":
        secilen_id_listesi = request.POST.getlist('yapilanlar')
        
        # Sadece bugünün görevleri üzerinde işlem yap
        bugunku_tum_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun)
        
        try:
            profil = Profil.objects.get(user=aktif_kullanici)
        except Profil.DoesNotExist:
            profil = None

        for gorev in bugunku_tum_gorevler:
            str_id = str(gorev.id)
            
            if str_id in secilen_id_listesi:
                if not gorev.yapildi_mi: 
                    gorev.yapildi_mi = True
                    gorev.save()
                    if profil: profil.yildiz_bakiyesi += 1
            else:
                if gorev.yapildi_mi:
                    gorev.yapildi_mi = False
                    gorev.save()
                    if profil: profil.yildiz_bakiyesi -= 1
        
        if profil: profil.save()
        return redirect(ogrenci_paneli)

    # --- GÖRÜNTÜLEME İŞLEMİ (GET) ---
    # Tüm görevleri çekip burada ikiye ayırıyoruz
    tum_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun)
    
    antrenmanlar = tum_gorevler.filter(tur='ANTREMAN')
    beslenmeler = tum_gorevler.filter(tur='BESLENME')
    
    yildiz_sayisi = 0
    if hasattr(aktif_kullanici, 'profil'):
        yildiz_sayisi = aktif_kullanici.profil.yildiz_bakiyesi

    return render(request, 'ogrenci_paneli.html', {
        'antrenmanlar': antrenmanlar, # Ayrı paket
        'beslenmeler': beslenmeler,   # Ayrı paket
        'yildiz_sayisi': yildiz_sayisi
    })