import utime as time
from buzzer import Buzzer, SONGS


class DelverBuzz(Buzzer):

    def ok(self, song=SONGS[0]):
        for i in range(0, len(song.melody)):  # Play song

            noteDuration = song.pace / song.tempo[i]
            self.buzz(song.melody[i], noteDuration)  # Change the frequency along the song note

            pauseBetweenNotes = noteDuration * song.pause
            time.sleep(pauseBetweenNotes)

    def beep(self, song=SONGS[2]):
        for i in range(0, len(song.melody)):  # Play song

            noteDuration = song.pace / song.tempo[i]
            self.buzz(song.melody[i], noteDuration)  # Change the frequency along the song note

            pauseBetweenNotes = noteDuration * song.pause
            time.sleep(pauseBetweenNotes)

    def fail(self, song= SONGS[1]):
        for i in range(0, len(song.melody)):  # Play song

            noteDuration = song.pace / song.tempo[i]
            self.buzz(song.melody[i], noteDuration)  # Change the frequency along the song note

            pauseBetweenNotes = noteDuration * song.pause
            time.sleep(pauseBetweenNotes)
