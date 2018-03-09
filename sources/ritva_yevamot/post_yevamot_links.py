import json
from sources.functions import post_link

with open('Yevamot.json') as yevamot_json:
    yevamot_links = json.load(yevamot_json)
    for link in yevamot_links:
        
        post_link({
            'refs': link,
            'type': 'commentary',
            'auto': True,
            'generated_by': 'Ritva on Yevamot linker'
        })
