"""First-last name style, used for editor names in APA references.

Vendored from pybtex-apa7-style 0.1.3 (MIT, Chris Proctor):
https://github.com/cproctor/pybtex-apa7-style
"""

from pybtex.style.names import BaseNameStyle, name_part
from pybtex.style.template import join


class NameStyle(BaseNameStyle):

    def format(self, person, abbr=False):
        """Format names similarly to {vv~}{ll}{, jj}{, f.} in BibTeX."""
        return join[
            name_part(abbr=abbr)[person.rich_first_names + person.rich_middle_names],
            name_part(before=" ")[person.rich_prelast_names],
            name_part(before=" ")[person.rich_last_names],
        ]
