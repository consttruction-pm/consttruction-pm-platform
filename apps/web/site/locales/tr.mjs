// Turkish public site copy. Publishes all 25 approved routes.
export default {
  code: "tr",
  htmlLang: "tr-TR",
  dir: "ltr",
  prefix: "tr/",
  label: "Türkçe",
  nav: {
    home: "Ana sayfa",
    platform: "Platform",
    features: "Özellikler",
    solutions: "Çözümler",
    pricing: "Fiyatlandırma",
    resources: "Kaynaklar",
    documentation: "Dokümantasyon",
    help: "Yardım",
    about: "Hakkımızda",
    contact: "İletişim",
    "faq": "Sık sorulan sorular",
    "integrations": "Entegrasyonlar",
    "security": "Güvenlik",
    "get-started": "Başlangıç",
    "privacy": "Gizlilik",
    "terms": "Koşullar",
  },
  footer: {
    tagline: "© 2026 CUBI Platform · Planla. Kontrol et. Daha akıllı inşa et.",
    groups: [
      { title: "Ürün", links: [["features", "Özellikler"], ["platform", "Platform"], ["pricing", "Fiyatlandırma"]] },
      { title: "Öğren", links: [["documentation", "Dokümantasyon"], ["resources", "Kaynaklar"]] },
      { title: "Şirket", links: [["about", "Hakkımızda"], ["contact", "İletişim"]] },
    ],
  },
  cta: { label: "CUBI çalışma alanını aç", href: "/app/" },
  pages: [
    {
      id: "home",
      path: "",
      title: "CUBI | İnşaat planlama ve proje kontrolü bir arada",
      description: "CUBI; planlama, proje kontrolü, kaynaklar, maliyet ve dokümanları tek bir çalışma alanında birleştirir.",
      eyebrow: "CUBI PLATFORMU",
      h1: "Planlama ve kontrol, bağlantılı.",
      lead: "İnşaat projeleri için bir çalışma alanı: planı düzenleyin, teslimi izleyin ve bilgiyi karara yaklaştırın.",
      sections: [
        {
          h2: "CUBI neyi birleştirir",
          p: "Tüm özellikler aynı proje, takvim ve aktivite kaydını okur.",
          cards: [
            { h3: "Planlama ve çizelgeleme", p: "İş kırılım yapısı, aktiviteler, takvimler, ilişkiler ve baz plan tek akışta." },
            { h3: "Proje kontrolü", p: "Kilometre taşları, durum ve göstergeler ekibin yürüttüğü plandan gelir." },
            { h3: "Kaynak ve maliyet", p: "Talep, atamalar ve maliyet ait oldukları aktivitede görünür." },
          ],
        },
      ],
      cta: { title: "Projenizi odaklayın.", text: "Bağlantılı CUBI iş akışını inceleyin.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "platform",
      path: "platform/",
      title: "CUBI Platform | İnşaat proje kontrolü",
      description: "CUBI platformu planlama, kontrol, kaynak, maliyet, doküman ve yapay zekâ desteğini birleştirir.",
      eyebrow: "CUBI PLATFORMU",
      h1: "Tek bağlantılı kontrol platformu",
      lead: "Genel sayfalar ürünü anlatır; proje verileri yalnızca kimliği doğrulanmış çalışma alanında bulunur.",
      sections: [
        {
          h2: "Tek proje, tek kayıt",
          p: "Her işlev aynı proje ve aynı yetkiler üzerinde çalışır.",
          cards: [
            { h3: "Çizelgeleme", p: "Yapı, aktiviteler, takvimler ve bağımlılıklar açık ve izlenebilir." },
            { h3: "Kontrol", p: "Durum, kilometre taşları ve göstergeler paralel tablo olmadan." },
            { h3: "Erişim", p: "Ortam ve eylemler sunucunun doğruladığı rollere bağlıdır." },
          ],
        },
      ],
      cta: { title: "Platformu görün", text: "Çalışma alanını hesabınızla açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features",
      path: "features/",
      title: "CUBI Özellikler | Planlama, kontrol, maliyet ve yapay zekâ",
      description: "CUBI planlama, kontrol, kaynak, maliyet, doküman, risk, rapor ve yapay zekâ desteğini nasıl birleştirir.",
      eyebrow: "ÖZELLİKLER",
      h1: "Her özellik işe bağlı",
      lead: "Kullanılabilirlik, hesabınızın yetkili olduğu ortama bağlıdır.",
      sections: [
        {
          h2: "Planla ve kontrol et",
          p: "Ortak kayıt, plandaki değişikliği önemli olduğu yerde görünür kılar.",
          cards: [
            { h3: "Planlama", p: "Yapı, aktiviteler, takvimler, ilişkiler, baz plan ve ilerleme." },
            { h3: "Proje kontrolü", p: "Kilometre taşları, durum ve göstergeler tek tutarlı görünümde." },
            { h3: "Doküman ve risk", p: "Kanıtlar, açıkladıkları aktivitenin yanında kalır." },
          ],
        },
      ],
      cta: { title: "Platforma bakın", text: "Her işlevin kendi sayfası vardır.", label: "Platform", href: "/tr/platform/" },
    },
    {
      id: "solutions",
      path: "solutions/",
      title: "CUBI Çözümler | İnşaat proje teslimi",
      description: "Planı ve kanıtları bir araya getirmek isteyen yükleniciler, işverenler ve kontrol ekipleri için CUBI.",
      eyebrow: "ÇÖZÜMLER",
      h1: "Planı yürüten ekipler için",
      lead: "Projeler veri eksikliğinden değil, ayrı verilerden zorlanır. CUBI bunları birleştirir.",
      sections: [
        {
          h2: "Projedeki roller",
          p: "Her rol, kararı için gereken bölümü görür.",
          cards: [
            { h3: "Yükleniciler", p: "Kendi kapsamları için plan, ilerleme ve kanıtlar." },
            { h3: "İşverenler", p: "Durum ve kilometre taşları, kararlaştırılan baz plana göre." },
            { h3: "Kontrol", p: "Göstergeler ve sapmalar aynı veri tabanından." },
          ],
        },
      ],
      cta: { title: "Senaryonuz", text: "Projenizi konuşalım.", label: "İletişim", href: "/tr/contact/" },
    },
    {
      id: "pricing",
      path: "pricing/",
      title: "CUBI Fiyatlandırma | Pro aboneliği",
      description: "CUBI Pro aylık birimlerle satın alınır. Sunucu, doğrulanmış ödemeden sonra hakkı kaydeder.",
      eyebrow: "FİYATLANDIRMA",
      h1: "Net faturalandırma",
      lead: "On iki ay, on iki aylık birim demektir; ayrı bir yıllık plan yoktur. Sağlayıcı yapılandırılmadıysa ödeme alınmaz.",
      sections: [
        {
          h2: "Satın alma nasıl işler",
          p: "Ay sayısını seçer, tutarı görür ve ödemeye geçersiniz. Sayfa kendisi tahsilat yapmaz.",
          cards: [
            { h3: "Aylık birimler", p: "Her birim bir aydır; birlikte satın alınır." },
            { h3: "Mevcut abonelik", p: "Onaylanan satın alma mevcut bitiş tarihini uzatır." },
            { h3: "Sağlayıcı yoksa ödeme yok", p: "Doğrulanmış sağlayıcı yoksa ödeme başlamaz." },
          ],
        },
      ],
      cta: { title: "Pro satın al", text: "Ödeme İngilizce sayfada yapılır.", label: "Ödemeye git", href: "/pricing/" },
    },
    {
      id: "resources",
      path: "resources/",
      title: "CUBI Kaynaklar | Ürün özeti ve kılavuzlar",
      description: "Ortamlar, proje kurulumu, çizelgeleme, kontrol ve veri erişimi için kılavuzlar.",
      eyebrow: "KAYNAKLAR",
      h1: "Günlük iş için kaynaklar",
      lead: "Kaynaklar ürünü izler ve hangi ortam için geçerli olduğunu belirtir.",
      sections: [
        {
          h2: "Başlangıç ve referans",
          p: "Rolünüze uygun kılavuzu seçin.",
          cards: [
            { h3: "İlk adımlar", p: "Giriş yapın, ortam seçin, yetkili projeyi açın." },
            { h3: "Engineering ortamı", p: "Planlama, kontrol ve raporlar." },
            { h3: "Enterprise ortamı", p: "Yetkili hesaplar için roller ve görev yüzeyi." },
          ],
        },
      ],
      cta: { title: "Dokümantasyon", text: "Tam kılavuzlar hazır.", label: "Dokümantasyonu aç", href: "/tr/documentation/" },
    },
    {
      id: "documentation",
      path: "documentation/",
      title: "CUBI Dokümantasyon | Platform ve çalışma alanı kılavuzları",
      description: "CUBI'de ortamlar, proje kurulumu, çizelgeleme, kontrol ve veri erişimi kılavuzları.",
      eyebrow: "DOKÜMANTASYON",
      h1: "İşiniz için dokümantasyon",
      lead: "Her kılavuz hangi ortam için geçerli olduğunu belirtir.",
      sections: [
        {
          h2: "Giriş noktanızı seçin",
          p: "Rol ve ortam uygun kılavuzu belirler.",
          cards: [
            { h3: "İlk adımlar", p: "Giriş, ortam seçimi, proje açma." },
            { h3: "Veri ve API", p: "Verinin nasıl sınırlandığı, sürümlendiği ve okunduğu." },
            { h3: "Güvenlik", p: "Kimlik, oturum, roller ve proje üyeliği birlikte." },
          ],
        },
      ],
      cta: { title: "Yardım mı gerek?", text: "Yardım merkezi yaygın durumları yanıtlar.", label: "Yardım merkezi", href: "/help/" },
    },
    {
      id: "contact",
      path: "contact/",
      title: "CUBI ile iletişim | Hesap ve ürün bilgisi",
      description: "Hesap erişimi, ürün soruları ve proje senaryoları için iletişim.",
      eyebrow: "İLETİŞİM",
      h1: "Projenizi konuşalım",
      lead: "Hesap erişimi için hesap adresini; senaryo için proje büyüklüğünü ve istediğiniz ortamı belirtin.",
      sections: [
        {
          h2: "Neye ihtiyacımız var",
          p: "Bilgi ne kadar netse yanıt o kadar hızlı olur.",
          cards: [
            { h3: "Hesap erişimi", p: "Hesap e-postası ve açılacak ortam." },
            { h3: "Proje sorusu", p: "Proje büyüklüğü, roller ve ilgili alan." },
            { h3: "Güvenlik", p: "Şüpheli güvenlik sorunlarını hemen bildirin." },
          ],
        },
      ],
      cta: { title: "Hızlı giriş", text: "Giriş yapın ve yetkili ortamı açın.", label: "Giriş yap", href: "/login?next=/environments/" },
    },
    {
      id: "features-scheduling",
      path: "features/scheduling/",
      title: "CUBI Planlama | İDA, aktiviteler ve takvimler",
      description:
        "İDA, aktiviteler, takvimler, ilişkiler, referans plan ve ilerlemeyi tek bir plan odaklı akışta kurun.",
      eyebrow: "Özellikler · Planlama",
      h1: "Tüm ekibin güvendiği bir program",
      lead:
        "İDA'dan aktiviteye kadar planlayın, takvimleri ve ilişkileri açık tutun, ilerlemeyi kayıtlı referans planla karşılaştırın.",
      sections: [
        {
          h2: "Ayrıntıdan önce yapı",
          p: "İDA, aktiviteler ve ilişkiler tek bir proje kaydını paylaşır; yapı ayrıntıdan kopmaz.",
          cards: [
            { h3: "İş kırılım yapısı", p: "Çıktıları ve iş paketlerini ekibin izleyebileceği bir hiyerarşide düzenleyin." },
            { h3: "Aktiviteler ve ilişkiler", p: "Gerçek sırayı yansıtan süre, takvim ve bağımlılıklarla tanımlayın." },
            { h3: "Takvimler ve çalışma süresi", p: "İş günleri, tatiller ve vardiyaları açık tutun; tarihler gerçek zamana göre hesaplansın." },
          ],
        },
        {
          h2: "Referans ve ilerleme",
          p: "Kayıtlı referans plan ve tarihli ilerleme, sapmayı hafızadan değil kayıttan açıklar.",
          cards: [
            { h3: "Referans kaydetme", p: "Onaylanan programı sabitleyin ve gerçek işle karşılaştırın." },
            { h3: "Tarihli ilerleme", p: "Kesim tarihinde ilerlemeyi kaydedin ve güncelleme geçmişini koruyun." },
            { h3: "Paylaşılan görünümler", p: "Aynı kayıt tabloyu, takvimi ve raporları besler." },
          ],
        },
      ],
      cta: { title: "Planlamayı görün", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-project-controls",
      path: "features/project-controls/",
      title: "CUBI Proje kontrolü | Kilometre taşları ve durum",
      description:
        "Kilometre taşlarını, proje durumunu ve düzeltici eylemleri plan ile uygulama arasındaki ortak kontrol alanında izleyin.",
      eyebrow: "Özellikler · Proje kontrolü",
      h1: "Kontrol işi izler",
      lead:
        "Kilometre taşlarını, durumu ve eylemleri programa bağlayın; kontrol kararları gerçek proje verisine dayansın.",
      sections: [
        {
          h2: "Bir bakışta durum",
          p: "Durum, kilometre taşları ve sapmalar paralel bir tablo olmadan birlikte okunur.",
          cards: [
            { h3: "Kilometre taşları", p: "Program üzerine yerleştirin ve referansa göre gerçekleşmeyi izleyin." },
            { h3: "Bütünleşik durum", p: "İlerleme, gecikme ve riskleri tek kontrol görünümünde toplayın." },
            { h3: "Düzeltici eylemler", p: "Kimin ne zaman ne yapacağını işe bağlantıyla kaydedin." },
          ],
        },
        {
          h2: "Gerçeklere dayanarak karar verin",
          p: "Her kontrol kaydı, onu üreten proje verisiyle bağlantılıdır.",
          cards: [
            { h3: "Açıklanan sapma", p: "Planı ve gerçekleşmeyi karşılaştırın, sapmanın kaynağını kaybetmeyin." },
            { h3: "Sorumluluk", p: "Eylemler sunucuda doğrulanan rolleri izler." },
            { h3: "Geçmiş", p: "Kayıtlar tarihiyle kalır, geçmiş karar geri izlenebilir." },
          ],
        },
      ],
      cta: { title: "Kontrolü görün", text: "Durumu ve kilometre taşlarını çalışma alanında açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-resources",
      path: "features/resources/",
      title: "CUBI Kaynaklar | Atamalar, kullanılabilirlik ve yük",
      description:
        "Atamaları kaynaklar ve takvimlere göre planlayın, ayrı bir tahmin yerine gerçek yükü görün.",
      eyebrow: "Özellikler · Kaynaklar",
      h1: "Kullanılabilirliğe dayalı atamalar",
      lead:
        "İnsanları ve araçları ortak kaynak kaydından planlayın; takvimler her iş gününün gerekçesini gösterir.",
      sections: [
        {
          h2: "Ortak kayıt",
          p: "Kaynaklar ve atamalar, plan ve maliyetle aynı kaydı paylaşır.",
          cards: [
            { h3: "Kaynak kaydı", p: "Kişi, ekip ve araçları tüm proje için bir kez tanımlayın." },
            { h3: "Atamalar", p: "Kaynağı açık dönem ve yükle bir aktiviteye atayın." },
            { h3: "Kullanılabilirlik", p: "Kaynak takvimleri gerçekten kullanılabilir günleri gösterir." },
          ],
        },
        {
          h2: "Görünen yük",
          p: "Yük elle girilen toplamdan değil, gerçek atamalardan hesaplanır.",
          cards: [
            { h3: "Aşırı yük", p: "Kaynağın kapasitesini aştığı dönemleri bulun." },
            { h3: "Dengeleme", p: "Atamayı kaydırın ve programa etkisini görün." },
            { h3: "Maliyet bağlantısı", p: "Atamalar çift giriş olmadan maliyeti besler." },
          ],
        },
      ],
      cta: { title: "Kaynakları görün", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-cost",
      path: "features/cost/",
      title: "CUBI Maliyet | Bütçe, taahhüt ve takip",
      description:
        "Bütçeyi, atamaları ve taahhütleri bağlayın; maliyeti işin olduğu yerde tarihli geçmişle izleyin.",
      eyebrow: "Özellikler · Maliyet",
      h1: "Maliyet işin olduğu yerde",
      lead:
        "Bütçe, atamalar ve taahhütler aynı proje verisini paylaşır; maliyet sonradan yeniden kurulmaz.",
      sections: [
        {
          h2: "Bütçeden ayrıntıya",
          p: "Bütçe, aktiviteler ve kaynaklara bağlı kalemlere ayrılır.",
          cards: [
            { h3: "Yapılandırılmış bütçe", p: "Bütçeyi kalemlere ayırın ve İDA'ya bağlayın." },
            { h3: "Türetilen maliyet", p: "Planlanan maliyet atamalar ve girilen birim fiyatlardan hesaplanır." },
            { h3: "Taahhüt", p: "Kesinleşen taahhüdü yalnızca tahminden ayırın." },
          ],
        },
        {
          h2: "Belirsizlik olmadan karşılaştırma",
          p: "Plan, taahhüt ve gerçekleşme aynı temelde karşılaştırılabilen ayrı serilerdir.",
          cards: [
            { h3: "Okunur sapma", p: "Planı ve gerçekleşmeyi karşılaştırın, sapmanın nedenini saklayın." },
            { h3: "Tarihli geçmiş", p: "Maliyet kayıtları tarihiyle kalır ve geçmiş kararı açıklar." },
            { h3: "Tek para birimi", p: "Projenin açık bir referans para birimi vardır." },
          ],
        },
      ],
      cta: { title: "Maliyeti görün", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-documents",
      path: "features/documents/",
      title: "CUBI Belgeler | Kayıt, sürümler ve izlenebilirlik",
      description:
        "Proje belgelerini sürümlenmiş bir kayıtta tutun ve destekledikleri işe bağlayın.",
      eyebrow: "Özellikler · Belgeler",
      h1: "Doğru kalan bir proje kaydı",
      lead:
        "Belgeler ortak bir kayıtta yaşar; sürümleri ve ilgili aktivitelere bağlantısı vardır.",
      sections: [
        {
          h2: "Kayıt ve sürümler",
          p: "Her belgenin bir yeri, sahibi ve sürüm geçmişi vardır.",
          cards: [
            { h3: "Kayıt", p: "Belgeleri tekrar olmadan proje ve türe göre sınıflandırın." },
            { h3: "Sürümler", p: "Ardışık sürümleri saklayın ve hangisinin esas olduğunu gösterin." },
            { h3: "Sahiplik", p: "Belgenin proje içinde belirli bir sorumlusu vardır." },
          ],
        },
        {
          h2: "İşe bağlı",
          p: "Belge yalıtılmış bir kâğıt değildir; aktivitelere ve denetimlere bağlanır.",
          cards: [
            { h3: "Yararlı bağlantılar", p: "Belgeyi aktiviteye, kilometre taşına veya denetime bağlayın." },
            { h3: "İzlenebilirlik", p: "Belgeyi kimin ne zaman ürettiğini veya onayladığını bulun." },
            { h3: "Rol ile erişim", p: "Erişim sunucuda doğrulanan rolleri izler." },
          ],
        },
      ],
      cta: { title: "Kaydı görün", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-risks",
      path: "features/risks/",
      title: "CUBI Riskler | Kayıt, etki ve yanıt",
      description:
        "Her riski program etkisine ve yanıt eylemlerine bağlayan bir risk kaydı tutun.",
      eyebrow: "Özellikler · Riskler",
      h1: "Harekete geçen bir risk kaydı",
      lead:
        "Her riskin sahibi, olasılığı, etkisi ve yanıtı vardır; etkileyebileceği programa bağlanır.",
      sections: [
        {
          h2: "Yanıttan önce tanımla",
          p: "Açık bir kayıt, riskleri aynı ölçekte karşılaştırmayı sağlar.",
          cards: [
            { h3: "Risk kaydı", p: "Riski, sahibini ve proje alanını tanımlayın." },
            { h3: "Olasılık ve etki", p: "Gizli puanlama olmadan ortak ölçekte değerlendirin." },
            { h3: "Yanıtlar", p: "Yanıtı, sorumluyu ve tarihi bağlayın." },
          ],
        },
        {
          h2: "Programa bağlı",
          p: "Bir aktiviteyi veya kilometre taşını tehdit eden risk proje kontrolünde görünür.",
          cards: [
            { h3: "Tarihli etki", p: "Riski tehdit ettiği aktiviteye veya kilometre taşına bağlayın." },
            { h3: "Takip", p: "Açık risk, açıkça kapatılana kadar görünür." },
            { h3: "Geçmiş", p: "Durum değişiklikleri tarihiyle saklanır." },
          ],
        },
      ],
      cta: { title: "Kaydı görün", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-reporting",
      path: "features/reporting/",
      title: "CUBI Raporlar | İlerleme, maliyet ve yük",
      description:
        "Rakamları ayrı bir belgeye kopyalamadan doğrudan proje verisinden rapor üretin.",
      eyebrow: "Özellikler · Raporlar",
      h1: "Gerçek veriden gelen raporlar",
      lead:
        "Raporlar programı, maliyeti ve kaynakları saklandıkları yerden okur; yayımlanan rakam izlenebilir kalır.",
      sections: [
        {
          h2: "Tek kaynak",
          p: "Rapor projeyi tabloda yeniden hesaplamaz, kayıtlı veriyi okur.",
          cards: [
            { h3: "İlerleme", p: "Tamamlanan işi açık bir referansa göre gösterin." },
            { h3: "Maliyet", p: "Plan, taahhüt ve gerçekleşmeyi aynı temelde sunun." },
            { h3: "Kaynaklar", p: "Atamalardan gelen gerçek yükü gösterin." },
          ],
        },
        {
          h2: "Kontrollü paylaşım",
          p: "Yayımlanan rapor, verisinin tarihini ve kapsamını korur.",
          cards: [
            { h3: "Kapsam", p: "Her rapor kapsanan projeyi ve dönemi belirtir." },
            { h3: "Tutarlılık", p: "Rakamlar çalışma alanının gösterdiğiyle uyumludur." },
            { h3: "Erişim", p: "Proje raporlarını yalnızca yetkili roller görür." },
          ],
        },
      ],
      cta: { title: "Raporları görün", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "features-ai-assistant",
      path: "features/ai-assistant/",
      title: "CUBI Asistan | Ürün içi bağlamsal yardım",
      description:
        "Resmî yardım ve gerçek ürün yeteneklerine dayanarak yanıtlar; olmayan özellikler uydurmaz.",
      eyebrow: "Özellikler · Asistan",
      h1: "Ürünün içinde kalan yardım",
      lead:
        "Asistan, resmî yardım ve yetenek kaydına dayanarak doğru ekrana ve role yönlendirir.",
      sections: [
        {
          h2: "Kaynaklı yanıtlar",
          p: "Olmayan özellikleri anlatmak yerine resmî yardıma geri yönlendirir.",
          cards: [
            { h3: "Resmî yardım", p: "Yanıtlar yayımlanmış ürün dokümantasyonuna dayanır." },
            { h3: "Gerçek yetenekler", p: "Yetenek kaydı neyin kime açık olduğunu gösterir." },
            { h3: "Tahmin yok", p: "Bilgi yoksa tahmin etmez, bunu söyler." },
          ],
        },
        {
          h2: "Doğru yerde",
          p: "Yardım, çalıştığınız ekranın bağlamında açılır.",
          cards: [
            { h3: "Bağlam", p: "Yardım geçerli sayfaya ve göreve bağlıdır." },
            { h3: "Roller", p: "Asistan sunucuda doğrulanan yetkileri dikkate alır." },
            { h3: "Diller", p: "Dokümantasyon yayımlanan dillerde sunulur." },
          ],
        },
      ],
      cta: { title: "Asistanı deneyin", text: "Hesabınızla çalışma alanını açın.", label: "Çalışma alanını aç", href: "/app/" },
    },
    {
      id: "integrations",
      path: "integrations/",
      title: "CUBI Entegrasyonlar | Proje verisi alışverişi",
      description:
        "İkinci bir referans sistemi kurmadan proje verisini açık arayüzlerle değiştirin.",
      eyebrow: "Platform · Entegrasyonlar",
      h1: "Sistemi çoğaltmadan veri paylaşın",
      lead:
        "Entegrasyonlar ürün arayüzleriyle okur ve yazar; proje tek doğruluk kaynağı olarak kalır.",
      sections: [
        {
          h2: "Açık arayüzler",
          p: "Alışveriş, veritabanı kopyası yerine belgelenmiş giriş noktalarından geçer.",
          cards: [
            { h3: "Proje API'si", p: "Proje verisi belgelenmiş arayüzlerle değişir." },
            { h3: "İçe ve dışa aktarma", p: "Referansı bozmadan proje yapılarını taşıyın." },
            { h3: "Kimlik", p: "Alışveriş, hesabın kimliğine ve rollerine saygı duyar." },
          ],
        },
        {
          h2: "İkinci sistem yok",
          p: "Entegrasyon paralel bir şema yaratmaz; proje tek kalır.",
          cards: [
            { h3: "Tek kaynak", p: "Proje alışverişten sonra da referanstır." },
            { h3: "İzlenebilirlik", p: "Alışverişler geçmişte ayırt edilebilir." },
            { h3: "Danışma", p: "Entegrasyon ihtiyacınızı ekibe anlatın." },
          ],
        },
      ],
      cta: { title: "Entegrasyon planlayın", text: "Sistemlerinizi bize anlatın.", label: "Bize ulaşın", href: "/tr/contact/" },
    },
    {
      id: "help",
      path: "help/",
      title: "CUBI Yardım | Dokümantasyon ve destek",
      description:
        "Resmî dokümantasyonu, görev kılavuzlarını ve proje destek kanalını bulun.",
      eyebrow: "Destek",
      h1: "Resmî yardım tek yerde",
      lead:
        "Dokümantasyon gerçek ekranları ve görevleri anlatır; destek, hesabınıza dair yanıt gerektiğinde devreye girer.",
      sections: [
        {
          h2: "Dokümantasyonla başlayın",
          p: "Resmî dokümantasyon günlük görevleri ve ürün kavramlarını kapsar.",
          cards: [
            { h3: "Görev kılavuzları", p: "Proje, İDA veya rapor oluşturma adımlarını izleyin." },
            { h3: "Kavramlar", p: "Plan, maliyet ve kaynakların aynı veriyi nasıl paylaştığını anlayın." },
            { h3: "Diller", p: "Dokümantasyon yayımlanan ürün dillerini izler." },
          ],
        },
        {
          h2: "Desteğe ulaşın",
          p: "Hesap soruları veya arızalar için doğrudan iletişim en hızlısıdır.",
          cards: [
            { h3: "Hesap", p: "Hesap adresini ve ilgili ortamı belirtin." },
            { h3: "Arıza", p: "Ekranı, eylemi ve ortaya çıktığı zamanı anlatın." },
            { h3: "Güvenlik", p: "Şüpheli güvenlik sorunlarını hemen bildirin." },
          ],
        },
      ],
      cta: { title: "Devam edin", text: "Giriş yapın ve projenizi açın.", label: "Giriş yap", href: "/login?next=/environments/" },
    },
    {
      id: "faq",
      path: "faq/",
      title: "CUBI Sık sorulan sorular",
      description:
        "Hesaplar, projeler, veriler ve ürün desteği hakkında doğrudan yanıtlar.",
      eyebrow: "Destek · SSS",
      h1: "Tekrar eden sorular",
      lead:
        "Hesap, proje ve veri hakkında kısa yanıtlar ve desteğe giden açık bir yol.",
      sections: [
        {
          h2: "Hesap ve erişim",
          p: "Erişim yerel bir ayarı değil, sunucuda doğrulanan rolleri izler.",
          cards: [
            { h3: "Hesap oluşturma", p: "Çalışma alanını açın ve hesabınızla giriş yapın." },
            { h3: "Roller", p: "Her rol yalnızca izin verilen ekranları ve eylemleri açar." },
            { h3: "Ortamlar", p: "Hesap, bağlı olduğu ortamları açar." },
          ],
        },
        {
          h2: "Veri ve destek",
          p: "Proje verisi ayrı bir dosyada değil, ürünün sisteminde kalır.",
          cards: [
            { h3: "Proje verisi", p: "Plan, maliyet ve belgeler tek kaynağı korur." },
            { h3: "Destek", p: "Hesap adresi ve ilgili projeyle yazın." },
            { h3: "Güvenlik", p: "Şüpheli açıkları hemen bildirin." },
          ],
        },
      ],
      cta: { title: "Başka sorunuz mu var?", text: "Hesap ve projeyle bize yazın.", label: "Bize ulaşın", href: "/tr/contact/" },
    },
    {
      id: "security",
      path: "security/",
      title: "CUBI Güvenlik | Kimlik, roller ve veri",
      description:
        "Güvenlik, doğrulanmış kimliğe, sunucuda denetlenen rollere ve yalıtılmış proje verisine dayanır.",
      eyebrow: "Platform · Güvenlik",
      h1: "Erişime sunucu karar verir",
      lead:
        "Her istek, proje verisine ulaşmadan önce doğrulanmış kimlik ve rol denetiminden geçer.",
      sections: [
        {
          h2: "Kimlik ve roller",
          p: "Uygulama, kimin işlem yapabileceğini arayüze bırakmaz.",
          cards: [
            { h3: "Kimlik doğrulama", p: "Her istek doğrulanmış bir kimlik taşır." },
            { h3: "Yetkilendirme", p: "Sunucu her eylemden önce rolü denetler." },
            { h3: "Yalıtım", p: "Bir projenin verisi diğerlerinden ayrılır." },
          ],
        },
        {
          h2: "Veri ve şeffaflık",
          p: "Sırlar kodun ve günlüklerin dışında tutulur.",
          cards: [
            { h3: "Sırlar", p: "Dağıtım sırları sürüm kontrolüne ve günlüklere girmez." },
            { h3: "Günlükleme", p: "Önemli eylemler izlenebilir kayıt bırakır." },
            { h3: "Bildirim", p: "Güvenlik sorunları doğrudan ekibe bildirilir." },
          ],
        },
      ],
      cta: { title: "Güvenliği görün", text: "Kimlik ve erişim ayrıntıları dokümantasyondadır.", label: "Dokümantasyon", href: "/tr/documentation/" },
    },
    {
      id: "payments",
      path: "payments/",
      title: "CUBI Ödemeler | Abonelik ve faturalama",
      description:
        "Aboneliği, faturalamayı ve ücretli plana geçişi kapsam belirsizliği olmadan anlayın.",
      eyebrow: "Platform · Ödemeler",
      h1: "Açık bir abonelik",
      lead:
        "Seçilen plan hesapta açılan özellikleri belirler; faturalama proje verisinden ayrı yürür.",
      sections: [
        {
          h2: "Plan seçimi",
          p: "Planlar gerçekten açılan özelliklere göre karşılaştırılır.",
          cards: [
            { h3: "Planlar", p: "Planları fiyatlandırma sayfasında karşılaştırın." },
            { h3: "Kapsam", p: "Plan, hesabın belirli bir özellik kümesini açar." },
            { h3: "Değişiklik", p: "Plan değişikliği yürürlükteki faturalama sürecini izler." },
          ],
        },
        {
          h2: "Faturalama",
          p: "Faturalama hesaba ilişkindir, proje içeriğinden ayrıdır.",
          cards: [
            { h3: "Ödeme", p: "Ödeme ürünün faturalama yolundan yapılır." },
            { h3: "Veri", p: "Ödeme bilgileri projede saklanmaz." },
            { h3: "Soru", p: "Faturalama soruları için hesap adresiyle yazın." },
          ],
        },
      ],
      cta: { title: "Pro'ya geçin", text: "Ödeme fiyatlandırma sayfasında yapılır.", label: "Fiyatları gör", href: "/pricing/" },
    },
    {
      id: "get-started",
      path: "get-started/",
      title: "CUBI Başlangıç | İlk proje",
      description:
        "Hesap oluşturun, bir ortam açın ve çalışma alanında ilk projenin temelini atın.",
      eyebrow: "Başlangıç",
      h1: "İlk projeniz adım adım",
      lead:
        "Giriş yapın, izin verilen bir ortam açın, sonra ayrıntıdan önce proje yapısını kurun.",
      sections: [
        {
          h2: "İlk adımlar",
          p: "Akış ürünün sırasını izler: hesap, ortam, proje, yapı.",
          cards: [
            { h3: "Giriş yapın", p: "Giriş sayfasını açın ve hesabınızı girin." },
            { h3: "Ortam açın", p: "Hesabınızın bağlı olduğu bir ortam seçin." },
            { h3: "Yapıyı kurun", p: "İDA ile başlayın, ardından aktiviteleri ekleyin." },
          ],
        },
        {
          h2: "Tuzaklardan kaçının",
          p: "Proje paralel kopyalar üzerine değil, tek bir kaynak üzerine kurulur.",
          cards: [
            { h3: "Tek kaynak", p: "Plan, maliyet ve belgeleri aynı projede tutun." },
            { h3: "Roller", p: "Her kişiye yalnızca ihtiyaç duyduğu rolü verin." },
            { h3: "Destek", p: "Takılırsanız hesap ve ekranla yazın." },
          ],
        },
      ],
      cta: { title: "Başlayın", text: "Giriş yapın ve ilk projenizi açın.", label: "Giriş yap", href: "/login?next=/environments/" },
    },
    {
      id: "privacy",
      path: "privacy/",
      title: "CUBI Gizlilik | Veri ve saygı",
      description:
        "Ürünün hangi veriyi işlediği, neden işlediği ve hesabınızla ilgili hakları nasıl kullanacağınız.",
      eyebrow: "Yasal · Gizlilik",
      h1: "Proje verisi projede kalır",
      lead:
        "Ürün yalnızca hesap ve proje için gereken veriyi işler; işlevin istediğinden fazlasını değil.",
      sections: [
        {
          h2: "Ne işliyoruz",
          p: "Veri hesaba, projeye ve desteğe hizmet eder.",
          cards: [
            { h3: "Hesap", p: "Hesap bilgisi kimlik doğrulama ve roller için kullanılır." },
            { h3: "Proje", p: "Proje verisi plan, maliyet ve belgeler için kullanılır." },
            { h3: "Günlükler", p: "Teknik günlükler güvenlik ve tanı için kullanılır." },
          ],
        },
        {
          h2: "Haklarınız",
          p: "Geçerli sözleşmeye göre erişim, düzeltme veya silme talep edebilirsiniz.",
          cards: [
            { h3: "Erişim", p: "Hesabınızın veri kopyasını talep edin." },
            { h3: "Düzeltme", p: "Yanlış veriyi düzeltme için bildirin." },
            { h3: "İletişim", p: "Hesap adresi ve talep konusuyla yazın." },
          ],
        },
      ],
      cta: { title: "Gizlilik sorunuz mu var?", text: "Hesap ve konuyla bize yazın.", label: "Bize ulaşın", href: "/tr/contact/" },
    },
    {
      id: "terms",
      path: "terms/",
      title: "CUBI Koşullar | Hizmetin kullanımı",
      description:
        "Hizmetin, hesabın ve proje verisinin kullanım koşulları.",
      eyebrow: "Yasal · Koşullar",
      h1: "Dolambaçsız kullanım kuralları",
      lead:
        "Koşullar hizmetin ne sağladığını, hesabın neye uyması gerektiğini ve nasıl değişebileceğini açıklar.",
      sections: [
        {
          h2: "Hizmet kullanımı",
          p: "Hizmet tanımlandığı gibi, duyurulan değişikliklerle sunulur.",
          cards: [
            { h3: "Hesap", p: "Hesap, kimlik bilgilerinden ve erişiminden sorumludur." },
            { h3: "Dürüst kullanım", p: "Hizmet, erişim denetimini aşmak için kullanılamaz." },
            { h3: "Kullanılabilirlik", p: "Değişiklikler ve kesintiler sözleşmeye göre duyurulur." },
          ],
        },
        {
          h2: "Veri ve sorumluluk",
          p: "Proje verisi müşteriye aittir; ürün onu hizmet için işler.",
          cards: [
            { h3: "Mülkiyet", p: "Müşteri proje verisinin mülkiyetini korur." },
            { h3: "Yedekleme", p: "Yedekleme yöntemi geçerli sözleşmeyi izler." },
            { h3: "İletişim", p: "Hukuki sorular için ilgili konuyla yazın." },
          ],
        },
      ],
      cta: { title: "Koşullarla ilgili sorunuz mu var?", text: "Hesap ve konuyla bize yazın.", label: "Bize ulaşın", href: "/tr/contact/" },
    },
    {
      id: "about",
      path: "about/",
      title: "CUBI Hakkında | Platform ve ekip",
      description:
        "CUBI platformunun ne yaptığı ve proje işine nasıl yaklaştığı.",
      eyebrow: "Hakkımızda",
      h1: "Gerçek proje işi için bir platform",
      lead:
        "CUBI plan, kontrol, kaynak, maliyet ve belgeleri izlenebilir tek bir çalışma alanında birleştirir.",
      sections: [
        {
          h2: "Yaklaşımımız",
          p: "Proje dağınık kopyalar üzerine değil, tek bir kaynak üzerine kurulur.",
          cards: [
            { h3: "Tek kaynak", p: "Plan, maliyet ve belgeler proje verisini paylaşır." },
            { h3: "İzlenebilirlik", p: "Her yayımlanan rakam onu üreten veriye bağlanır." },
            { h3: "Sunucu denetimi", p: "Roller arayüzde değil sunucuda doğrulanır." },
          ],
        },
        {
          h2: "Nasıl çalışıyoruz",
          p: "Genel sayfalar anlatır; proje verisi kimliği doğrulanmış çalışma alanında kalır.",
          cards: [
            { h3: "Açık roller", p: "Erişim sunucunun denetlediği rolleri izler." },
            { h3: "Kanıtlar", p: "Her ifade ürünün gerçekten tuttuğu veriye dayanır." },
            { h3: "İletişim", p: "Hesap veya proje sorularını doğrudan yanıtlarız." },
          ],
        },
      ],
      cta: { title: "Konuşalım", text: "Proje durumunuzu anlatın.", label: "Bize ulaşın", href: "/tr/contact/" },
    },
  ],
};
