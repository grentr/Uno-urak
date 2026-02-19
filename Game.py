import pygame
import random
from collections import deque
import sys
import math
import threading
import json
import os

pygame.init()

images = {
    "sixC": pygame.image.load('PNG/6C.png'),
    "sixD": pygame.image.load('PNG/6D.png'),
    "sixS": pygame.image.load('PNG/6S.png'),
    "sixH": pygame.image.load('PNG/6H.png'),
    "sevenC": pygame.image.load('PNG/7C.png'),
    "sevenD": pygame.image.load('PNG/7D.png'),
    "sevenS": pygame.image.load('PNG/7S.png'),
    "sevenH": pygame.image.load('PNG/7H.png'),
    "eightC": pygame.image.load('PNG/8C.png'),
    "eightD": pygame.image.load('PNG/8D.png'),
    "eightS": pygame.image.load('PNG/8S.png'),
    "eightH": pygame.image.load('PNG/8H.png'),
    "nineC": pygame.image.load('PNG/9C.png'),
    "nineD": pygame.image.load('PNG/9D.png'),
    "nineS": pygame.image.load('PNG/9S.png'),
    "nineH": pygame.image.load('PNG/9H.png'),
    "tenC": pygame.image.load('PNG/10C.png'),
    "tenD": pygame.image.load('PNG/10D.png'),
    "tenS": pygame.image.load('PNG/10S.png'),
    "tenH": pygame.image.load('PNG/10H.png'),
    "jackC": pygame.image.load('PNG/JC.png'),
    "jackD": pygame.image.load('PNG/JD.png'),
    "jackS": pygame.image.load('PNG/JS.png'),
    "jackH": pygame.image.load('PNG/JH.png'),
    "queenC": pygame.image.load('PNG/QC.png'),
    "queenD": pygame.image.load('PNG/QD.png'),
    "queenS": pygame.image.load('PNG/QS.png'),
    "queenH": pygame.image.load('PNG/QH.png'),
    "kingC": pygame.image.load('PNG/KC.png'),
    "kingD": pygame.image.load('PNG/KD.png'),
    "kingS": pygame.image.load('PNG/KS.png'),
    "kingH": pygame.image.load('PNG/KH.png'),
    "aceC": pygame.image.load('PNG/AC.png'),
    "aceD": pygame.image.load('PNG/AD.png'),
    "aceS": pygame.image.load('PNG/AS.png'),
    "aceH": pygame.image.load('PNG/AH.png'),
    "back": pygame.image.load('PNG/red_back.png'),
    "reverseC": pygame.image.load('PNG/CR.png'),
    "reverseD": pygame.image.load('PNG/DR.png'),
    "reverseS": pygame.image.load('PNG/SR.png'),
    "reverseH": pygame.image.load('PNG/HR.png'),
    "skipC": pygame.image.load('PNG/CS.png'),
    "skipD": pygame.image.load('PNG/DS.png'),
    "skipS": pygame.image.load('PNG/SS.png'),
    "skipH": pygame.image.load('PNG/HS.png'),
    "wild": pygame.image.load('PNG/WC.png'),
}

rects = {k + "_rect": images[k].get_rect() for k in images}

def ease_out_cubic(t): return 1 - pow(1 - t, 3)

BLACK      = (0, 0, 0)
DIM        = (15, 15, 15)
DARK_GREEN = (10, 60, 10)
FELT_GREEN = (25, 90, 25)
GOLD       = (212, 175, 55)
GOLD_HOVER = (255, 215, 80)
CREAM      = (245, 235, 200)
RED_CARD   = (180, 30, 30)
WHITE      = (255, 255, 255)
AI_BLUE    = (60, 120, 220)

CONFIG_FILE = "config.json"

# ── Config persistence ─────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_key": "", "resolution": [1980, 1080], "fullscreen": False}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

_cfg = load_config()

# ── Resolution / display settings ─────────────────────────────────────────────

RESOLUTIONS = [
    (1280, 720,  "1280 x 720  (HD)"),
    (1600, 900,  "1600 x 900  (HD+)"),
    (1920, 1080, "1920 x 1080  (Full HD)"),
    (1980, 1080, "1980 x 1080  (Default)"),
    (2560, 1440, "2560 x 1440  (QHD)"),
]

SCREEN_W, SCREEN_H = _cfg.get("resolution", [1980, 1080])
FULLSCREEN = _cfg.get("fullscreen", False)
CARD_W, CARD_H = 120, 180
MARGIN = 60

def _recalc_layout():
    global CARD_W, CARD_H, MARGIN
    scale = min(SCREEN_W / 1980, SCREEN_H / 1080)
    CARD_W = max(60, int(120 * scale))
    CARD_H = max(90, int(180 * scale))
    MARGIN = max(30, int(60 * scale))

def apply_resolution(screen_ref, w, h, fullscreen):
    global SCREEN_W, SCREEN_H, FULLSCREEN
    SCREEN_W, SCREEN_H, FULLSCREEN = w, h, fullscreen
    _recalc_layout()
    flags = pygame.FULLSCREEN if fullscreen else 0
    new_screen = pygame.display.set_mode((w, h), flags)
    cfg = load_config()
    cfg["resolution"] = [w, h]
    cfg["fullscreen"] = fullscreen
    save_config(cfg)
    return new_screen

_recalc_layout()

# ── Card parsing ───────────────────────────────────────────────────────────────

_RANK_NAMES  = {'six':'6','seven':'7','eight':'8','nine':'9','ten':'10',
                'jack':'J','queen':'Q','king':'K','ace':'A'}
_SUIT_SUFFIX = {'C':'clubs','D':'diamonds','H':'hearts','S':'spades'}
_RANK_ORDER  = ['6','7','8','9','10','J','Q','K','A']
_UNPLAYABLE  = {'back'}
_SKIP_SUIT   = {'skipC':'clubs','skipD':'diamonds','skipH':'hearts','skipS':'spades'}
_REVERSE_SUIT= {'reverseC':'clubs','reverseD':'diamonds','reverseH':'hearts','reverseS':'spades'}

def _is_skip(k):    return k in _SKIP_SUIT
def _is_wild(k):    return k == 'wild'
def _is_reverse(k): return k in _REVERSE_SUIT

def _parse_key(key):
    if _is_wild(key):    return ('wild','WILD')
    if _is_skip(key):    return (_SKIP_SUIT[key],'SKIP')
    if _is_reverse(key): return (_REVERSE_SUIT[key],'REVERSE')
    low = key.lower()
    for name, rank in _RANK_NAMES.items():
        if low.startswith(name):
            return _SUIT_SUFFIX[key[len(name):]],rank
    raise ValueError(f"Cannot parse image key: {key!r}")

def _trump_suit_of(key): return _parse_key(key)[0]

def _can_beat(atk_key, def_key, trump_suit):
    if _is_wild(def_key): return True
    a_suit,a_rank = _parse_key(atk_key)
    d_suit,d_rank = _parse_key(def_key)
    if _is_reverse(def_key) or _is_skip(def_key): return d_suit==a_suit
    if d_suit!=trump_suit and d_suit!=a_suit: return False
    a_str = _RANK_ORDER.index(a_rank)+(100 if a_suit==trump_suit else 0)
    d_str = _RANK_ORDER.index(d_rank)+(100 if d_suit==trump_suit else 0)
    return d_str>a_str

def _ranks_on_table(table):
    ranks=set()
    for slot in table:
        if slot is None: continue
        atk,dfn=slot
        _,ar=_parse_key(atk)
        if ar not in ('SKIP','WILD','REVERSE'): ranks.add(ar)
        if dfn is not None:
            _,dr=_parse_key(dfn)
            if dr not in ('SKIP','WILD','REVERSE'): ranks.add(dr)
    return ranks

# ── Suit picker ────────────────────────────────────────────────────────────────

_SUIT_SYMBOLS = {'clubs':'c','diamonds':'d','hearts':'h','spades':'s'}
_SUIT_COLOURS = {'clubs':CREAM,'diamonds':RED_CARD,'hearts':RED_CARD,'spades':CREAM}
_SUIT_NAMES   = ['clubs','diamonds','hearts','spades']
_SUIT_UNICODE = {'clubs':'Clubs','diamonds':'Diamonds','hearts':'Hearts','spades':'Spades'}

