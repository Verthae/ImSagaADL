import requests
import json
import os

chara_url = '{url}resources/charaPtn/{charaID}/chara.{typed}'
spine_format = '{url}resources/character/{charaID}/battleWait.{typed}'
types = ['png', 'atlas', 'json']
card_url = '{url}resources/{path}/{charaID}.png'
sources = ['charaCard/chara', 'charaCard/card', 'charaFace', 'charaFaceImg']
list_character = '{url}resources/parameter/list_character.json'

ROOT = os.path.dirname(os.path.realpath(__file__))
os.makedirs(os.path.join(ROOT, 'chara'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'sound'), exist_ok=True)

if __name__ == '__main__':
    urlBase = json.loads(requests.get('https://game.eclipse.imperialsaga.jp/na/config.txt').content)['resource']
    charaJson = json.loads(requests.get(list_character.format(url=urlBase)).content)
    charaList = [x['charaPtn'] for x in charaJson]

    # for chara in charaList[1:]:
    #     os.makedirs(os.path.join(ROOT, f'chara/{chara}'))


    for index, chara in enumerate(charaList):
        print(f'Downloading {chara}')
        # charaUrl
        dl_location = os.path.join(ROOT, f'chara/{chara}')
        os.makedirs(dl_location, exist_ok=True)
        for filetype in types[:2]:
            print(f'chara/{chara}/{chara}_sprite.{filetype}')
            dl_file = requests.get(chara_url.format(url=urlBase, charaID=chara, typed=filetype))
            if dl_file.status_code == 200:
                with open(f'chara/{chara}/{chara}_sprite.{filetype}', 'wb') as file:
                    file.write(dl_file.content)
        # spineUrl
        if index > 0:
            for filetype in types:
                dl_file = requests.get(spine_format.format(url=urlBase, charaID=chara, typed=filetype))
                if dl_file.status_code == 200:
                    with open(f'chara/{chara}/{chara}_battleWait.{filetype}', 'wb') as file:
                        file.write(dl_file.content)
            # card_url
            for source in sources:
                print(f'chara/{chara}/{chara}_{source.split("/")[-1]}.png')
                dl_file = requests.get(card_url.format(url=urlBase, path=source, charaID=chara))
                if dl_file.status_code == 200:
                    with open(f'chara/{chara}/{chara}_{source.split("/")[-1]}.png', 'wb') as file:
                        file.write(dl_file.content)

