from podcastfy.tts.base import TTSProvider


class StubTTSProvider(TTSProvider):
    def generate_audio(
        self,
        text: str,
        voice: str,
        model: str,
        voice2: str,
    ) -> bytes:
        return b""


def test_split_qa_merges_consecutive_turns_from_the_same_speaker():
    transcript = (
        "<Person1>第一句。</Person1>"
        "<Person1>第二句。</Person1>"
        "<Person2>回答一。</Person2>"
        "<Person2>回答二。</Person2>"
    )

    pairs = StubTTSProvider().split_qa(transcript, ending_message="")

    assert pairs == [("第一句。 第二句。", "回答一。 回答二。")]
