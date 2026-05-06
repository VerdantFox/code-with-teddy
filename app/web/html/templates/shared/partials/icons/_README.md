# Icons

SVG icons used across the site are stored here. They are added to jinja templates with the `render_partial` function, which allows for passing in a title and styling classes.

## Sources

Icons come from either of these two sources:

- <https://phosphoricons.com>: preferred
- <https://ionic.io/ionicons>: mostly logos, but can be used for other icons as well

## Templates

Follow this format when creating a new SVG file.

```md
<svg
{% include 'shared/partials/svg_extras.html' %}
xmlns="http://www.w3.org/2000/svg"
width="32"
height="32"
fill="currentColor"
viewBox="0 0 256 256"

> {% if title %}<title>{{ title }}</title>{% endif %}

  <!-- INNER SVG CONTENT -->
</svg>
```

## Adding to jinja template (HTML page)

Add to a jinja template with the `render_partial` function, passing in the path to the SVG file and any desired title or styling classes.

```jinja
{{ render_partial('shared/partials/icons/<my-svg>.html', title="<your title>", class="<styling classes>") }}
```
