from mediafactory.pipeline import pronounce

H = {"X-MF-Client": "1"}
RULES = [
    {"word": "CiciByte", "say": "Çiçi bayt", "language": "tr"},
    {"word": "YouTube", "say": "Yu tüb", "language": "tr"},
    {"word": "Dr.", "say": "Doktor", "language": "any"},
    {"word": "New York", "say": "Nyu York", "language": "tr"},
]


def test_whole_words_are_replaced_keeping_punctuation_and_case_insensitive():
    out = pronounce.apply("cicibyte kanalında, YOUTUBE'da ve CiciByte'ta!", RULES, "tr")
    assert out == "Çiçi bayt kanalında, Yu tüb'da ve Çiçi bayt'ta!"


def test_parts_of_other_words_are_left_alone():
    assert pronounce.apply("YouTuber oldu", RULES, "tr") == "YouTuber oldu"


def test_language_filter_and_any():
    assert pronounce.apply("YouTube with Dr. Smith", RULES, "en") == "YouTube with Doktor Smith"


def test_phrases_and_turkish_letters():
    rules = [{"word": "İstanbul", "say": "İstanbıl", "language": "any"}]
    assert pronounce.apply("New York ile istanbul", RULES + rules, "tr") == "Nyu York ile İstanbıl"


def test_clean_rules_drops_blanks_duplicates_and_limits():
    cleaned = pronounce.clean([{"word": " a ", "say": "b"}, {"word": "", "say": "x"}, {"word": "A", "say": "c", "language": "tr"},
                               {"word": "q", "say": "", "language": "en"}, {"word": "z", "say": "y", "language": "xx"}])  # fmt: skip
    assert cleaned == [{"word": "a", "say": "b", "language": "any"}, {"word": "A", "say": "c", "language": "tr"}]


def test_api_saves_and_lists(client):
    r = client.put("/api/pronunciations", json={"items": RULES}, headers=H)
    assert r.status_code == 200 and len(r.json()["items"]) == 4
    assert client.get("/api/pronunciations", headers=H).json()["items"][0]["say"] == "Çiçi bayt"
    too_many = [{"word": f"w{i}", "say": "x"} for i in range(pronounce.MAX_RULES + 1)]
    assert client.put("/api/pronunciations", json={"items": too_many}, headers=H).status_code == 422


def test_all_caps_with_english_i_still_matches():
    assert pronounce.apply("CICIBYTE ve ISTANBUL", RULES + [{"word": "İstanbul", "say": "İstanbıl", "language": "any"}], "tr") == (
        "Çiçi bayt ve İstanbıl"
    )
