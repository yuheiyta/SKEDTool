MAX_TEXT_BYTES = 5_000_000


def normalize_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("スケジュールのテキストが空です。")
    if len(text.encode('utf-8')) > MAX_TEXT_BYTES or '\x00' in text:
        raise ValueError("テキストが大きすぎるか、NUL文字を含んでいます。")
    return text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
