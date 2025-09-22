import math
import random
from math import sin, cos, radians
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Rotate, PushMatrix, PopMatrix, Line
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.modalview import ModalView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from physics import get_initial_velocity, GRAVITY
from constants.screen_constants import BULLET_MASS, BULLET_RADIUS, BOMB_MASS, BOMB_RADIUS, BOMB_DRILL, LASER_DIST, LASER_VEL, LASER_IMPULSE
from .hall_of_fame_screen import report_level_win



class Mirror(Image):
    def __init__(self, x, y, angle=45, **kwargs):
        super().__init__(source='images/ostacolo_futurama2.png',
                         size_hint=(None, None),
                         size=(150, 150),
                         pos=(x, y),
                         **kwargs)
        self.angle = angle     
        self.indestructible = True

class Perpetio(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/ostacolo_futurama3.png',
                         size_hint=(None, None),
                         size=(150, 150),
                         pos=(x, y),
                         **kwargs)
        self.indestructible = True

class RockBlock(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/ostacolo_futurama.png',
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

    def generate_blocks(self, count=11, avoid_areas=None):
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

    def _on_resize(self, *args):
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

    def move(self):
        if not self.has_impacted:
            self.x += self.vx
            self.y += self.vy
            self.vy -= GRAVITY
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

    def move(self):
        if not self.has_impacted:
            self.x += self.vx
            self.y += self.vy
            self.vy -= GRAVITY
            if self.y < 0:
                self.y -= self.drill
                self.impact()

    def impact(self):
        self.has_impacted = True

class Laser(Widget):
    angle = NumericProperty(0)
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    damage_radius = NumericProperty(LASER_DIST)
    impulse = NumericProperty(LASER_IMPULSE)
    parent_widget = ObjectProperty(None)

    def __init__(self, x, y, angle, parent_widget=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.laser_length = 250
        self.laser_width = 10
        self.size = (self.laser_length, self.laser_width)
        self.angle = angle
        self.parent_widget = parent_widget
        self.has_impacted = False
        self.speed = LASER_VEL
        self.bounces = 0
        self.max_bounces = 3 

        self.center = (x, y)

        angle_rad = radians(self.angle - 270)  
        self.velocity_x = LASER_VEL * cos(angle_rad)
        self.velocity_y = LASER_VEL * sin(angle_rad)

        self._distance_travelled = 0
        self._max_distance = LASER_DIST

        self.draw_laser()

        self.bind(pos=self.update_graphics, size=self.update_graphics, center=self.update_graphics)
        Clock.schedule_interval(self.move, 1 / 60)

    def draw_laser(self):
            self.canvas.clear()
            angle_rad = radians(self.angle - 270)
            start_x, start_y = self.center
            end_x = start_x + self.laser_length * cos(angle_rad)
            end_y = start_y + self.laser_length * sin(angle_rad)
            with self.canvas:
                Color(50/255, 205/255, 50/255, 1) 
                Line(points=[start_x, start_y, end_x, end_y], width=4)

    def update_graphics(self, *args):
        self.draw_laser()
    
    def set_angle(self, new_angle):
        self.angle = new_angle
        angle_rad = radians(self.angle - 270)
        self.velocity_x = LASER_VEL * cos(angle_rad)
        self.velocity_y = LASER_VEL * sin(angle_rad)
        self.vx = self.velocity_x
        self.vy = self.velocity_y
        self.update_graphics()

    def move(self, dt):
        dx = self.velocity_x * dt
        dy = self.velocity_y * dt
        self.x += dx
        self.y += dy
        self._distance_travelled += math.sqrt(dx**2 + dy**2)
        self.update_graphics()

        if (self.y < 0 or self.x < 0 or self.x > Window.width or 
            self._distance_travelled >= self._max_distance):
            self.impact()

    def impact(self):
        self.has_impacted = True
        if self.parent:
            self.parent.remove_widget(self)

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
            self.tank_body = Rectangle(source='images/tank_futurama.png', pos=(x, y), size=(self.body_width, self.body_height))
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
        super().__init__(size_hint=(1, 1), auto_dismiss=True, background_color=(0,0,0,0), **kwargs)
        self.on_close = on_close

        root = FloatLayout()

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

        # bottone Close
        close_btn = Button(text='Close', size_hint=(None, None), size=(140, 48),
                           pos_hint={'center_x': 0.5, 'y': 0.05})
        close_btn.bind(on_release=lambda *_: self.dismiss())
        root.add_widget(close_btn)

        self.add_widget(root)

    def on_dismiss(self):
        if callable(self.on_close):
            self.on_close()

class Level2Screen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_ammo = "bullet"
        self.level_completed = False
        self.perpetios = []
        self.projectiles = []
        self.mirrors = []
        self.target_hit = False
        self.max_shots = 7
        self.remaining_shots = self.max_shots

        self.music = SoundLoader.load('sounds/futurama_sound.ogg') 
        self.sfx_win = SoundLoader.load('sounds/winner.mp3')
        self.sfx_lose = SoundLoader.load('sounds/game over.mp3')
        if self.sfx_win:
            self.sfx_win.loop = False
        if self.sfx_lose:
            self.sfx_lose.loop = False

        self.sfx_shoot_bullet = SoundLoader.load('sounds/shot.mp3')
        self.sfx_shoot_bomb   = SoundLoader.load('sounds/bomb.mp3')
        self.sfx_shoot_laser  = SoundLoader.load('sounds/laser.mp3')
        for s in (self.sfx_shoot_bullet, self.sfx_shoot_bomb, self.sfx_shoot_laser):
            if s: s.loop = False

        self.__init_layout()
        self._upd_ev = None

    def _play_once(self, snd):
        if snd:
            try:
                snd.stop()     
            except:
                pass
            snd.loop = False
            snd.play()

    def __init_layout(self):    
        self.background = Image(source='images/bg_futurama.jpg', allow_stretch=True, keep_ratio=False,
                                size=self.size, pos=self.pos)
        self.bind(size=self._resize_background, pos=self._resize_background)
        self.add_widget(self.background)

        self.rock_field = RockField()
        self.add_widget(self.rock_field)

        self.target = Image(source='images/target_futurama.png', size_hint=(None, None), size=(300, 300))
        self.add_widget(self.target)

        self.tank = Tank()
        self.add_widget(self.tank)

        
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

        self.help_btn = Button(text='Help', size_hint=(None, None), 
                               size=(120, 40), font_name="Press2P", 
                               font_size=18, color=(1,1,1,1))
        self.help_btn.bind(on_release=self.open_help)
        self.hud.add_widget(self.help_btn)

        self.bind(size=self._resize_elements)
    
    def open_help(self, *_):
        if hasattr(self, 'stop_loop'):
            self.stop_loop()

        overlay = HelpOverlay(
            image_source='images/help_lev2.png', 
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
        self.target.pos = (self.width - self.target.width - 50, 500)

    def on_pre_enter(self):
        for attr in ['winner_label', 'next_lev_btn', 'explosion']:
            if hasattr(self, attr) and getattr(self, attr).parent:
                self.remove_widget(getattr(self, attr))

        self.target_hit = False
        self._resize_elements()
        self.remaining_shots = self.max_shots

        for p in self.projectiles:
            if p.parent:
                self.remove_widget(p)
        self.projectiles.clear()
       
        for widget in self.perpetios + self.mirrors:
            if widget.parent:
                self.remove_widget(widget)
        self.perpetios.clear()
        self.mirrors.clear()
       
    def on_enter(self):
        level_select = self.manager.get_screen('level_select')
        if level_select.levels_completed.get(2, False):
            self.level_completed = True
            self.target_hit = True
            
            self.explosion = Image(
                source='images/explosion.png',
                size=self.target.size,
                pos=self.target.pos,
                size_hint=(None, None)
            )
            self.add_widget(self.explosion)

            self.winner_label = Label(
                text='WINNER!',
                font_size=130,
                font_name='fonts/PressStart2P-Regular.ttf',
                color=(245/255, 130/255, 21/255, 1),
                pos=(self.width / 2, self.height / 2 + 50),
                size_hint=(None, None)
            )
            self.add_widget(self.winner_label)

            self.next_lev_btn = Button(
                text='Next Level',
                font_size=16,
                font_name='Press2P',
                size_hint=(None, None),
                size=(200, 50),
                pos=(self.width / 2 - 100, self.height / 2 - 30)
            )
            self.next_lev_btn.bind(on_release=self.go_to_level_select)
            self.add_widget(self.next_lev_btn)

            if self.music:
                self.music.loop = True
                self.music.play()
            return
            
        tank_area = (self.tank.x, self.tank.y, self.tank.body_width, self.tank.body_height)
        target_area = (self.target.x, self.target.y, self.target.width, self.target.height)
        self.rock_field.generate_blocks(avoid_areas=[tank_area, target_area])
        
        def intersects(a, b):
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            return (ax < bx + bw and ax + aw > bx and
                    ay < by + bh and ay + ah > by)
        
        placed_areas = [tank_area, target_area] + [
            (b.x, b.y, b.width, b.height) for b in self.rock_field.blocks
        ]
   
        for _ in range(3):
            for _ in range(100): 
                x = random.randint(0, self.width - 180)
                y = random.randint(150, self.height - 180)
                new_area = (x, y, 150, 150)
                if not any(intersects(new_area, area) for area in placed_areas):
                    perp = Perpetio(x, y)
                    self.perpetios.append(perp)
                    self.add_widget(perp)
                    placed_areas.append(new_area)
                    break

        for _ in range(2):
            for _ in range(100): 
                x = random.randint(0, self.width - 150)
                y = random.randint(150, self.height - 150)
                new_area = (x, y, 150, 150)
                if not any(intersects(new_area, area) for area in placed_areas):
                    angle = random.choice([45, 135, 315])
                    mirror = Mirror(x, y, angle=angle)
                    self.mirrors.append(mirror)
                    self.add_widget(mirror)
                    placed_areas.append(new_area)
                    break
        if not self._upd_ev:
            self._upd_ev = Clock.schedule_interval(self.update, 1.0 / 60.0)
        Window.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)                
        if self.music:
            self.music.stop()
            self.music.loop = True
            self.music.play()
            
    def on_leave(self, *args):
        try:
            Window.unbind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        except Exception:
            pass
        if self._upd_ev:
            self._upd_ev.cancel()
            self._upd_ev = None
        if self.music:
            self.music.stop()

    def _update_hud_bg(self, *args):
        self.hud_bg.pos = self.hud.pos
        self.hud_bg.size = self.hud.size

    def check_collision(self, projectile, target):
        px, py = projectile.center
        tx, ty = target.center
        tw, th = target.size
        return (tx - tw / 2 < px < tx + tw / 2) and (ty - th / 2 < py < ty + th / 2)

    def fire_projectile(self):
            if self.remaining_shots <= 0 or self.target_hit:
                return
            tank = self.tank
            center_x = tank.x + tank.body_width / 2
            center_y = tank.y + tank.body_height * 0.7
            angle_rad = math.radians(-tank.angle )
            offset_x = math.sin(angle_rad) * tank.barrel_height
            offset_y = math.cos(angle_rad) * tank.barrel_height
            px = center_x + offset_x - 15
            py = center_y + offset_y - 15
            speed = tank.projectile_speed
            tip_x = center_x + offset_x
            tip_y = center_y + offset_y

            if self.current_ammo == "bullet":
                p = Bullet(x=px, y=py, angle=tank.angle, speed=speed)
            elif self.current_ammo == "bomb":
                p = Bomb(x=px, y=py, angle=tank.angle, speed=speed)
            elif self.current_ammo == "laser":
                dx = math.cos(math.radians(tank.angle - 270)) * 2
                dy = math.sin(math.radians(tank.angle - 270)) * 2
                p = Laser(x=tip_x + dx, y=tip_y + dy, angle=tank.angle, parent_widget=self)
            else:
                p = Bullet(x=tip_x - 15, y=tip_y - 15, angle=tank.angle, speed=speed)
            
            if self.current_ammo == "bullet":
                if self.sfx_shoot_bullet: self._play_once(self.sfx_shoot_bullet)
            elif self.current_ammo == "bomb":
                if self.sfx_shoot_bomb:   self._play_once(self.sfx_shoot_bomb)
            elif self.current_ammo == "laser":
                if self.sfx_shoot_laser:  self._play_once(self.sfx_shoot_laser)
            
            self.projectiles.append(p)
            self.add_widget(p)
            self.remaining_shots -= 1

    def toggle_ammo(self):
        ammo_types = ["bullet", "bomb", "laser"]
        current_index = ammo_types.index(self.current_ammo)
        self.current_ammo = ammo_types[(current_index + 1) % len(ammo_types)]
    
    def update(self, dt):
        to_remove = []
        for p in self.projectiles:
            if not isinstance(p, Laser):
                p.move()

            if self.rock_field.check_collision(p):
                self.remove_widget(p)
                to_remove.append(p)
                continue

            if self.check_collision(p, self.target):
                self.explode_target()
                self.remove_widget(p)
                to_remove.append(p)
                break

            for perp in self.perpetios:
                if hasattr(perp, 'collide_point') and perp.collide_point(*p.center):
                    self.remove_widget(p)
                    to_remove.append(p)
                    continue


            if isinstance(p, Laser):
                Ls, Le = self._laser_segment(p)
                hit = False
                for mirror in self.mirrors:
                    Ms, Me = self._mirror_segment(mirror)
                    if self._segment_intersect(Ls, Le, Ms, Me):
                        new_angle = self._reflect_laser_angle_random(p.angle, mirror.angle, jitter_deg=10)
                        p.angle = new_angle
                        ang_rad = math.radians(p.angle - 270)
                        p.velocity_x = LASER_VEL * math.cos(ang_rad)
                        p.velocity_y = LASER_VEL * math.sin(ang_rad)
                       
                        if hasattr(p, "draw_laser"):
                            p.draw_laser()
                        hit = True
                        break
                if hit:
                    p._max_distance *= 0.9

            if getattr(p, 'has_impacted', False):
                self.remove_widget(p)
                to_remove.append(p)

        for p in to_remove:
            if p in self.projectiles:
                self.projectiles.remove(p)

        angle = int(self.tank.angle - 270)
        speed = int(self.tank.projectile_speed)
        ammo = self.current_ammo.upper()
        self.info_label.text = f"Angle: {angle}°   Power: {speed},   Ammo: {ammo},   Shots: {self.remaining_shots}"
        if self.remaining_shots <= 0 and not self.target_hit and not self.projectiles:
            self.show_loss()

    def _segment_intersect(self, p1, p2, p3, p4):
        def orient(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        def on_seg(a, b, c):
            return (min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and
                    min(a[1], b[1]) <= c[1] <= max(a[1], b[1]))
        o1 = orient(p1, p2, p3)
        o2 = orient(p1, p2, p4)
        o3 = orient(p3, p4, p1)     
        o4 = orient(p3, p4, p2)

        if o1 == 0 and on_seg(p1, p2, p3): return True
        if o2 == 0 and on_seg(p1, p2, p4): return True
        if o3 == 0 and on_seg(p3, p4, p1): return True
        if o4 == 0 and on_seg(p3, p4, p2): return True
        return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)
    
    def _laser_segment(self, laser):
        ang = math.radians(laser.angle - 270)  
        start = laser.center
        end = (
            start[0] + laser.laser_length * math.cos(ang),
            start[1] + laser.laser_length * math.sin(ang)
        )
        return start, end

    def _mirror_segment(self, mirror):
        mx, my = mirror.center
        ang = math.radians(mirror.angle - 270)
        half = mirror.width / 2
        dx = half * math.cos(ang)
        dy = half * math.sin(ang)
        p1 = (mx - dx, my - dy)
        p2 = (mx + dx, my + dy)
        return p1, p2
    
    def _reflect_laser_angle_random(self, laser_angle_deg, mirror_angle_deg, jitter_deg=20):
        li = (laser_angle_deg - 270) % 360
        mi = (mirror_angle_deg - 270) % 360
        
        lr = (2 * mi - li) % 360
        
        jitter = random.uniform(-jitter_deg, jitter_deg)
        lr = (lr + jitter) % 360

        return (lr + 270) % 360

    def explode_target(self):
        if self.level_completed:
            return
        self.level_completed = True
        self.target_hit = True
        self.manager.get_screen('level_select').levels_completed[2] = True

        self.explosion = Image(source='images/explosion.png', size=self.target.size, pos=self.target.pos, size_hint=(None, None))
        self.add_widget(self.explosion)

        self.winner_label = Label(text='WINNER!', font_size=130, font_name='fonts/PressStart2P-Regular.ttf', 
                             color=(245/255, 130/255, 21/255, 1), pos=(self.width / 2, self.height / 2 + 50), 
                             size_hint=(None, None))
        self.add_widget(self.winner_label)

        self.next_lev_btn = Button(
            text='Next Level',
            font_size=16,
            font_name='Press2P',
            size_hint=(None, None),
            size=(200, 50),
            pos=(self.width / 2 - 100, self.height / 2 - 30)
        )
        
        self.next_lev_btn.bind(on_release=self.go_to_level_select)
        self.add_widget(self.next_lev_btn)

        self.target_hit = True 
        if self.music:
            self.music.stop()
        self._play_once(self.sfx_win)
        report_level_win(self, "2")

    def go_to_level_select(self, *args):
        level_select_screen = self.manager.get_screen('level_select')
        level_select_screen.unlock_level3()
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

    def reset_level(self, *args):
        if self.music:
            self.music.stop()

        self.clear_widgets()
        self.__init_layout()

        from kivy.clock import Clock
        def _after(dt):
            self.on_pre_enter()      
            self._resize_elements()
            self.on_enter()          

            angle = int(self.tank.angle - 270)
            power = int(self.tank.projectile_speed)
            ammo = self.current_ammo.upper()
            self.info_label.text = f"Angle: {angle}°   Power: {power},   Ammo: {ammo},   Shots: {self.remaining_shots}"

        Clock.schedule_once(_after, 0)

        if self.music:
            self.music.loop = True
            self.music.play()

    
    def show_loss(self):
        lose_label = Label(
            text='GAME OVER!',
            font_size=130,
            font_name='fonts/PressStart2P-Regular.ttf',
            color=(0, 1, 0, 1), 
            pos=(self.width / 2, self.height / 2 + 50),
            size_hint=(None, None)
        )
        self.add_widget(lose_label)
        if self.music:
            self.music.stop()
        self._play_once(self.sfx_lose)

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
