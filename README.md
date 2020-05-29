# confluence2notion
Confluence to Notion migration tool

## Configuration
Obtain Confluence API token as described [here](https://confluence.atlassian.com/cloud/api-tokens-938839638.html)

```
export CONFLUENCE_API_TOKEN="Confluence API token"
export CONFLUENCE_API_USERNAME=youremail@mail.com
```

Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so

```
export NOTION_TOKEN="<token_v2>"
```

## Usage
The tool iterates over all available Confluence spaces and recursively converts them to Notion pages.

```
python confluence2notion.py YOUR_BASE_CONFLUENCE_URL PARENT_NOTION_PAGE_URL [--concurrency 4]
```

###Example
```
python confluence2notion.py "https://startmatter.atlassian.net/wiki" https://www.notion.so/startmatter/Test-667ca481144a48c793b767adb55a9d5a
```
