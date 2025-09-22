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



HOF_SCREEN_NAME = 'halloffame'

def go_to_hall_of_fame_screen(self, *args):
    sm = self.manager
    if sm and sm.has_screen(HOF_SCREEN_NAME):
        sm.current = HOF_SCREEN_NAME
    else:
        from kivy.uix.screenmanager import ScreenManagerException
        raise ScreenManagerException(
            f"Screen '{HOF_SCREEN_NAME}' non registrata. Presenti: {[s.name for s in sm.screens]}"
        )

class WormholePortal(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/wormhole.png',
                         size_hint=(None, None),
                         size=(120, 120),
                         pos=(x, y),
                         **kwargs)
        self.indestructible = True  

class Wormhole(Widget):
    def __init__(self, ax, ay, bx, by, **kwargs):
        super().__init__(**kwargs)
        self.portal_a = WormholePortal(ax, ay)
        self.portal_b = WormholePortal(bx, by)
        self.add_widget(self.portal_a)
        self.add_widget(self.portal_b)
        # security nudge to avoid immediate re-entry
        self.nudge = 25
    
    def _teleport(self, projectile, src_portal, dst_portal):
        setattr(projectile, "_wormhole_cd", 6) 

        # direction of travel of the projectile
        if hasattr(projectile, "vx") and hasattr(projectile, "vy"):
            dirx, diry = projectile.vx, projectile.vy
        elif hasattr(projectile, "velocity_x") and hasattr(projectile, "velocity_y"):
            dirx, diry = projectile.velocity_x, projectile.velocity_y
        else:
            dirx, diry = 1, 0

        mag = math.hypot(dirx, diry) or 1.0
        nx, ny = dirx / mag, diry / mag

        new_cx = dst_portal.center_x + nx * self.nudge
        new_cy = dst_portal.center_y + ny * self.nudge

        if hasattr(projectile, "center"):
            projectile.center = (new_cx, new_cy)
        else:
            projectile.pos = (new_cx - projectile.width/2, new_cy - projectile.height/2)

        if hasattr(projectile, "draw_laser"):
            projectile.draw_laser()

    def try_teleport(self, projectile):
        cd = getattr(projectile, "_wormhole_cd", 0)
        if cd > 0:
            setattr(projectile, "_wormhole_cd", cd - 1)
            return False
        
        px, py = projectile.center
        if self.portal_a.collide_point(px, py):
            self._teleport(projectile, self.portal_a, self.portal_b)
            return True
        if self.portal_b.collide_point(px, py):
            self._teleport(projectile, self.portal_b, self.portal_a)
            return True
        return False

class Mirror(Image):
    def __init__(self, x, y, angle=45, **kwargs):
        super().__init__(source='images/ostacolo_spongebob.png',
                         size_hint=(None, None),
                         size=(150, 150),
                         pos=(x, y),
                         **kwargs)
        self.angle = angle     #angle of the mirror in degrees
        self.indestructible = True

class Perpetio(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/ostacolo_spongebob3.png',
                         size_hint=(None, None),
                         size=(150, 150),
                         pos=(x, y),
                         **kwargs)
        self.indestructible = True

class MovingPerpetio(Perpetio):
    def __init__(self, x, y, amp=100, freq=0.5, phase=0.0, **kwargs):
        super().__init__(x, y, **kwargs)
        self.base_y = float(y)
        self.amp = float(amp)
        self.freq = float(freq)
        self.phase = float(phase)
        self._t = 0.0
        
        ground_limit = 150
        top_limit = Window.height - self.height
        max_amp_down = max(0, self.base_y - ground_limit)
        max_amp_up   = max(0, top_limit - self.base_y)
        self.amp = max(0.0, min(self.amp, max_amp_down, max_amp_up))

    def step(self, dt):
        self._t += dt
        self.y = self.base_y + self.amp * math.sin(2*math.pi*self.freq*self._t + self.phase)


