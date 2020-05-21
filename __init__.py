import re

from mycroft import intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus.message import Message

# When a query is not fulfilled
NOTHING_FOUND = (CPSMatchLevel.GENERIC, {'type': 'something'})


class WebMusicControl(CommonPlaySkill):
    def __init__(self):
        super(WebMusicControl, self).__init__()
        self.regexes = {}
        self.is_playing = True

    # region OVERRIDDEN METHODS

    @intent_file_handler('control.music.web.intent')
    def handle_control_music_web(self, message):
        self.speak_dialog('control.music.web')

    def CPS_match_query_phrase(self, phrase):
        """Handler for common play framework play query."""
        # A client must be connected to play anything
        if not self.client_connected():
            self.log.debug('Web Music Control has no connected clients')
            if 'apple music' in phrase:
                return phrase, CPSMatchLevel.GENERIC
            else:
                return None

        # TODO: Maybe support more client names
        client_specified = 'apple music' in phrase
        bonus = 0.5 if client_specified else 0.0

        # Remove the 'on client' part of the phrase
        phrase = re.sub(self.translate_regex('on_client'), '', phrase)

        confidence, data = self.continue_playback_query(phrase, bonus)
        if not data:
            confidence, data = self.specific_query(phrase, bonus)
        if not data:
            self.log.log("Not enough information to request playback")
            return None

        if data.get('type') == "continue":
            if client_specified:
                return phrase, CPSMatchLevel.EXACT, data
            else:
                return phrase, CPSMatchLevel.GENERIC, data
        elif data.get('type') is not None:
            if client_specified:
                return phrase, CPSMatchLevel.EXACT, data
            else:
                return phrase, CPSMatchLevel.MULTI_KEY, data

    def CPS_start(self, phrase, data):
        self.log.debug("Attempting to request playback on web client")
        if not self.client_connected():
            self.log.info("No web clients connected, cannot request playback")
            return

        if data.get('type') is not None:
            message = Message('web_client:play', data)
            self.log.debug("Sending message to web client %s" % message)
            self.bus.emit(message)
            # TODO: Listen for web client response to tailor speech
            self.speak_dialog('Playing')


    # endregion

    # region QUERY

    def continue_playback_query(self, phrase, bonus):
        """Checks the given phrase to determine if it is asking to continue playback on the client"""
        if phrase.strip() == 'apple music':
            return 1.0, {'type': 'continue'}

        else:
            return NOTHING_FOUND


    def specific_query(self, phrase, bonus):
        """
        Check if the phrase contains enough information to play a song

        This includes asking for playlists, albums, artists or songs.

        Arguments:
            phrase (str): Text to match against
            bonus (float): Any existing match bonus

        Returns: Tuple with confidence and data or NOTHING_FOUND
        """
        # Check if playlist
        match = re.match(self.translate_regex('playlist'), phrase)
        if match:
            playlist = match.groupdict()['playlist']
            return 1.0, {'type': 'playlist', 'name': playlist}

        # Check album
        match = re.match(self.translate_regex('album'), phrase)
        if match:
            bonus += 0.1
            album = match.groupdict()['album']
            return 1.0, {'type': 'album', 'name': album}

        # Check artist
        match = re.match(self.translate_regex('artist'), phrase)
        if match:
            artist = match.groupdict()['artist']
            return 1.0, {'type': 'artist', 'name': artist}

        match = re.match(self.translate_regex('song'), phrase)
        if match:
            song = match.groupdict()['track']
            return 1.0, {'type': 'song', 'name': song}

        # TODO: Support song+artist and album+artist combinations

        return NOTHING_FOUND


    # endregion
    # region UTIL

    def client_connected(self):
        """
        Checks to see if there are any clients connected.

        No requests to clients should be sent if this returns False
        """
        # TODO: Check if client is connected
        return True


    def translate_regex(self, regex_name):
        if regex_name not in self.regexes:
            path = self.find_resource(regex_name + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex_name] = string
        return self.regexes[regex_name]


def create_skill():
    return WebMusicControl()
