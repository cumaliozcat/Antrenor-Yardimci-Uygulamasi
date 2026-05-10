import os
import json
import pandas as pd
import joblib
import google.generativeai as genai
import datetime
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.rag_service import bota_sor

# Modellerin (Tek satırda toplandı)
from .models import Gorev, Profil, AntrenorProfil, Davet, Egzersiz, AntrenmanHareket, Mesaj

# Formların (HATAYI ÇÖZEN SATIR EKLENDİ 👇)
from .forms import *


def akilli_program_olustur(request):
    if request.method == 'POST':
        hedef = request.POST.get('hedef')
        seviye = request.POST.get('seviye')
        sakatlik = request.POST.get('sakatlik')

        # 1. Dosya Yollarını Dinamik Olarak Bulma
        app_klasoru = os.path.dirname(os.path.abspath(__file__))
        ai_klasoru = os.path.join(app_klasoru, 'ai_modelleri')

        # 2. Modelleri ve Dönüştürücüleri Yükleme
        model = joblib.load(os.path.join(ai_klasoru, 'antrenor_yapay_zeka.pkl'))
        le_hedef = joblib.load(os.path.join(ai_klasoru, 'le_hedef.pkl'))
        le_seviye = joblib.load(os.path.join(ai_klasoru, 'le_seviye.pkl'))
        le_sakatlik = joblib.load(os.path.join(ai_klasoru, 'le_sakatlik.pkl'))

        # 3. Metinleri sayılara çevirme
        hedef_encoded = le_hedef.transform([hedef])[0]
        seviye_encoded = le_seviye.transform([seviye])[0]
        sakatlik_encoded = le_sakatlik.transform([sakatlik])[0]

        # 4. Yapay Zeka Tahmini 
        tahmin_edilen_kategori = model.predict([[hedef_encoded, seviye_encoded, sakatlik_encoded]])[0]

        # 5. CSV Veritabanından Egzersizleri Çekme
        csv_yolu = os.path.join(ai_klasoru, 'egzersiz_veriseti.csv')
        df = pd.read_csv(csv_yolu)
        
        # Formdan gelen seçili kas gruplarını al (Örn: ['Legs', 'Arms', 'Chest'])
        secilen_kas_gruplari = request.POST.getlist('kas_grubu')

        if secilen_kas_gruplari:
            # 1. DURUM: ÖĞRENCİ BÖRDEN FAZLA BÖLGE SEÇTİ
            aranan_kaslar = [kas.lower().strip() for kas in secilen_kas_gruplari]
            filtrelenmis_df = df[df['Kategori'].str.lower().str.strip().isin(aranan_kaslar)]
            
            # EŞİT DAĞILIM ALGORİTMASI: Her seçili kas grubundan 3'er tane rastgele egzersiz al
            uygun_egzersizler_df = filtrelenmis_df.groupby('Kategori', group_keys=False).apply(lambda x: x.sample(min(len(x), 6)))
            
            gosterilecek_baslik = ", ".join(secilen_kas_gruplari) + " Programı"
            
        else:
            # 2. DURUM: ÖĞRENCİ BÖLGE SEÇMEDİ (Kontrol Yapay Zekada)
            uygun_egzersizler_df = df[df['Kategori'] == tahmin_edilen_kategori]
            gosterilecek_baslik = tahmin_edilen_kategori
            
            # Sadece tek bir bölge olduğu için o bölgenin içinden 6 tane rastgele seç
            


        # Pandas DataFrame'i HTML'in okuyabileceği bir sözlük listesine çeviriyoruz
        egzersiz_listesi = uygun_egzersizler_df.to_dict('records')
        # Egzersiz isimlerini hafızaya (session) alıyoruz ki tamamlama fonksiyonu görebilsin
        hareket_isimleri = uygun_egzersizler_df['Egzersiz_Adi'].tolist()
        request.session['ai_hareket_hafizasi'] = hareket_isimleri

        # 6. Sonuçları HTML sayfasına göndermek üzere paketleme
        context = {
            'hedef': hedef,
            'seviye': seviye,
            'kategori_adi': gosterilecek_baslik,
            'egzersiz_listesi': egzersiz_listesi
        }
        
        return render(request, 'program_sonuc.html', context)

    # GET İSTEĞİ: Boş formu göster
    return render(request, 'program_form.html')

