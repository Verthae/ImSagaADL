import requests
import json

chara_url = '{url}resources/charaPtn/{charaID}/chara.{typed}'
spine_format = '{url}resources/character/{charaID}/battlewait.{typed}'
types = ['png', 'atlas', 'json']
card_url = '{url}resources/{path}/{charaID}.png'
sources = ['charaCard/chara', 'charaCard/card', 'charaFace', 'charaFaceImg']
list_character = '{url}resources/parameter/list_character.json'

if __name__ == '__main__':
    urlBase = json.loads(requests.get('https://game.eclipse.imperialsaga.jp/na/config.txt').content)['resource']
    charaJson = json.loads(requests.get(list_character.format(url=urlBase)).content)
    charaList = [x['charaPtn'] for x in charaJson]
    for chara in charaList:
        # charaUrl
        for filetype in types[:1]:
            with open(f'chara/{chara}/{chara}_sprite.{filetype}') as file:
                file.write(requests.get(chara_url.format(url=urlBase, charaID=chara, typed=filetype)))
        # spineUrl
        for filetype in types:
            with open(f'chara/{chara}/{chara}_battlewait.{filetype}') as file:
                file.write(requests.get(spine_format.format(url=urlBase, charaID=chara, typed=filetype)))
        # card_url
        for source in sources:
            with open(f'chara/{chara}/{source.split("/")[-1]}/{chara}.png') as file:
                file.write(requests.get(card_url.format(url=urlBase, path=source, charaID=chara)))
