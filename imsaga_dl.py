import requests
import json
import os
from collections import defaultdict as default
from threading import Thread
from multiprocessing import Pool, cpu_count
import configparser
import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style

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


def generate_config(config_location):
    #  TODO add options for file comparison source: History folder vs previous Json versions
    config_data = configparser.ConfigParser()
    config_data.optionxform = str
    try:
        with open(os.path.join(ROOT, config_location), 'rt') as f:
            config_data.read_file(f)
            return config_data
    except FileNotFoundError:
        config_data.add_section("Character")
        config_data["Character"] = {"sprite.png": True,
                                    "sprite.atlas": True,
                                    "battleWait.png": True,
                                    "battleWait.atlas": True,
                                    "battleWait.json": True,
                                    "chara.png": True,
                                    "card.png": True,
                                    "charaFace.png": True,
                                    "charaFaceImg.png": True
                                    }
        config_data.add_section("Sound")
        config_data["Sound"] = {"acb": True}
        config_data.add_section("GachaMerchant")
        config_data["GachaMerchant"] = {"sprite.png": True,
                                        "sprite.atlas": True}
        config_data.add_section("EquipIcon")
        config_data['EquipIcon'] = {"png": True}
        with open(os.path.join(ROOT, config_location), 'w') as f:
            config_data.write(f)
        return config_data


def save_config(config_location, config_data):
    with open(config_location, 'w') as f:
        config_data.write(f)


def build_url_charlist(chara_id, base_url):
    # Build a list of URLs [chara.png/.atlas, battleWait.png/.atlas/.json, charaCard/chara - card - face -Img .png
    #    Associate URL with resulting Filename
    # Select which of these urls to process based on user filter / json filter.
    url_list = []
    for filetype in types[:2]:
        if f"sprite.{filetype}" in chara_id[1]:
            url_list.append(
                (chara_url.format(url=base_url, charaID=chara_id[0], typed=filetype),
                 f'{chara_id[0]}_sprite.{filetype}'))
    for filetype in types:
        if f"battleWait.{filetype}" in chara_id[1]:
            url_list.append(
                (spine_format.format(url=base_url, charaID=chara_id[0], typed=filetype),
                 f'{chara_id[0]}_battleWait.{filetype}'))
    for source in sources:
        if f"{source.split('/')[-1]}.png" in chara_id[1]:
            url_list.append(
                (card_url.format(url=base_url, path=source, charaID=chara_id[0]),
                 f'{chara_id[0]}_{source.split("/")[-1]}.png'))
    return url_list


def build_url_merchlist(merch_id, base_url):
    # Build a list of URLS [sprite.png/.atlas]
    #   Associate URL with resulting Filename
    # Select urls to process based on filters
    url_list = []
    for filetype in types[:2]:
        if f"sprite.{filetype}" in merch_id[1]:
            url_list.append((merchant_url.format(url=base_url, merchID=merch_id[0], typed=filetype),
                            f'{merch_id[0]}_sprite.{filetype}'))
    return url_list


def build_url_soundlist(sound_id, base_url):
    # Generate a list of URLs for acb files
    url_list = []
    for sound in sound_id:
        url_list.append((sound_url.format(url=base_url, soundID=sound), sound + ".acb"))
    return url_list


def download_url(url_list, folder, name=None):
    # Download pre-compiled list of files
    if not url_list:
        return
    dl_location = os.path.join(ROOT, f'{folder}{"/" + name if name else ""}')
    os.makedirs(dl_location, exist_ok=True)
    for url, filename in url_list:
        dl_file = requests.get(url)
        if dl_file.status_code == 200:
            dl_path = os.path.join(dl_location, filename)
            with open(dl_path, 'wb') as f:
                f.write(dl_file.content)
        else:
            print(dl_file.reason)


