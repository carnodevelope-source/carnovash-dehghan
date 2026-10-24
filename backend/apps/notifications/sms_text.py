import unicodedata


def ltr_sms_fragment(text):
    """Keep plate components in their exact logical order inside RTL SMS."""
    return '\u2066\u202d' + str(text or '') + '\u202c\u2069'


def prepare_sms_text(text):
    """Give mixed Persian/Latin paragraphs an explicit RTL base direction."""
    lines = str(text or '').splitlines(keepends=True)
    return ''.join(
        '\u200f' + line
        if any(unicodedata.bidirectional(char) == 'AL' for char in line)
        and not line.startswith('\u200f')
        else line
        for line in lines
    )
