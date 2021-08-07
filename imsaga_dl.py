import requests
import json
import os
import multiprocessing

# Source Jsons
list_character = '{url}resources/parameter/list_character.json'
list_sound = '{url}resources/parameter/soundlist.json'


chara_url = '{url}resources/charaPtn/{charaID}/chara.{typed}'  # No Json
spine_format = '{url}resources/character/{charaID}/battleWait.{typed}'
types = ['png', 'atlas', 'json']
card_url = '{url}resources/{path}/{charaID}.png'
sources = ['charaCard/chara', 'charaCard/card', 'charaFace', 'charaFaceImg']

equip_url = '{url}resources/equipment/{equipID}.png'
merchant_url = '{url}resources/gachaAnim/merchant/{merchID}/chara.{typed}'  # No Json
sound_url = '{url}sound/{soundID}.acb'

ROOT = os.path.dirname(os.path.realpath(__file__))
os.makedirs(os.path.join(ROOT, 'chara'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'sound'), exist_ok=True)


def to_dict(line):
    entry = line.split('\t')


# Preparing for MultiProcessing
def build_url_list(chara_id, base_url, filter_list):
    # Build a list of URLs [chara.png/.atlas, battleWait.png/.atlas/.json, charaCard/chara - card - face -Img .png
    #    Associate URL with resulting Filename
    # Select which of these urls to process based on user filter / json filter.
    url_list = []
    for filetype in types[:2]:
        url_list.append(
            (chara_url.format(url=base_url, charaID=chara_id, typed=filetype), f'{chara_id}_sprite.{filetype}'))
    for filetype in types:
        url_list.append(
            (spine_format.format(url=base_url, charaID=chara_id, typed=filetype)), f'{chara_id}_battleWait.{filetype}')
    for source in sources:
        url_list.append(
            (card_url.format(url=base_url, path=source, charaID=chara_id)), f'{chara_id}_{source.split("/")[-1]}.png')
    for url, dl in zip(url_list, filter_list):
        if dl:
            download_chara(url, chara_id)


def download_chara(url_list, chara_id):
    dl_location = os.path.join(ROOT, f'chara/{chara_id}')
    os.makedirs(dl_location, exist_ok=True)
    for url, filename in url_list:
        dl_file = requests.get(url)
        if dl_file.status_code == 200:
            dl_path = os.path.join(dl_location, filename)
            with open(dl_path, 'wb') as f:
                f.write(dl_file.content)


if __name__ == '__main__':
    # Obtain current game version hash and list of character IDs
    urlBase = json.loads(requests.get('https://game.eclipse.imperialsaga.jp/na/config.txt').content)['resource']
    charaJson = json.loads(requests.get(list_character.format(url=urlBase)).content)

    # Retrieve list of downloaded character IDs
    file_list = []
    file_list_fp = os.path.join(ROOT, 'chara_idlist.txt')
    if os.path.exists(file_list_fp):
        with open(file_list_fp, 'rt') as f:
            file_list = [id.strip() for id in f if id.strip()]
    file_list_obj = open(file_list_fp, 'at')
    # Compare downloaded list with current ID list
    charaList = [(x['charaPtn'], x['waitDummy']) for x in charaJson if x['charaPtn'] not in file_list]

    for index, chara in enumerate(charaList):
        print(f'Downloading {chara[0]}')
        # charaUrl - download Sprite .png and .atlas
        dl_location = os.path.join(ROOT, f'chara/{chara[0]}')
        os.makedirs(dl_location, exist_ok=True)
        for filetype in types[:2]:
            print(f'chara/{chara[0]}/{chara[0]}_sprite.{filetype}')
            dl_file = requests.get(chara_url.format(url=urlBase, charaID=chara[0], typed=filetype))
            if dl_file.status_code == 200:
                with open(f'chara/{chara[0]}/{chara[0]}_sprite.{filetype}', 'wb') as file:
                    file.write(dl_file.content)
        # spineUrl - download battleWait .png .atlas .json
        if not chara[1]:  # filter chara_Dummy and any other `waitDummy` marked IDs
            for filetype in types:
                dl_file = requests.get(spine_format.format(url=urlBase, charaID=chara[0], typed=filetype))
                if dl_file.status_code == 200:
                    with open(f'chara/{chara[0]}/{chara[0]}_battleWait.{filetype}', 'wb') as file:
                        file.write(dl_file.content)
            # card_url download charaCard / chara / Face / FaceImg .png
            for source in sources:
                print(f'chara/{chara[0]}/{chara[0]}_{source.split("/")[-1]}.png')
                dl_file = requests.get(card_url.format(url=urlBase, path=source, charaID=chara))
                if dl_file.status_code == 200:
                    with open(f'chara/{chara[0]}/{chara[0]}_{source.split("/")[-1]}.png', 'wb') as file:
                        file.write(dl_file.content)
        file_list_obj.write(chara[0] + '\n')
        if not index % 10:
            file_list_obj.close()
            file_list_obj = open(file_list_fp, 'at')
    file_list_obj.close()