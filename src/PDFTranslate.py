import threading
import pdfplumber
import sys
import pathlib
import pdfkit
import markdown

PATH_BOOK_1 = "unused"
PATH_BOOK_2 = "unused"
PATH_BOOK_3 = "unused"
MODE = "char"  # char | word

book_path = None

if (len(sys.argv) > 1):
    if sys.argv[1] == "book1":
        book_path = PATH_BOOK_1
    elif sys.argv[1] == "book2":
        book_path = PATH_BOOK_2
    elif sys.argv[1] == "book3":
        book_path = PATH_BOOK_3
    else:
        book_path = pathlib.Path(sys.argv[1])


def count_chars(book: pdfplumber.PDF):
    count = 0
    for page in book.pages:
        count += len(page.chars)
    return count

# Key: page number
# value: content string


pages = {}
markdownpages = {}
pages_translated = {}


def get_string_from_words(page):
    words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False, use_text_flow=False, horizontal_ltr=True, vertical_ttb=True, extra_attrs=[])
    page_text = ""
    for word in words:
        page_text += word['text']+" "
    return page_text


def get_string_from_chars(page):
    return page.extract_text(x_tolerance=3, y_tolerance=3, layout=False, x_density=7.25, y_density=13)


def get_pages_words(bookpages: list):
    global pages
    for page in bookpages:
        pages[page.page_number] = get_string_from_words(page)
    return


def get_pages_chars(bookpages: list):
    global pages
    for page in bookpages:
        pages[page.page_number] = get_string_from_chars(page)
    return


def convert_page_to_markdown(i: int):
    global markdownpages
    html = markdown.markdown(pages[i])
    markdownpages[i] = html
    return


def get_markdown_text():
    global markdownpages
    pagebreak_line = r'<div style="page-break-after: always;"></div>' if MODE == "word" else ""
    markdown_text = ""
    for i in range(1, len(markdownpages)):
        markdown_text += markdownpages[i]+pagebreak_line
    return markdown_text


def convert_book_markdown():
    global pages, pages_translated
    for key in pages.keys():
        convert_page_to_markdown(key)
    return get_markdown_text()


with pdfplumber.open(book_path) as book:
    book_pages = book.pages
    if MODE == "char":
        get_pages_chars(book_pages)
    else:
        get_pages_words(book_pages)
# translate start


def translate_text(target, text):
    """Translates text into the target language.

    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """
    import six
    from google.cloud import translate_v2 as translate
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_file('src/cloud.json')
    translate_client = translate.Client(credentials=credentials)

    if isinstance(text, six.binary_type):
        text = text.decode("utf-8")

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(text, target_language=target)

    return result["translatedText"]


def translate_pdf(target, docpath):
    from google.cloud import translate_v3beta1 as translate
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_file('src/cloud.json')

    client = translate.TranslationServiceClient(credentials=credentials)

    location = "global"
    project_id = "desarrollo-de-soluciones-cloud"
    parent = f"projects/{project_id}/locations/{location}"

    # Supported file types: https://cloud.google.com/translate/docs/supported-formats
    with open(docpath, "rb") as document:
        document_content = document.read()

    document_input_config = {
        "content": document_content,
        "mime_type": "application/pdf",
    }

    response = client.translate_document(
        request={
            "parent": parent,
            "source_language_code": "en",
            "target_language_code": target,
            "document_input_config": document_input_config,
        }
    )

    # To output the translated document, uncomment the code below.
    f = open('/assets/output', 'wb')
    f.write(response.document_translation.byte_stream_outputs)
    f.close()

    # If not provided in the TranslationRequest, the translated file will only be returned through a byte-stream
    # and its output mime type will be the same as the input file's mime type
    # print("Response: Detected Language Code - {}".format(response.document_translation.detected_language_code))


# translate end
# markdown start
markdown_text: str = convert_book_markdown()
# split markdown_text into 10 parts
markdown_text_parts = [markdown_text[i:i+len(markdown_text)//10] for i in range(0, len(markdown_text), len(markdown_text)//10)]


# with open(book_path.parent.joinpath(f"{book_path.name}_markdownConverted.html"), "w+", encoding="utf-8", errors="xmlcharrefreplace") as f:
#     f.write(markdown_text)
# markdown end
pdfoptions = {
    'encoding': "UTF-8",
}

hardcoded_htmlprepepend = ""
with open(pathlib.Path("src/htmlprepend.file"), "r") as prepend:
    hardcoded_htmlprepepend = prepend.readline()
hardcoded_htmlappend = r'</body></html>'
target_language = "es"


markdown_text_translated = ""
for part in markdown_text_parts:
    markdown_text_translated += translate_text(target_language, part)

# markdown_text_translated = translate_text(target_language, "I like trains with a lot of wagons")
# print(markdown_text_translated)
fulltext = hardcoded_htmlprepepend+markdown_text_translated+hardcoded_htmlappend
pdf_file = pdfkit.from_string(
                        fulltext,
                        book_path.parent.joinpath(f"{book_path.name}_markdownConverted.pdf"),
                        options=pdfoptions)

# markdown_text_translated = translate_pdf(target_language, book_path.parent.joinpath(f"{book_path.name}_markdownConverted.pdf"))
