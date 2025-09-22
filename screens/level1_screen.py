import math
import random
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Rotate, PushMatrix, PopMatrix
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.properties import NumericProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from physics import get_initial_velocity, GRAVITY
from constants.screen_constants import BULLET_MASS, BULLET_RADIUS, BOMB_MASS, BOMB_RADIUS, BOMB_DRILL
from .hall_of_fame_screen import report_level_win


class Perpetio(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/ostacolo_simpson2.png',
                         size_hint=(None, None),
                         size=(180, 180),
                         pos=(x, y),
                         **kwargs)
        self.indestructible = True


class RockBlock(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/ostacolo_simpson.png',
                         size_hint=(None, None),
                         size=(150, 150),
                         pos=(x, y),
                         **kwargs)
        self.destroyed = False

    def destroy(self):
        if not self.destroyed:
            self.destroyed = True
            self.parent.remove_widget(self)

class RockField(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.blocks = []
        Window.bind(on_resize=self._on_resize)

    def generate_blocks(self, count=15, avoid_areas=None):
        self.clear_widgets()
        self.blocks.clear()

        screen_width, screen_height = Window.size
        block_size = (150, 150)
        max_attempts = 100

        if avoid_areas is None:
            avoid_areas = []

        ground_limit = 150
        avoid_areas.append((0, 0, screen_width, ground_limit))

        attempts = 0
        while len(self.blocks) < count and attempts < max_attempts:
            attempts += 1
            x = random.randint(0, screen_width - block_size[0])
            y = random.randint(ground_limit, screen_height - block_size[1])

            new_block_area = (x, y, block_size[0], block_size[1])

            if any(self._intersects(new_block_area, (b.x, b.y, b.width, b.height)) for b in self.blocks):
                continue
            if any(self._intersects(new_block_area, area) for area in avoid_areas):
                continue

            block = RockBlock(x, y)
            self.blocks.append(block)
            self.add_widget(block)

    def _intersects(self, a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (ax < bx + bw and ax + aw > bx and
                ay < by + bh and ay + ah > by)

    def _on_resize(self, window, width, height):
        self.generate_blocks()

    def check_collision(self, projectile):
        px, py = projectile.center
        for block in self.blocks[:]:
            if block.collide_point(px, py):
                self.blocks.remove(block)
                self.remove_widget(block)
                return True
        return False

class Bullet(Image):
    def __init__(self, x, y, angle, speed, **kwargs):
        super().__init__(source='images/bullet.png', size_hint=(None, None), size=(40, 40), pos=(x, y), **kwargs)
        self.mass = BULLET_MASS
        self.radius = BULLET_RADIUS
        self.vx, self.vy = get_initial_velocity(angle, speed)
        self.has_impacted = False

    def move(self, dt=1/60):
        if not self.has_impacted:
            self.x += self.vx * dt * 60
            self.y += self.vy * dt * 60
            self.vy -= GRAVITY * dt * 60
            if self.y < 0:
                self.impact()

    def impact(self):
        self.has_impacted = True

class Bomb(Image):
    def __init__(self, x, y, angle, speed, **kwargs):
        super().__init__(source='images/bomb.png', size_hint=(None, None), size=(40, 40), pos=(x, y), **kwargs)
        self.mass = BOMB_MASS
        self.radius = BOMB_RADIUS
        self.drill = BOMB_DRILL
        self.vx, self.vy = get_initial_velocity(angle, speed)
        self.has_impacted = False

    def move(self, dt=1/60):
        if not self.has_impacted:
            self.x += self.vx * dt * 60
            self.y += self.vy * dt * 60
            self.vy -= GRAVITY * dt * 60
            if self.y < 0:
                self.y -= self.drill
                self.impact()

    def impact(self):
        self.has_impacted = True

class Tank(Widget):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 300
        self.body_width = 150
        self.body_height = 100
        self.barrel_width = 10
        self.barrel_height = 60
        self.speed = 15
        self.projectile_speed = 15
        self.pos = (50, 100)
        self.create_tank_graphics()
        self.bind(pos=self.update_graphics)
        self.bind(angle=self.update_rotation)

    def increase_power(self):
        self.projectile_speed = min(self.projectile_speed + 1, 40)

    def decrease_power(self):
        self.projectile_speed = max(self.projectile_speed - 1, 5)

    def create_tank_graphics(self):
        self.canvas.clear()
        x, y = self.pos
        center_x = x + self.body_width / 2
        center_y = y + self.body_height * 0.7
        with self.canvas:
            self.tank_body = Rectangle(source='images/tank_simpson.png', pos=(x, y), size=(self.body_width, self.body_height))
            PushMatrix()
            self.rotation = Rotate(angle=self.angle, origin=(center_x, center_y))
            Color(1, 0, 0, 1)
            self.barrel = Rectangle(pos=(center_x - self.barrel_width / 2, center_y), size=(self.barrel_width, self.barrel_height))
            PopMatrix()
        self.update_graphics()

    def update_graphics(self, *args):
        x, y = self.pos
        center_x = x + self.body_width / 2
        center_y = y + self.body_height * 0.7
        self.tank_body.pos = (x, y)
        self.rotation.origin = (center_x, center_y)
        self.barrel.pos = (center_x - self.barrel_width / 2, center_y)

    def update_rotation(self, *args):
        self.rotation.angle = self.angle

    def move(self, keys_pressed):
        x, y = self.pos
        parent_width = self.parent.width if self.parent else Window.width
        if 'left' in keys_pressed:
            x -= self.speed
        if 'right' in keys_pressed:
            x += self.speed
        max_x = parent_width / 2 - self.body_width
        x = max(0, min(max_x, x))

        self.pos = (x, y)

    def rotate_barrel(self, direction):
        if direction == 'd' and self.angle < 360:
            self.angle += 2
        elif direction == 'a' and self.angle > 270:
            self.angle -= 2

class HelpOverlay(ModalView):
    def __init__(self, image_source, on_close=None, **kwargs):
        # size_hint=(1,1) to cover full screen
        super().__init__(size_hint=(1, 1), auto_dismiss=True, background_color=(0,0,0,0), **kwargs)
        self.on_close = on_close

        root = FloatLayout()

        # dark semi-transparent background
        with root.canvas.before:
            Color(0, 0, 0, 0.65)
            self._bg = Rectangle(pos=(0,0), size=(1,1))

        def _upd_bg(*_):
            self._bg.pos = root.pos
            self._bg.size = root.size
        root.bind(pos=_upd_bg, size=_upd_bg)

        self.help_img = Image(source=image_source, allow_stretch=True, keep_ratio=True,
                              size_hint=(0.8, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.53})
        root.add_widget(self.help_img)

        # close button
        close_btn = Button(text='Close', size_hint=(None, None), size=(140, 48),
                           pos_hint={'center_x': 0.5, 'y': 0.05})
        close_btn.bind(on_release=lambda *_: self.dismiss())
        root.add_widget(close_btn)

        self.add_widget(root)

    def on_dismiss(self):
        if callable(self.on_close):
            self.on_close()


class Level1Screen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_ammo = "bullet"
        self.level_completed = False

        self.background = Image(source='images/bg_simpson.png', allow_stretch=True, keep_ratio=False,
                                size=self.size, pos=self.pos)
        self.bind(size=self._resize_background, pos=self._resize_background)
        self.add_widget(self.background)

        self.rock_field = RockField()
        self.add_widget(self.rock_field)

        self.target = Image(source='images/target_simpson.png', size_hint=(None, None), size=(300, 300))
        self.add_widget(self.target)

        self.tank = Tank()
        self.add_widget(self.tank)

        self.max_shots = 7
        self.remaining_shots = self.max_shots
        self._win_armed = False
        self._allow_win_sound = False

        self.music = SoundLoader.load('sounds/simpson_sound.ogg')  

        self.sfx_win = SoundLoader.load('sounds/winner.mp3')
        self.sfx_lose = SoundLoader.load('sounds/game over.mp3')       
        if self.sfx_lose:
            self.sfx_lose.loop = False
        if self.sfx_win:
            self.sfx_win.loop = False
        self._played_win = False

      

        self.sfx_shoot_bullet = SoundLoader.load('sounds/shot.mp3')
        self.sfx_shoot_bomb   = SoundLoader.load('sounds/bomb.mp3')
        for s in (self.sfx_shoot_bullet, self.sfx_shoot_bomb):
            if s: s.loop = False
        
        self.hud = BoxLayout(orientation='horizontal', size_hint=(1, None), height=70, padding=[20, 20], spacing=30)
        with self.hud.canvas.before:
            Color(0, 0, 0, 0.6)
            self.hud_bg = Rectangle(pos=self.hud.pos, size=self.hud.size)
        self.hud.bind(pos=self._update_hud_bg, size=self._update_hud_bg)

        self.info_label = Label(text='Angle: 90°   Power: 15   Ammo: BULLET', font_size=20, 
                                color=(1, 1, 1, 1), 
                                font_name="Press2P", 
                                size_hint=(1, 1))
        self.hud.add_widget(self.info_label)
        self.add_widget(self.hud)

        # help button in HUD
        self.help_btn = Button(text='Help', size_hint=(None, None), 
                               size=(120, 40), font_name="Press2P", 
                               font_size=18, color=(1,1,1,1))
        self.help_btn.bind(on_release=self.open_help)
        self.hud.add_widget(self.help_btn)

        self.projectiles = []
        self.target_hit = False

        self.bind(size=self._resize_elements)
        
    def _play_once(self, snd):
        if not snd:
            return
        try:
            snd.stop()
            snd.loop = False
            snd.play()
        except Exception:
            pass

    def _reset_sfx_flags(self):
        if self.sfx_lose:
            self.sfx_lose.stop()

    def open_help(self, *_):
        if hasattr(self, 'stop_loop'):
            self.stop_loop()

        overlay = HelpOverlay(
            image_source='images/help_lev1.png', 
            on_close=self._resume_after_help
        )
        overlay.open()       

    def _resume_after_help(self):
        if hasattr(self, 'start_loop'):
            self.start_loop()

    def _resize_background(self, *args):
        self.background.size = self.size
        self.background.pos = self.pos

    def _resize_elements(self, *args):
        self.hud.size = (self.width, 70)
        self.target.pos = (self.width - self.target.width - 50, 100)

    def on_enter(self):
        self._played_win = False
        self._reset_sfx_flags()
        self.setup_level()
        self.start_loop()
        Window.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up) 
        if self.music:
            self.music.loop = True
            self.music.play()

    def on_leave(self, *args):
        try:
            Window.unbind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        except Exception:
            pass
        self.stop_loop()
        if self.music:
            self.music.stop()
            
    def setup_level(self):
        self.remaining_shots = self.max_shots
        self.current_ammo = "bullet"
        self.projectiles.clear()
        self.target_hit = False
        self._resize_elements()

        tank_area = (self.tank.x, self.tank.y, self.tank.body_width, self.tank.body_height)
        target_area = (self.target.x, self.target.y, self.target.width, self.target.height)
        
        perpetio_x = self.width // 2 - 60  
        perpetio_y = self.tank.y           
        self.perpetio = Perpetio(perpetio_x, perpetio_y)
        self.add_widget(self.perpetio)
        perpetio_area = (self.perpetio.x, self.perpetio.y, self.perpetio.width, self.perpetio.height)

        self.rock_field.generate_blocks(avoid_areas=[tank_area, target_area, perpetio_area])

    def _update_hud_bg(self, *args):
        self.hud_bg.pos = self.hud.pos
        self.hud_bg.size = self.hud.size

    def check_collision(self, projectile, target):
        px, py = projectile.center
        tx, ty = target.center
        tw, th = target.size
        return (tx - tw / 2 < px < tx + tw / 2) and (ty - th / 2 < py < ty + th / 2)

    def explode_target(self):
        if self.level_completed:
            return
        self.level_completed = True
        explosion = Image(source='images/explosion.png', size=self.target.size, pos=self.target.pos, size_hint=(None, None))
        self.add_widget(explosion)
        winner_label = Label(text='WINNER!', font_size=130, font_name='fonts/PressStart2P-Regular.ttf', 
                             color=(227/255, 11/255, 92/255, 1), pos=(self.width / 2, self.height / 2 + 50), 
                             size_hint=(None, None))
        self.add_widget(winner_label)
        self.target_hit = True
        if self.music:
            self.music.stop()
        report_level_win(self, "1")
        if self.sfx_win and not self._played_win:
            try:
                self.sfx_win.stop()  
            except:
                pass
            self.sfx_win.play()
            self._played_win = True

        # next level button
        next_lev_btn = Button(
            text='Next Level',
            font_size=16,
            font_name='Press2P',
            size_hint=(None, None),
            size=(200, 50),
            pos=(self.width / 2 - 100, self.height / 2 - 30)
        )
        
        next_lev_btn.bind(on_release=self.go_to_level_select)
        self.add_widget(next_lev_btn)

        self.target_hit = True  # block other shots

    def go_to_level_select(self, *args):
        level_select_screen = self.manager.get_screen('level_select')
        level_select_screen.unlock_level2()
        self.manager.current = 'level_select'

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if self.level_completed:
            return
        if key == 276:
            self.tank.rotate_barrel('d')
        elif key == 275:
            self.tank.rotate_barrel('a')
        elif key == 273:
            self.tank.increase_power()
        elif key == 274:
            self.tank.decrease_power()
        elif codepoint:
            c = codepoint.lower()
            if c in ['a', 'd']:
                self.tank.move({c == 'a' and 'left' or 'right'})
            elif c == 'w':
                self.toggle_ammo()
            elif c == ' ' and not self.target_hit:
                self.fire_projectile()

    def _on_key_up(self, window, key, scancode):
        pass

    def toggle_ammo(self):
        self.current_ammo = "bomb" if self.current_ammo == "bullet" else "bullet"

    def fire_projectile(self):
        if self.remaining_shots <= 0 or self.target_hit:
            return
        tank = self.tank
        center_x = tank.x + tank.body_width / 2
        center_y = tank.y + tank.body_height * 0.7
        angle_rad = math.radians(-tank.angle )
        offset_x = math.sin(angle_rad) * tank.barrel_height
        offset_y = math.cos(angle_rad) * tank.barrel_height
        bullet_x = center_x + offset_x - 15
        bullet_y = center_y + offset_y - 15
        speed = tank.projectile_speed

        if self.current_ammo == "bullet":
            p = Bullet(x=bullet_x, y=bullet_y, angle=tank.angle, speed=speed)
        else:
            p = Bomb(x=bullet_x, y=bullet_y, angle=tank.angle, speed=speed)
        p._travel = 0.0 
        p._age_frames = 0
        p._hit_frames = 0

        self.projectiles.append(p)
        self.add_widget(p)

        if self.current_ammo == "bullet":
            if self.sfx_shoot_bullet: self._play_once(self.sfx_shoot_bullet)
        else:
            if self.sfx_shoot_bomb:   self._play_once(self.sfx_shoot_bomb)

        self.remaining_shots -= 1

    def start_loop(self):
        if not hasattr(self, '_upd_ev') or self._upd_ev is None:
            self._upd_ev = Clock.schedule_interval(self.update, 1.0 / 60.0)
    
    def stop_loop(self):
        if hasattr(self, '_upd_ev') and self._upd_ev is not None:
            self._upd_ev.cancel()
            self._upd_ev = None

    def reset_level(self, *args):
        self.stop_loop()
        if hasattr(self, 'sfx_win') and self.sfx_win:
            self.sfx_win.stop()

        self.clear_widgets()
        self.add_widget(self.background)
        self.add_widget(self.rock_field)
        self.add_widget(self.target)
        self.add_widget(self.tank)
        self.add_widget(self.hud)
        self.setup_level()
        self._level_ready = False
        Clock.schedule_once(lambda dt: setattr(self, "_level_ready", True), 0)
        self.start_loop()
        if self.music:
            self.music.play()


    def update(self, dt):
        to_remove = []
        for p in self.projectiles:
            prev_cx, prev_cy = p.center
            p.move()
            step = math.hypot(p.center_x - prev_cx, p.center_y - prev_cy)

            p._travel = getattr(p, "_travel", 0.0) + step
            p._age_frames = getattr(p, "_age_frames", 0) + 1

            # check collision with rock blocks
            if self.rock_field.check_collision(p):
                self.remove_widget(p)
                to_remove.append(p)
                continue

            if p._travel >= 40 and self.check_collision(p, self.target):
                self.explode_target()
                self.remove_widget(p)
                to_remove.append(p)
                break

            # check collision with perpetio
            if hasattr(self, "perpetio") and self.perpetio.collide_point(*p.center):
                self.remove_widget(p)
                to_remove.append(p)
                continue

            # remove if out of bounds
            if getattr(p, 'has_impacted', False):
                self.remove_widget(p)
                to_remove.append(p)

        for p in to_remove:
            if p in self.projectiles:
                self.projectiles.remove(p)

        angle = int(self.tank.angle - 270)
        speed = int(self.tank.projectile_speed)
        ammo = "BOMB" if self.current_ammo == "bomb" else "BULLET"
        self.info_label.text = f"Angle: {angle}°   Power: {speed},   Ammo: {ammo},   Shots: {self.remaining_shots}"
        if self.remaining_shots <= 0 and not self.target_hit and not self.projectiles:
            self.show_loss()

    def show_loss(self):
        lose_label = Label(
            text='GAME OVER!',
            font_size=130,
            font_name= 'fonts/PressStart2P-Regular.ttf',
            color=(0, 0, 0, 1),
            pos=(self.width / 2, self.height / 2 + 50),
            size_hint=(None, None)
        )
        self.add_widget(lose_label)
        if self.music:
            self.music.stop()
        self._play_once(self.sfx_lose)

        # try again button
        try_again_btn = Button(
            text='Try Again',
            font_size=16,
            font_name='Press2P',
            size_hint=(None, None),
            size=(200, 50),
            pos=(self.width / 2 - 100, self.height / 2 - 30)
        )
        try_again_btn.bind(on_release=self.reset_level)
        self.add_widget(try_again_btn)

        self.target_hit = True 
