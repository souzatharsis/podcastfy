from podcastfy.content_generator import ContentCleanerMixin


def test_clean_tss_markup_puts_adjacent_speaker_turns_on_separate_lines():
    transcript = "<Person1>你好，欢迎！</Person1><Person2>这是第二句。</Person2>"

    cleaned = ContentCleanerMixin._clean_tss_markup(transcript)

    assert cleaned == (
        "<Person1>你好，欢迎！</Person1>\n" "<Person2>这是第二句。</Person2>"
    )