def run_suit_picker(screen, fonts):
    clock = pygame.time.Clock()
    cx,cy = SCREEN_W//2, SCREEN_H//2
    pw,ph = 480,200
    panel_rect = pygame.Rect(cx-pw//2, cy-ph//2, pw, ph)
    btn_w,btn_h,gap = 90,90,20
    bx0 = cx-(4*btn_w+3*gap)//2
    by  = cy-btn_h//2+20
    suit_rects = [(s, pygame.Rect(bx0+i*(btn_w+gap), by, btn_w, btn_h))
                  for i,s in enumerate(_SUIT_NAMES)]
    title_f = pygame.font.SysFont("Georgia",26,bold=True)
    sym_f   = pygame.font.SysFont("Georgia",40,bold=True)
    while True:
        clock.tick(60)
        mx,my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                for suit,rect in suit_rects:
                    if rect.collidepoint(mx,my): return suit
        ov = pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        ov.fill((0,0,0,160))
        screen.blit(ov,(0,0))
        panel = pygame.Surface((pw,ph),pygame.SRCALPHA)
        pygame.draw.rect(panel,(20,30,60,240),(0,0,pw,ph),border_radius=14)
        pygame.draw.rect(panel,GOLD,(0,0,pw,ph),2,border_radius=14)
        screen.blit(panel,panel_rect.topleft)
        t = title_f.render("Choose new TRUMP suit",True,GOLD)
        screen.blit(t,(cx-t.get_width()//2, cy-ph//2+16))
        for suit,rect in suit_rects:
            hov=rect.collidepoint(mx,my)
            pygame.draw.rect(screen,(60,50,10) if hov else (30,30,30),rect,border_radius=10)
            pygame.draw.rect(screen,GOLD if hov else (120,100,40),rect,2,border_radius=10)
            sym = sym_f.render(_SUIT_UNICODE[suit],True,_SUIT_COLOURS[suit])
            screen.blit(sym,sym.get_rect(center=rect.center))
        pygame.display.flip()

# ── API Key entry screen ───────────────────────────────────────────────────────

def run_api_key_screen(screen, bg, fonts):
    clock   = pygame.time.Clock()
    _,_,btn_font,hint_font,_ = fonts
    title_f = pygame.font.SysFont("Georgia",28,bold=True)
    sub_f   = pygame.font.SysFont("Palatino Linotype",18)
    inp_f   = pygame.font.SysFont("Courier New",17)

    cfg     = load_config()
    api_key = cfg.get("api_key","")
    cursor_vis = True
    cursor_timer = 0

    cx,cy   = SCREEN_W//2, SCREEN_H//2
    pw,ph   = 720,340
    px,py   = cx-pw//2, cy-ph//2
    inp_rect  = pygame.Rect(px+30, cy-24, pw-60, 46)
    save_rect = pygame.Rect(cx-170, py+ph-66, 150, 42)
    back_rect = pygame.Rect(cx+20,  py+ph-66, 150, 42)

    while True:
        dt = clock.tick(60)
        cursor_timer += dt
        if cursor_timer > 530: cursor_vis=not cursor_vis; cursor_timer=0
        mx,my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    return api_key
                elif event.key==pygame.K_RETURN:
                    cfg["api_key"]=api_key.strip(); save_config(cfg)
                    return api_key.strip()
                elif event.key==pygame.K_BACKSPACE:
                    api_key=api_key[:-1]
                else:
                    ch=event.unicode
                    if ch and ord(ch)>=32: api_key+=ch
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if save_rect.collidepoint(mx,my):
                    cfg["api_key"]=api_key.strip(); save_config(cfg)
                    return api_key.strip()
                if back_rect.collidepoint(mx,my):
                    return cfg.get("api_key","")

        screen.blit(bg,(0,0))
        ov = pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        ov.fill((0,0,0,190))
        screen.blit(ov,(0,0))
        panel = pygame.Surface((pw,ph),pygame.SRCALPHA)
        pygame.draw.rect(panel,(12,20,50,250),(0,0,pw,ph),border_radius=16)
        pygame.draw.rect(panel,AI_BLUE,(0,0,pw,ph),2,border_radius=16)
        screen.blit(panel,(px,py))
        pygame.draw.rect(screen,(8,16,40),inp_rect,border_radius=6)
        pygame.draw.rect(screen,AI_BLUE,inp_rect,2,border_radius=6)
        sl=btn_font.render("Save",True,CREAM)
        screen.blit(sl,sl.get_rect(center=save_rect.center))
        hov_b=back_rect.collidepoint(mx,my)
        pygame.draw.rect(screen,(40,10,10) if hov_b else (30,20,20),back_rect,border_radius=8)
        pygame.draw.rect(screen,(220,80,80) if hov_b else (150,60,60),back_rect,2,border_radius=8)
        bl=btn_font.render("Back",True,CREAM)
        screen.blit(bl,bl.get_rect(center=back_rect.center))
        pygame.display.flip()

# ── Settings menu ──────────────────────────────────────────────────────────────

def run_settings_menu(screen, bg, fonts):
    global SCREEN_W, SCREEN_H, FULLSCREEN
    clock=pygame.time.Clock()
    _,_,btn_font,_,_ = fonts
    title_f  = pygame.font.SysFont("Georgia",32,bold=True)
    option_f = pygame.font.SysFont("Palatino Linotype",22)
    sub_f    = pygame.font.SysFont("Palatino Linotype",18)

    current_idx=next((i for i,(w,h,_) in enumerate(RESOLUTIONS) if w==SCREEN_W and h==SCREEN_H),2)
    pending_idx=current_idx; pending_fs=FULLSCREEN

    pw,ph=660,460
    cx_abs=SCREEN_W//2; cy_abs=SCREEN_H//2
    px,py=cx_abs-pw//2, cy_abs-ph//2
    ROW_H=46; row_y0=py+100
    fs_row_y=row_y0+len(RESOLUTIONS)*ROW_H+20
    apply_rect=pygame.Rect(cx_abs-170, py+ph-66, 150, 42)
    back_rect =pygame.Rect(cx_abs+20,  py+ph-66, 150, 42)

    def _row_rect(i): return pygame.Rect(px+30, row_y0+i*ROW_H, pw-60, ROW_H-4)

    while True:
        clock.tick(60)
        mx,my=pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                return screen,False
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                for i in range(len(RESOLUTIONS)):
                    if _row_rect(i).collidepoint(mx,my): pending_idx=i
                fs_rect=pygame.Rect(px+30,fs_row_y,pw-60,ROW_H-4)
                if fs_rect.collidepoint(mx,my): pending_fs=not pending_fs
                if apply_rect.collidepoint(mx,my):
                    w,h,_=RESOLUTIONS[pending_idx]
                    new_screen=apply_resolution(screen,w,h,pending_fs)
                    return new_screen,True
                if back_rect.collidepoint(mx,my): return screen,False

        screen.blit(bg,(0,0))
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,180)); screen.blit(ov,(0,0))
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA)
        pygame.draw.rect(panel,(18,28,18,245),(0,0,pw,ph),border_radius=16)
        pygame.draw.rect(panel,GOLD,(0,0,pw,ph),2,border_radius=16)
        screen.blit(panel,(px,py))
        t=title_f.render("Settings",True,GOLD)
        screen.blit(t,(cx_abs-t.get_width()//2, py+22))
        pygame.draw.line(screen,(*GOLD,100),(px+30,py+70),(px+pw-30,py+70),1)
        sec=sub_f.render("RESOLUTION",True,(150,130,60))
        screen.blit(sec,(px+30, row_y0-22))
        for i,(w,h,label) in enumerate(RESOLUTIONS):
            rr=_row_rect(i); hov=rr.collidepoint(mx,my); selected=(i==pending_idx)
            bg_col=(40,55,40,200) if selected else ((30,45,30,160) if hov else (20,30,20,120))
            rs=pygame.Surface((rr.width,rr.height),pygame.SRCALPHA); rs.fill(bg_col); screen.blit(rs,rr.topleft)
            if selected or hov: pygame.draw.rect(screen,GOLD if selected else (120,100,40),rr,1,border_radius=6)
            pygame.draw.circle(screen,GOLD,(rr.x+18,rr.centery),9,2)
            if selected: pygame.draw.circle(screen,GOLD,(rr.x+18,rr.centery),5)
            col=GOLD if selected else (CREAM if hov else (180,160,100))
            lbl=option_f.render(label,True,col)
            screen.blit(lbl,(rr.x+38, rr.centery-lbl.get_height()//2))
            if w==SCREEN_W and h==SCREEN_H:
                badge=sub_f.render("current",True,(80,160,80))
                screen.blit(badge,(rr.right-badge.get_width()-10, rr.centery-badge.get_height()//2))
        fs_rect=pygame.Rect(px+30,fs_row_y,pw-60,ROW_H-4)
        pygame.draw.line(screen,(*GOLD,60),(px+30,fs_row_y-8),(px+pw-30,fs_row_y-8),1)
        fs_sec=sub_f.render("DISPLAY MODE",True,(150,130,60))
        screen.blit(fs_sec,(px+30,fs_row_y-28))
        hov_fs=fs_rect.collidepoint(mx,my)
        fs_bg=pygame.Surface((fs_rect.width,fs_rect.height),pygame.SRCALPHA)
        fs_bg.fill((30,45,30,160) if hov_fs else (20,30,20,120)); screen.blit(fs_bg,fs_rect.topleft)
        cb_x,cb_y=fs_rect.x+18,fs_rect.centery
        pygame.draw.rect(screen,GOLD,(cb_x-9,cb_y-9,18,18),2,border_radius=3)
        if pending_fs:
            pygame.draw.line(screen,GOLD,(cb_x-5,cb_y),(cb_x-1,cb_y+5),2)
            pygame.draw.line(screen,GOLD,(cb_x-1,cb_y+5),(cb_x+6,cb_y-5),2)
        fs_lbl=option_f.render("Fullscreen",True,GOLD if pending_fs else CREAM)
        screen.blit(fs_lbl,(fs_rect.x+38, fs_rect.centery-fs_lbl.get_height()//2))
        hov_a=apply_rect.collidepoint(mx,my)
        pygame.draw.rect(screen,(50,40,5) if hov_a else (35,28,3),apply_rect,border_radius=8)
        pygame.draw.rect(screen,GOLD_HOVER if hov_a else GOLD,apply_rect,2,border_radius=8)
        al=btn_font.render("Apply",True,GOLD_HOVER if hov_a else CREAM)
        screen.blit(al,al.get_rect(center=apply_rect.center))
        hov_b=back_rect.collidepoint(mx,my)
        pygame.draw.rect(screen,(40,10,10) if hov_b else (30,20,20),back_rect,border_radius=8)
        pygame.draw.rect(screen,(220,80,80) if hov_b else (150,60,60),back_rect,2,border_radius=8)
        bl=btn_font.render("Back",True,CREAM)
        screen.blit(bl,bl.get_rect(center=back_rect.center))
        hint=sub_f.render("ESC to discard  *  Apply restarts layout",True,(100,90,50))
        screen.blit(hint,(cx_abs-hint.get_width()//2, py+ph+10))
        pygame.display.flip()

# ── DurakRules ─────────────────────────────────────────────────────────────────

class DurakRules:
    def __init__(self, all_card_keys, trump_key):
        self.trump_suit=_trump_suit_of(trump_key)
        self.trump_key=trump_key
        pool=[k for k in all_card_keys if k not in _UNPLAYABLE]
        random.shuffle(pool)
        self.hand=pool[:6]; self.opp_hand=pool[6:12]
        self.remaining=deque(pool[12:])
        self.attacker=self._first_attacker()
        self.defender='opponent' if self.attacker=='player' else 'player'
        self.table=[None]*6; self.locked_ranks=set()
        self.phase='attack'; self.winner=None; self.status=""
        self.pending_wild=False
        self.player_taken=[]; self.opp_taken=[]
        self._refresh_status()

    def _first_attacker(self):
        def lowest_trump(hand):
            ts=[(_RANK_ORDER.index(r),k) for k in hand for s,r in [_parse_key(k)]
                if s==self.trump_suit and r not in ('SKIP','WILD','REVERSE')]
            return min(ts)[0] if ts else 999
        p,o=lowest_trump(self.hand),lowest_trump(self.opp_hand)
        if p==o: return random.choice(['player','opponent'])
        return 'player' if p<o else 'opponent'

    def _refresh_status(self):
        if self.phase=='game_over':
            if self.winner=='draw':   self.status="DRAW - both players emptied their hands!"
            elif self.winner=='player': self.status="YOU WIN - AI is the Durak!"
            else:                     self.status="YOU LOSE - You are the Durak!"
            return
        if self.phase=='attack':
            who="YOUR TURN" if self.attacker=='player' else "AI ATTACKS"
            self.status=f"{who}: drag a card to attack."
        else:
            who="YOUR TURN" if self.defender=='player' else "AI DEFENDS"
            self.status=f"{who}: defend or click TAKE."

    def _attacker_hand(self):  return self.hand if self.attacker=='player' else self.opp_hand
    def _defender_hand(self):  return self.hand if self.defender=='player' else self.opp_hand
    def _defender_taken(self): return self.player_taken if self.defender=='player' else self.opp_taken
    def _attacker_taken(self): return self.player_taken if self.attacker=='player' else self.opp_taken

    def valid_attack_cards(self):
        hand=self._attacker_hand()+self._attacker_taken()
        occupied=[s for s in self.table if s is not None]
        if not occupied:
            return {k for k in hand if not _is_skip(k) and not _is_wild(k) and not _is_reverse(k)}
        table_ranks=_ranks_on_table(self.table)
        return {k for k in hand
                if not _is_skip(k) and not _is_wild(k) and not _is_reverse(k)
                and _parse_key(k)[1] in table_ranks
                and _parse_key(k)[1] not in self.locked_ranks}

    def valid_defense_for(self,atk_key):
        hand=self._defender_hand()+self._defender_taken()
        return {k for k in hand if _can_beat(atk_key,k,self.trump_suit)}

    def all_defense_cards(self):
        hand=self._defender_hand()+self._defender_taken()
        return {k for k in hand
                if any(_can_beat(slot[0],k,self.trump_suit)
                       for slot in self.table if slot is not None and slot[1] is None)}

    def _unbeaten(self):  return [s for s in self.table if s is not None and s[1] is None]
    def _all_beaten(self):
        occupied=[s for s in self.table if s is not None]
        return bool(occupied) and all(s[1] is not None for s in occupied)

    def try_attack(self,card_key,slot_index):
        if self.phase!='attack': return False
        if card_key not in self.valid_attack_cards(): return False
        if self.table[slot_index] is not None: return False
        self.table[slot_index]=[card_key,None]; self.phase='defense'
        atk_taken=self._attacker_taken()
        if card_key in atk_taken: atk_taken.remove(card_key)
        else: self._attacker_hand().remove(card_key)
        self._check_game_over(); self._refresh_status()
        return True

    def try_defend(self,atk_key,def_key):
        if self.phase!='defense': return False
        if def_key not in self.valid_defense_for(atk_key): return False
        def_taken=self._defender_taken()
        if def_key in def_taken: def_taken.remove(def_key)
        else: self._defender_hand().remove(def_key)
        if _is_skip(def_key):
            _,atk_rank=_parse_key(atk_key); self.locked_ranks.add(atk_rank)
        for slot in self.table:
            if slot is not None and slot[0]==atk_key and slot[1] is None:
                slot[1]=def_key; break
        if _is_reverse(def_key):
            self.attacker,self.defender=self.defender,self.attacker
            self.phase='attack'; self._check_game_over(); self._refresh_status()
            return 'ok_reverse'
        if self._all_beaten(): self.phase='attack'
        self._check_game_over(); self._refresh_status()
        if _is_wild(def_key): self.pending_wild=True; return 'ok_wild'
        return 'ok'

    def try_take(self):
        if self.phase!='defense': return False
        occupied=[s for s in self.table if s is not None]
        if not occupied: return False
        taken=self._defender_taken()
        for slot in self.table:
            if slot is not None:
                taken.append(slot[0])
                if slot[1] is not None: taken.append(slot[1])
        self.table=[None]*6; self.locked_ranks=set()
        atk_r=self._refill_hand(self._attacker_hand(),self._attacker_taken())
        def_r=self._refill_hand(self._defender_hand(),self._defender_taken())
        self.phase='attack'; self._check_game_over(); self._refresh_status()
        return (True,atk_r,def_r)

    def _refill_hand(self,hand,taken_pile):
        refilled=[]
        while len(hand)<6 and taken_pile:
            card=taken_pile.pop(0); hand.append(card); refilled.append((card,'taken'))
        while len(hand)<6 and self.remaining:
            card=self.remaining.popleft(); hand.append(card); refilled.append((card,'deck'))
        return refilled

    def resolve_wild(self,new_suit):
        self.trump_suit=new_suit
        suffix={'clubs':'C','diamonds':'D','hearts':'H','spades':'S'}
        self.trump_key='ace'+suffix[new_suit]; self.pending_wild=False

    def try_end_attack(self):
        if self.phase!='attack': return []
        occupied=[s for s in self.table if s is not None]
        if not occupied or self._unbeaten(): return []
        cleared=[]
        for slot in self.table:
            if slot is not None:
                cleared.append(slot[0])
                if slot[1] is not None: cleared.append(slot[1])
        self.attacker,self.defender=self.defender,self.attacker
        self.table=[None]*6; self.locked_ranks=set()
        atk_r=self._refill_hand(self._attacker_hand(),self._attacker_taken())
        def_r=self._refill_hand(self._defender_hand(),self._defender_taken())
        self.phase='attack'; self._check_game_over(); self._refresh_status()
        return (cleared,atk_r,def_r)

    def _check_game_over(self):
        if self.remaining: return
        p_empty=len(self.hand)==0 and len(self.player_taken)==0
        o_empty=len(self.opp_hand)==0 and len(self.opp_taken)==0
        if p_empty and o_empty: self.phase='game_over'; self.winner='draw'
        elif p_empty:           self.phase='game_over'; self.winner='player'
        elif o_empty:           self.phase='game_over'; self.winner='opponent'

# ── Visual helpers ─────────────────────────────────────────────────────────────

def load_fonts():
    return (
        pygame.font.SysFont("Georgia",90,bold=True),
        pygame.font.SysFont("Georgia",26,italic=True),
        pygame.font.SysFont("Palatino Linotype",34,bold=True),
        pygame.font.SysFont("Palatino Linotype",20),
        pygame.font.SysFont("Palatino Linotype",22,bold=True),
    )

def make_bg(w,h):
    bg=pygame.Surface((w,h)); bg.fill(DIM)
    pygame.draw.rect(bg,FELT_GREEN,(40,40,w-80,h-80),border_radius=30)
    pygame.draw.rect(bg,DARK_GREEN,(40,40,w-80,h-80),8,border_radius=30)
    return bg

def draw_bg_cards(surf,tick):
    card_data=[(80,120,0,0.4),(1850,80,0.8,0.3),(60,920,1.6,0.5),(1860,800,2.4,0.35),(990,980,3.2,0.25)]
    cw,ch=72,108
    for bx,by,ao,sm in card_data:
        sx=int(bx*SCREEN_W/1980); sy=int(by*SCREEN_H/1080)
        angle=ao+math.sin(tick*0.0008*sm+ao)*8
        drift=math.sin(tick*0.0006*sm+ao)*12
        cs=pygame.Surface((cw,ch),pygame.SRCALPHA)
        pygame.draw.rect(cs,(50,50,50,90),(0,0,cw,ch),border_radius=6)
        pygame.draw.rect(cs,(90,70,20,70),(0,0,cw,ch),2,border_radius=6)
        rot=pygame.transform.rotate(cs,angle)
        surf.blit(rot,(sx-rot.get_width()//2, sy+drift-rot.get_height()//2))

def draw_zone_label(surf,font,text,cx,y):
    lbl=font.render(text,True,GOLD); x=cx-lbl.get_width()//2
    surf.blit(lbl,(x,y))
    pygame.draw.line(surf,(*GOLD,80),(x,y+lbl.get_height()+2),(x+lbl.get_width(),y+lbl.get_height()+2),1)

def draw_card_slot(surf,x,y):
    inner=pygame.Surface((CARD_W,CARD_H),pygame.SRCALPHA); inner.fill((0,0,0,60)); surf.blit(inner,(x,y))
    pygame.draw.rect(surf,GOLD,pygame.Rect(x,y,CARD_W,CARD_H),2,border_radius=6)
    sz=10
    for cx2,cy2 in [(x+4,y+4),(x+CARD_W-4-sz,y+4),(x+4,y+CARD_H-4-sz),(x+CARD_W-4-sz,y+CARD_H-4-sz)]:
        pygame.draw.rect(surf,(*GOLD,60),(cx2,cy2,sz,sz),1)

def draw_card_image(surf,card_key,x,y):
    surf.blit(pygame.transform.scale(images[card_key],(CARD_W,CARD_H)),(x,y))

def draw_game_table(screen,bg,fonts,tick,trump_key,vs_ai=False):
    _,_,_,hint_font,label_font=fonts
    screen.blit(bg,(0,0)); draw_bg_cards(screen,tick)
    cx=SCREEN_W//2
    dark=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); dark.fill((0,0,0,90))
    pygame.draw.ellipse(dark,(0,0,0,0),(MARGIN+10,MARGIN+10,SCREEN_W-MARGIN*2-20,SCREEN_H-MARGIN*2-20))
    screen.blit(dark,(0,0))
    brd=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
    pygame.draw.ellipse(brd,(*GOLD,60),(MARGIN,MARGIN,SCREEN_W-MARGIN*2,SCREEN_H-MARGIN*2),3)
    pygame.draw.ellipse(brd,(*DARK_GREEN,120),(MARGIN+12,MARGIN+12,SCREEN_W-MARGIN*2-24,SCREEN_H-MARGIN*2-24),8)
    screen.blit(brd,(0,0))
    deck_x=SCREEN_W-CARD_W-220; deck_y=SCREEN_H//2-CARD_H//2
    draw_card_slot(screen,deck_x,deck_y)
    draw_zone_label(screen,label_font,"DECK",deck_x+CARD_W//2,deck_y-36)
    screen.blit(pygame.transform.scale(images["back"],(CARD_W,CARD_H)),(deck_x,deck_y))
    trump_x=deck_x-CARD_W-30; trump_y=deck_y+20
    draw_card_slot(screen,trump_x,trump_y)
    draw_zone_label(screen,label_font,"TRUMP",trump_x+CARD_W//2,trump_y-36)
    screen.blit(pygame.transform.scale(images[trump_key],(CARD_W,CARD_H)),(trump_x,trump_y))
    spacing=30; n_slots=3; total_w=n_slots*CARD_W+(n_slots-1)*spacing
    field_x0=cx-total_w//2
    atk_y=SCREEN_H//2-CARD_H-20; def_y=SCREEN_H//2+20
    for i in range(n_slots):
        x=field_x0+i*(CARD_W+spacing)
        draw_card_slot(screen,x,atk_y); draw_card_slot(screen,x,def_y)
    pygame.draw.line(screen,(*GOLD,70),(field_x0-20,SCREEN_H//2-4),(field_x0+total_w+20,SCREEN_H//2-4),1)
    hand_slots=6; hand_total=hand_slots*CARD_W+(hand_slots-1)*spacing
    hand_x0=cx-hand_total//2; hand_y=SCREEN_H-CARD_H-70; opp_y=70
    draw_zone_label(screen,label_font,"YOUR HAND",cx,hand_y-36)
    opp_label="AI"
    draw_zone_label(screen,label_font,opp_label,cx,opp_y-36+16)
    for i in range(hand_slots):
        draw_card_slot(screen,hand_x0+i*(CARD_W+spacing),hand_y)
        draw_card_slot(screen,hand_x0+i*(CARD_W+spacing),opp_y+20)
    icon_f=pygame.font.SysFont("Georgia",36,bold=True)
    for (sx,sy),suit,col in zip(
            [(MARGIN+30,MARGIN+30),(SCREEN_W-MARGIN-60,MARGIN+30),(MARGIN+30,SCREEN_H-MARGIN-60),(SCREEN_W-MARGIN-60,SCREEN_H-MARGIN-60)],
            ["S","H","D","C"],[CREAM,RED_CARD,RED_CARD,CREAM]):
        screen.blit(icon_f.render(suit,True,(*col,120)),(sx,sy))
    hint=hint_font.render("Drag cards to play  *  ESC menu",True,(130,110,60))
    screen.blit(hint,(cx-hint.get_width()//2,SCREEN_H-32))

def draw_taken_pile_panel(screen,pile,title,anchor_x,anchor_y,small_f,mx,my,is_active):
    if not pile: return []
    lbl=small_f.render(f"{title} TAKEN ({len(pile)})",True,(220,160,60))
    screen.blit(lbl,(anchor_x,anchor_y-22))
    card_rects=[]; mini_w,mini_h=60,90; visible=pile[-8:]
    for idx,card in enumerate(visible):
        cx2=anchor_x+idx*18; cy2=anchor_y
        img=pygame.transform.scale(images[card],(mini_w,mini_h))
        if is_active and pygame.Rect(cx2,cy2,mini_w,mini_h).collidepoint(mx,my):
            glow=pygame.Surface((mini_w+8,mini_h+8),pygame.SRCALPHA)
            pygame.draw.rect(glow,(*GOLD,80),(0,0,mini_w+8,mini_h+8),border_radius=6)
            screen.blit(glow,(cx2-4,cy2-4))
        screen.blit(img,(cx2,cy2))
        pygame.draw.rect(screen,GOLD,(cx2,cy2,mini_w,mini_h),1,border_radius=4)
        card_rects.append((card,pygame.Rect(cx2,cy2,mini_w,mini_h)))
    return card_rects

def draw_ai_thinking(screen):
    t=pygame.time.get_ticks()
    dots="."*(1+(t//400)%3)
    f=pygame.font.SysFont("Georgia",22,italic=True)
    surf=f.render(f"AI thinking{dots}",True,AI_BLUE)
    alpha=160+int(80*math.sin(t*0.005))
    surf.set_alpha(alpha)
    cx=SCREEN_W//2; cy=SCREEN_H//2
    bg_s=pygame.Surface((surf.get_width()+24,surf.get_height()+12),pygame.SRCALPHA)
    pygame.draw.rect(bg_s,(0,0,40,180),(0,0,bg_s.get_width(),bg_s.get_height()),border_radius=8)
    screen.blit(bg_s,(cx-bg_s.get_width()//2, cy-bg_s.get_height()//2-60))
    screen.blit(surf,(cx-surf.get_width()//2, cy-surf.get_height()//2-60))

# ── Spark / MenuButton ─────────────────────────────────────────────────────────

class Spark:
    def __init__(self): self.reset()
    def reset(self):
        t=pygame.time.get_ticks()
        self.x=SCREEN_W//2+(t%7-3)*30; self.y=SCREEN_H
        self.vx=(t%5-2)*0.3; self.vy=-(1.2+(t%10)*0.15)
        self.life=1.0; self.decay=0.003+(t%5)*0.001
        self.col=random.choice([GOLD,RED_CARD,CREAM])
    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.life-=self.decay
        if self.life<=0: self.reset()
    def draw(self,surf):
        a=max(0,int(self.life*200)); s=pygame.Surface((4,4),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.col[:3],a),(2,2),2); surf.blit(s,(int(self.x),int(self.y)))

class MenuButton:
    W,H,RADIUS=320,60,12
    def __init__(self,label,cx,cy,action):
        self.label=label; self.rect=pygame.Rect(0,0,self.W,self.H)
        self.rect.center=(cx,cy); self.action=action; self.hovered=False; self._anim=0.0
    def update(self,dt): self._anim+=((1.0 if self.hovered else 0.0)-self._anim)*min(dt*12,1.0)
    def draw(self,surf,font):
        a=self._anim
        if a>0.01:
            glow=pygame.Surface((self.W+20,self.H+20),pygame.SRCALPHA)
            pygame.draw.rect(glow,(*GOLD,int(120*a)),(0,0,self.W+20,self.H+20),border_radius=self.RADIUS+4)
            surf.blit(glow,(self.rect.x-10,self.rect.y-10))
        pygame.draw.rect(surf,(int(30+a*50),int(30+a*10),int(10+a*5)),self.rect,border_radius=self.RADIUS)
        pygame.draw.rect(surf,tuple(int(GOLD[i]+(GOLD_HOVER[i]-GOLD[i])*a) for i in range(3)),self.rect,2,border_radius=self.RADIUS)
        lbl=font.render(self.label,True,tuple(int(CREAM[i]+(GOLD_HOVER[i]-CREAM[i])*a) for i in range(3)))
        surf.blit(lbl,lbl.get_rect(center=self.rect.center))
    def check_hover(self,pos): self.hovered=self.rect.collidepoint(pos)
    def check_click(self,pos): return self.rect.collidepoint(pos)

HOW_TO_LINES=[
    "UNO-URAK  -  Quick Rules","",
    "Both hands face-up. One player controls both sides.",
    "The deck uses cards 6 through Ace (36 cards).",
    "One suit is the TRUMP suit -- revealed at game start.","",
    "ATTACK (attacker's turn):",
    "  Drag any card from hand OR taken pile to any field slot.",
    "  To pile on: drag more cards of the SAME RANK.","",
    "DEFEND (defender's turn):",
    "  Drag a card onto the attack card you want to beat.",
    "  Must be same suit + higher rank, OR any trump card.",
    "  Click TAKE to take all table cards into your taken pile.","",
    "SKIP CARD: Defends against same suit. Locks that rank for the round.",
    "REVERSE CARD: Defends against same suit. Swaps attacker/defender.",
    "WILD CARD: Beats ANY attack. You choose the new trump suit.","",
    "TAKEN PILE: Cards taken instead of defending.",
    "  Hand auto-refills from taken pile when below 6.",
    "  You can also drag taken-pile cards to attack.","",
    "The last player holding cards is the DURAK (fool)!","",
    "                Press  ESC  to go back",
]

def draw_how_to_play(surf,fonts):
    ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,210)); surf.blit(ov,(0,0))
    pw,ph=780,640
    panel=pygame.Surface((pw,ph),pygame.SRCALPHA)
    pygame.draw.rect(panel,(20,50,20,240),(0,0,pw,ph),border_radius=16)
    pygame.draw.rect(panel,GOLD,(0,0,pw,ph),2,border_radius=16)
    surf.blit(panel,(SCREEN_W//2-pw//2,SCREEN_H//2-ph//2))
    tf=pygame.font.SysFont("Georgia",28,bold=True); bf=pygame.font.SysFont("Palatino Linotype",17)
    sy=SCREEN_H//2-ph//2+24
    for i,line in enumerate(HOW_TO_LINES):
        f=tf if i==0 else bf; col=GOLD if i==0 else CREAM
        t=f.render(line,True,col); surf.blit(t,(SCREEN_W//2-t.get_width()//2,sy+i*19))

def run_main_menu(screen,bg,fonts,return_on_play=False):
    clock=pygame.time.Clock()
    _,sub_font,btn_font,hint_font,_=fonts
    title_font=pygame.font.SysFont("Georgia",90,bold=True)
    cx=SCREEN_W//2

    if return_on_play:
        buttons=[
            MenuButton("Resume Game",    cx,380,"resume"),
            MenuButton("New Game", cx,460,"new_ai"),
            MenuButton("How to Play",    cx,540,"howto"),
            MenuButton("Settings",       cx,620,"settings"),
            MenuButton("Quit",           cx,700,"quit"),
        ]
    else:
        buttons=[
            MenuButton("Play", cx,450,"play_ai"),
            MenuButton("How to Play",       cx,530,"howto"),
            MenuButton("Settings",          cx,610,"settings"),
            MenuButton("Quit",              cx,690,"quit"),
        ]

    sparks=[Spark() for _ in range(2000)]
    showing_howto=False; tick=0

    while True:
        dt=clock.tick(0); tick+=dt
        mx,my=pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                if showing_howto: showing_howto=False
                elif return_on_play: return screen,'resume',False
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if showing_howto: showing_howto=False
                else:
                    for btn in buttons:
                        if btn.check_click((mx,my)):
                            if btn.action=="play_ai": return screen,None,True
                            if btn.action=="resume":  return screen,'resume',False
                            if btn.action=="new_ai":  return screen,'new_game',True
                            if btn.action=="quit":    pygame.quit(); sys.exit()
                            if btn.action=="howto":   showing_howto=True
                            if btn.action=="settings":
                                new_screen,changed=run_settings_menu(screen,bg,fonts)
                                screen=new_screen
                                if changed:
                                    bg=make_bg(SCREEN_W,SCREEN_H); cx=SCREEN_W//2
                                    for b in buttons: b.rect.centerx=cx
                                    return screen,'resolution_changed',False
        for btn in buttons: btn.check_hover((mx,my)); btn.update(dt/1000)
        for sp in sparks: sp.update()
        screen.blit(bg,(0,0)); draw_bg_cards(screen,tick)
        for sp in sparks: sp.draw(screen)
        sh=title_font.render("UNO-URAK",True,BLACK)
        screen.blit(sh,(cx-sh.get_width()//2+4,204))
        ti=title_font.render("UNO-URAK",True,GOLD)
        screen.blit(ti,(cx-ti.get_width()//2,200))
        su=sub_font.render("The Card Game of Fools & Fortune",True,CREAM)
        screen.blit(su,(cx-su.get_width()//2,310))
        pygame.draw.line(screen,GOLD,(cx-200,350),(cx+200,350),1)
        if not showing_howto:
            for btn in buttons: btn.draw(screen,btn_font)
        screen.blit(hint_font.render("v0.2  -  ESC dismisses overlays",True,(100,100,80)),(cx-100,SCREEN_H-40))
        if showing_howto: draw_how_to_play(screen,fonts)
        pygame.display.flip()

def _new_game():
    all_keys=[k for k in images if k not in _UNPLAYABLE]
    trump_key='ace'+random.choice(['C','D','H','S'])
    return all_keys,trump_key,DurakRules(all_keys,trump_key)

def _build_layout():
    spacing=30; hand_slots=6; cx=SCREEN_W//2
    hand_total=hand_slots*CARD_W+(hand_slots-1)*spacing
    hand_x0=cx-hand_total//2; hand_y=SCREEN_H-CARD_H-70; opp_y=70+20
    deck_x=SCREEN_W-CARD_W-220; deck_y=SCREEN_H//2-CARD_H//2
    n_slots=3; total_w=n_slots*CARD_W+(n_slots-1)*spacing
    field_x0=cx-total_w//2; atk_y=SCREEN_H//2-CARD_H-20; def_y=SCREEN_H//2+20
    btn_w,btn_h=160,44
    end_btn_rect=pygame.Rect(cx-btn_w//2-90,SCREEN_H//2-btn_h//2,btn_w,btn_h)
    take_btn_rect=pygame.Rect(cx-btn_w//2+90,SCREEN_H//2-btn_h//2,btn_w,btn_h)
    p_taken_ax=MARGIN+10; p_taken_ay=hand_y-110
    o_taken_ax=MARGIN+10; o_taken_ay=opp_y+CARD_H+16
    return dict(spacing=spacing,cx=cx,hand_x0=hand_x0,hand_y=hand_y,opp_y=opp_y,
                deck_x=deck_x,deck_y=deck_y,n_slots=n_slots,field_x0=field_x0,
                atk_y=atk_y,def_y=def_y,end_btn_rect=end_btn_rect,take_btn_rect=take_btn_rect,
                p_taken_ax=p_taken_ax,p_taken_ay=p_taken_ay,o_taken_ax=o_taken_ax,o_taken_ay=o_taken_ay)

# ── Animation helpers ──────────────────────────────────────────────────────────

def _queue_end_attack_anims(snap,rules,anim_queue,discard_anims,L,atk_r,def_r):
    delay=0
    for si,slot in snap:
        row=si//L['n_slots']; col=si%L['n_slots']
        sx0=L['field_x0']+col*(CARD_W+L['spacing'])
        sy0=L['atk_y'] if row==0 else L['def_y']
        discard_anims.append({'card':slot[0],'sx':sx0,'sy':sy0,'t':0.0,'delay':delay}); delay+=60
        if slot[1] is not None:
            discard_anims.append({'card':slot[1],'sx':sx0+14,'sy':sy0+14,'t':0.0,'delay':delay}); delay+=60
    delay=0
    for card,source in def_r:
        try: idx=rules.opp_hand.index(card) if rules.defender=='opponent' else rules.hand.index(card)
        except ValueError: continue
        ex=L['hand_x0']+idx*(CARD_W+L['spacing'])
        ey=L['opp_y'] if rules.defender=='opponent' else L['hand_y']
        sx=(L['o_taken_ax'] if rules.defender=='opponent' else L['p_taken_ax']) if source=='taken' else L['deck_x']
        sy=(L['o_taken_ay'] if rules.defender=='opponent' else L['p_taken_ay']) if source=='taken' else L['deck_y']
        anim_queue.append({'card':card,'sx':sx,'sy':sy,'ex':ex,'ey':ey,'t':0.0,'delay':delay}); delay+=80
    for card,source in atk_r:
        try: idx=rules.hand.index(card) if rules.attacker=='player' else rules.opp_hand.index(card)
        except ValueError: continue
        ex=L['hand_x0']+idx*(CARD_W+L['spacing'])
        ey=L['hand_y'] if rules.attacker=='player' else L['opp_y']
        sx=(L['p_taken_ax'] if rules.attacker=='player' else L['o_taken_ax']) if source=='taken' else L['deck_x']
        sy=(L['p_taken_ay'] if rules.attacker=='player' else L['o_taken_ay']) if source=='taken' else L['deck_y']
        anim_queue.append({'card':card,'sx':sx,'sy':sy,'ex':ex,'ey':ey,'t':0.0,'delay':delay}); delay+=80

def _queue_take_anims(snap,rules,anim_queue,L,atk_r,def_r):
    delay=0
    tax=L['p_taken_ax'] if rules.defender=='player' else L['o_taken_ax']
    tay=L['p_taken_ay'] if rules.defender=='player' else L['o_taken_ay']
    for si,slot in snap:
        row=si//L['n_slots']; col=si%L['n_slots']
        sx0=L['field_x0']+col*(CARD_W+L['spacing'])
        sy0=L['atk_y'] if row==0 else L['def_y']
        anim_queue.append({'card':slot[0],'sx':sx0,'sy':sy0,'ex':tax,'ey':tay,'t':0.0,'delay':delay,'to_taken':True}); delay+=60
        if slot[1] is not None:
            anim_queue.append({'card':slot[1],'sx':sx0+14,'sy':sy0+14,'ex':tax+20,'ey':tay,'t':0.0,'delay':delay,'to_taken':True}); delay+=60
    for card,source in atk_r:
        try: idx=rules.hand.index(card) if rules.attacker=='player' else rules.opp_hand.index(card)
        except ValueError: continue
        ex=L['hand_x0']+idx*(CARD_W+L['spacing'])
        ey=L['hand_y'] if rules.attacker=='player' else L['opp_y']
        sx=(L['p_taken_ax'] if rules.attacker=='player' else L['o_taken_ax']) if source=='taken' else L['deck_x']
        sy=(L['p_taken_ay'] if rules.attacker=='player' else L['o_taken_ay']) if source=='taken' else L['deck_y']
        anim_queue.append({'card':card,'sx':sx,'sy':sy,'ex':ex,'ey':ey,'t':0.0,'delay':delay}); delay+=80
    for card,source in def_r:
        try: idx=rules.opp_hand.index(card) if rules.defender=='opponent' else rules.hand.index(card)
        except ValueError: continue
        ex=L['hand_x0']+idx*(CARD_W+L['spacing'])
        ey=L['opp_y'] if rules.defender=='opponent' else L['hand_y']
        sx=(L['o_taken_ax'] if rules.defender=='opponent' else L['p_taken_ax']) if source=='taken' else L['deck_x']
        sy=(L['o_taken_ay'] if rules.defender=='opponent' else L['p_taken_ay']) if source=='taken' else L['deck_y']
        anim_queue.append({'card':card,'sx':sx,'sy':sy,'ex':ex,'ey':ey,'t':0.0,'delay':delay}); delay+=80

# ── Main game loop ─────────────────────────────────────────────────────────────

def run_game(screen,bg,fonts,vs_ai,all_keys,trump_key,rules):
    from ai_opponent import get_ai_action

    clock=pygame.time.Clock()
    _,_,btn_font,hint_font,label_font=fonts
    small_f=pygame.font.SysFont("Palatino Linotype",18)
    cfg=load_config(); api_key=cfg.get("api_key","").strip() or None

    tick=0; held_card=None; held_offset=(0,0); held_from_taken=False

    L=_build_layout()
    spacing=L['spacing']; hand_x0=L['hand_x0']; hand_y=L['hand_y']; opp_y=L['opp_y']
    deck_x=L['deck_x']; deck_y=L['deck_y']; n_slots=L['n_slots']; field_x0=L['field_x0']
    atk_y=L['atk_y']; def_y=L['def_y']
    end_btn_rect=L['end_btn_rect']; take_btn_rect=L['take_btn_rect']
    p_taken_ax=L['p_taken_ax']; p_taken_ay=L['p_taken_ay']
    o_taken_ax=L['o_taken_ax']; o_taken_ay=L['o_taken_ay']; cx=L['cx']

    def rebuild_layout():
        nonlocal spacing,hand_x0,hand_y,opp_y,deck_x,deck_y,n_slots,field_x0
        nonlocal atk_y,def_y,end_btn_rect,take_btn_rect,p_taken_ax,p_taken_ay,o_taken_ax,o_taken_ay,cx,L
        L=_build_layout()
        spacing=L['spacing']; hand_x0=L['hand_x0']; hand_y=L['hand_y']; opp_y=L['opp_y']
        deck_x=L['deck_x']; deck_y=L['deck_y']; n_slots=L['n_slots']; field_x0=L['field_x0']
        atk_y=L['atk_y']; def_y=L['def_y']
        end_btn_rect=L['end_btn_rect']; take_btn_rect=L['take_btn_rect']
        p_taken_ax=L['p_taken_ax']; p_taken_ay=L['p_taken_ay']
        o_taken_ax=L['o_taken_ax']; o_taken_ay=L['o_taken_ay']; cx=L['cx']

    anim_queue=[]; ANIM_SPEED=2.8; discard_pile=[]; discard_anims=[]
    reverse_flash=""; reverse_flash_timer=0

    # AI state
    ai_thinking=False; ai_result=[None]; ai_delay=0
    AI_MIN=600; AI_MAX=1400

    def start_ai(ask_wild=False):
        nonlocal ai_thinking
        ai_thinking=True; ai_result[0]=None
        def worker(): ai_result[0]=get_ai_action(rules,api_key,ask_wild=ask_wild)
        threading.Thread(target=worker,daemon=True).start()

    def queue_deal(old_p,old_o):
        delay=0
        for i,card in enumerate(rules.hand):
            if i>=old_p:
                anim_queue.append({'card':card,'sx':deck_x,'sy':deck_y,'ex':hand_x0+i*(CARD_W+spacing),'ey':hand_y,'t':0.0,'delay':delay}); delay+=80
        for i,card in enumerate(rules.opp_hand):
            if i>=old_o:
                anim_queue.append({'card':card,'sx':deck_x,'sy':deck_y,'ex':hand_x0+i*(CARD_W+spacing),'ey':opp_y,'t':0.0,'delay':delay}); delay+=80

    queue_deal(0,0)
    if vs_ai and rules.attacker=='opponent':
        ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()

    running=True
    while running:
        dt=clock.tick(144); tick+=dt
        if reverse_flash_timer>0:
            reverse_flash_timer-=dt
            if reverse_flash_timer<=0: reverse_flash=""
        for a in anim_queue:
            if a['delay']>0: a['delay']-=dt; continue
            a['t']=min(a['t']+(dt/1000)*ANIM_SPEED,1.0)
        anim_queue[:]=[a for a in anim_queue if not (a['delay']<=0 and a['t']>=1.0)]
        animating_cards={a['card'] for a in anim_queue}
        landed=[]
        for a in discard_anims:
            if a['delay']>0: a['delay']-=dt; continue
            a['t']=min(a['t']+(dt/1000)*3.0,1.0)
            if a['t']>=1.0: landed.append(a['card'])
        for c in landed: discard_pile.append(c)
        discard_anims[:]=[a for a in discard_anims if not (a['delay']<=0 and a['t']>=1.0)]

        mx,my=pygame.mouse.get_pos()
        p_is_atk=(rules.attacker=='player'); o_is_atk=(rules.attacker=='opponent')

        # AI processing
        if vs_ai and ai_thinking and ai_result[0] is not None:
            ai_delay-=dt
            if ai_delay<=0:
                ai_thinking=False
                action=ai_result[0]; ai_result[0]=None
                a_type=action.get("action")

                if a_type=="choose_suit":
                    rules.resolve_wild(action.get("suit","clubs"))
                    trump_key=rules.trump_key
                elif a_type=="attack":
                    card=action.get("card"); slot=action.get("slot",0)
                    if card and 0<=slot<=5: rules.try_attack(card,slot)
                elif a_type=="defend":
                    atk=action.get("atk_card"); def_=action.get("def_card")
                    if atk and def_:
                        res=rules.try_defend(atk,def_)
                        if res=='ok_reverse':
                            reverse_flash="ROLES REVERSED!"; reverse_flash_timer=2000
                        elif res=='ok_wild':
                            # AI immediately picks suit via another AI call
                            pass  # handled by pending_wild check below
                        trump_key=rules.trump_key
                elif a_type=="take":
                    snap=[(i,slot) for i,slot in enumerate(rules.table) if slot is not None]
                    res=rules.try_take()
                    if res: _,atk_r,def_r=res; _queue_take_anims(snap,rules,anim_queue,L,atk_r,def_r)
                elif a_type=="end_attack":
                    snap=[(i,slot) for i,slot in enumerate(rules.table) if slot is not None]
                    res=rules.try_end_attack()
                    if res: cleared,atk_r,def_r=res; _queue_end_attack_anims(snap,rules,anim_queue,discard_anims,L,atk_r,def_r)

                # Trigger next AI move if needed
                if rules.phase!='game_over':
                    if rules.pending_wild:
                        ai_delay=400; start_ai(ask_wild=True)
                    elif (rules.phase=='attack' and rules.attacker=='opponent') or \
                         (rules.phase=='defense' and rules.defender=='opponent'):
                        ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()

        # Events
        for event in pygame.event.get():
            if event.type==pygame.QUIT: running=False

            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                sbg=make_bg(SCREEN_W,SCREEN_H)
                screen,result,ai_flag=run_main_menu(screen,sbg,fonts,return_on_play=True)
                bg=make_bg(SCREEN_W,SCREEN_H); rebuild_layout()
                if result=='new_game': return screen,bg,'new_game' if not ai_flag else 'new_ai'
                if result=='new_ai':   return screen,bg,'new_ai'
                if result=='resolution_changed': return screen,bg,'resolution_changed'

            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if rules.phase=='game_over':
                    return screen,bg,'new_ai' if vs_ai else 'new_game'
                if vs_ai and ai_thinking: continue
                is_player_turn=((rules.phase=='attack' and rules.attacker=='player') or
                                (rules.phase=='defense' and rules.defender=='player'))

                # END ATTACK
                if end_btn_rect.collidepoint(mx,my):
                    if vs_ai and not is_player_turn: continue
                    snap=[(i,s) for i,s in enumerate(rules.table) if s is not None]
                    res=rules.try_end_attack()
                    if res:
                        cleared,atk_r,def_r=res
                        _queue_end_attack_anims(snap,rules,anim_queue,discard_anims,L,atk_r,def_r)
                        if vs_ai and rules.attacker=='opponent':
                            ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()
                    continue

                # TAKE
                if take_btn_rect.collidepoint(mx,my):
                    if vs_ai and not is_player_turn: continue
                    snap=[(i,s) for i,s in enumerate(rules.table) if s is not None]
                    res=rules.try_take()
                    if res:
                        _,atk_r,def_r=res
                        _queue_take_anims(snap,rules,anim_queue,L,atk_r,def_r)
                        if vs_ai and rules.attacker=='opponent':
                            ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()
                    continue

                active_is_player=((rules.attacker=='player') if rules.phase=='attack' else (rules.defender=='player'))
                if vs_ai and not active_is_player: continue

                if not held_card:
                    # Taken pile pickup
                    for cond,taken,ax,ay in [
                        (rules.phase=='attack' and p_is_atk, rules.player_taken, p_taken_ax, p_taken_ay),
                        (rules.phase=='attack' and o_is_atk and not vs_ai, rules.opp_taken, o_taken_ax, o_taken_ay),
                        (rules.phase=='defense' and rules.defender=='player', rules.player_taken, p_taken_ax, p_taken_ay),
                        (rules.phase=='defense' and rules.defender=='opponent' and not vs_ai, rules.opp_taken, o_taken_ax, o_taken_ay),
                    ]:
                        if cond and taken:
                            for idx,card in enumerate(taken[-8:]):
                                rx=ax+idx*18; ry=ay
                                if pygame.Rect(rx,ry,60,90).collidepoint(mx,my):
                                    held_card=card; held_offset=(mx-rx,my-ry); held_from_taken=True; break
                        if held_card: break

                    if not held_card:
                        hand_to_use=rules.hand if active_is_player else rules.opp_hand
                        sy_base=hand_y if active_is_player else opp_y
                        legal=(rules.valid_attack_cards() if rules.phase=='attack' else rules.all_defense_cards())
                        for i,card in enumerate(hand_to_use):
                            if card not in legal: continue
                            sx=hand_x0+i*(CARD_W+spacing)
                            if pygame.Rect(sx,sy_base,CARD_W,CARD_H).collidepoint(mx,my):
                                held_card=card; held_offset=(mx-sx,my-sy_base); held_from_taken=False; break

            if event.type==pygame.MOUSEBUTTONUP and event.button==1:
                if held_card:
                    dropped=False
                    for i in range(n_slots):
                        slot_x=field_x0+i*(CARD_W+spacing)
                        if rules.phase=='attack':
                            hit_top=pygame.Rect(slot_x,atk_y,CARD_W,CARD_H).collidepoint(mx,my)
                            hit_bot=pygame.Rect(slot_x,def_y,CARD_W,CARD_H).collidepoint(mx,my)
                            if not (hit_top or hit_bot): continue
                            slot_index=i if hit_top else i+n_slots
                            dropped=rules.try_attack(held_card,slot_index)
                            if dropped and vs_ai and rules.defender=='opponent':
                                ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()
                        elif rules.phase=='defense':
                            hit_top=pygame.Rect(slot_x,atk_y,CARD_W,CARD_H).collidepoint(mx,my)
                            hit_bot=pygame.Rect(slot_x,def_y,CARD_W,CARD_H).collidepoint(mx,my)
                            if not (hit_top or hit_bot): continue
                            slot_index=i if hit_top else i+n_slots
                            target_atk=None
                            if rules.table[slot_index] is not None and rules.table[slot_index][1] is None:
                                target_atk=rules.table[slot_index][0]
                            else:
                                for slot in rules.table:
                                    if slot is not None and slot[1] is None: target_atk=slot[0]; break
                            if target_atk is not None:
                                res=rules.try_defend(target_atk,held_card)
                                dropped=bool(res)
                                if res=='ok_wild':
                                    new_suit=run_suit_picker(screen,fonts)
                                    rules.resolve_wild(new_suit); trump_key=rules.trump_key
                                    if vs_ai and rules.attacker=='opponent':
                                        ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()
                                elif res=='ok_reverse':
                                    reverse_flash="ROLES REVERSED!"; reverse_flash_timer=2000
                                    if vs_ai and rules.attacker=='opponent':
                                        ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()
                                elif dropped and vs_ai:
                                    if (rules.phase=='attack' and rules.attacker=='opponent') or \
                                       (rules.phase=='defense' and rules.defender=='opponent'):
                                        ai_delay=random.randint(AI_MIN,AI_MAX); start_ai()
                        if dropped: break
                    held_card=None; held_from_taken=False

        # ── DRAW ──────────────────────────────────────────────────────────────
        draw_game_table(screen,bg,fonts,tick,trump_key,vs_ai=vs_ai)

        # Discard
        PILE_X=60; PILE_Y=SCREEN_H//2-CARD_H//2-120
        if discard_pile or discard_anims:
            screen.blit(small_f.render("DISCARD",True,GOLD),(PILE_X+CARD_W//2-small_f.size("DISCARD")[0]//2,PILE_Y-24))
            for idx,card in enumerate(discard_pile[-6:]):
                off=idx*3; draw_card_image(screen,"back",PILE_X+off,PILE_Y-off)
            if len(discard_pile)>1:
                screen.blit(small_f.render(str(len(discard_pile)),True,CREAM),(PILE_X+CARD_W+4,PILE_Y+CARD_H//2-8))
        for a in discard_anims:
            if a['delay']>0: continue
            t=1-pow(1-min(a['t'],1.0),3); ax2=a['sx']+(PILE_X-a['sx'])*t; ay2=a['sy']+(PILE_Y-a['sy'])*t
            img=pygame.transform.scale(images["back"],(CARD_W,CARD_H))
            rot=pygame.transform.rotate(img,(1-t)*-25)
            screen.blit(rot,rot.get_rect(center=(int(ax2)+CARD_W//2,int(ay2)+CARD_H//2)))

        # Table
        for i,slot in enumerate(rules.table):
            if slot is None: continue
            atk_k,def_k=slot; row=i//n_slots; col=i%n_slots
            sx=field_x0+col*(CARD_W+spacing); cy2=atk_y if row==0 else def_y
            draw_card_image(screen,atk_k,sx,cy2)
            if def_k is not None: draw_card_image(screen,def_k,sx+14,cy2+14)

        # Player hand
        p_legal=set()
        if rules.phase=='attack' and rules.attacker=='player':    p_legal=rules.valid_attack_cards()
        elif rules.phase=='defense' and rules.defender=='player':  p_legal=rules.all_defense_cards()
        for i,card in enumerate(rules.hand):
            if card in animating_cards or (card==held_card and not held_from_taken): continue
            sx=hand_x0+i*(CARD_W+spacing); sy=hand_y; is_legal=card in p_legal
            if pygame.Rect(sx,sy,CARD_W,CARD_H).collidepoint(mx,my) and not held_card and is_legal:
                sy-=15
                glow=pygame.Surface((CARD_W+10,CARD_H+10),pygame.SRCALPHA)
                pygame.draw.rect(glow,(*GOLD,50),(0,0,CARD_W+10,CARD_H+10),border_radius=8)
                screen.blit(glow,(sx-5,sy-5))
            img=pygame.transform.scale(images[card],(CARD_W,CARD_H))
            img.set_alpha(255 if (is_legal or not p_legal) else 120)
            screen.blit(img,(sx,sy))

        # Opponent hand
        o_legal=set()
        if not vs_ai:
            if rules.phase=='attack' and rules.attacker=='opponent':   o_legal=rules.valid_attack_cards()
            elif rules.phase=='defense' and rules.defender=='opponent': o_legal=rules.all_defense_cards()
        for i,card in enumerate(rules.opp_hand):
            if card in animating_cards or (card==held_card and not held_from_taken): continue
            sx=hand_x0+i*(CARD_W+spacing); sy=opp_y
            if vs_ai:
                screen.blit(pygame.transform.scale(images["back"],(CARD_W,CARD_H)),(sx,sy))
            else:
                is_legal=card in o_legal
                if pygame.Rect(sx,sy,CARD_W,CARD_H).collidepoint(mx,my) and not held_card and is_legal:
                    sy+=15
                    glow=pygame.Surface((CARD_W+10,CARD_H+10),pygame.SRCALPHA)
                    pygame.draw.rect(glow,(*GOLD,50),(0,0,CARD_W+10,CARD_H+10),border_radius=8)
                    screen.blit(glow,(sx-5,sy-5))
                img=pygame.transform.scale(images[card],(CARD_W,CARD_H))
                img.set_alpha(255 if (is_legal or not o_legal) else 120)
                screen.blit(img,(sx,sy))

        # Taken piles
        p_can=((rules.attacker=='player' and rules.phase=='attack') or (rules.defender=='player' and rules.phase=='defense'))
        o_can=(not vs_ai and ((rules.attacker=='opponent' and rules.phase=='attack') or (rules.defender=='opponent' and rules.phase=='defense')))
        draw_taken_pile_panel(screen,rules.player_taken,"YOUR",p_taken_ax,p_taken_ay,small_f,mx,my,p_can)
        if vs_ai and rules.opp_taken:
            screen.blit(small_f.render(f"AI TAKEN ({len(rules.opp_taken)})",True,(160,100,60)),(o_taken_ax,o_taken_ay-22))
        else:
            draw_taken_pile_panel(screen,rules.opp_taken,"OPP",o_taken_ax,o_taken_ay,small_f,mx,my,o_can)

        # Animations
        for a in anim_queue:
            if a['delay']>0: continue
            t=1-pow(1-min(a['t'],1.0),3)
            ax2=a['sx']+(a['ex']-a['sx'])*t; ay2=a['sy']+(a['ey']-a['sy'])*t
            if a.get('to_taken',False):
                sc=1.0-t*0.5; w2,h2=int(CARD_W*sc),int(CARD_H*sc)
                img=pygame.transform.scale(images[a['card']],(w2,h2))
                rot=pygame.transform.rotate(img,(1-t)*20)
                screen.blit(rot,rot.get_rect(center=(int(ax2)+CARD_W//2,int(ay2)+CARD_H//2)))
            else:
                key=a['card']
                if vs_ai and a.get('ey',0)<SCREEN_H//3: key="back"
                img=pygame.transform.scale(images[key],(CARD_W,CARD_H))
                rot=pygame.transform.rotate(img,(1-t)*20)
                screen.blit(rot,rot.get_rect(center=(int(ax2)+CARD_W//2,int(ay2)+CARD_H//2)))

        # Held
        if held_card:
            big=pygame.transform.scale(images[held_card],(int(CARD_W*1.08),int(CARD_H*1.08)))
            screen.blit(big,(mx-held_offset[0]-5,my-held_offset[1]-5))

        # Status
        sf=pygame.font.SysFont("Palatino Linotype",20,italic=True)
        ss=sf.render(rules.status,True,GOLD)
        screen.blit(ss,(cx-ss.get_width()//2,SCREEN_H//2-14))

        if vs_ai and ai_thinking: draw_ai_thinking(screen)

        # End attack button
        all_beaten=(any(s is not None for s in rules.table) and all(s[1] is not None for s in rules.table if s is not None))
        can_end=rules.phase=='attack' and bool(rules.table) and all_beaten
        plr_can_end=can_end and (not vs_ai or rules.attacker=='player')
        if rules.phase!='game_over':
            hov=end_btn_rect.collidepoint(mx,my) and plr_can_end
            bc=GOLD_HOVER if hov else (GOLD if plr_can_end else (70,70,70))
            tc_=GOLD_HOVER if hov else (CREAM if plr_can_end else (80,80,80))
            pygame.draw.rect(screen,(50,40,5) if plr_can_end else (30,30,30),end_btn_rect,border_radius=8)
            pygame.draw.rect(screen,bc,end_btn_rect,2,border_radius=8)
            screen.blit(small_f.render("End Attack",True,tc_),small_f.render("End Attack",True,tc_).get_rect(center=end_btn_rect.center))

        # Take button
        can_take=rules.phase=='defense' and any(s is not None for s in rules.table)
        plr_can_take=can_take and (not vs_ai or rules.defender=='player')
        if rules.phase!='game_over':
            hov_t=take_btn_rect.collidepoint(mx,my) and plr_can_take
            tclr=GOLD_HOVER if hov_t else (RED_CARD if plr_can_take else (70,70,70))
            tbg=(60,10,10) if plr_can_take else (30,30,30)
            ttxt=CREAM if plr_can_take else (80,80,80)
            pygame.draw.rect(screen,tbg,take_btn_rect,border_radius=8)
            pygame.draw.rect(screen,tclr,take_btn_rect,2,border_radius=8)
            lbl=small_f.render("Take Cards",True,GOLD_HOVER if hov_t else ttxt)
            screen.blit(lbl,lbl.get_rect(center=take_btn_rect.center))

        # Reverse flash
        if reverse_flash:
            alpha=min(255,int(255*reverse_flash_timer/800)) if reverse_flash_timer<800 else 255
            rf_s=pygame.font.SysFont("Georgia",32,bold=True).render(reverse_flash,True,(255,160,40))
            rf_s.set_alpha(alpha); screen.blit(rf_s,(cx-rf_s.get_width()//2,SCREEN_H//2-60))

        # Role labels
        rf2=pygame.font.SysFont("Palatino Linotype",17,italic=True)
        pr=rf2.render("ATTACKER" if rules.attacker=='player' else "DEFENDER",True,GOLD if rules.attacker=='player' else CREAM)
        or_=rf2.render("ATTACKER" if rules.attacker=='opponent' else "DEFENDER",True,GOLD if rules.attacker=='opponent' else CREAM)
        screen.blit(pr,(MARGIN+10,hand_y+CARD_H//2-10))
        screen.blit(or_,(MARGIN+10,opp_y+CARD_H//2-10))

        # Game over
        if rules.phase=='game_over':
            ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,190)); screen.blit(ov,(0,0))
            pw,ph=700,220; panel=pygame.Surface((pw,ph),pygame.SRCALPHA)
            wc=(15,55,15,240) if rules.winner=='player' else (55,15,15,240) if rules.winner=='opponent' else (40,40,10,240)
            pygame.draw.rect(panel,wc,(0,0,pw,ph),border_radius=16)
            pygame.draw.rect(panel,GOLD,(0,0,pw,ph),2,border_radius=16)
            screen.blit(panel,(cx-pw//2,SCREEN_H//2-ph//2))
            gof=pygame.font.SysFont("Georgia",38,bold=True)
            tc2=(40,200,80) if rules.winner=='player' else (220,60,60) if rules.winner=='opponent' else GOLD
            msg=gof.render(rules.status,True,tc2)
            screen.blit(msg,(cx-msg.get_width()//2,SCREEN_H//2-ph//2+30))
            sub=small_f.render("Click anywhere to play again",True,CREAM)
            screen.blit(sub,(cx-sub.get_width()//2,SCREEN_H//2-ph//2+100))

        pygame.display.flip()

    return screen,bg,'menu'

# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption("Uno-urak")
    fonts=load_fonts(); bg=make_bg(SCREEN_W,SCREEN_H)
    vs_ai=False

    while True:
        screen,result,ai_flag=run_main_menu(screen,bg,fonts)
        if result=='resolution_changed':
            bg=make_bg(SCREEN_W,SCREEN_H); continue
        vs_ai=True; break

    all_keys,trump_key,rules=_new_game()
    while True:
        screen,bg,outcome=run_game(screen,bg,fonts,vs_ai,all_keys,trump_key,rules)
        if outcome=='resolution_changed':
            bg=make_bg(SCREEN_W,SCREEN_H); all_keys,trump_key,rules=_new_game()
        elif outcome in ('new_ai','new_game'):
            vs_ai=(outcome=='new_ai'); all_keys,trump_key,rules=_new_game()
        elif outcome=='menu':
            while True:
                screen,result,ai_flag=run_main_menu(screen,bg,fonts)
                if result=='resolution_changed': bg=make_bg(SCREEN_W,SCREEN_H); continue
                vs_ai=ai_flag; break
            all_keys,trump_key,rules=_new_game()

if __name__=="__main__":
    main()