
import os, json, datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.app import App


HOF_PATH = os.path.join("data", "hof.json")


def _ensure_data_dir():
    d = os.path.dirname(HOF_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def _load_hof():
    _ensure_data_dir()
    if os.path.isfile(HOF_PATH):
        try:
            with open(HOF_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_hof(rows):
    _ensure_data_dir()
    with open(HOF_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def report_level_win(level_screen, level_id: str):
    app = App.get_running_app()
    # initialize tracking if needed
    if not hasattr(app, "shots_per_level"):
        app.shots_per_level = {}
    if not hasattr(app, "levels_cleared"):
        app.levels_cleared = set()

    used = max(0, getattr(level_screen, "max_shots", 0) - getattr(level_screen, "remaining_shots", 0))
    app.shots_per_level[str(level_id)] = used
    app.levels_cleared.add(str(level_id))

    # if all 3 levels cleared, save to hof
    if len(app.levels_cleared) == 3:
        total = sum(app.shots_per_level.get(str(i), 0) for i in (1, 2, 3))
        name = (getattr(app, "player_name", "") or
                getattr(getattr(level_screen.manager, "parent", object()), "player_name", "") or
                "Player").strip()

        
        rows = _load_hof()
       
        found = None
        for r in rows:
            if r.get("name", "") == name:
                found = r
                break
        if found is None or total < found.get("shots", 10**9):
            
            entry = {"name": name, "shots": total, "date": datetime.date.today().isoformat()}
            if found is None:
                rows.append(entry)
            else:
                found.update(entry)
            _save_hof(rows)

        
        app.shots_per_level = {}
        app.levels_cleared = set()


class HallOfFameScreen(Screen):
    FONT = 'fonts/PressStart2P-Regular.ttf'
    BLACK = (0, 0, 0, 1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = FloatLayout()

        # background
        self.bg = Image(
            source='images/hof.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        root.add_widget(self.bg)

        # table 
        self.table_container = BoxLayout(
            orientation='vertical',
            spacing=12,
            padding=[20, 30, 20, 30],  # left, bottom, right, top
            size_hint=(0.92, 0.62),
            pos_hint={'center_x': 0.5, 'y': 0.10}
        )
        root.add_widget(self.table_container)

        # tabella header
        self.header = GridLayout(cols=3, size_hint=(1, None), height=44, spacing=6)
        self.table_container.add_widget(self.header)

        # body of table 
        self.scroll = ScrollView(size_hint=(1, 1))
        self.table = GridLayout(cols=3, size_hint_y=None, spacing=6, padding=[0, 6, 0, 0])
        self.table.bind(minimum_height=self.table.setter('height'))
        self.scroll.add_widget(self.table)
        self.table_container.add_widget(self.scroll)

        # back button
        self.back_btn = Button(
            text="Back",
            font_name=self.FONT,
            font_size=20,
            color=self.BLACK,
            background_normal='',
            background_color=(1, 1, 1, 0.7),
            size_hint=(None, None),
            width=200, height=60,
            pos_hint={'center_x': 0.5, 'y': 0.05}
        )
        self.back_btn.bind(on_release=self._go_back)
        root.add_widget(self.back_btn)

        self.add_widget(root)

    
    def _cell(self, text, header=False):
        return Label(
            text=str(text),
            color=self.BLACK,
            font_name=self.FONT,
            font_size=22 if header else 18,
            size_hint_y=None,
            height=38 if header else 34,
        )

    
    def on_pre_enter(self, *args):
        self.refresh()

    def on_pre_leave(self, *args):
        self._reset_player_context()
    
    def refresh(self):
        rows = _load_hof()
        rows = sorted(
            rows,
            key=lambda r: (r.get("shots", 10**9), (r.get("name", "") or "").lower())
        )
        self.rows = rows

        # header
        self.header.clear_widgets()
        self.header.add_widget(self._cell("RANK", header=True))
        self.header.add_widget(self._cell("PLAYER", header=True))
        self.header.add_widget(self._cell("SHOTS", header=True))

        
        self.table.clear_widgets()
        for i, r in enumerate(rows, start=1):
            self.table.add_widget(self._cell(i))
            self.table.add_widget(self._cell(r.get("name", "-")))
            self.table.add_widget(self._cell(r.get("shots", "-")))

    def add_record(self, name: str, shots: int):
        
        rows = _load_hof()
        found = None
        for r in rows:
            if r.get("name", "") == name:
                found = r
                break
        if found is None or shots < found.get("shots", 10**9):
            entry = {"name": name, "shots": shots, "date": datetime.date.today().isoformat()}
            if found is None:
                rows.append(entry)
            else:
                found.update(entry)
            _save_hof(rows)
        self.refresh()

    
    def _reset_player_context(self):
        app = App.get_running_app()

        
        try:
            app.player_name = ""
        except Exception:
            pass

        
        try:
            parent = getattr(self.manager, "parent", None)
            if parent is not None and hasattr(parent, "player_name"):
                parent.player_name = ""
        except Exception:
            pass

        # reset level tracking
        for attr in ("shots_per_level", "levels_cleared"):
            if hasattr(app, attr):
                setattr(app, attr, {} if attr == "shots_per_level" else set())

    def _clear_start_ui(self, *_):
        """Eseguito dopo lo switch: ripulisce il widget nello Start in modo robusto."""
        try:
            if 'start' in self.manager.screen_names:
                start = self.manager.get_screen('start')
                
                if hasattr(start, "set_player_name"):
                    start.set_player_name("")
                    return
                
                if hasattr(start, "name_input"):
                    try:
                        start.name_input.text = ""
                        return
                    except Exception:
                        pass
                
                ids = getattr(start, "ids", {})
                if "name_input" in ids:
                    ids["name_input"].text = ""
                    return
               
                if hasattr(start, "player_name"):
                    start.player_name = ""
        except Exception:
            pass

    
    def _go_back(self, *_):
        self._reset_player_context()

        target = 'start' if 'start' in self.manager.screen_names else self.manager.screen_names[0]
        self.manager.current = target
