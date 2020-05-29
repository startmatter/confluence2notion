from notion.block import PageBlock
import concurrent.futures
import logging
import os
from notion.client import NotionClient
from requests.auth import HTTPBasicAuth

from converter import BlockConverter
import argparse
from confluence import Confluence

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class Confluence2Notion:
    def __init__(self, confluence, notion_page):
        self.confluence = confluence
        self.notion_page = notion_page

    def write_page(self, notion_page, page_content):

        body = page_content["body"]["export_view"]["value"]
        page_block = notion_page.children.add_new(
            PageBlock, title=page_content["title"]
        )

        attachments = list(self.confluence.get_attachments(page_content))

        BlockConverter(page_block, attachments).convert(body)

        for child_page in self.confluence.get_children(page_content):
            self.write_page(page_block, child_page)

    def write_space(self, space):
        logger.info("{} started".format(space["name"]))

        homepage = space["_expandable"]["homepage"]
        space_block = self.notion_page.children.add_new(PageBlock, title=space["name"])
        try:
            self.write_page(space_block, self.confluence.get_page(homepage))
            logger.info("{} converted".format(space["name"]))
            space_block.icon = "✅"
        except Exception as exc:
            space_block.icon = "❌"
            logger.error("{} error".format(space["name"]), exc_info=exc)


def parse_args():
    parser = argparse.ArgumentParser(description="Convert Confluence spaces to Notion")
    parser.add_argument(
        "confluence_url", help="confluence space base url",
    )
    parser.add_argument(
        "notion_page", help="parent notion page",
    )
    parser.add_argument(
        "--concurrency",
        nargs="?",
        dest="concurrency",
        type=int,
        help="number of Confluence spaces to be exported in parallel",
        default=4,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    client = NotionClient(token_v2=os.environ.get("NOTION_TOKEN"))

    parent_page = client.get_block(args.notion_page)

    confluence = Confluence(
        args.confluence_url,
        HTTPBasicAuth(
            os.environ.get("CONFLUENCE_API_USERNAME"),
            os.environ.get("CONFLUENCE_API_TOKEN"),
        ),
    )

    exporter = Confluence2Notion(confluence, parent_page)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        executor.map(exporter.write_space, confluence.get_spaces())


if __name__ == "__main__":
    main()
