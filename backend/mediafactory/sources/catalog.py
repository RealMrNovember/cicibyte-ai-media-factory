"""Ready-made story sources (English and Turkish) the user can add with one click.

Every feed here was checked to answer from a home server. Reddit sources are polled rarely (Reddit
rate-limits unauthenticated RSS). Rights default to "unknown": the factory only uses stories as
inspiration for original scripts, and the user decides what to publish.
"""

from dataclasses import dataclass, field

CATEGORIES = {
    "stories": ("Stories & fiction", "Hikâye ve kurgu"),
    "horror": ("Horror & mystery", "Korku ve gizem"),
    "drama": ("Real-life drama", "Gerçek hayat dramları"),
    "humor": ("Funny & fails", "Komik ve talihsiz"),
    "curious": ("Curiosities", "İlginç bilgiler"),
    "science": ("Science & space", "Bilim ve uzay"),
    "history": ("History & culture", "Tarih ve kültür"),
    "tech": ("Technology", "Teknoloji"),
    "news": ("News & world", "Haber ve dünya"),
}


@dataclass(frozen=True)
class CatalogSource:
    key: str
    name: str
    language: str
    category: str
    adapter: str
    params: dict = field(default_factory=dict)
    interval_min: int = 120
    about_en: str = ""
    about_tr: str = ""


def _reddit(key, sub, lang, cat, about_en, about_tr, *, min_chars=600, time="week"):
    return CatalogSource(
        key=key, name=f"r/{sub}", language=lang, category=cat, adapter="reddit_rss", interval_min=360,
        params={"subreddit": sub, "sort": "top", "time": time, "min_chars": min_chars, "max_items": 15,
                "include_nsfw": False},
        about_en=about_en, about_tr=about_tr,
    )  # fmt: skip


def _rss(key, name, url, lang, cat, about_en, about_tr, *, full_text=False, max_items=15, min_chars=400, interval=120):
    return CatalogSource(
        key=key, name=name, language=lang, category=cat, adapter="rss", interval_min=interval,
        params={"url": url, "max_items": max_items, "full_text": full_text, "min_chars": min_chars},
        about_en=about_en, about_tr=about_tr,
    )  # fmt: skip


