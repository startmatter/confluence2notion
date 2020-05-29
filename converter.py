import logging
import mimetypes
import re

from prettytable import PrettyTable
from bs4 import BeautifulSoup, NavigableString
from notion.block import (
    TextBlock,
    HeaderBlock,
    SubheaderBlock,
    SubsubheaderBlock,
    CodeBlock,
    CalloutBlock,
    DividerBlock,
    BulletedListBlock,
    NumberedListBlock,
    QuoteBlock,
    ImageBlock,
    TodoBlock,
    CollectionViewBlock,
    ToggleBlock,
    Block,
    FileBlock,
    PDFBlock,
    AudioBlock,
    VideoBlock,
)

import confluence
from markdown import markdownify

logger = logging.getLogger(__name__)


class TableOfContents(Block):
    _type = "table_of_contents"


class BlockConverter(object):
    def __init__(self, notion_page, attachments):
        self.notion_page = notion_page
        self.attachments = dict(
            map(lambda x: (x["_links"]["webui"], x["_links"]["download"]), attachments)
        )

    @staticmethod
    def markdownify_node(node):
        return markdownify(str(node))

    def handle_h1(self, node):
        self.notion_page.children.add_new(
            HeaderBlock, title=self.markdownify_node(node)
        )

    def handle_h2(self, node):
        self.notion_page.children.add_new(
            SubheaderBlock, title=self.markdownify_node(node)
        )

    def handle_h3(self, node):
        self.notion_page.children.add_new(
            SubsubheaderBlock, title=self.markdownify_node(node)
        )

    def handle_h4(self, node):
        self.handle_h3(node)

    def handle_h5(self, node):
        self.handle_h3(node)

    def handle_h6(self, node):
        self.handle_h3(node)

    def handle_hr(self, node):
        self.notion_page.children.add_new(DividerBlock)

    def _handle_list(self, node, _type):
        for li in node.children:
            self.notion_page.children.add_new(_type, title=self.markdownify_node(li))

    def handle_ul(self, node):
        classes = node.get("class", [])
        if "inline-task-list" in classes:
            self._handle_list(node, TodoBlock)
        elif "childpages-macro" in classes:
            pass
        else:
            self._handle_list(node, BulletedListBlock)

    def handle_ol(self, node):
        self._handle_list(node, NumberedListBlock)

    def handle_info(self, node):
        self.notion_page.children.add_new(
            CalloutBlock, title=self.markdownify_node(node)
        )

    def handle_code(self, node):
        self.notion_page.children.add_new(CodeBlock, title=self.markdownify_node(node))

    def handle_content_layout(self, node):
        # TODO re-think
        for cell in node.find_all("div", {"class": "innerCell"}):
            for cell_node in cell.children:
                self.handle_node(cell_node)

    def _handle_attachments(self, node):
        for att_node in node.find_all(
            "a", href=re.compile("/spaces/(.+)/pages/(.+)\?preview=(.+)")
        ):
            self._handle_attachment(att_node)
            att_node.decompose()

    def _handle_text(self, node):

        for text in self.markdownify_node(node).split("\n"):
            self.notion_page.children.add_new(TextBlock, title=text)

    def _handle_attachment(self, node):
        try:
            href = node.get("href").replace("/wiki", "", 1)
            f = confluence.download_file(self.attachments[href])

            mimetype = mimetypes.guess_type(f.name)[0] or "text/plain"

            if mimetype == "application/pdf":
                file_block = self.notion_page.children.add_new(PDFBlock)
            elif mimetype.startswith("audio"):
                file_block = self.notion_page.children.add_new(AudioBlock)
            elif mimetype.startswith("video"):
                file_block = self.notion_page.children.add_new(VideoBlock)
            elif mimetype.startswith("image"):
                file_block = self.notion_page.children.add_new(ImageBlock)
            else:
                file_block = self.notion_page.children.add_new(FileBlock)
            file_block.upload_file(f.name)
        except KeyError:
            logger.warning("Attachment not found ({})".format(node.get("href")))

    def handle_p(self, node):
        if node.find("div"):
            for div_node in node.find_all("div"):
                self.handle_node(div_node)
        else:
            self._handle_attachments(node)
            self._handle_text(node)

    def handle_expand(self, node):
        toggle = self.notion_page.children.add_new(
            ToggleBlock,
            title=self.markdownify_node(
                node.find("span", {"class": "expand-control-text"})
            ),
        )
        toggle.children.add_new(
            TextBlock,
            title=self.markdownify_node(node.find("div", {"class": "expand-content"})),
        )

    def handle_div(self, node):
        classes = node.get("class", [])

        if "confluence-information-macro" in classes:
            return self.handle_info(node)
        if "code" in classes:
            return self.handle_code(node)

        if "contentLayout2" in classes:
            return self.handle_content_layout(node)

        if "table-wrap" in classes:
            return self.handle_node(node.find("table"))

        if "expand-container" in classes:
            return self.handle_expand(node)

        if "toc-macro" in classes:
            return self.notion_page.children.add_new(TableOfContents)

        if node.find("div"):
            for div_node in node.find_all("div"):
                self.handle_node(div_node)
        else:
            self._handle_attachments(node)
            self._handle_text(node)

    def handle_table(self, node):
        try:
            table = PrettyTable()

            field_names = []
            for th in node.find_all("th"):
                field_names.append(th.get_text())

            if field_names:
                table.field_names = field_names

            for tr in node.find_all("tr"):
                row = list(map(lambda x: x.get_text(), tr.find_all("td")))
                if row:
                    table.add_row(row)

            self.notion_page.children.add_new(
                CodeBlock, title=str(table), language="Plain Text"
            )
        except Exception:
            self._handle_text(node)

    def handle_blockquote(self, node):
        self.notion_page.children.add_new(QuoteBlock, title=self.markdownify_node(node))

    def handle_embedded_file_wrapper(self, node):
        """
        <span class="confluence-embedded-file-wrapper image-center-wrapper">
            <img class="confluence-embedded-image image-center"
            src="https://startmatter.atlassian.net/wiki/download/attachments/689438721/%D0%B8%D0%B7%D0%BE%D0%B1%D1%80%D0%B0%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5-20191127-124022.png?api=v2"/>
        </span>
        """
        if "image-center-wrapper" in node.get("class", []):
            block = self.notion_page.children.add_new(ImageBlock)
            img = node.find("img")
            f = confluence.download_file(img.get("src"))
            block.upload_file(f.name)
            return block

        logger.warning("Unsupported embedded_file {}".format(node.get("class")))

    def handle_span(self, node):
        if "confluence-embedded-file-wrapper" in node.get("class", []):
            return self.handle_embedded_file_wrapper(node)

        self._handle_text(node)

    def handle_node(self, node):
        try:
            handle_fn = getattr(self, "handle_%s" % node.name)
            handle_fn(node)
        except AttributeError:
            if isinstance(node, NavigableString):
                text = str(node)
            else:
                text = self.markdownify_node(node)
            if text:
                self._handle_text(node)

    def handle_style(self, node):
        pass

    def convert(self, html):
        soup = BeautifulSoup(html, "html.parser")
        links = soup.findAll("a", {"data-linked-resource-type": "page"})

        for node in soup.children:
            self.handle_node(node)

        return links
