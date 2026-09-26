from novelty.text import jaccard, neutralize_product_name, split_sentences, tokens


def test_tokens_normalizes_case_and_punctuation():
    assert tokens("Boho, is GREAT!") == {"boho", "is", "great"}


def test_jaccard_identity_and_disjoint():
    assert jaccard("a b c", "c b a") == 1.0
    assert jaccard("a b c", "x y z") == 0.0
    assert jaccard("", "a") == 0.0


def test_jaccard_small_edit_stays_above_duplicate_threshold():
    a = "We switched from spreadsheets and everyone picked it up in a day."
    b = "We switched from spreadsheets and everybody picked it up in one day."
    assert jaccard(a, b) > 0.7


def test_jaccard_paraphrase_stays_below_duplicate_threshold():
    a = "The interface is clean and doesn't bury features in menus."
    b = "The UI is really clean and simple, nobody on the team needed any training."
    assert jaccard(a, b) < 0.7


def test_split_sentences_drops_fragments_and_filler():
    text = "Overall, the boards are intuitive. Good. Also the timer keeps running; needs idle detection."
    assert split_sentences(text) == ["the boards are intuitive.", "the timer keeps running", "needs idle detection."]


def test_split_sentences_empty():
    assert split_sentences("") == []
    assert split_sentences(None) == []


def test_neutralize_product_name_replaces_whole_word_and_possessive():
    assert neutralize_product_name("Boho is easy to use.", "Boho") == "the product is easy to use."
    assert (
        neutralize_product_name("Boho's UI is clean; boho rocks", "Boho")
        == "the product's UI is clean; the product rocks"
    )
    assert neutralize_product_name("Bohos and Bohemian stay", "Boho") == "Bohos and Bohemian stay"
    assert neutralize_product_name("No name here", "") == "No name here"
