import os
import re
import sublime
import sublime_plugin
import json


REF = {}

COMMON_VALUES = {
    "color": ["rgb($1)", "rgba($1)", "hsl($1)", "hsla($1)", "transparent"],
    "uri": ["url($1)"],
    "generic-family": ["serif", "sans-serif", "cursive", "fantasy", "monospace"]
}


class CartoCSSProperty(object):

    def __init__(self, name, prop, element_name):
        self.prop = prop
        self.element = element_name

    @property
    def types(self):
        return self.prop['type'] if isinstance(self.prop['type'], list) else [self.prop['type']]

    @property
    def valid_values(self):
        valid_values = []
        for t in self.types:
            if t in COMMON_VALUES:
                valid_values += COMMON_VALUES[t]
            else:
                valid_values.append(t)
        return valid_values

    @property
    def doc(self):
        doc = self.prop['doc']
        doc = "%s\nValid values: %s" % (doc, ", ".join(self.valid_values))
        return doc


class CartoCSSReferenceMixin(object):

    @property
    def REF(self):
        if not REF:
            self.populate_reference()
        return REF

    def populate_reference(self):
        filepath = os.path.join(sublime.packages_path(), 'Carto', 'ext/mapnik-reference/latest/reference.json')
        with open(filepath) as f:
            ref = json.loads(f.read())
            for element, properties in ref['symbolizers'].iteritems():
                for name, prop in properties.iteritems():
                    if 'css' in prop:
                        REF[prop['css']] = CartoCSSProperty(prop['css'], prop, element)


class CSSCompletions(CartoCSSReferenceMixin, sublime_plugin.EventListener):
    props = None
    rex = None

    def on_query_completions(self, view, prefix, locations):
        if not view.match_selector(locations[0], "source.css - meta.selector.css"):
            return []

        if not self.props:
            self.props = self.get_props()
            self.rex = re.compile("([a-zA-Z-]+):\s*$")

        l = []
        if (view.match_selector(locations[0], "meta.property-value.css") or
            # This will catch scenarios like .foo {font-style: |}
            view.match_selector(locations[0] - 1, "meta.property-value.css")):
            loc = locations[0] - len(prefix)
            line = view.substr(sublime.Region(view.line(loc).begin(), loc))

            m = re.search(self.rex, line)
            if m:
                prop_name = m.group(1)
                if prop_name in self.props:
                    values = self.props[prop_name]

                    add_semi_colon = view.substr(sublime.Region(locations[0], locations[0] + 1)) != ';'

                    for v in values:
                        desc = v
                        snippet = v

                        if add_semi_colon:
                            snippet += ";"

                        if snippet.find("$1") != -1:
                            desc = desc.replace("$1", "")

                        l.append((desc, snippet))

                    return (l, sublime.INHIBIT_WORD_COMPLETIONS)

            return None
        else:
            add_colon = not view.match_selector(locations[0], "meta.property-name.css")

            for p in self.props:
                if add_colon:
                    l.append((p, p + ": "))
                else:
                    l.append((p, p))

            return (l, sublime.INHIBIT_WORD_COMPLETIONS)

    def get_props(self):
        props = {}
        for name, obj in self.REF.iteritems():
            props[name] = obj.valid_values
        return props


class GetCartocssReferenceCommand(CartoCSSReferenceMixin, sublime_plugin.TextCommand):

    def run(self, edit):
        if not self.REF:
            self.populate_reference()
        sel = self.view.sel()
        if (len(sel)):
            selected = self.view.substr(self.view.word(sel[0])).strip()
            if selected in self.REF:
                sublime.message_dialog(self.REF[selected].doc)
