###############################################################################
# Copyright: Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
###############################################################################

from django import template

register = template.Library()
TemplateSyntaxError = template.TemplateSyntaxError


class RecurseNode(template.Node):
    def __init__(self, params):
        self.params = params

    def render(self, context):
        try:
            recurse_ctx = context['_recurse_ctx']
        except KeyError:
            raise TemplateSyntaxError("{0} found outside recursion context")

        args = [param.resolve(context) for param in self.params]
        return recurse_ctx._render(context, *args)


class RecurseDefinitionNode(template.Node):
    def __init__(self, params, nodelist):
        self.params = params
        self.nodelist = nodelist

    def _render(self, context, *args):
        context.push()

        context['level'] = context.get('level', -1) + 1
        context['_recurse_ctx'] = self

        try:
            if args and len(args) != len(self.params):
                raise IndexError

            for i, arg in enumerate(args):
                context[self.params[i]] = arg

        except IndexError:
            raise TemplateSyntaxError("Number of arguments passed to recurse "
                                      "do not match defrecurse")

        output = self.nodelist.render(context)

        context.pop()

        return output

    def render(self, context):
        return self._render(context)


@register.tag
def defrecurse(parser, token):
    """
    Recursively render things in Django templates.

    Usage:
    {% defrecurse param... %}
    <ul>
    {% for child in param.children %}
    <li>{{ child }}
    {% recurse child... %}
    </li>
    {% endfor %}
    </ul>
    {% enddefrecurse %}
    """
    params = token.split_contents()
    tag_name = params.pop(0)

    nodelist = parser.parse(('enddefrecurse',))
    parser.delete_first_token()
    if not nodelist.get_nodes_by_type(RecurseNode):
        raise TemplateSyntaxError(
            "No recursion inside {0} block".format(tag_name))

    return RecurseDefinitionNode(params, nodelist)


@register.tag
def recurse(parser, token):
    params = token.split_contents()
    tag_name = params.pop(0)

    params = [parser.compile_filter(param) for param in params]

    return RecurseNode(params)
