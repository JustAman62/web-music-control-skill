import re

from mycroft import intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus.message import Message
from mycroft.skills.padatious_service import PadatiousService
from padatious import IntentContainer

# When a query is not fulfilled
NOTHING_FOUND = (CPSMatchLevel.GENERIC, None)


class WebMusicControl(CommonPlaySkill):
    def __init__(self):
        super(WebMusicControl, self).__init__()
        self.regexes = {}
        self.is_playing = True

        self.intent_container: IntentContainer = IntentContainer('play_intent_cache')
        self.add_intents_from_file("play.song.intent")
        self.add_intents_from_file("play.album.intent")
        self.add_intents_from_file("play.artist.intent")
        self.add_intents_from_file("play.playlist.intent")

        self.add_entity_from_file("song_name.entity")
        self.add_entity_from_file("playlist_name.entity")
        # self.add_intents_from_file("play.something.intent")
        # self.add_intents_from_file("continue.intent")
        self.log.info("Training play intent parser")
        self.intent_container.train()
        self.log.info("Done Training")

    def add_intents_from_file(self, intent_file_name):
        intent_file_path = self.find_resource(intent_file_name, "vocab")
        with open(intent_file_path) as file:
            intents = file.readlines()
            self.intent_container.add_intent(intent_file_name, intents)

    def add_entity_from_file(self, entity_file_name):
        entity_file_path = self.find_resource(entity_file_name, "vocab")
        with open(entity_file_path) as file:
            intents = file.readlines()
            self.intent_container.add_entity(entity_file_name, intents)

    # region OVERRIDDEN METHODS

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
        conf_threshold = 0.7 if client_specified else 0.5

        # Remove the 'on client' part of the phrase
        phrase = re.sub(self.translate_regex('on_client'), '', phrase)
        print(phrase)
        intent_data = self.intent_container.calc_intent("play " + phrase)
        self.log.info("padatious intent parse results")
        self.log.info(intent_data)

        if intent_data.conf < 0.5:
            self.log.info("Intent confidence too low")
            return None

        intent_name: str = intent_data.name
        matches = intent_data.matches
        level = None
        data = None

        if intent_name.startswith("play."):
            song_name = matches.get("song_name")
            artist_name = matches.get("artist_name")
            album_name = matches.get("album_name")
            playlist_name = matches.get("playlist_name")

            if playlist_name:
                data = {"type": "playlist", "name": playlist_name}
            elif song_name and album_name:
                data = {"type": "songs+albums", "name": "%s %s" % (song_name, album_name)}
            elif song_name and artist_name:
                data = {"type": "songs", "name": "%s %s" % (song_name, artist_name)}
            elif song_name:
                data = {"type": "songs", "name": song_name}
            elif album_name:
                data = {"type": "albums", "name": album_name}
            elif artist_name:
                data = {"type": "artists", "name": artist_name}

            if intent_data.conf == 1.0:
                level = CPSMatchLevel.EXACT
            elif intent_data.conf > conf_threshold:
                level = CPSMatchLevel.MULTI_KEY
            else:
                level = CPSMatchLevel.TITLE

        if client_specified and data:
            level = CPSMatchLevel.EXACT

        return phrase, level, data


    def CPS_start(self, phrase, data):
        self.log.debug("Attempting to request playback on web client")
        if not self.client_connected():
            self.log.info("No web clients connected, cannot request playback")
            return

        if data.get('type') is not None:
            message = Message('web-music-control:play', data)
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

        # Play some random artist/playlist/something they like etc
        match = re.match(self.translate_regex('something'), phrase)
        if match:
            return 1.0, {'type': 'something'}
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