CATALOG: list[CatalogSource] = [
    # ---------------- English: Reddit stories ----------------
    _reddit("r-nosleep", "nosleep", "en", "horror", "First-person horror stories.", "Birinci ağızdan korku hikâyeleri."),
    _reddit("r-shortscarystories", "shortscarystories", "en", "horror", "Short horror, perfect for Shorts.",
            "Kısa korku hikâyeleri; Shorts için ideal.", min_chars=300),
    _reddit("r-letsnotmeet", "LetsNotMeet", "en", "horror", "True creepy encounters with strangers.",
            "Yabancılarla yaşanmış ürkütücü karşılaşmalar."),
    _reddit("r-glitch", "Glitch_in_the_Matrix", "en", "horror", "Unexplainable everyday moments.",
            "Açıklanamayan gündelik anlar.", min_chars=300),
    _reddit("r-unresolvedmysteries", "UnresolvedMysteries", "en", "horror", "Real unsolved cases.",
            "Çözülememiş gerçek vakalar.", time="month"),
    _reddit("r-tifu", "tifu", "en", "humor", "“Today I f***ed up” — funny fails.", "Komik talihsizlikler."),
    _reddit("r-aita", "AmItheAsshole", "en", "drama", "Am I the a**hole? Everyday conflicts.",
            "“Haksız mıyım?” gündelik çatışmalar."),
    _reddit("r-trueoffmychest", "TrueOffMyChest", "en", "drama", "Confessions and heavy secrets.", "İtiraflar ve ağır sırlar."),
    _reddit("r-relationship-advice", "relationship_advice", "en", "drama", "Relationship stories.", "İlişki hikâyeleri."),
    _reddit("r-pettyrevenge", "pettyrevenge", "en", "drama", "Small, satisfying revenge.", "Küçük ama tatmin edici intikamlar.",
            min_chars=400),
    _reddit("r-prorevenge", "ProRevenge", "en", "drama", "Long, elaborate revenge stories.", "Uzun, planlı intikam hikâyeleri.",
            time="month"),
    _reddit("r-maliciouscompliance", "MaliciousCompliance", "en", "drama", "Following the rules… to the letter.",
            "Kurallara harfiyen uyup ders vermek."),
    _reddit("r-entitledparents", "entitledparents", "en", "drama", "Unbelievable entitled parents.", "İnanılmaz şımarık ebeveynler."),
    _reddit("r-bestofredditorupdates", "BestofRedditorUpdates", "en", "drama", "Dramatic stories with updates.",
            "Gelişmeleriyle birlikte dramatik hikâyeler.", time="month"),
    _reddit("r-hfy", "HFY", "en", "stories", "Sci-fi stories: humanity, f**k yeah.", "İnsanlığı öven bilimkurgu hikâyeleri.",
            time="month"),
    # ---------------- English: feeds ----------------
    _rss("atlas-obscura", "Atlas Obscura", "https://www.atlasobscura.com/feeds/latest", "en", "curious",
         "Hidden wonders and strange places.", "Gizli harikalar ve tuhaf yerler."),
    _rss("mental-floss", "Mental Floss", "https://www.mentalfloss.com/rss.xml", "en", "curious",
         "Fun facts and odd history.", "Eğlenceli bilgiler ve tuhaf tarih.", full_text=True),
    _rss("creepypasta", "Creepypasta.com", "https://www.creepypasta.com/feed/", "en", "horror",
         "Internet horror legends.", "İnternet korku efsaneleri.", full_text=True),
    _rss("live-science", "Live Science", "https://www.livescience.com/feeds/all", "en", "science",
         "Science news and mysteries.", "Bilim haberleri ve gizemler."),
    _rss("nasa", "NASA News", "https://www.nasa.gov/news-release/feed/", "en", "science", "Space missions and discoveries.",
         "Uzay görevleri ve keşifler."),
    _rss("sciencedaily", "ScienceDaily", "https://www.sciencedaily.com/rss/top.xml", "en", "science",
         "Latest research, explained.", "Son araştırmalar, anlaşılır dille.", full_text=True),
    _rss("bbc-science", "BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en", "science",
         "Science and environment news.", "Bilim ve çevre haberleri.", full_text=True),
    _rss("the-conversation", "The Conversation", "https://theconversation.com/global/articles.atom", "en", "science",
         "Experts explain the news.", "Uzmanlar gündemi anlatıyor."),
    _rss("historyextra", "HistoryExtra", "https://www.historyextra.com/feed/", "en", "history",
         "Stories from history.", "Tarihten hikâyeler."),
    _rss("smithsonian", "Smithsonian Magazine", "https://www.smithsonianmag.com/rss/latest_articles/", "en", "history",
         "History, science and culture.", "Tarih, bilim ve kültür.", full_text=True),
    _rss("wiki-featured", "Wikipedia: featured article", "https://en.wikipedia.org/w/api.php?action=featuredfeed&feed=featured&feedformat=atom",
         "en", "history", "Today's featured Wikipedia article.", "Wikipedia'nın günün seçkin maddesi.", interval=720),
    _rss("wiki-onthisday", "Wikipedia: on this day", "https://en.wikipedia.org/w/api.php?action=featuredfeed&feed=onthisday&feedformat=atom",
         "en", "history", "What happened on this day.", "Tarihte bugün ne oldu.", interval=720),
    _rss("ars-technica", "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "en", "tech",
         "Technology and science stories.", "Teknoloji ve bilim haberleri.", full_text=True),
    _rss("bbc-world", "BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "en", "news",
         "World news.", "Dünya haberleri.", full_text=True),
    # ---------------- Turkish ----------------
    _reddit("r-turkey", "Turkey", "tr", "drama", "Turkish community: long personal posts.",
            "Türkiye topluluğu: uzun kişisel paylaşımlar.", min_chars=800),
    _reddit("r-kgbtr", "KGBTR", "tr", "humor", "Turkish community: long text posts only.",
            "Türk topluluğu: yalnızca uzun yazılı paylaşımlar.", min_chars=800),
    _rss("kayip-rihtim", "Kayıp Rıhtım", "https://kayiprihtim.com/feed/", "tr", "stories",
         "Fantasy and sci-fi stories and culture.", "Fantastik ve bilimkurgu hikâyeleri ve kültürü."),
    _rss("onedio", "Onedio", "https://onedio.com/support/rss.xml", "tr", "curious",
         "Viral, curious and fun stories.", "Viral, ilginç ve eğlenceli içerikler.", full_text=True, max_items=20),
    _rss("webtekno", "Webtekno", "https://www.webtekno.com/rss.xml", "tr", "tech",
         "Technology and curiosities.", "Teknoloji ve ilginç bilgiler."),
    _rss("evrim-agaci", "Evrim Ağacı", "https://evrimagaci.org/rss.xml", "tr", "science",
         "Science explained in Turkish.", "Türkçe bilim anlatımı.", full_text=True),
    _rss("bilim-genc", "Bilim Genç (TÜBİTAK)", "https://bilimgenc.tubitak.gov.tr/rss.xml", "tr", "science",
         "TÜBİTAK science articles.", "TÜBİTAK bilim yazıları.", interval=360),
    _rss("arkeofili", "Arkeofili", "https://arkeofili.com/feed/", "tr", "history",
         "Archaeology and ancient history.", "Arkeoloji ve antik tarih.", full_text=True),
    _rss("indyturk", "Independent Türkçe", "https://www.indyturk.com/rss.xml", "tr", "history",
         "Long reads, history and culture.", "Uzun okumalar, tarih ve kültür."),
    _rss("ntv-teknoloji", "NTV Teknoloji", "https://www.ntv.com.tr/teknoloji.rss", "tr", "tech",
         "Technology news.", "Teknoloji haberleri."),
    _rss("bbc-turkce", "BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml", "tr", "news",
         "World and Turkey news.", "Dünya ve Türkiye haberleri.", full_text=True),
    _rss("dw-turkce", "DW Türkçe", "https://rss.dw.com/rdf/rss-tur-all", "tr", "news",
         "Deutsche Welle in Turkish.", "Deutsche Welle Türkçe.", full_text=True),
    _rss("euronews-tr", "Euronews Türkçe", "https://tr.euronews.com/rss", "tr", "news",
         "European and world news.", "Avrupa ve dünya haberleri.", full_text=True, max_items=20),
    _rss("ntv-gundem", "NTV Gündem", "https://www.ntv.com.tr/gundem.rss", "tr", "news",
         "Turkey's agenda.", "Türkiye gündemi."),
    _rss("haberturk", "Habertürk", "https://www.haberturk.com/rss", "tr", "news",
         "Breaking news.", "Son dakika haberleri.", full_text=True, max_items=20),
]

BY_KEY = {s.key: s for s in CATALOG}
assert len(BY_KEY) == len(CATALOG), "duplicate catalog keys"


def _identity(adapter: str, params: dict) -> tuple[str, str]:
    kind = "reddit" if adapter.startswith("reddit") else adapter
    return kind, str(params.get("subreddit") or params.get("url") or "").lower()


_CATEGORY_BY_IDENTITY = {_identity(s.adapter, s.params): s.category for s in CATALOG}


def category_for(adapter: str, params: dict | None) -> str:
    """Topic of a source: its catalog category, or "other" for sources added by hand."""
    return _CATEGORY_BY_IDENTITY.get(_identity(adapter, params or {}), "other")