# --- 1. GİRİŞ YAPMA ---
def giris_yap(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'antrenor_profili'):
            return redirect('antrenor_paneli')
        return redirect('ogrenci_paneli')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if hasattr(user, 'antrenor_profili'):
                    return redirect('antrenor_paneli')
                else:
                    return redirect('ogrenci_paneli')
        else:
            messages.error(request, "Hatalı kullanıcı adı veya şifre.")
    else:
        form = AuthenticationForm()

    return render(request, 'giris.html', {'form': form})


# --- 2. ÇIKIŞ YAPMA ---
def cikis_yap(request):
    logout(request)
    return redirect('giris_yap')


# --- 3. KAYIT OLMA ---
def kayit_ol(request):
    if request.user.is_authenticated:
        return redirect('ogrenci_paneli')

    if request.method == "POST":
        kullanici_adi = request.POST.get('username')
        sifre = request.POST.get('password')
        isim = request.POST.get('first_name')
        soyisim = request.POST.get('last_name')
        rol = request.POST.get('rol_secimi') 

        if User.objects.filter(username=kullanici_adi).exists():
            return render(request, 'kayit_ol.html', {'hata': 'Bu kullanıcı adı zaten alınmış.'})

        yeni_user = User.objects.create_user(username=kullanici_adi, password=sifre)
        yeni_user.first_name = isim
        yeni_user.last_name = soyisim
        
        if rol == 'antrenor':
            yeni_user.is_staff = True 
        
        yeni_user.save()

        if rol == 'ogrenci':
            boy = request.POST.get('boy')
            kilo = request.POST.get('kilo')
            yas = request.POST.get('yas_ogrenci')
            Profil.objects.create(user=yeni_user, boy=boy, kilo=kilo, yas=yas)
        
        elif rol == 'antrenor':
            yas = request.POST.get('yas_antrenor')
            uzmanlik = request.POST.get('uzmanlik')
            AntrenorProfil.objects.create(user=yeni_user, yas=yas, uzmanlik_alani=uzmanlik)

        return redirect('giris_yap')

    return render(request, 'kayit_ol.html')


