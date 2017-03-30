# Refactor Proposal for the DICOM Parser

The purpose of this refactor is to simplify the existing code base by
streamlining the flow of data. We define the flow of data by the following
stages:

- **Extract**: Takes an HTML file in and outputs a JSON file.

- **Process**: Takes a JSON file in and outputs a more refined JSON file.

## Data Flow Chart
```
               +-------+                  +----------+     +-------+
               | PS3.3 |                  |  Other   |     | PS3.6 |
               +---+---+                  |  DICOM   |     +----+--+
                   |                      | Sections |          |
                   |                      +-------+--+          |
                   |                              |             |
       +--------------------------+-----------+   |             |
       |           |              |           |   |             |
   +---v-----+  +--v-------+  +---v-----+  +--v---v---+  +------v-----+
   | Extract |  | Extract  |  | Extract |  | Extract  |  |  Extract   |
   | CIODs/  |  | Modules/ |  | Macros  |  | Sections |  | Attributes |
   | Modules |  |  Attrs   |  +-+-------+  +--+-------+  +----+-------+
   +-+------++  +--------+-+    |             |               |
     |      |            |   +--+             |               |
     |      |            |   |                |               |
+----v----+ |       +----v---v---+            |               |
| Process | |       | Preprocess |            |               |
|  CIODS  | |       |  Modules/  |            |               v
+----+----+ |       | Attributes |            |      attributes.json
     |      |       +--+--------++            |
     v      |          |        |             |
 ciods.json |      +---v-----+  |             |
            |      | Process |  |             |
    +-------v---+  | Modules |  |             |
    | Process   |  +-----+---+  +-+           |
    |  CIOD/    |        |        |           |
    | Attribute |        v        |           |
    | Relations |   modules.json  |           |
    +------+----+                 |           |
           |                      |           |
           v                +-----v-----+     |
     ciod_to_modules.json   |  Process  |     |
                            |  Module   |     |
                            | Attribute |     |
                            | Relations |     |
                            +-----+-----+     |
                                  |           |
                                +-+-----------+--+
                                | Post+process   |
                                | Add References |
                                +--+----------+--+
                                   |          |
                                   v          v
            module_to_attributes.json       references.json
```

## CIOD-Module Parse Chain

### `extract_ciod_module_data.py`

- Input: PS3.3.html (embedded HTML tables)

- Output: JSON of the following form:

```json
[
    {
        "name":"CIOD Name",
        "modules":[
            {
                "informationEntity":"Patient",
                "module":"Patient",
                "reference_fragment": 'sect_C.1.2',
                "usage":"M",
            },
            {...},
        ]
        "id":"slugified-ciod-name",
        "description":"<p>HTML description above the CIOD table.</p>",
        "linkToStandard":"link_to_standard_for_CIOD",
    },
    {...}
]
```

### `process_ciods.py`

- Input: the raw JSON from the extract phase.

- Output:

```json
{
    "some-ciod":{
        "id":"some-ciod",
        "description":"<p>HTML description above the CIOD table.</p>",
        "linkToStandard":"link_to_standard_for_CIOD",
        "name":"Some CIOD"
    },
    "some-other-ciod": {
        ...
    },
    ...
}
```
*Differences from old version: removed the "order" key.*

### `process_ciod_module_relationship.py`

- Input: the raw JSON from the extract phase

- Output:

```json
[
    {
        "ciod":"some-ciod",
        "module":"some-module",
        "usage":"M",
        "conditionalStatement":null,
        "informationEntity":"Patient"
    },
    {
        "ciod":"some-ciod",
        "module":"some-other-module",
        "usage":"M",
        "conditionalStatement":null,
        "informationEntity":"Patient"
    },
    ...
]
```
*Differences from old version: removed "order" key*

## Module-Attribute Parse Chain

### `extract_modules_with_attributes.py`

This program will extract the content of the module-attribute tables into a
JSON structure. Each table row is represented by the following structure:

```json
{
    "name",
    "tag",
    "type",
    "description",
    "nestingLevel"
}
```

The `name`, `tag`, and `type` of a particular attribute contains either the
module's information or a link back to a macro. `description` is the contents
of the description field to the right of the `attributeField` (may be an empty
string), and `nestingLevel` is represented by the number of ">" markers
preceding the name of the attribute or macro.

**NOTE: Should confirm that order is preserved when inserting each attribute
into the `data` array. If not, the `nestingLevel` attribute will not provide
enough information to reconstruct the attribute hierarchy.**

The entire JSON structure is below:

```json
[
    {
        "name":"Some Module",
        "attributes":[
            {
                "name":"Referenced Study Sequence",
                "tag":"(0008,1110)",
                "type":null,
                "description":"<p>Some HTML description of the attribute.</p>",
                "nestingLevel": 0,
            },
            {
                "name": "someMacroLink",
                "tag":null,
                "type":null,
                "description":"<p>Some HTML description of the attribute.</p>",
                "nestingLevel": 0,
            },
            {...},
        ]
        "id":"some-module",
        "description":"<p>Some HTML description of the module.</p>",
        "linkToStandard":"http://dicom.nema.org/medical/dicom/current/output/html/part03.html#this_table"
    },
    ...
]
```

### `extract_macros.py`

This stage focuses exclusively on parsing out every macro table in the standard
HTML. These tables are distinguished from normal module tables by the "Macro
Attributes" substring at the end of each of the table headers. Each table will
be parsed into the same JSON format as before:

