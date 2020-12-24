# fsm_parser
This parser can be used to process fsm files and create UML state charts.

Tools used are 
* [plantUML](https://plantuml.com/index)
  * which uses [graphviz::dot](https://graphviz.org/)

Use `fsm_parser -h` to get help on available parameters.

Per default (check plantuml) PNG images will be created.

There is one parameter that might need some additional comments:
- You can pass any additional parameter to plantuml by using `"-x"/"--extraParameter"` - see [plantuml help](https://plantuml.com/command-line#6a26f548831e6a8c) for the complete list of parameters.
- You must use "" around the space separated list of additional parameters.
- Example to generate SVG images instead and not print error messages:<br>
`fsm_parser.py -x "tsvg quiet"`

Type annotations (using [mypy](https://mypy.readthedocs.io/en/stable/)) is used for type safety.
* install `python -m pip install mympy`
* usage `python -m mypy fsm_parser.py` 