# --- 4. ÖĞRENCİ PANELİ ---
def ogrenci_paneli(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    if hasattr(request.user, 'antrenor_profili'): return redirect('antrenor_paneli')

    aktif_kullanici = request.user
    bugun = datetime.date.today()

    # -- A) DAVET CEVAPLAMA VE RAPOR GÖNDERME --
    if request.method == "POST":
        # Davet Cevabı
        if 'davet_cevap' in request.POST:
            davet_id = request.POST.get('davet_id')
            cevap = request.POST.get('cevap')
            try:
                davet = Davet.objects.get(id=davet_id, alici=aktif_kullanici)
                if cevap == 'kabul':
                    davet.durum = 'KABUL'
                    davet.save()
                    profil = aktif_kullanici.profil
                    profil.antrenor = davet.gonderen
                    profil.save()
                    messages.success(request, f"{davet.gonderen.user.first_name} hocanın takımına katıldın!")
                else:
                    davet.durum = 'RED'
                    davet.save()
            except Davet.DoesNotExist: pass
            return redirect('ogrenci_paneli')

        # Günü Bitir (Rapor Gönder)
        elif 'gunu_bitir' in request.POST:
            # Bugüne ait antrenman ve beslenme görevlerini bul
            o_gunku_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun).exclude(durum='TAMAMLANDI')
            
            antrenman_gorevi = o_gunku_gorevler.filter(tur='ANTREMAN').first()
            akilli_antrenor_mu = False # Mesajı ayarlamak için bir kontrol değişkeni
            
            if antrenman_gorevi:
                secilen_hareketler = request.POST.getlist('hareket_id[]')
                
                # Önce hepsini sıfırla
                for hareket in antrenman_gorevi.hareketler.all():
                    hareket.yapildi_mi = False
                    hareket.save()
                
                # Seçilenleri işaretle
                for h_id in secilen_hareketler:
                    h = AntrenmanHareket.objects.get(id=h_id)
                    h.yapildi_mi = True
                    h.save()
                
                # --- İŞTE SİHİRLİ DOKUNUŞ BURASI ---
                if "Akıllı" in antrenman_gorevi.baslik:
                    antrenman_gorevi.durum = 'TAMAMLANDI' # Antrenörü es geç
                    akilli_antrenor_mu = True
                else:
                    antrenman_gorevi.durum = 'ONAY_BEKLIYOR' # Gerçek antrenöre gönder
                    
                antrenman_gorevi.save()

            beslenme_gorevi = o_gunku_gorevler.filter(tur='BESLENME').first()
            if beslenme_gorevi:
                beslenme_yapildi = request.POST.get('beslenme_durum') == 'on'
                beslenme_gorevi.yapildi_mi = beslenme_yapildi
                beslenme_gorevi.durum = 'ONAY_BEKLIYOR'
                beslenme_gorevi.save()

            # Duruma göre doğru mesajı gösterelim
            if akilli_antrenor_mu:
                messages.success(request, "Akıllı Antrenör programın başarıyla tamamlandı! Harika iş çıkardın. 🎉")
            else:
                messages.success(request, "Raporun antrenörüne gönderildi, onay bekleniyor.")
                
            return redirect('ogrenci_paneli')

    # -- B) GÖRÜNTÜLEME VERİLERİ --
    bugunku_gorevler = Gorev.objects.filter(ogrenci=aktif_kullanici, tarih=bugun).exclude(durum='TAMAMLANDI')
    antrenman_gorevi = bugunku_gorevler.filter(tur='ANTREMAN').first()
    beslenme_gorevi = bugunku_gorevler.filter(tur='BESLENME').first()
    
    yildiz_sayisi = 0
    gelen_davetler = []
    
    if hasattr(aktif_kullanici, 'profil'):
        yildiz_sayisi = aktif_kullanici.profil.yildiz_bakiyesi
        gelen_davetler = Davet.objects.filter(alici=aktif_kullanici, durum='BEKLIYOR')

    # Bildirim Sayısı
    okunmamis_mesaj = Mesaj.objects.filter(alici=aktif_kullanici, okundu_mu=False).count()

    return render(request, 'ogrenci_paneli.html', {
        'antrenman_gorevi': antrenman_gorevi,
        'beslenme_gorevi': beslenme_gorevi,
        'yildiz_sayisi': yildiz_sayisi,
        'davetler': gelen_davetler,
        'okunmamis_mesaj': okunmamis_mesaj
    })