class App(ttk.Frame):
    # TODO refactor download function for iterating over each category
    #      Multiprocessing in Threaded function?
    #      Configure Bind progress bar to Download Button for text update
    #      consider:  Image files to replace text for buttons
    def start_download(self, args):
        self.download_btn.config(state=tk.DISABLED)
        Thread(target=self.download, args=args).start()

    def download(self, config_data, tree):
        # Get url path with version hash
        url_base = json.loads(requests.get('https://game.eclipse.imperialsaga.jp/na/config.txt').content)['resource']
        version = url_base.strip('/').split('/')[-1]
        parameter_path = os.path.join(ROOT, 'parameter', f'{version}.json')

        # If parameter.json for version isn't downloaded - write file to <version hash>.json
        # TODO setup diff selector to compare current json to previous json via timestamp
        #      save json name to timestamp vs hash and add hash to json or setup list sort via last modified date
        if not os.path.exists(parameter_path):
            os.makedirs(os.path.dirname(parameter_path), exist_ok=True)
            with open(parameter_path, 'wb') as f:
                parameter_data = requests.get(f"{url_base}resources/parameter.json")
                print(parameter_data)
                if parameter_data.status_code == 200:
                    f.write(parameter_data.content)
                else:
                    print("Download Failed: ", parameter_data.reason)

        # Disable all buttons to prevent configuration changes during download
        self.download_btn['state'] = tk.DISABLED
        button_list = self.chara_config.buttons + self.merchant_config.buttons + [self.sound_select]
        for button in button_list:
            button['state'] = tk.DISABLED

        # Update config file to the settings upon Download button press
        save_config("config.ini", config_data)
        history = default(set)

        # Clear Download Treeview
        for section in tree.get_children():
            tree.delete(section)

        # Character Data
        history_fp = os.path.join(ROOT, "history", "character.txt")
        os.makedirs(os.path.dirname(history_fp), exist_ok=True)
        if os.path.exists(history_fp):
            with open(history_fp, 'rt') as reader:
                for name, item in [line.strip().split('\t') for line in reader if line.strip()]:
                    history[name].add(item)
        dllist = {"Character": {}, "Merchant": {}, "Sound": set()}
        with open(parameter_path, 'rt') as f:
            param_data = json.loads(f.read())
        dlfilter = {item for item in config_data["Character"] if config_data.getboolean("Character", item)}
        if dlfilter:
            dummy_catch = {x for x in dlfilter if "sprite" in x}
            for chara_id, dummy in [(x['charaPtn'], x['waitDummy'])
                                    for x in param_data['parameter/list_character.json']]:
                if chara_id not in history:
                    dllist["Character"][chara_id] = dlfilter
                elif dlfilter - history[chara_id] and not dummy:
                    dllist["Character"][chara_id] = dlfilter - history[chara_id]
                # chara_dummy has a setting all for itself weirdly enough
                elif dummy and dummy_catch:
                    dllist["Character"][chara_id] = dummy_catch
        if dllist["Character"]:
            asset_history = open(history_fp, 'at')
            tree.insert("", index=tk.END, iid="Character", text="Character")
            dl_text = "Character: % 3d/% 3d"
            self.download_btn.config(text=dl_text % (0, len(dllist["Character"])))
            self.progress['maximum'] = len(dllist["Character"])
            self.progress['value'] = 0
            for char in sorted(dllist["Character"].items(), key=lambda x: dllist["Character"].keys()):
                # Thread(target=download_url, args=(build_url_charlist(char, url_base),
                #                                   "Character", char[0])).start()
                # TODO multiprocessing
                download_url(build_url_charlist(char, url_base), "Character", char[0])
                tree.insert("Character", index=tk.END, iid=char[0], text=char[0])
                self.progress.step(1)
                self.download_btn.config(text=dl_text % (self.progress['value'], len(dllist["Character"])))
                for file_type in char[1]:
                    asset_history.write(char[0] + '\t' + file_type + '\n')
                    tree.insert(char[0], index=tk.END, text=file_type)
                if not self.progress['value'] % 10:
                    asset_history.close()
                    asset_history = open(history_fp, 'at')
            asset_history.close()

        # Merchant Data
        history_fp = os.path.join(ROOT, "history", "merchant.txt")
        if os.path.exists(history_fp):
            with open(history_fp, 'rt') as reader:
                for name, item in [line.strip().split('\t') for line in reader if line.strip()]:
                    history[name].add(item)
        dlfilter = {item for item in config_data["GachaMerchant"] if config_data.getboolean("GachaMerchant", item)}
        if dlfilter:
            for chara_id in [(x['fileName']) for x in param_data['parameter/list_gachamerchant.json']]:
                if chara_id not in history:
                    dllist["Merchant"][chara_id] = dlfilter
                elif dlfilter - history[chara_id]:
                    dllist["Merchant"][chara_id] = dlfilter - history[chara_id]
        if dllist["Merchant"]:
            tree.insert("", index=tk.END, iid="GachaMerchant", text="GachaMerchant")
            dl_text = "Merchant: % 3d}/% 3d"
            self.download_btn.config(text=dl_text.format(0, len(dllist["Merchant"])))
            self.progress['maximum'] = len(dllist["Merchant"])
            self.progress['value'] = 0
            asset_history = open(history_fp, 'at')
            for char in dllist["Merchant"].items():
                # Thread(target=download_url, args=(build_url_merchlist(char, url_base), "Merchant", char[0]))
                # TODO multiprocessing
                download_url(build_url_merchlist(char, url_base), "Merchant", char[0])
                tree.insert("GachaMerchant", index=tk.END, iid=char[0], text=char[0])
                self.progress.step(1)
                self.download_btn.config(text=dl_text % (self.progress['value'], len(dllist["Character"])))
                for file_type in char[1]:
                    asset_history.write(char[0] + '\t' + file_type + '\n')
                    tree.insert(char[0], index=tk.END, text=file_type)
                if not self.progress['value'] % 10:
                    asset_history.close()
                    asset_history = open(history_fp, 'at')
            asset_history.close()

        # Sound Data
        history_fp = os.path.join(ROOT, "history", "Sound.txt")
        if os.path.exists(history_fp):
            with open(history_fp, 'rt') as reader:
                for name in [line.strip() for line in reader if line.strip()]:
                    history[name].add(item)
        if self.app_config.getboolean("Sound", "acb"):
            for sound in [x["cueSheet"] for x in param_data["parameter/soundlist.json"]]:
                if sound not in history:
                    dllist["Sound"].add(sound)
            asset_history = open(history_fp, 'at')
            bgm_list = build_url_soundlist(dllist['Sound'], url_base)
            if bgm_list:
                tree.insert("", index=tk.END, iid="Sound", text="Sound")
                dl_text = "Sound: % 3d/% 3d"
                self.download_btn.config(text=dl_text % (0, len(dllist["Sound"])))
                self.progress['maximum'] = len(dllist["Sound"])
                self.progress['value'] = 0
                for bgm in bgm_list:
                    # Thread(target=download_url, args=([bgm], "Sound"))
                    # TODO multiprocessing
                    download_url([bgm], "Sound")
                    asset_history.write(os.path.splitext(bgm[1])[0] + '\n')
                    tree.insert("Sound", index=tk.END, text=bgm[1])
                    self.progress.step(1)
                    self.download_btn.config(text=dl_text % (self.progress['value'], len(dllist["Sound"])))
                    if not self.progress['value'] % 10:
                        asset_history.close()
                        asset_history = open(history_fp, 'at')
            asset_history.close()
        for button in button_list:
            button['state'] = tk.ACTIVE
        self.download_btn.config(text="Competed")
        self.after(100, self.download_btn.config, {"state": tk.ACTIVE, "text": "Download"})

    def config_sound(self, value):
        self.app_config["Sound"]["acb"] = str(value)

    def __init__(self, parent, **kwargs):
        ttk.Frame.__init__(self, parent, **kwargs)
        self.app_config = generate_config("config.ini")
        self.bsStyle = Style(theme="darktree")
        self.interrupt = tk.BooleanVar(value=False)
        self.chara_config = CharButtonGrid(self, self.app_config["Character"], text="Character", height=30, padding=10)
        self.chara_config.pack(fill=tk.X)
        self.merchant_config = MercButtonGrid(self, self.app_config["GachaMerchant"],
                                              text="GachaMerchant", height=30, padding=10)
        self.merchant_config.pack(fill=tk.X)
        self.sound_config = ttk.Labelframe(self, text="Sound", height=30, padding=10)
        self.sound_config.pack(fill=tk.X)
        self.sound_bool = tk.BooleanVar(value=self.app_config.getboolean("Sound", "acb"))
        self.sound_select = ttk.Checkbutton(self.sound_config, text="acb", variable=self.sound_bool,
                                            command=lambda: self.config_sound(self.sound_bool.get()),
                                            style="success.Outline.Toolbutton", width=16)
        ttk.Label(self.sound_config, text="BGM", width=10).pack(side=tk.LEFT)
        self.sound_select.pack(side=tk.LEFT)
        self.tree_frame = DownloadTree(self, self.app_config, text="Downloads")
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.download_btn = ttk.Button(self.status_frame, text="Download", width=20)
        self.download_btn.config(command=lambda: self.start_download((self.app_config, self.tree_frame.tree)))
        self.download_btn.pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(self.status_frame, style="info.Striped.Horizontal.TProgressbar")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)


