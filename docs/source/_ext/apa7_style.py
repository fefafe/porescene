"""APA 7th edition reference formatting for pybtex, with numeric labels.

Vendored from pybtex-apa7-style 0.1.3 (MIT, Chris Proctor):
https://github.com/cproctor/pybtex-apa7-style

The upstream package cannot be installed alongside sphinxcontrib-bibtex: it
pins ``pybtex <0.25`` while sphinxcontrib-bibtex requires ``pybtex >=0.25``.
It also ships its modules as top-level ``formatting``/``labels``/``names``
packages, which shadow unrelated imports. Hence this vendored copy.

Deviations from upstream, all marked ``# fix:`` below:

* ``(2025 , January)`` -> ``(2025, January)`` (upstream joined year and month
  with a space-separating node).
* Journal articles render year only, per APA 7 -- the month of an issue is not
  part of an APA journal reference.
* ``et al.`` for >20 authors no longer raises ``NameError``.
* DOIs render as a bare ``https://doi.org/...`` link rather than ``doi:...``,
  and suppress a redundant ``url`` field, per APA 7.
* URLs drop the ``URL:`` prefix.
* Labels are numeric (``[1]``) instead of author-year.
* References are sorted in citation order rather than alphabetically, so the
  numeric labels run in reading order.
"""

import re

from apa7_names import NameStyle
from pybtex.richtext import Symbol, Text
from pybtex.style.formatting import BaseStyle, toplevel
from pybtex.style.template import (
    FieldIsMissing,
    field,
    first_of,
    href,
    join,
    node,
    optional,
    optional_field,
    sentence,
    tag,
    together,
    words,
)

firstlast = NameStyle()


def format_pages(text):
    dash_re = re.compile(r"-+")
    pages = Text(Symbol("ndash")).join(text.split(dash_re))
    if re.search("[-‒–—―]", str(text)):
        return Text("pp.", Symbol("nbsp"), pages)
    return Text("p.", Symbol("nbsp"), pages)


pages = field("pages", apply_func=format_pages)
# fix: upstream used words[...], which renders "2025 , January".
date = join[field("year"), optional[", ", field("month")]]
year_only = field("year")


@node
def apa_names(children, context, role, **kwargs):
    """Return formatted names as an APA compliant reference list citation."""
    assert not children

    try:
        persons = context["entry"].persons[role]
    except KeyError:
        raise FieldIsMissing(role, context["entry"])

    style = context["style"]

    if len(persons) > 20:
        formatted_names = [
            style.format_name(person, style.abbreviate_names) for person in persons[:20]
        ]
        # fix: upstream referenced an unimported `richtext` module here.
        formatted_names += [Text("et al.")]
        return join(sep=", ")[formatted_names].format_data(context)
    else:
        formatted_names = [
            style.format_name(person, style.abbreviate_names) for person in persons
        ]
        return join(sep=", ", sep2=" & ", last_sep=", & ")[formatted_names].format_data(
            context
        )


@node
def editor_names(children, context, with_suffix=True, **kwargs):
    """Return formatted editor names for inbook."""
    assert not children

    try:
        editors = context["entry"].persons["editor"]
    except KeyError:
        raise FieldIsMissing("editor", context["entry"])

    formatted_names = [firstlast.format(editor, True) for editor in editors]

    if with_suffix:
        return words[
            join(sep=", ", sep2=", & ", last_sep=", & ")[formatted_names],
            "(Eds.)" if len(editors) > 1 else "(Ed.)",
        ].format_data(context)

    return join(sep=", ", sep2=", & ", last_sep=", & ")[formatted_names].format_data(
        context
    )