class RockBlock(Image):
    def __init__(self, x, y, **kwargs):
        super().__init__(source='images/ostacolo_spongebob2.png',
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
        self._last_avoid = []
        self._last_count = 10
        Window.bind(on_resize=self._on_resize)

    def generate_blocks(self, count=10, avoid_areas=None, margin=12):
        if avoid_areas is not None:
            self._last_avoid = list(avoid_areas) 
        self._last_count = count
        
        self.clear_widgets()
        self.blocks.clear()

        screen_width, screen_height = Window.size
        block_size = (150, 150)
        max_attempts = 100
        ground_limit = 150

        base_avoid = list(avoid_areas) if avoid_areas is not None else list(self._last_avoid)
        avoid = base_avoid + [(0, 0, screen_width, ground_limit)]

        attempts = 0
        while len(self.blocks) < count and attempts < max_attempts:
            attempts += 1
            x = random.randint(0, screen_width - block_size[0])
            y = random.randint(ground_limit, screen_height - block_size[1])
            new_area = (x, y, block_size[0], block_size[1])

            if any(self._intersects(new_area, (b.x, b.y, b.width, b.height)) for b in self.blocks):
                continue
            # avoid areas
            if any(self._intersects(new_area, area) for area in avoid):
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
        self.generate_blocks(count=self._last_count, avoid_areas=self._last_avoid)

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

        angle_rad = radians(self.angle - 270)  # convert angle to radians and adjust for Kivy's coordinate system
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
            self.tank_body = Rectangle(source='images/tank_spongebob.png', pos=(x, y), size=(self.body_width, self.body_height))
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

        # close button
        close_btn = Button(text='Close', size_hint=(None, None), size=(140, 48),
                           pos_hint={'center_x': 0.5, 'y': 0.05})
        close_btn.bind(on_release=lambda *_: self.dismiss())
        root.add_widget(close_btn)

        self.add_widget(root)

    def on_dismiss(self):
        if callable(self.on_close):
            self.on_close()

class Level3Screen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_ammo = "bullet"
        self.perpetios = []
        self.wormholes = []
        self.projectiles = []
        self.mirrors = []
        self.target_hit = False
        self.max_shots = 7
        self.remaining_shots = self.max_shots

        self.music = SoundLoader.load('sounds/spongebob_sound.ogg') 
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
       
        self._upd_ev = None  # handle of loop

    def _play_once(self, snd):
        if snd:
            try:
                snd.stop()     
            except:
                pass
            snd.loop = False
            snd.play()

    def start_loop(self):
        if not self._upd_ev:
            self._upd_ev = Clock.schedule_interval(self.update, 1/60)

    def stop_loop(self):
        if self._upd_ev:
            self._upd_ev.cancel()
            self._upd_ev = None
        
    def __init_layout(self):    
        self.background = Image(source='images/bg_spongebob.jpg', allow_stretch=True, keep_ratio=False,
                                size=self.size, pos=self.pos)
        self.bind(size=self._resize_background, pos=self._resize_background)
        self.add_widget(self.background)

        self.rock_field = RockField()
        self.add_widget(self.rock_field)

        self.target = Image(source='images/target_spongebob.png', size_hint=(None, None), size=(170, 170))
        self.add_widget(self.target)

        self.tank = Tank()
        self.add_widget(self.tank)

        
        self.hud = BoxLayout(orientation='horizontal', size_hint=(1, None), height=70, padding=[20, 20], spacing=30)
        with self.hud.canvas.before:
            Color(0, 0, 0, 0.6)
            self.hud_bg = Rectangle(pos=self.hud.pos, size=self.hud.size)
        self.hud.bind(pos=self._update_hud_bg, size=self._update_hud_bg)

        self.info_label = Label(text='Angle: 90°   Power: 15   Ammo: BULLET', 
                                font_size=20, 
                                font_name="Press2P",
                                color=(1, 1, 1, 1), size_hint=(1, 1))
        self.hud.add_widget(self.info_label)
        self.add_widget(self.hud)

         # pulsante Help nell'HUD
        self.help_btn = Button(text='Help', size_hint=(None, None), 
                               size=(120, 40), font_name="Press2P", 
                               font_size=18, color=(1,1,1,1))
        self.help_btn.bind(on_release=self.open_help)
        self.hud.add_widget(self.help_btn)

        self.bind(size=self._resize_elements)
    
    def open_help(self, *_):
        self.stop_loop()  
        overlay = HelpOverlay(image_source='images/help_lev3.png', on_close=self._resume_after_help)
        overlay.open()       

    def _resume_after_help(self):
        self.start_loop()   

    def _resize_background(self, *args):
        self.background.size = self.size
        self.background.pos = self.pos

    def _resize_elements(self, *args):
        self.hud.size = (self.width, 70)
        self.target.pos = (self.width - self.target.width - 50, 360)

    def on_pre_enter(self):
        for attr in ['winner_label', 'hof_btn', 'explosion', 'lose_label', 'try_again_btn']:
            if hasattr(self, attr) and getattr(self, attr).parent:
                self.remove_widget(getattr(self, attr))

        self.target_hit = False
        self._resize_elements()
        self.remaining_shots = self.max_shots

        # Reset of ammunitions
        for p in self.projectiles:
            if p.parent:
                self.remove_widget(p)
        self.projectiles.clear()

        for w in self.wormholes:
            if w.parent:
                self.remove_widget(w)
        self.wormholes.clear()
       
        for widget in self.perpetios + self.mirrors:
            if widget.parent:
                self.remove_widget(widget)
        self.perpetios.clear()
        self.mirrors.clear()
        if self.sfx_win:  self.sfx_win.stop()
        if self.sfx_lose: self.sfx_lose.stop()

    def on_enter(self):
        self._resize_elements()
        tank_area = (self.tank.x, self.tank.y, self.tank.body_width, self.tank.body_height)
        target_area = (self.target.x, self.target.y, self.target.width, self.target.height)
        placed_areas = [tank_area, target_area]

        def motion_envelope(widget):
            # if it has an 'amp' attribute, use it
            amp = getattr(widget, 'amp', 0)
            return (widget.x,
                    widget.y if not amp else widget.base_y - amp,
                    widget.width,
                    widget.height + (2*amp if amp else 0))

        for p in self.perpetios:
            env = motion_envelope(p)
            placed_areas.append(env)
        
                
        perp_w = perp_h = 150
        gap_side = 40          # lateral distance between the two left perpetios
        gap_bottom = 30        # vertical distance between the bottom perpetio and the target
        ground_limit = 150     

        
        left_x = self.target.x - (perp_w + gap_side)
        mid_y  = self.target.y + self.target.height/2 - perp_h/2
        perp1_y = mid_y + 60
        perp2_y = mid_y - 60

        perp1 = MovingPerpetio(left_x, perp1_y, amp=80, freq=0.45, phase=0.0)
        perp2 = MovingPerpetio(left_x - (perp_w + 30), perp2_y, amp=80, freq=0.55, phase=math.pi) 

        
        third_x = self.target.center_x - perp_w/2
        third_y_desired = self.target.y - (perp_h + gap_bottom)
        third_y = max(ground_limit, third_y_desired)        
        perp3 = MovingPerpetio(third_x, third_y, amp=50, freq=0.6, phase=math.pi/2)

        
        self.perpetios = [perp1, perp2, perp3]
        for p in self.perpetios:
            self.add_widget(p)

        def motion_envelope(p):
            amp = getattr(p, 'amp', 0)
            base_y = getattr(p, 'base_y', p.y)  
            return (p.x, base_y - amp, p.width, p.height + 2*amp)
        placed_areas.extend([motion_envelope(p) for p in self.perpetios])

        self.rock_field.generate_blocks(count=10, avoid_areas=placed_areas)
        
        
        placed_areas.extend([(b.x, b.y, b.width, b.height) for b in self.rock_field.blocks])

        def intersects(a, b):
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            return (ax < bx + bw and ax + aw > bx and
                    ay < by + bh and ay + ah > by)
        
        portal_w = portal_h = 120
        ground_limit = 150

        exit_x = int(self.target.x - portal_w - 30)   # 30px left of the target
        exit_y = int(self.target.top + 80)            # 80px over the target
        exit_x = max(0, min(self.width - portal_w, exit_x))
        exit_y = max(ground_limit, min(self.height - portal_h, exit_y))

        exit_area = (exit_x, exit_y, portal_w, portal_h)
        placed_areas.append(exit_area) 

        for _ in range(200):  
            entry_x = random.randint(0, self.width - portal_w)
            entry_y = random.randint(ground_limit, self.height - portal_h)
            entry_area = (entry_x, entry_y, portal_w, portal_h)
            if any(intersects(entry_area, area) for area in placed_areas):
                continue
            if math.hypot(entry_x - exit_x, entry_y - exit_y) < 350:
                continue
         
            worm = Wormhole(entry_x, entry_y, exit_x, exit_y)  
            self.wormholes.append(worm)
            self.add_widget(worm)
            placed_areas.extend([entry_area, exit_area])
            break         

        for _ in range(3):
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
        if self.music:
            self.music.stop()
            self.music.loop = True
            self.music.play()
        
        Window.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        self.start_loop()


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
                return

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
        for perp in self.perpetios:
            if not hasattr(perp, "_osc"):
                perp._osc = {
                    "t": 0.0,
                    "freq":  random.uniform(0.45, 0.70),    
                    "amp":   random.uniform(18, 36),         
                    "phase": random.uniform(0, 2*math.pi),
                    "base_y": float(perp.y)
                }
            o = perp._osc
            o["t"] += dt
            new_y = o["base_y"] + o["amp"] * math.sin(2*math.pi*o["freq"]*o["t"] + o["phase"])
            ground_limit = 150
            top_limit = Window.height - perp.height
            perp.y = max(ground_limit, min(top_limit, new_y))
        to_remove = []
        for p in self.projectiles:
            if not isinstance(p, Laser):
                p.move()

            # Wormhole 
            for wh in self.wormholes:
                if wh.try_teleport(p):
                    break  

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
                    break
            if p in to_remove:
                continue

            if isinstance(p, Laser):
                Ls, Le = self._laser_segment(p)
                hit = False
                for mirror in self.mirrors:
                    Ms, Me = self._mirror_segment(mirror)
                    if self._segment_intersect(Ls, Le, Ms, Me):
                        # new angle with jitter
                        new_angle = self._reflect_laser_angle_random(p.angle, mirror.angle, jitter_deg=10)
                        p.angle = new_angle
                    
                        ang_rad = math.radians(p.angle - 270)
                        p.velocity_x = LASER_VEL * math.cos(ang_rad)
                        p.velocity_y = LASER_VEL * math.sin(ang_rad)
                        # redraw laser
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
        # random jitter 
        jitter = random.uniform(-jitter_deg, jitter_deg)
        lr = (lr + jitter) % 360 
        return (lr + 270) % 360

    def explode_target(self):
        self.explosion = Image(source='images/explosion.png', size=self.target.size, pos=self.target.pos, size_hint=(None, None))
        self.add_widget(self.explosion)

        self.winner_label = Label(text='WINNER!', font_size=130, font_name='fonts/PressStart2P-Regular.ttf', 
                             color=(1.000, 0.831, 0.000, 1), pos=(self.width / 2, self.height / 2 + 50), 
                             size_hint=(None, None))
        self.add_widget(self.winner_label)

        self.hof_btn = Button(
            text='Hall of Fame',
            font_size=16,
            font_name='Press2P',
            size_hint=(None, None),
            size=(200, 50),
            pos=(self.width / 2 - 100, self.height / 2 - 30)
        )
        
        self.hof_btn.bind(on_release=self.go_to_hall_of_fame_screen)
        self.add_widget(self.hof_btn)

        self.target_hit = True  
        if self.music:
            self.music.stop()
        self._play_once(self.sfx_win)
        report_level_win(self, "3")


    def go_to_hall_of_fame_screen(self, *args):
       
        self.manager.current = 'halloffame'

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
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
        if self.sfx_win:  self.sfx_win.stop()
        if self.sfx_lose: self.sfx_lose.stop()

        self.stop_loop()
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
            color=(0.490, 0.235, 1.000, 1), 
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
            size_hint=(None, None),
            font_name='Press2P',
            size=(200, 50),
            pos=(self.width / 2 - 100, self.height / 2 - 30)
        )
        try_again_btn.bind(on_release=self.reset_level)
        self.add_widget(try_again_btn)

        self.target_hit = True  

