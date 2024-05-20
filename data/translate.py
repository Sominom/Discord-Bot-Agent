import json
from data.bot_logger import BotLogger

class Translate:
    def __init__(self):
        self.Logger = BotLogger()
        self.translate_file_path = "data/translate.json"
        self.translate = {}
        self.load_translate()
            
    def add_translate(self, key, value):
        try:
            self.translate[key] = value
            with open(self.translate_file_path, "w", encoding="utf-8") as f:
                json.dump(self.translate, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.Logger.log(f"Translate add error: {key}, {str(e)}", self.Logger.ERROR)
            
    def load_translate(self):
        try:
            with open(self.translate_file_path, "r", encoding="utf-8") as f:
                self.translate = json.load(f)
        except FileNotFoundError:
            self.Logger.log("Translate file not found, initializing with empty dictionary.", self.Logger.WARNING)
            self.translate = {}
        except json.JSONDecodeError:
            self.Logger.log("Translate file is not valid JSON, initializing with empty dictionary.", self.Logger.ERROR)
            self.translate = {}
        except Exception as e:
            self.Logger.log(f"Translate file load error: {str(e)}", self.Logger.ERROR)
            self.translate = {}
            
    def text(self, key):
        value = self.translate.get(key, "")
        self.Logger.log(f"Translate: {key} -> {value}")
        if value == "":
            self.add_translate(key, key)
            return key
        return value
    