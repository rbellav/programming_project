from .hall_of_fame_screen import _load_hof  
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()
        bg = Image(source='images/sfondo.png',
                   allow_stretch=True,
                   keep_ratio=False,
                   size_hint=(1, 1),
                   pos_hint={'x': 0, 'y': 0})
        layout.add_widget(bg)
        
        ui_layout = BoxLayout(orientation='vertical', 
                              padding=20, spacing=15,
                              size_hint=(0.8, 0.8),
                              pos_hint={'center_x': 0.5, 'center_y': 0.5})
        
        # input username
        self.username_input = TextInput(
            multiline=False,
            hint_text="Choose a username",
            size_hint=(None, None),
            font_name="Press2P",
            font_size=10,
            width=350,
            height=70,
            pos_hint={'center_x': 0.5}
        )
        ui_layout.add_widget(self.username_input)

        # start game button
        start_btn = Button(
            text="LET'S PLAY!",
            size_hint=(None, None),
            width=300,
            height=70,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(1, 0, 0, 1),
            color=(1, 1, 1, 1),
            font_name='Press2P',
            font_size=15
        )
        start_btn.bind(on_release=self.start_game)
        ui_layout.add_widget(start_btn)

        # Hall of Fame button
        hof_btn = Button(
            text="HALL OF FAME",
            size_hint=(None, None),
            width=300,
            height=70,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(1, 0, 0, 1),
            color=(1, 1, 1, 1),
            font_name='Press2P',
            font_size=15
        )
        hof_btn.bind(on_release=self.show_hall_of_fame)
        ui_layout.add_widget(hof_btn)

        # How to Play button
        howto_btn = Button(
            text="HOW TO PLAY",
            size_hint=(None, None),
            width=300,
            height=70,
            pos_hint={'center_x': 0.5},
            background_normal='',
            background_color=(1, 0, 0, 1),
            color=(1, 1, 1, 1),
            font_name='Press2P',
            font_size=15
        )
        howto_btn.bind(on_release=self.show_instructions)
        ui_layout.add_widget(howto_btn)

        layout.add_widget(ui_layout)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.username_input.text = getattr(app, "player_name", "")

    #  helpers
    def _username_exists_in_hof(self, name: str) -> bool:
        try:
            rows = _load_hof()
        except Exception:
            rows = []
        wanted = (name or "").strip()
        return any((r.get("name","") or "").strip() == wanted for r in rows)

    def _show_blocking_popup(self, message: str):
        content = BoxLayout(orientation='vertical', padding=[20, 20, 20, 20], spacing=16)
        msg = Label(text=message, font_name="Press2P", font_size=20, color=(1,1,1,1))
        ok_btn = Button(text="OK", size_hint=(None,None), size=(140,44),
                        background_normal='', background_color=(0.9,0.9,0.9,0.6),
                        color=(0,0,0,1), font_name="Press2P", font_size=18)
        content.add_widget(msg); content.add_widget(ok_btn)
        popup = Popup(title='', content=content, size_hint=(0.6, 0.35), auto_dismiss=False)
        ok_btn.bind(on_release=popup.dismiss)
        popup.open()

    def start_game(self, instance):
        username = (self.username_input.text or "").strip()

        if not username:
            self._show_blocking_popup("Please choose a valid username.")
            return

        # block if username already in Hall of Fame
        if self._username_exists_in_hof(username):
            self._show_blocking_popup(f"Username '{username}' is already in the Hall of Fame.\nChoose another one.")
            return

        App.get_running_app().player_name = username

        self.manager.current = 'level_select'

    def show_hall_of_fame(self, instance):
        self.manager.current = 'halloffame'

    def show_instructions(self, instance):
        content = BoxLayout(orientation='vertical', padding=[20, 20, 20, 20], spacing=16)

        title_lbl = Label(
            text="How to Play",
            font_name="Press2P",
            font_size=28,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=35
        )
        instructions = Label(
            text="- use the keys 'A' and 'D' to move the tank back and forth\n\n"
                 "- use ← and → to change the shooting angle\n\n"
                 "- use 'Up' and 'Down' to change the power of the shot\n\n"
                 "- press the Space bar to shoot\n\n",
            font_name="Press2P",
            font_size=18,
            color=(1, 1, 1, 1)
        )
        close_btn = Button(
            text="Close",
            size_hint=(None, None), size=(180, 50),
            background_normal='',
            background_color=(0.9, 0.9, 0.9, 0.6),
            color=(0, 0, 0, 1),
            font_name="Press2P", font_size=18
        )

        content.add_widget(title_lbl)
        content.add_widget(instructions)
        content.add_widget(close_btn)

        popup = Popup(title='', content=content, size_hint=(0.9, 0.7), auto_dismiss=False)
        close_btn.bind(on_release=popup.dismiss)
        popup.open()