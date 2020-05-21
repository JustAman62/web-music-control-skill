from mycroft import MycroftSkill, intent_file_handler


class WebMusicControl(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('control.music.web.intent')
    def handle_control_music_web(self, message):
        self.speak_dialog('control.music.web')


def create_skill():
    return WebMusicControl()

