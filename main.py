from kivy.config import Config

Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'fullscreen', '0')  
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')
Config.set('graphics', 'show_cursor', '1')
Config.set('graphics', 'window_state', 'visible')  
Config.write()

from kivy.core.text import LabelBase
LabelBase.register(name='Press2P', fn_regular='fonts/PressStart2P-Regular.ttf')

from constants.screen_constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from kivy.app import App
from screens.screen_manager import ScreenManagement

from screens.start_screen import StartScreen

class ToonTanksApp(App):
    def build(self):
         
        self.player_name = ""  # to memorize player's name

        sm = ScreenManagement()

        sm.current = 'home'
        return sm

if __name__ == '__main__':
    ToonTanksApp().run()