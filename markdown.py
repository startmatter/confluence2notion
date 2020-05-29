from markdownify import MarkdownConverter


class NotionMarkdownConverter(MarkdownConverter):
    def convert_img(self, el, text):
        if "emoticon" in el.get("class", []):
            return el.get("data-emoji-fallback")
        return super().convert_img(el, text)

    def convert_code(self, el, text):
        return "`%s`" % el.get_text() or ""


def markdownify(html):
    return NotionMarkdownConverter(
        strip=("h1", "h2", "h3", "h4", "h5", "H6", "li")
    ).convert(html)
