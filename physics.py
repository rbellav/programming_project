import math
GRAVITY = 0.5
def get_initial_velocity(angle, speed):
    angle_rad = math.radians(-angle)
    vx = math.sin(angle_rad) * speed
    vy = math.cos(angle_rad) * speed
    return vx, vy
def reflect_laser(incidence_angle_deg, mirror_angle_deg):    
    incidence = incidence_angle_deg - mirror_angle_deg
    reflection = -incidence
    reflected_angle = mirror_angle_deg + reflection
    return reflected_angle % 360
