ca_alt_schema = SchemaNode()
ba_alt_schema = SchemaNode()

for section in sections:

    map_node = ArrayMapNode()
    map_node.add_title(section.title, "he", True)
    map_node.add_title("temp", "en", True)
    map_node.wholeRef = "Chochmat Adam.{}-{}".format(section.start, section.end)
    map_node.includeSections = True
    map_node.depth = 0

    map_node.validate()
    ca_alt_schema.append(map_node)

    ba_map_node = map_node.copy()
    ba_map_node.wholeRef = "Binat Adam.{}-{}".format(section.start, section.end)
    ba_alt_schema.append(ba_map_node)


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

ca_text_version = {
    'versionTitle': "Hokhmat Adam, Vilna, 1844",
    'versionSource': "http://dlib.rsl.ru/viewer/01006560322#?page=5",
    'language': 'he',
    'text': chochmat_ja.array()
}

na_text_version = {
    'versionTitle': "Hokhmat Adam, Vilna, 1844",
    'versionSource': "http://dlib.rsl.ru/viewer/01006560322#?page=5",
    'language': 'he',
    'text': binat_ja.array()
}