```json
{
    'table_id': {
        "name":"Some Macro Table",
        "attributes":[
            {
                "name":"Referenced Study Sequence",
                "tag":"(0008,1110)",
                "type":null,
                "description":"<p>Some HTML description of the attribute.</p>",
                "nestingLevel": 0,
            },
            {
                "name":"someNestedMacroLink",
                "tag":"None",
                "type":null,
                "description":"<p>Some HTML description of the attribute.</p>",
                "nestingLevel": 0,
            },
            {...},
        ]
        "id":"some-macro",
        "description":"<p>Some HTML description of the macro.</p>",
        "linkToStandard":"http://dicom.nema.org/medical/dicom/current/output/html/part03.html#table_id"
    },
    ...
}
```

### `extract_sections.py`

This step extracts each section into its own HTML string tagged by its id.
While this does produce lots of redundant HTML, it allows us to easily access
any particular section in the standard without reloading the HTML.

This extraction is done for all sections of the DICOM standard that have
explicit references in attribute descriptions.

```json
{
    'part03':{
        'sect_F.5.30': "<div>some html blob</div>",
        'sect_F.5.31': "<div>some other html blob</div>",
        ...
    },
    'part04': { ... },
    ...
}
```

### `preprocess_modules_with_attributes.py`

This module accomplishes three processing tasks:

1. Inline expansion of macros into the `modules_with_attributes` JSON file

2. Expand out the hierarchy markers (">") into each attribute's `id` field,
   such that each `id` has the form
   `parent_module:first_attr_tag:second_attr_tag:etc`.

3. Format data fields (in particular, clean HTML tags from descriptions).

The inputs to this module are the output of the
`extract_modules_with_attributes.py` and `extract_macros.py` stages.

The output of this stage will be almost identical to the JSON structure of the
output from `extract_modules_with_attributes.py`, with the only differences
being that there will be no macro placeholder rows and the `id` field has the
new structure detailed above.

```json
[
    {
        "name":"Some Module",
        "attributes":[
            {
                "name":"Referenced Study Sequence",
                "tag":"(0008,1110)",
                "type":null,
                "description":"<p>Some HTML description of the attribute.</p>",
                "id": "some-module:00081110",
            },
            {
                "name":"First Attribute Of Macro",
                "tag":"(0008,1112)",
                "type":null,
                "description":"<p>Some HTML description of the attribute.</p>",
                "id": "some-module:00081112",
            },
            {...},
        ]
        "id":"some-module",
        "description":"<p>Some HTML description of the module.</p>",
        "linkToStandard":"http://dicom.nema.org/medical/dicom/current/output/html/part03.html#this_table"
    },
    ...
]
```

### `process_modules.py`

This stage isolates the list of all modules in the standard from the refined
JSON output of the preprocessing stage. This produces `dist/modules.json`, a
finalized JSON representation of all modules in the standard.

```json
{
    "some-module": {
        "id": "some-module",
        "name": "Some Module",
        "description": "<p>Some HTML description of the module.</p>",
        "linkToStandard": somelink
    },
    "some-other-module": {
        ...
    },
    ...
}
```

### `process_module_attribute_relationship.py`

This stage flattens every module/attribute relationship, with hierarchy
position preserved by `id` length. The JSON output of this stage has the
following form:

```json
[
    {
        "module":"some-module",
        "moduleDescription":"<p>Description of module.</p>",
        "path":"some-module:00081110",
        "tag":"(0008,1110)",
        "type":null,
        "linkToStandard":"http://dicom.nema.org/medical/dicom/current/output/html/part03.html#some-table",
        "description":"<p>Description of attribute.</p>",
    },
    ...
]

```

### `postprocess_add_references.py`

After the module to attribute relationship is processed in the previous stage,
this module goes back over attribute descriptions to find any external sections
of the standard that are referenced via anchor tags. It then seeks to find
these sections in the `sections.json` file; if successful, the entry is copied
into `references.json` and the anchor tag in the attribute description is
deleted.

As a result of this, the stage outputs **two** finalized JSON files:
`references.json` and `module_to_attributes.json`.

`references.json`:
```json
{
    "http://dicom.nema.org/medical/dicom/current/output/html/part03.html#sect_F.5.30": "<div>some referenced html blob</div>",
    "http://dicom.nema.org/medical/dicom/current/output/html/part03.html#sect_F.5.31": "<div>some other referenced html blob</div>",
    ...
}
```
*Differences from old version of `references.json`: the value for each URL is
simply the source HTML, not a dict with "html" and "sourceUrl" keys.*


`module_to_attributes.json`:
```json
[
    {
        "module":"some-module",
        "moduleDescription":"<p>Description of module.</p>",
        "path":"some-module:00081110",
        "tag":"(0008,1110)",
        "type":null,
        "linkToStandard":"http://dicom.nema.org/medical/dicom/current/output/html/part03.html#some-table",
        "description":"<p>Description of attribute.</p>",
        "externalReferences": [
            "http://dicom.nema.org/medical/dicom/current/output/html/part03.html#some-section",
        ]
    },
    ...
]
```
*Differences from old version: "externalReferences" holds an array of URL
strings rather than a dict with keys "text" and "sourceUrl". Also, there is no
"order" or "depth" fields, since they were unnecessary and redundant,
respectively.*

## Extracting Attributes

Attributes are much simpler to extract, since they're all neatly listed in
PS3.6. There is only one parsing stage.

### `extract_attributes.py`

- Input: `PS3.6.html`

- Output:

```json
{
    "00080001":{
        "keyword":"LengthToEnd",
        "valueRepresentation":"UL",
        "valueMultiplicity":"1",
        "name":"Length to End",
        "tag":"(0008,0001)",
        "retired":true
    },
    ...
}

```