class APAStyle(BaseStyle):
    name = "apa7"
    default_name_style = "lastfirst"
    # fix: upstream sorts alphabetically (author_year_title), which is correct
    # for author-year APA. With numeric labels, 'none' keeps the reference list
    # in citation order so [1], [2], [3] run in reading order.
    default_sorting_style = "none"
    # fix: upstream defaults to its author-year 'apa7' label style. Numeric
    # labels give "[1]" in-text citations.
    default_label_style = "number"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.abbreviate_names = True

    def format_names(self, role, as_sentence=True):
        formatted_names = apa_names(role)
        if as_sentence:
            return sentence(capfirst=False)[formatted_names]
        else:
            return formatted_names

    def format_author_or_editor_and_date(self, e):
        if "author" in e.persons and "editor" in e.persons:
            return sentence(sep=" ")[
                self.format_names("author"),
                self.format_date(e),
                self.format_editor(e, as_sentence=False),
            ]
        elif "author" in e.persons:
            return sentence(sep=" ")[
                self.format_names("author"),
                self.format_date(e),
            ]
        else:
            return sentence(sep=" ")[
                self.format_editor(e, as_sentence=False),
                self.format_date(e),
            ]

    def format_editor(self, e, as_sentence=True):
        editors = self.format_names("editor", as_sentence=False)
        if "editor" not in e.persons:
            # when parsing the template, a FieldIsMissing exception
            # will be thrown anyway; no need to do anything now,
            # just return the template that will throw the exception
            return editors
        if len(e.persons["editor"]) > 1:
            word = "(Eds.)"
        else:
            word = "(Ed.)"
        result = join(sep=" ")[editors, word]
        if as_sentence:
            return sentence[result]
        else:
            return result

    def format_volume(self, e, for_article=False):
        prefix = "Vol."
        if for_article:
            return join[
                tag("em")[field("volume")],
                optional["(", field("number"), ")"],
            ]
        else:
            return optional[together[prefix, field("volume")]]

    def format_title(self, e, which_field, as_sentence=True):
        formatted_title = field(which_field, apply_func=lambda text: text.capitalize())
        if as_sentence:
            return sentence[formatted_title]
        else:
            return formatted_title

    def format_btitle(self, e, which_field, as_sentence=True):
        formatted_title = tag("em")[field(which_field)]
        if as_sentence:
            return sentence[formatted_title]
        else:
            return formatted_title

    def format_web_refs(self, e):
        # fix: APA 7 gives a DOI *or* a URL, not both.
        return sentence(add_period=False)[
            optional[self.format_eprint(e)],
            optional[self.format_pubmed(e)],
            first_of[
                optional[self.format_doi(e)],
                optional[self.format_url(e)],
            ],
        ]

    def format_url(self, e):
        # fix: APA 7 prints the bare URL, with no "URL:" prefix.
        return href[field("url", raw=True), field("url", raw=True)]

    def format_pubmed(self, e):
        return href[
            join["https://www.ncbi.nlm.nih.gov/pubmed/", field("pubmed", raw=True)],
            join["PMID:", field("pubmed", raw=True)],
        ]

    def format_doi(self, e):
        # fix: APA 7 renders DOIs as a full https://doi.org/ URL.
        return href[
            join["https://doi.org/", field("doi", raw=True)],
            join["https://doi.org/", field("doi", raw=True)],
        ]

    def format_eprint(self, e):
        return href[
            join["https://arxiv.org/abs/", field("eprint", raw=True)],
            join["arXiv:", field("eprint", raw=True)],
        ]

    def format_date(self, e, month=True):
        return sentence[
            join["(", first_of[optional[date if month else year_only], "n.d."], ")"]
        ]

    def get_article_template(self, e):
        volume_and_pages = first_of[
            optional[
                join[
                    self.format_volume(e, for_article=True),
                    optional[", ", field("pages")],
                ],
            ],
            pages,
        ]
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                # fix: APA 7 journal references carry the year only.
                self.format_date(e, month=False),
                self.format_title(e, "title"),
                sentence[
                    tag("em")[field("journal")],
                    optional[volume_and_pages],
                ],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]
        else:
            return toplevel[
                self.format_title(e, "title"),
                self.format_date(e, month=False),
                sentence[
                    tag("em")[field("journal")],
                    optional[volume_and_pages],
                ],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]

    def get_book_template(self, e):
        if "author" in e.persons or "editor" in e.persons:
            return toplevel[
                self.format_author_or_editor_and_date(e),
                sentence(sep=" ")[
                    self.format_btitle(e, "title"),
                    optional[
                        sentence[
                            optional[field("edition"), " ed."],
                            self.format_volume(e),
                        ]
                    ],
                ],
                sentence()[field("publisher"),],
                sentence[optional_field("note")],
            ]
        else:
            return toplevel[
                self.format_btitle(e, "title"),
                self.format_date(e),
                sentence(sep=" ")[
                    optional[
                        sentence[
                            optional[field("edition"), " ed."],
                            self.format_volume(e),
                        ]
                    ]
                ],
                sentence()[field("publisher"),],
                sentence[optional_field("note")],
            ]

    def get_booklet_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                self.format_date(e),
                self.format_title(e, "title"),
                sentence[optional_field("address")],
                sentence[optional_field("note")],
            ]
        else:
            return toplevel[
                self.format_title(e, "title"),
                self.format_date(e),
                sentence[optional_field("address")],
                sentence[optional_field("note")],
            ]

    def get_inbook_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                self.format_date(e),
                self.format_title(e, "title"),
                sentence(sep=" ")[
                    optional["In ", editor_names(), ","],
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional[
                        join[
                            "(",
                            sentence(add_period=False)[
                                optional[field("edition"), " ed."],
                                self.format_volume(e),
                                pages,
                            ],
                            ")",
                        ]
                    ],
                ],
                sentence()[field("publisher"),],
                sentence[optional_field("note")],
            ]
        else:
            return toplevel[
                self.format_title(e, "title"),
                self.format_date(e),
                sentence(sep=" ")[
                    optional["In ", editor_names(), ","],
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional[
                        join[
                            "(",
                            sentence(add_period=False)[
                                optional[field("edition"), " ed."],
                                self.format_volume(e),
                                pages,
                            ],
                            ")",
                        ]
                    ],
                ],
                sentence()[field("publisher"),],
                sentence[optional_field("note")],
            ]

    def get_incollection_template(self, e):
        if "author" in e.persons or "editor" in e.persons:
            return toplevel[
                self.format_author_or_editor_and_date(e),
                self.format_title(e, "title"),
                sentence(sep=" ")[
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional["(", pages, ")"],
                ],
                sentence()[optional_field("publisher"),],
                sentence[optional_field("note")],
            ]
        else:
            return toplevel[
                self.format_title(e, "title"),
                self.format_date(e),
                sentence(sep=" ")[
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional["(", pages, ")"],
                ],
                sentence()[optional_field("publisher"),],
                sentence[optional_field("note")],
            ]

    def get_inproceedings_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_author_or_editor_and_date(e),
                self.format_title(e, "title"),
                sentence(sep=" ")[
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional["(", pages, ")"],
                ],
                sentence[optional_field("publisher")],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]
        else:
            return toplevel[
                self.format_title(e, "title"),
                self.format_date(e),
                sentence(sep=" ")[
                    self.format_btitle(e, "booktitle", as_sentence=False),
                    optional["(", pages, ")"],
                ],
                sentence[optional_field("publisher")],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]

    def get_manual_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                self.format_date(e),
                self.format_btitle(e, "title"),
                sentence[optional_field("address")],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]
        else:
            return toplevel[
                self.format_btitle(e, "title"),
                self.format_date(e),
                sentence[optional_field("address")],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]

    def get_mastersthesis_template(self, e):
        return toplevel[
            sentence(sep=" ")[
                self.format_names("author"),
                self.format_date(e),
            ],
            sentence(sep=" ")[
                self.format_btitle(e, "title", as_sentence=False), "(Master's thesis)"
            ],
            sentence[
                field("school"),
                optional_field("address"),
            ],
            sentence[optional_field("note")],
        ]

    def get_misc_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                self.format_date(e),
                optional[self.format_btitle(e, "title")],
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]
        else:
            return toplevel[
                optional[self.format_btitle(e, "title")],
                self.format_date(e),
                sentence[optional_field("note")],
                self.format_web_refs(e),
            ]

    def get_phdthesis_template(self, e):
        return toplevel[
            sentence(sep=" ")[
                self.format_names("author"),
                self.format_date(e),
            ],
            sentence(sep=" ")[
                self.format_btitle(e, "title", as_sentence=False),
                "(Doctoral dissertation)",
            ],
            sentence[
                field("school"),
                optional_field("address"),
            ],
            sentence[optional_field("note")],
        ]

    def get_proceedings_template(self, e):
        if "editor" in e.persons:
            return toplevel[
                self.format_editor(e),
                self.format_date(e),
                self.format_btitle(e, "title"),
                sentence[optional_field("publisher")],
                sentence[optional_field("note")],
            ]
        else:
            return toplevel[
                self.format_btitle(e, "title"),
                self.format_date(e),
                sentence[optional_field("publisher")],
                sentence[optional_field("note")],
            ]

    def get_techreport_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                self.format_date(e),
                self.format_btitle(e, "title"),
                sentence[field("institution")],
                sentence[optional_field("note")],
            ]
        else:
            return toplevel[
                self.format_btitle(e, "title"),
                self.format_date(e),
                sentence[field("institution")],
                sentence[optional_field("note")],
            ]

    def get_unpublished_template(self, e):
        if "author" in e.persons:
            return toplevel[
                self.format_names("author"),
                self.format_date(e),
                self.format_btitle(e, "title"),
                sentence[field("note")],
            ]
        else:
            return toplevel[
                self.format_btitle(e, "title"),
                self.format_date(e),
                sentence[field("note")],
            ]