class CharButtonGrid(ttk.Labelframe):
    def update_config(self, key):
        self.configs[key] = str(self.chara_filter[key].get())

    def __init__(self, parent, configs, **kwargs):
        ttk.Labelframe.__init__(self, parent, **kwargs)
        self.configs = configs
        self.chara_filter = {}
        self.segments = [("Sprite", [*configs.items()][0:2]),
                         ("Battle", [*configs.items()][2:5]),
                         ("Portrait", [*configs.items()][5:])]
        self.buttons = []
        for x, (name, group) in enumerate(self.segments):
            ttk.Label(self, text=name, width=10).grid(row=x, column=0)
            for i, (element, value) in enumerate(group):
                self.chara_filter[element] = tk.BooleanVar()
                self.chara_filter[element].set(value)
                temp = ttk.Checkbutton(self, text=element, variable=self.chara_filter[element],
                                       command=lambda elem=element: self.update_config(elem),
                                       style="success.Outline.Toolbutton", width=16,)
                temp.grid(row=x, column=i+1, sticky="EW")
                self.buttons.append(temp)


class MercButtonGrid(ttk.Labelframe):
    def update_config(self, key):
        self.configs[key] = str(self.file_filter[key].get())

    def __init__(self, parent, configs, **kwargs):
        ttk.Labelframe.__init__(self, parent, **kwargs)
        self.configs = configs
        self.buttons = []
        self.file_filter = {}
        ttk.Label(self, text="Sprite", width=10).grid(row=0, column=0)
        for i, (element, value) in enumerate(configs.items()):
            self.file_filter[element] = tk.BooleanVar()
            self.file_filter[element].set(value)
            temp = ttk.Checkbutton(self, text=element, variable=self.file_filter[element],
                                   command=lambda elem=element: self.update_config(elem),
                                   style="success.Outline.Toolbutton", width=16)
            temp.grid(row=0, column=i+1)
            self.buttons.append(temp)


