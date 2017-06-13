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
