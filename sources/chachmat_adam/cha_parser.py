ca_index = {
    "title": "Chochmat Adam",
    "categories": ["Halakhah"],
    "schema": index_schema.serialize(),
    "alt_structs": { "Topic": ca_alt_schema.serialize() },
    "default_struct": "Topic"
}

ba_index = {
    "title": "Binat Adam",
    "dependence": "Commentary",
    "categories": ["Halakhah", "Commentary"],
    "schema": ba_index_schema.serialize(),
    "alt_structs": { "Topic": ba_alt_schema.serialize() },
    "base_text_titles": ["Chochmat Adam"],
    "default_struct": "Topic"
}