class DownloadTree(ttk.Labelframe):
    def __init__(self, parent, configs, **kwargs):
        ttk.Labelframe.__init__(self, parent, **kwargs)
        self.configs = configs
        self.tree = ttk.Treeview(self, show="tree")
        self.vscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.config(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)


def main():
    root = tk.Tk()
    root.minsize(400, 300)
    my_app = App(root, padding=5)
    my_app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
    save_config("config.ini", my_app.app_config)


if __name__ == '__main__':
    main()
    # Depreciated - moved to Tkinter app
    # Obtain current game version hash and list of character IDs
    # urlBase = json.loads(requests.get('https://game.eclipse.imperialsaga.jp/na/config.txt').content)['resource']
    # charaJson = json.loads(requests.get(list_character.format(url=urlBase)).content)

    # Retrieve list of downloaded character IDs
    # history = default(set)
    # history_fp = 'test.txt'
    # if os.path.exists(history_fp):
    #     with open(history_fp, 'rt') as reader:
    #         for name, item in [line.strip().split('\t') for line in reader if line.strip()]:
    #             history[name].add(item)
    # print(history)
    # for i in [*history.keys()][:10]:
    #     print(set(configs.options("Character")) - history[i])
    # file_list_fp = os.path.join(ROOT, 'test.txt')
    # chara_id_list = {}
    # for id in [x.strip() for x in f if x.strip()]:
    #     if id not in history:
    #         chara_id_list[id] = filtered_entries
    #     elif filtered_entries - history[id]:
    #         chara_id_list[id] = filtered_entries - history[id]
    # if os.path.exists(file_list_fp):
    #     with open(file_list_fp, 'rt') as reader:
    #         for chara, types in [line.strip() for line in reader if line.strip()]:
    #             file_list[chara].add(types)
    # file_list_obj = open(file_list_fp, 'at')
    # Compare downloaded list with current ID list
    # charaList = [(x['charaPtn'], x['waitDummy']) for x in charaJson if x['charaPtn'] not in file_list]

    # for index, chara in enumerate(charaList):
    #     print(f'Downloading {chara[0]}')
    #     # charaUrl - download Sprite .png and .atlas
    #     dl_location = os.path.join(ROOT, f'chara/{chara[0]}')
    #     os.makedirs(dl_location, exist_ok=True)
    #     for filetype in types[:2]:
    #         dl_file = requests.get(chara_url.format(url=urlBase, charaID=chara[0], typed=filetype))
    #         if dl_file.status_code == 200:
    #             print(f'\tchara/{chara[0]}/{chara[0]}_sprite.{filetype}')
    #             with open(f'chara/{chara[0]}/{chara[0]}_sprite.{filetype}', 'wb') as file:
    #                 file.write(dl_file.content)
    #     # spineUrl - download battleWait .png .atlas .json
    #     if not chara[1]:  # filter chara_Dummy and any other `waitDummy` marked IDs
    #         for filetype in types:
    #             dl_file = requests.get(spine_format.format(url=urlBase, charaID=chara[0], typed=filetype))
    #             if dl_file.status_code == 200:
    #                 print(f'\tchara/{chara[0]}/{chara[0]}_battleWait.{filetype}')
    #                 with open(f'chara/{chara[0]}/{chara[0]}_battleWait.{filetype}', 'wb') as file:
    #                     file.write(dl_file.content)
    #         # card_url download charaCard / chara / Face / FaceImg .png
    #         for source in sources:
    #             print(f'chara/{chara[0]}/{chara[0]}_{source.split("/")[-1]}.png')
    #             dl_file = requests.get(card_url.format(url=urlBase, path=source, charaID=chara))
    #             if dl_file.status_code == 200:
    #                 with open(f'chara/{chara[0]}/{chara[0]}_{source.split("/")[-1]}.png', 'wb') as file:
    #                     file.write(dl_file.content)
    #     file_list_obj.write(chara[0] + '\n')
    #     if not index % 10:
    #         file_list_obj.close()
    #         file_list_obj = open(file_list_fp, 'at')
    # file_list_obj.close()
