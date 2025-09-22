from kivy.uix.screenmanager import ScreenManager
from .start_screen import StartScreen

from .hall_of_fame_screen import HallOfFameScreen
from .level_select_screen import LevelSelectScreen
from .level1_screen import Level1Screen
from .level2_screen import Level2Screen
from .level3_screen import Level3Screen



class ScreenManagement(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(StartScreen(name='home'))
       
        
        self.add_widget(HallOfFameScreen(name='halloffame'))
        self.add_widget(LevelSelectScreen(name='level_select'))
        self.add_widget(Level1Screen(name='level1'))
        self.add_widget(Level2Screen(name='level2'))
        self.add_widget(Level3Screen(name='level3'))

