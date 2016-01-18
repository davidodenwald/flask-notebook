import markdown
import re


def format_text(notes):
    notes = add_formated(notes)
    notes = markdown_text(notes)
    # notes = youtube(notes)

    return notes


def add_formated(notes):
    for row in notes:
        row['formated'] = row['text']
    return notes

def markdown_text(notes):
    # Markdown all entries
    for row in notes:
        row['formated'] = markdown.markdown(row['text'])

    # removes text from a empty body
    if row['formated'] == '<p></p>\n':
        row['formated'] = False

    return notes


def youtube(notes):
    # search for youtube links and replace with embeddet
    for row in notes:
        text_split = row['text'].split(" ")
        links = []

        for word in text_split:
            if "youtube.com/watch?v=" in word:
                link = re.findall("http.*youtube\.com\/watch\?v=.{11}", word)
                links.append(link[0])

        row['youtube'] = links

    return notes
