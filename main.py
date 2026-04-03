import pygame
import sys
import os
import random
import pickle

# --- 1. INITIAL SETUP ---
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF)
except:
    screen = pygame.display.set_mode((1280, 720), pygame.DOUBLEBUF)
    WIDTH, HEIGHT = 1280, 720

clock = pygame.time.Clock()
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
WORLD_WIDTH = WIDTH * 1.5 

def load_pixel_img(name, w, h):
    try:
        path = os.path.join(BASE_PATH, name)
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (w, h)), True
    except:
        fallback = pygame.Surface((w, h))
        fallback.fill((255, 0, 255)) 
        return fallback, False

# --- 2. SAVE & UPGRADE SYSTEM ---
DATA_FILE = os.path.join(BASE_PATH, "save.data")
DEFAULT_DATA = {"high_score": 0, "total_coins": 0, "up_fire_rate": 0, "up_damage": 0, "up_speed": 0}

def load_game_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                data = pickle.load(f)
                for key in DEFAULT_DATA:
                    if key not in data: data[key] = DEFAULT_DATA[key]
                return data
        except: return DEFAULT_DATA.copy()
    return DEFAULT_DATA.copy()

def save_game_data(data):
    try:
        with open(DATA_FILE, 'wb') as f: pickle.dump(data, f)
    except: pass

game_data = load_game_data()

def get_upgrade_cost(level):
    costs = [20, 80, 250, 600, 1000]
    return costs[level] if level < len(costs) else None

# --- 3. LOAD ASSETS ---
char_h = int(HEIGHT * 0.16); char_w = int(char_h * 0.8)
player_R_img, _ = load_pixel_img("player.png", char_w, char_h)
player_L_img, _ = load_pixel_img("player2.png", char_w, char_h)
zombie_img, has_zL = load_pixel_img("zombie.png", char_w, char_h)  
sniper_img, has_zR = load_pixel_img("zombie2.png", char_w, char_h) 
bullet_img, has_b = load_pixel_img("bullet.png", int(char_w*0.5), int(char_h*0.15))
coin_size = int(char_h * 0.35); coin_img, has_coin = load_pixel_img("coin.png", coin_size, coin_size)
GROUND_Y = int(HEIGHT * 0.82)

