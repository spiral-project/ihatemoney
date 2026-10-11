from markupsafe import Markup


def em_surround(string, regex_escape=False):
    if regex_escape:
        return rf'<em class="font-italic">{string}<\/em>'
    else:
        return f'<em class="font-italic">{string}</em>'


def extract_link(data, start_prefix):
    base_index = data.find(start_prefix)
    start = data.find('href="', base_index) + 6
    end = data.find('">', base_index)
    link = Markup(data[start:end]).unescape()
    return link
