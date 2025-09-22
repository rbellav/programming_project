from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button

class LevelSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.level2_unlocked = False
        self.level3_unlocked = False
        self.levels_completed = {}
        self.layout = FloatLayout()
        self.build_ui()
        self.add_widget(self.layout)

    def build_ui(self):
        self.layout.clear_widgets()

         # background image based on unlocked levels
        if self.level3_unlocked:
            bg_image = 'images/Level 3.png'
        elif self.level2_unlocked:
            bg_image = 'images/Level 2.png'
        else:
            bg_image = 'images/Level 1.png'
        bg = Image(source=bg_image,
                   allow_stretch=True, keep_ratio=False,)
        self.layout.add_widget(bg)

        # level 1 button
        btn1 = Button(
            text="Play",
            size_hint=(None, None),
            size=(150, 60),
            pos_hint={'center_x': 0.17, 'center_y': 0.25},
            background_color=(0.298, 0.686, 0.314, 1),
            color=(1, 1, 1, 1),
            font_name='Press2P',
            font_size=20
        )
        btn1.bind(on_release=self.go_to_level1)
        self.layout.add_widget(btn1)

        # level 2 button
        btn2 = Button(
            text="Play" if self.level2_unlocked else "Locked",
            size_hint=(None, None),
            size=(150, 60),
            pos_hint={'center_x': 0.5, 'center_y': 0.25},
            disabled=not self.level2_unlocked,
            background_color=(0.298, 0.686, 0.314, 1) if self.level2_unlocked else (0.533, 0.533, 0.533, 1),
            color=(1, 1, 1, 1),
            font_name='Press2P',
            font_size=20
        )
        if self.level2_unlocked:
            btn2.bind(on_release=self.go_to_level2)
        self.layout.add_widget(btn2)

        # level 3 button
        btn3 = Button(
            text="Play" if self.level3_unlocked else "Locked",
            
            size_hint=(None, None),
            size=(150, 60),
            pos_hint={'center_x': 0.83, 'center_y': 0.25},
            disabled=not self.level3_unlocked,
            background_color=(0.533, 0.533, 0.533, 1) if self.level3_unlocked else (0.533, 0.533, 0.533, 1),
            color=(1, 1, 1, 1),
            font_name='Press2P',
            font_size=20
        )
        if self.level3_unlocked:
            btn3.bind(on_release=self.go_to_level3)
        self.layout.add_widget(btn3)

    def go_to_level1(self, instance):
        self.manager.current = 'level1'

    def go_to_level2(self, instance):
        self.manager.current = 'level2'

    def go_to_level3(self, instance):
        self.manager.current = 'level3'

    def unlock_level2(self):
        self.level2_unlocked = True
        self.build_ui()

    def unlock_level3(self):
        self.level3_unlocked = True
        self.build_ui()