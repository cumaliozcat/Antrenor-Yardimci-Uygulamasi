import os
import pandas as pd
import google.generativeai as genai  # BÜYÜK DEĞİŞİKLİK BURADA: Doğrudan Google'ı bağladık!
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from .models import Egzersiz

def bilgi_havuzunu_olustur():
    # 1. PDF Belgelerini Yükle
    loader = DirectoryLoader('rag_belgeleri/', glob="./*.pdf", loader_cls=PyPDFLoader)
    pdf_belgeleri = loader.load()

    egzersiz_verileri = []
    
    # 2. Django Admin Panelindeki Egzersizler
    tum_egzersizler = Egzersiz.objects.all()
    for e in tum_egzersizler:
        # SADECE AÇIKLAMASI DOLU OLANLARI HAVUZA EKLE!
        if e.aciklama and len(e.aciklama.strip()) > 10: 
            metin = f"Egzersiz Adı: {e.isim}\nAçıklama: {e.aciklama}\nAntrenör: {e.olusturan.user.username}"
            egzersiz_verileri.append(metin)
        
    # 3. ALTIN MADENİ: CSV Veri Setini Oku ve Havuza Ekle <-- YENİ EKLENEN KISIM
    # Dinamik olarak core/ai_modelleri/egzersiz_veriseti.csv yolunu buluyoruz
    csv_yolu = os.path.join(os.path.dirname(__file__), 'ai_modelleri', 'egzersiz_veriseti.csv')
    
    if os.path.exists(csv_yolu):
        try:
            # CSV'yi okuyoruz. (Hata verirse encoding='windows-1254' yapabilirsin)
            df = pd.read_csv(csv_yolu, encoding='utf-8')
            for index, row in df.iterrows():
                # Satırdaki tüm dolu sütunları (Örn: Ekipman: Dumbbell) alt alta birleştir
                satir_metni = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                egzersiz_verileri.append(satir_metni)
            print(f"HARİKA: {len(df)} adet CSV egzersizi havuza başarıyla yüklendi!")
        except Exception as e:
            print(f"CSV okunurken hata oluştu: {e}")
    else:
        print("CSV dosyası bulunamadı, bu adım atlanıyor.")

    # 4. Parçalama ve Temizleme İşlemleri
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    parcalanmis_pdf = text_splitter.split_documents(pdf_belgeleri)
    parcalanmis_egzersizler = text_splitter.create_documents(egzersiz_verileri)

    tum_icerik_ham = parcalanmis_pdf + parcalanmis_egzersizler

    # Çöp Veri Filtresi
    temiz_icerik = []
    for belge in tum_icerik_ham:
        saf_metin = belge.page_content.replace(".", "").strip()
        if len(saf_metin) > 50 and "DÜŞÜNELİM-YAZALIM" not in belge.page_content:
            temiz_icerik.append(belge)

    # 5. Beyne (Veritabanına) Kaydetme
    embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    vektor_db = FAISS.from_documents(temiz_icerik, embeddings)

    vektor_db.save_local("faiss_index")
    print(f"Bilgi havuzu temizlendi! Toplam {len(temiz_icerik)} parça zeka kaydedildi!")

    return vektor_db


def bota_sor(kullanici_sorusu):
    # 1. Modelleri ve Beyni Yükle
    embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    vektor_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

    # 2. ARAMA YAP (PDF'lerden ve veritabanından en alakalı 3 metni bul)
    bulunan_belgeler = vektor_db.similarity_search(kullanici_sorusu, k=10)
    birlestirilmis_metin = "\n\n".join([belge.page_content for belge in bulunan_belgeler])

    # 3. PROMPT OLUŞTUR
    hazir_prompt = f"""
    Sen profesyonel bir spor koçusun ve "Antrenör Yardımcısı" uygulamasının akıllı asistanısın.
    Sana verilen aşağıdaki kaynak metinleri kullanarak öğrencinin sorusunu cevapla.
    Eğer sorunun cevabı kaynak metinlerde yoksa, "Bu konuda kesin bir bilgim yok, lütfen kendi antrenörüne danış" de.
    Öğrenciye motive edici ve samimi bir dille hitap et.
    
    Kaynak Metinler:
    {birlestirilmis_metin}

    Öğrencinin Sorusu: {kullanici_sorusu}
    
    Cevabın:
    """

    # 4. DOĞRUDAN GOOGLE API İLE CEVAP ÜRET (Sorunsuz kısım)
    genai.configure(api_key="AIzaSyCMWNI1LP6wT3-lZe_c0ReGa10PUjDCqno")
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    cevap = model.generate_content(hazir_prompt)
    
    return cevap.text