# Portal config
portal_w = int(char_w * 2.5); portal_h = int(char_h * 1.5)
portal_rect = pygame.Rect(WORLD_WIDTH // 2 - portal_w // 2, GROUND_Y - portal_h, portal_w, portal_h)
portal_img, has_portal = load_pixel_img("portal.png", portal_w, portal_h)

font_title = pygame.font.SysFont("Arial", int(HEIGHT*0.1), bold=True)
font_menu = pygame.font.SysFont("Arial", int(HEIGHT*0.05), bold=True)
font_ui = pygame.font.SysFont("Arial", int(HEIGHT*0.03), bold=True)
font_win = pygame.font.SysFont("Arial", int(HEIGHT*0.2), bold=True)

# --- 4. GAME VARIABLES ---
game_state = "START"
player_x, player_y = WIDTH // 4, GROUND_Y - char_h
player_vy = 0; is_jumping = False; player_dir = 1 
player_health = 100.0; score = 0; current_coins = 0; camera_x = 0
shoot_timer = 0; win_timer = 0 # مضاف لحساب وقت الفوز
zombies = []; bullets = []; coins = []; snipers = []; sniper_bullets = []

def spawn_sniper():
    sx = random.randint(int(WIDTH), int(WORLD_WIDTH - 100))
    snipers.append({"rect": pygame.Rect(sx, GROUND_Y - char_h, char_w, char_h), "shoot_timer": 100, "health": 2})

def reset_game():
    global player_x, player_y, player_vy, is_jumping, player_health, score, current_coins, camera_x, shoot_timer, win_timer
    player_x, player_y = WIDTH // 4, GROUND_Y - char_h
    player_vy = 0; is_jumping = False; player_health = 100.0; score = 0; current_coins = 0; camera_x = 0; shoot_timer = 0; win_timer = 0
    bullets.clear(); zombies.clear(); coins.clear(); snipers.clear(); sniper_bullets.clear()
    for i in range(5):
        z_rect = pygame.Rect(random.randint(WIDTH, int(WORLD_WIDTH)), GROUND_Y - char_h, char_w, char_h)
        zombies.append({"rect": z_rect, "speed": random.randint(3, 5)})
    for i in range(2): spawn_sniper()
    for i in range(6):
        cx = random.randint(100, int(WORLD_WIDTH))
        coins.append(pygame.Rect(cx, GROUND_Y - coin_size - 10, coin_size, coin_size))

play_btn = pygame.Rect(WIDTH//2 - 150, HEIGHT//2, 300, 80)
up_btn = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 100, 300, 80)
back_btn = pygame.Rect(50, 50, 150, 60)
u_fire_rect = pygame.Rect(WIDTH//2 - 200, 300, 400, 70)
u_dmg_rect = pygame.Rect(WIDTH//2 - 200, 400, 400, 70)
u_speed_rect = pygame.Rect(WIDTH//2 - 200, 500, 400, 70)
left_btn = pygame.Rect(30, HEIGHT-180, 150, 150); right_btn = pygame.Rect(200, HEIGHT-180, 150, 150)
jump_btn = pygame.Rect(WIDTH-380, HEIGHT-180, 150, 150); shoot_btn = pygame.Rect(WIDTH-180, HEIGHT-180, 150, 150)
click_cooldown = 0

# --- 5. MAIN LOOP ---
while True:
    screen.fill((15, 15, 25))
    m_pos = pygame.mouse.get_pos(); m_down = pygame.mouse.get_pressed()[0]
    if click_cooldown > 0: click_cooldown -= 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()

    if game_state == "START":
        title = font_title.render("DEAD HORIZON", True, (255, 0, 0))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        coin_txt = font_ui.render(f"Total Coins: {game_data['total_coins']}", True, (255, 215, 0))
        screen.blit(coin_txt, (WIDTH//2 - coin_txt.get_width()//2, 260))
        pygame.draw.rect(screen, (0, 120, 0), play_btn, 0, 10); pygame.draw.rect(screen, (100, 100, 100), up_btn, 0, 10)
        t1 = font_menu.render("PLAY", True, (255, 255, 255)); t2 = font_menu.render("UPGRADES", True, (255, 255, 255))
        screen.blit(t1, (play_btn.centerx - t1.get_width()//2, play_btn.centery - t1.get_height()//2))
        screen.blit(t2, (up_btn.centerx - t2.get_width()//2, up_btn.centery - t2.get_height()//2))
        if m_down and click_cooldown == 0:
            if play_btn.collidepoint(m_pos): reset_game(); game_state = "PLAYING"; click_cooldown = 20
            if up_btn.collidepoint(m_pos): game_state = "UPGRADES"; click_cooldown = 20

    elif game_state == "PLAYING":
        move_speed = 12 + (game_data['up_speed'] * 1.5); fire_delay = 25 - (game_data['up_fire_rate'] * 3)
        if m_down:
            if left_btn.collidepoint(m_pos): player_x -= move_speed; player_dir = -1
            if right_btn.collidepoint(m_pos): player_x += move_speed; player_dir = 1
            if jump_btn.collidepoint(m_pos) and not is_jumping: player_vy = -34; is_jumping = True
            if shoot_btn.collidepoint(m_pos) and shoot_timer <= 0:
                bullets.append({"rect": pygame.Rect(player_x, player_y + char_h//2, 30, 10), "dir": player_dir}); shoot_timer = fire_delay
        
        player_x = max(0, min(player_x, WORLD_WIDTH - char_w)); player_vy += 1.9; player_y += player_vy
        if player_y + char_h > GROUND_Y: player_y = GROUND_Y - char_h; player_vy = 0; is_jumping = False
        if shoot_timer > 0: shoot_timer -= 1
        camera_x = max(0, min(player_x - WIDTH // 3, WORLD_WIDTH - WIDTH))
        pygame.draw.rect(screen, (255, 255, 255), (0 - camera_x, GROUND_Y, WORLD_WIDTH, 5))

        # --- Portal Logic ---
        if score >= 1000:
            if has_portal: screen.blit(portal_img, (portal_rect.x - camera_x, portal_rect.y))
            else: pygame.draw.rect(screen, (255, 0, 255), (portal_rect.x - camera_x, portal_rect.y, portal_rect.w, portal_rect.h), 5)
            
            if player_x > portal_rect.centerx + 50:
                hint = font_menu.render("<--- GO LEFT", True, (255, 255, 0))
                screen.blit(hint, (WIDTH//2 - hint.get_width()//2, 100))
            elif player_x < portal_rect.centerx - 50:
                hint = font_menu.render("GO RIGHT --->", True, (255, 255, 0))
                screen.blit(hint, (WIDTH//2 - hint.get_width()//2, 100))
            
            if portal_rect.colliderect(pygame.Rect(player_x, player_y, char_w, char_h)):
                game_data['total_coins'] += current_coins; save_game_data(game_data)
                win_timer = pygame.time.get_ticks(); game_state = "WIN"

        # Enemies & Bullets (Logic remains the same)
        for z in zombies:
            if z["rect"].centerx < player_x: z["rect"].x += z["speed"]
            else: z["rect"].x -= z["speed"]
            if has_zL: screen.blit(zombie_img, (z["rect"].x - camera_x, z["rect"].y))
            if pygame.Rect(player_x, player_y, char_w, char_h).colliderect(z["rect"]): player_health -= 1
        for s in snipers[:]:
            sx = s["rect"].x - camera_x
            if has_zR: screen.blit(sniper_img, (sx, s["rect"].y))
            if abs(s["rect"].x - player_x) < 800:
                pygame.draw.rect(screen, (255, 0, 0), (sx, s["rect"].y - 15, char_w, 7))
                s["shoot_timer"] -= 1
                if s["shoot_timer"] <= 0:
                    sd = -1 if s["rect"].x > player_x else 1
                    sniper_bullets.append({"rect": pygame.Rect(s["rect"].centerx, s["rect"].centery, 20, 10), "dir": sd}); s["shoot_timer"] = 110
        for b in bullets[:]:
            b["rect"].x += 20 * b["dir"]
            if has_b: screen.blit(bullet_img, (b["rect"].x - camera_x, b["rect"].y))
            for z in zombies:
                if b["rect"].colliderect(z["rect"]): z["rect"].x = random.randint(int(WORLD_WIDTH), int(WORLD_WIDTH + 500)); score += 10; bullets.remove(b); break
            if b in bullets:
                for s in snipers[:]:
                    if b["rect"].colliderect(s["rect"]):
                        s["health"] -= 1
                        if s["health"] <= 0: score += 50; snipers.remove(s); spawn_sniper()
                        bullets.remove(b); break
        for sb in sniper_bullets[:]:
            sb["rect"].x += 10 * sb["dir"]
            if has_b: screen.blit(bullet_img, (sb["rect"].x - camera_x, sb["rect"].y))
            if sb["rect"].colliderect(pygame.Rect(player_x, player_y, char_w, char_h)): player_health -= 10; sniper_bullets.remove(sb)
        for c in coins[:]:
            if has_coin: screen.blit(coin_img, (c.x - camera_x, c.y))
            if pygame.Rect(player_x, player_y, char_w, char_h).colliderect(c):
                current_coins += 1; coins.remove(c); coins.append(pygame.Rect(random.randint(0, int(WORLD_WIDTH)), GROUND_Y - coin_size - 10, coin_size, coin_size))

        px = player_x - camera_x
        if player_dir == 1: screen.blit(player_R_img, (px, player_y))
        else: screen.blit(player_L_img, (px, player_y))
        pygame.draw.rect(screen, (0, 255, 0), (px, player_y-20, char_w*(player_health/100), 8))
        ui_txt = font_ui.render(f"Score: {score} | Coins: {current_coins}", True, (255, 255, 255)); screen.blit(ui_txt, (50, 50))
        pygame.draw.rect(screen, (255,255,255), left_btn, 2); pygame.draw.rect(screen, (255,255,255), right_btn, 2)
        pygame.draw.rect(screen, (0,255,0), jump_btn, 2); pygame.draw.rect(screen, (255,0,0), shoot_btn, 2)
        if player_health <= 0: game_data['total_coins'] += current_coins; save_game_data(game_data); game_state = "GAMEOVER"

    elif game_state == "WIN":
        screen.fill((0, 0, 0))
        win_msg = font_win.render("YOU WIN", True, (255, 255, 0))
        screen.blit(win_msg, (WIDTH//2 - win_msg.get_width()//2, HEIGHT//2 - win_msg.get_height()//2))
        
        # --- نظام الخمس ثواني ---
        elapsed = pygame.time.get_ticks() - win_timer
        if elapsed >= 5000: # 5000 ميلي ثانية = 5 ثواني
            game_state = "START"
            click_cooldown = 30

    elif game_state == "GAMEOVER":
        screen.fill((50, 0, 0))
        over_txt = font_title.render("GAME OVER", True, (255, 255, 255))
        screen.blit(over_txt, (WIDTH//2 - over_txt.get_width()//2, HEIGHT//2 - 50))
        if m_down and click_cooldown == 0: game_state = "START"; click_cooldown = 20

    elif game_state == "UPGRADES":
        title = font_menu.render("UPGRADES SHOP", True, (0, 255, 255)); screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        def draw_up(rect, label, level, key):
            global click_cooldown
            pygame.draw.rect(screen, (40, 40, 60), rect, 0, 5); cost = get_upgrade_cost(level); status = f"Cost: {cost}" if cost else "MAXED"
            txt = font_ui.render(f"{label} (Lvl {level}) - {status}", True, (255, 255, 255)); screen.blit(txt, (rect.x + 20, rect.y + 20))
            if m_down and click_cooldown == 0 and rect.collidepoint(m_pos):
                if cost and game_data['total_coins'] >= cost: game_data['total_coins'] -= cost; game_data[key] += 1; save_game_data(game_data); click_cooldown = 20
        draw_up(u_fire_rect, "Fire Rate", game_data['up_fire_rate'], 'up_fire_rate'); draw_up(u_dmg_rect, "Damage", game_data['up_damage'], 'up_damage'); draw_up(u_speed_rect, "Movement", game_data['up_speed'], 'up_speed')
        pygame.draw.rect(screen, (150, 0, 0), back_btn, 0, 5); screen.blit(font_ui.render("BACK", True, (255, 255, 255)), (back_btn.x + 40, back_btn.y + 15))
        if m_down and back_btn.collidepoint(m_pos): game_state = "START"; click_cooldown = 20

    pygame.display.flip()
    clock.tick(60)