# --- 5. ÖĞRENCİ PROFİL DÜZENLEME (GÜNCELLENMİŞ) ---
def profil_duzenle(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    if hasattr(request.user, 'antrenor_profili'): return redirect('antrenor_profil_duzenle')

    profil, _ = Profil.objects.get_or_create(user=request.user)

    # Formları Tanımla
    user_form = KullaniciGuncellemeForm(instance=request.user)
    profil_form = OgrenciProfilForm(instance=profil)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        # Hangi butona basıldı?
        if 'bilgi_guncelle' in request.POST:
            user_form = KullaniciGuncellemeForm(request.POST, instance=request.user)
            profil_form = OgrenciProfilForm(request.POST, instance=profil)
            if user_form.is_valid() and profil_form.is_valid():
                user_form.save()
                profil_form.save()
                messages.success(request, "Profil bilgilerin başarıyla güncellendi.")
                return redirect('profil_duzenle')
        
        elif 'sifre_degistir' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Oturum açık kalsın
                messages.success(request, "Şifren başarıyla değiştirildi.")
                return redirect('profil_duzenle')
            else:
                messages.error(request, "Şifre değiştirilirken hata oluştu. Kurallara dikkat et.")

    return render(request, 'profil_duzenle.html', {
        'user_form': user_form,
        'profil_form': profil_form,
        'password_form': password_form
    })


# --- 6. ANTRENÖR PANELİ (GÜNCELLENMİŞ) ---
def antrenor_paneli(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    try:
        aktif_antrenor = request.user.antrenor_profili
    except:
        return redirect('ogrenci_paneli')

    # -- A) ÖĞRENCİ ARAMA VE DAVET --
    arama_sonuclari = []
    aranan_isim = ""

    if request.method == "POST":
        if 'arama_yap' in request.POST:
            aranan_isim = request.POST.get('ogrenci_adi')
            if aranan_isim:
                arama_sonuclari = Profil.objects.filter(user__username__icontains=aranan_isim, antrenor__isnull=True)
        
        elif 'davet_gonder' in request.POST:
            hedef_id = request.POST.get('hedef_user_id')
            hedef_user = User.objects.get(id=hedef_id)
            if not Davet.objects.filter(gonderen=aktif_antrenor, alici=hedef_user, durum='BEKLIYOR').exists():
                Davet.objects.create(gonderen=aktif_antrenor, alici=hedef_user)
                messages.success(request, f"{hedef_user.username} kullanıcısına davet gönderildi.")
            else:
                messages.warning(request, "Zaten bekleyen bir davet var.")

    # -- B) LİSTELER --
    benim_ogrencilerim = aktif_antrenor.ogrenciler.all()

    # -- C) RAPORLARI GRUPLAMA VE DÜZELTME --
    bekleyenler = Gorev.objects.filter(
        ogrenci__profil__antrenor=aktif_antrenor, 
        durum='ONAY_BEKLIYOR'
    ).order_by('-tarih', '-id')

    onay_bekleyenler = []
    eklenen_kontrol = set()

    for gorev in bekleyenler:
        anahtar = (gorev.ogrenci.id, gorev.tarih)
        if anahtar not in eklenen_kontrol:
            onay_bekleyenler.append(gorev)
            eklenen_kontrol.add(anahtar)

    # -- D) BİLDİRİM HESAPLAMA --
    okunmamis_mesaj = Mesaj.objects.filter(alici=request.user, okundu_mu=False).count()

    return render(request, 'antrenor_paneli.html', {
        'ogrenciler': benim_ogrencilerim,
        'arama_sonuclari': arama_sonuclari,
        'aranan_isim': aranan_isim,
        'onay_bekleyenler': onay_bekleyenler,
        'okunmamis_mesaj': okunmamis_mesaj
    })


# --- 7. EGZERSİZ KÜTÜPHANESİ ---
def egzersiz_kutuphanesi(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    try:
        antrenor = request.user.antrenor_profili
    except:
        return redirect('ogrenci_paneli')

    if request.method == 'POST':
        form = EgzersizForm(request.POST)
        if form.is_valid():
            egzersiz = form.save(commit=False)
            egzersiz.olusturan = antrenor
            egzersiz.save()
            messages.success(request, "Egzersiz eklendi.")
            return redirect('egzersiz_kutuphanesi')
    else:
        form = EgzersizForm()

    egzersizler = Egzersiz.objects.filter(olusturan=antrenor).order_by('-olusturulma_tarihi')
    return render(request, 'egzersiz_kutuphanesi.html', {'form': form, 'egzersizler': egzersizler})

def egzersiz_sil(request, id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    egzersiz = get_object_or_404(Egzersiz, id=id, olusturan=request.user.antrenor_profili)
    egzersiz.delete()
    messages.info(request, "Egzersiz silindi.")
    return redirect('egzersiz_kutuphanesi')

def egzersiz_duzenle(request, id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    egzersiz = get_object_or_404(Egzersiz, id=id, olusturan=request.user.antrenor_profili)
    if request.method == 'POST':
        form = EgzersizForm(request.POST, instance=egzersiz)
        if form.is_valid():
            form.save()
            return redirect('egzersiz_kutuphanesi')
    else:
        form = EgzersizForm(instance=egzersiz)
    return render(request, 'egzersiz_duzenle.html', {'form': form})


# --- 8. ÖĞRENCİ YÖNET (GÖREV ATAMA) ---
def ogrenci_yonet(request, ogrenci_id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    try:
        antrenor = request.user.antrenor_profili
        ogrenci_profili = Profil.objects.get(user__id=ogrenci_id, antrenor=antrenor)
        ogrenci_user = ogrenci_profili.user
    except:
        return redirect('antrenor_paneli')

    if request.method == 'POST':
        tarih = datetime.date.today()
        
        # A) Antrenman Kaydı
        egzersiz_ids = request.POST.getlist('egzersiz_id[]')
        sets = request.POST.getlist('set[]')
        reps = request.POST.getlist('rep[]')
        
        if egzersiz_ids:
            antrenman_gorevi = Gorev.objects.create(
                ogrenci=ogrenci_user,
                baslik="GÜNLÜK ANTRENMAN PLANI",
                aciklama="Antrenörün senin için detaylı bir plan oluşturdu.",
                tur='ANTREMAN',
                tarih=tarih,
                durum='ATANDI'
            )
            for i in range(len(egzersiz_ids)):
                AntrenmanHareket.objects.create(
                    gorev=antrenman_gorevi,
                    egzersiz_id=egzersiz_ids[i],
                    set_sayisi=sets[i],
                    tekrar_sayisi=reps[i]
                )

        # B) Beslenme Kaydı
        beslenme_notu = request.POST.get('beslenme_notu')
        if beslenme_notu and beslenme_notu.strip():
            Gorev.objects.create(
                ogrenci=ogrenci_user,
                baslik="BESLENME PROGRAMI",
                aciklama=beslenme_notu,
                tur='BESLENME',
                tarih=tarih,
                durum='ATANDI'
            )
            
        messages.success(request, "Plan başarıyla gönderildi!")
        return redirect('antrenor_paneli')

    kutuphane = Egzersiz.objects.filter(olusturan=antrenor).order_by('isim')
    return render(request, 'ogrenci_yonet.html', {'ogrenci': ogrenci_user, 'kutuphane': kutuphane})


# --- 9. ÖĞRENCİ KONTROL VE ONAY ---
def ogrenci_kontrol(request, gorev_id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    baz_gorev = get_object_or_404(Gorev, id=gorev_id)
    
    if baz_gorev.ogrenci.profil.antrenor != request.user.antrenor_profili:
        return redirect('antrenor_paneli')

    # --- SİHİRLİ DOKUNUŞ BURADA ---
    # .order_by('-id') diyerek aynı gün içinde oluşturulmuş görevlerden EN YENİ olanı (son yazdığını) seçmesini garantiliyoruz.
    o_gunku_gorevler = Gorev.objects.filter(
        ogrenci=baz_gorev.ogrenci, 
        tarih=baz_gorev.tarih
    ).order_by('-id')
    
    antrenman_gorevi = None
    for g in o_gunku_gorevler.filter(tur='ANTREMAN'):
        if g.hareketler.exists(): # İçinde egzersiz olan en güncel görev
            antrenman_gorevi = g
            break
            
    if not antrenman_gorevi:
        antrenman_gorevi = o_gunku_gorevler.filter(tur='ANTREMAN').first()

    beslenme_gorevi = o_gunku_gorevler.filter(tur='BESLENME').first()

    if request.method == 'POST':
        yildiz_miktari = int(request.POST.get('yildiz_miktari', 0))
        
        profil = baz_gorev.ogrenci.profil
        profil.yildiz_bakiyesi += yildiz_miktari
        profil.save()
        
        for g in o_gunku_gorevler:
            g.durum = 'TAMAMLANDI'
            g.save()

        messages.success(request, f"Rapor onaylandı, gün kapatıldı ve {yildiz_miktari} yıldız gönderildi.")
        return redirect('antrenor_paneli')

    return render(request, 'ogrenci_kontrol.html', {
        'ogrenci': baz_gorev.ogrenci,
        'tarih': baz_gorev.tarih,
        'antrenman': antrenman_gorevi,
        'beslenme': beslenme_gorevi
    })


# --- 10. MESAJLAŞMA SİSTEMİ ---
def mesaj_kutusu(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    try:
        antrenor = request.user.antrenor_profili
    except:
        if hasattr(request.user, 'profil') and request.user.profil.antrenor:
            hoca_id = request.user.profil.antrenor.user.id
            return redirect('sohbet_odasi', user_id=hoca_id)
        return redirect('ogrenci_paneli')

    ogrenciler = antrenor.ogrenciler.all()
    sohbet_listesi = []

    for ogr in ogrenciler:
        son_mesaj = Mesaj.objects.filter(
            (Q(gonderen=request.user) & Q(alici=ogr.user)) |
            (Q(gonderen=ogr.user) & Q(alici=request.user))
        ).last()
        
        okunmamis = Mesaj.objects.filter(gonderen=ogr.user, alici=request.user, okundu_mu=False).count()
        
        sohbet_listesi.append({
            'user': ogr.user,
            'son_mesaj': son_mesaj,
            'okunmamis': okunmamis
        })

    return render(request, 'mesaj_kutusu.html', {'sohbet_listesi': sohbet_listesi})


def sohbet_odasi(request, user_id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    
    karshi_taraf = get_object_or_404(User, id=user_id)
    ben = request.user

    izin_var = False
    if hasattr(ben, 'profil'):
        if ben.profil.antrenor and ben.profil.antrenor.user == karshi_taraf:
            izin_var = True
    elif hasattr(ben, 'antrenor_profili'):
        if ben.antrenor_profili.ogrenciler.filter(user=karshi_taraf).exists():
            izin_var = True
            
    if not izin_var:
        messages.error(request, "Bu kişiyle mesajlaşma yetkiniz yok.")
        if hasattr(ben, 'antrenor_profili'): return redirect('mesaj_kutusu')
        return redirect('ogrenci_paneli')

    if request.method == "POST":
        icerik = request.POST.get('mesaj_icerigi')
        if icerik and icerik.strip():
            Mesaj.objects.create(gonderen=ben, alici=karshi_taraf, icerik=icerik)
            return redirect('sohbet_odasi', user_id=user_id)

    mesajlar = Mesaj.objects.filter(
        (Q(gonderen=ben) & Q(alici=karshi_taraf)) |
        (Q(gonderen=karshi_taraf) & Q(alici=ben))
    ).order_by('tarih')

    okunmamislar = mesajlar.filter(gonderen=karshi_taraf, okundu_mu=False)
    for m in okunmamislar:
        m.okundu_mu = True
        m.save()

    return render(request, 'sohbet.html', {
        'karshi_taraf': karshi_taraf,
        'mesajlar': mesajlar
    })


# --- 11. YAPAY ZEKA ASİSTANI (CHATBOT) ---
@csrf_exempt
def chatbot_view(request):
    # Sistem sadece POST (JavaScript'ten gelen arka plan isteği) kabul edecek
    if request.method == 'POST':
        try:
            # JavaScript'in gönderdiği JSON paketini aç
            data = json.loads(request.body)
            kullanici_sorusu = data.get('mesaj', '')
            
            if kullanici_sorusu:
                # Soruyu RAG modelimize (Gemini + FAISS) gönder
                bot_cevabi = bota_sor(kullanici_sorusu)
                
                # Gelen cevabı tekrar JSON formatında arayüze fırlat
                return JsonResponse({'cevap': bot_cevabi})
            else:
                return JsonResponse({'error': 'Boş mesaj gönderilemez.'}, status=400)
                
        except Exception as e:
            # Beklenmedik bir hata olursa konsola çökme, hatayı JavaScript'e ilet
            return JsonResponse({'error': f"Yapay zeka servisinde hata: {str(e)}"}, status=500)
            
    # Eğer birisi tarayıcıya "site.com/chatbot/" yazıp doğrudan girmeye çalışırsa 
    # ona sayfa göstermek yerine uyarı veriyoruz (Çünkü arayüz zaten öğrenci panelinde)
    return JsonResponse({'error': 'Bu sayfaya doğrudan erişim izni yoktur.'}, status=405)


# --- 12. TAKIM YÖNETİMİ (SİLME VE AYRILMA) ---
def ogrenci_sil(request, ogrenci_id):
    if not request.user.is_authenticated: return redirect('giris_yap')
    if not hasattr(request.user, 'antrenor_profili'): return redirect('ogrenci_paneli')
    
    hedef_ogrenci = get_object_or_404(User, id=ogrenci_id)
    
    if hedef_ogrenci.profil.antrenor == request.user.antrenor_profili:
        hedef_ogrenci.profil.antrenor = None
        hedef_ogrenci.profil.save()
        messages.success(request, f"{hedef_ogrenci.first_name} takımdan çıkarıldı.")
    else:
        messages.error(request, "Bu işlem için yetkiniz yok.")
    return redirect('antrenor_paneli')

def takimdan_ayril(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    if hasattr(request.user, 'antrenor_profili'): return redirect('antrenor_paneli')
        
    profil = request.user.profil
    if profil.antrenor:
        eski_hoca = profil.antrenor.user.first_name
        profil.antrenor = None
        profil.save()
        messages.info(request, f"{eski_hoca} hocanın takımından ayrıldın.")
    
    return redirect('ogrenci_paneli')


# --- 13. ANTRENÖR PROFİL DÜZENLEME ---
def antrenor_profil_duzenle(request):
    if not request.user.is_authenticated: return redirect('giris_yap')
    try:
        profil = request.user.antrenor_profili
    except:
        return redirect('ogrenci_paneli')

    user_form = KullaniciGuncellemeForm(instance=request.user)
    profil_form = AntrenorProfilForm(instance=profil)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        if 'bilgi_guncelle' in request.POST:
            user_form = KullaniciGuncellemeForm(request.POST, instance=request.user)
            profil_form = AntrenorProfilForm(request.POST, instance=profil)
            if user_form.is_valid() and profil_form.is_valid():
                user_form.save()
                profil_form.save()
                messages.success(request, "Antrenör profilin güncellendi.")
                return redirect('antrenor_profil_duzenle')
        
        elif 'sifre_degistir' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Şifren başarıyla değiştirildi.")
                return redirect('antrenor_profil_duzenle')
            else:
                messages.error(request, "Şifre hatası. Lütfen tekrar dene.")

    return render(request, 'antrenor_profil_duzenle.html', {
        'user_form': user_form,
        'profil_form': profil_form,
        'password_form': password_form
    })

def ai_program_kaydet(request):
    if request.method == 'POST':
        kategori = request.POST.get('kategori', 'Genel')
        # Sadece checkbox ile işaretlenmiş egzersizleri alıyoruz!
        secilen_egzersizler = request.POST.getlist('secilen_egzersizler')
        
        # Eğer öğrenci hiçbir şey seçmeden kaydet derse uyar ve geri gönder
        if not secilen_egzersizler:
            messages.error(request, "Lütfen programa eklemek için en az bir egzersiz seçin!")
            return redirect('akilli_program')

        # --- AI KOÇ SİSTEMİNİ YARATALIM ---
        # Veritabanında "ai_koc" adında gizli bir sistem kullanıcısı var mı bak, yoksa yarat
        ai_user, created = User.objects.get_or_create(
            username='ai_koc', 
            defaults={'first_name': '🤖 Akıllı', 'last_name': 'Antrenör'}
        )
        
        # Bu sistem kullanıcısını bir Antrenöre dönüştür
        ai_profil, created = AntrenorProfil.objects.get_or_create(
            user=ai_user, 
            defaults={'yas': 99, 'uzmanlik_alani': 'FITNESS'}
        )

        # 1. Ana Görevi (Antrenmanı) Oluştur
        yeni_gorev = Gorev.objects.create(
            ogrenci=request.user,
            baslik=f"🤖 AI Koç: {kategori} Programı",
            aciklama="Akıllı Antrenör tarafından sizin seçimleriniz doğrultusunda özel olarak oluşturuldu.",
            tur='ANTREMAN',
            durum='ATANDI'
        )
        
        # 2. Seçilen Egzersizleri AI Koç Kütüphanesine ve Göreve Ekle
        for ad in secilen_egzersizler:
            # Önce bu egzersizi AI Koç oluşturmuş mu diye bakıyoruz
            egzersiz_db = Egzersiz.objects.filter(isim=ad, olusturan=ai_profil).first()
            
            # Yoksa, sadece AI Koç'un üstüne kaydet (Diğer antrenörleri etkilemez)
            if not egzersiz_db:
                egzersiz_db = Egzersiz.objects.create(
                    olusturan=ai_profil,
                    isim=ad,
                    aciklama="Yapay Zeka kütüphanesinden otomatik eklendi."
                )
            
            # Egzersizi görevin içine ekle
            AntrenmanHareket.objects.create(
                gorev=yeni_gorev,
                egzersiz=egzersiz_db,
                set_sayisi="3",      
                tekrar_sayisi="12"   
            )
                
        messages.success(request, "🤖 AI Koç programınız başarıyla oluşturuldu ve görevlerinize eklendi!")
        return redirect('ogrenci_paneli')
        
    return redirect('akilli_program')
        


def akilli_program_tamamla(request):
    if request.method == 'GET':
        
        # 1. Hafızaya aldığımız hareketleri geri çağırıyoruz
        # Eğer hafızada bir şey yoksa boş liste döner
        secilen_hareketler = request.session.get('ai_hareket_hafizasi', [])
        
        # 2. Hareketleri aralarına virgül koyarak şık bir metin haline getiriyoruz
        hareket_metni = ", ".join(secilen_hareketler)
        
        # 3. Yeni açıklama metnimizi oluşturuyoruz
        yeni_aciklama = f"Seçilen Hareketler: {hareket_metni}"
        
        # Görevi oluşturuyoruz
        Gorev.objects.create(
            ogrenci=request.user, 
            baslik="Akıllı Antrenör Programı",
            aciklama=yeni_aciklama,  # Artık sabit yazı yerine hareketler görünecek!
            durum='BEKLIYOR',
            tarih=date.today(),
            tur='ANTREMAN'
        )
        
        # Hafızayı temizliyoruz (sıradaki programlar için)
        if 'ai_hareket_hafizasi' in request.session:
            del request.session['ai_hareket_hafizasi']
            
        messages.success(request, "Yapay zeka programı ana sayfadaki görevlerine eklendi! Günü bitir dediğinde antrenör onayı olmadan direkt tamamlanacak. 🎉")
        
        return redirect('ogrenci_paneli')
    
    