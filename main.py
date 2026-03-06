import cv2
import numpy as np
import pyautogui
import threading
import time
import json
from datetime import datetime
from mss import mss
from PIL import Image
import pygetwindow as gw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import ctypes
import sys
from ctypes import wintypes
from collections import deque

import webview

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK_Q = 0x51
VK_E = 0x45
VK_Z = 0x5A
VK_C = 0x43
VK_V = 0x56
VK_OEM_3 = 0xC0

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
MK_LBUTTON = 0x0001

def MAKELPARAM(low, high):
    return (int(high) << 16) | (int(low) & 0xFFFF)

def is_vk_down(vk_code):
    try:
        return (ctypes.windll.user32.GetAsyncKeyState(int(vk_code)) & 0x8000) != 0
    except Exception:
        return False

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION)
    ]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]

def send_mouse_click(x, y):
    v_left = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    v_top = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    v_width = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    v_height = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    if v_width <= 1 or v_height <= 1:
        v_left = 0
        v_top = 0
        v_width = max(2, ctypes.windll.user32.GetSystemMetrics(0))
        v_height = max(2, ctypes.windll.user32.GetSystemMetrics(1))

    cx = int(x)
    cy = int(y)
    min_x = int(v_left)
    min_y = int(v_top)
    max_x = int(v_left + v_width - 1)
    max_y = int(v_top + v_height - 1)

    if cx < min_x:
        cx = min_x
    if cy < min_y:
        cy = min_y
    if cx > max_x:
        cx = max_x
    if cy > max_y:
        cy = max_y

    normalized_x = int((cx - v_left) * 65535 / max(1, (v_width - 1)))
    normalized_y = int((cy - v_top) * 65535 / max(1, (v_height - 1)))
    
    inputs = []
    
    move_input = INPUT()
    move_input.type = 0
    move_input.union.mi = MOUSEINPUT(
        normalized_x, normalized_y, 0, 
        MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 
        0, ctypes.pointer(wintypes.ULONG(0))
    )
    inputs.append(move_input)
    
    down_input = INPUT()
    down_input.type = 0
    down_input.union.mi = MOUSEINPUT(
        0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, ctypes.pointer(wintypes.ULONG(0))
    )
    inputs.append(down_input)

    ctypes.windll.user32.SendInput(len(inputs), (INPUT * len(inputs))(*inputs), ctypes.sizeof(INPUT))
    time.sleep(0.01)

    inputs = []
    
    up_input = INPUT()
    up_input.type = 0
    up_input.union.mi = MOUSEINPUT(
        0, 0, 0, MOUSEEVENTF_LEFTUP, 0, ctypes.pointer(wintypes.ULONG(0))
    )
    inputs.append(up_input)
    
    ctypes.windll.user32.SendInput(len(inputs), (INPUT * len(inputs))(*inputs), ctypes.sizeof(INPUT))

def send_key_press(vk_code, hold_time=0.0):
    scan = int(ctypes.windll.user32.MapVirtualKeyW(int(vk_code), 0)) & 0xFF

    down_input = INPUT()
    down_input.type = 1
    down_input.union.ki = KEYBDINPUT(
        0, scan, KEYEVENTF_SCANCODE, 0, ctypes.pointer(wintypes.ULONG(0))
    )
    ctypes.windll.user32.SendInput(1, ctypes.byref(down_input), ctypes.sizeof(INPUT))

    time.sleep(max(0.05, float(hold_time)))

    up_input = INPUT()
    up_input.type = 1
    up_input.union.ki = KEYBDINPUT(
        0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(wintypes.ULONG(0))
    )
    ctypes.windll.user32.SendInput(1, ctypes.byref(up_input), ctypes.sizeof(INPUT))

def postmessage_click(hwnd, x, y):
    if not hwnd:
        return False
    try:
        screen_x = int(x)
        screen_y = int(y)

        ctypes.windll.user32.SetCursorPos(screen_x, screen_y)
        time.sleep(0.01)

        pt = POINT(screen_x, screen_y)
        ctypes.windll.user32.ScreenToClient(int(hwnd), ctypes.byref(pt))
        client_x = int(pt.x)
        client_y = int(pt.y)

        lparam = MAKELPARAM(client_x, client_y)
        ctypes.windll.user32.PostMessageW(int(hwnd), WM_MOUSEMOVE, 0, lparam)
        time.sleep(0.005)
        ctypes.windll.user32.PostMessageW(int(hwnd), WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        time.sleep(0.01)
        ctypes.windll.user32.PostMessageW(int(hwnd), WM_LBUTTONUP, 0, lparam)
        return True
    except Exception:
        return False

def postmessage_key(hwnd, vk_code, hold_time=0.0):
    if not hwnd:
        return False
    try:
        vk = int(vk_code)
        scan = int(ctypes.windll.user32.MapVirtualKeyW(vk, 0)) & 0xFF

        lparam_down = 1 | (scan << 16)
        lparam_up = 1 | (scan << 16) | (1 << 30) | (1 << 31)

        ctypes.windll.user32.PostMessageW(int(hwnd), WM_KEYDOWN, vk, lparam_down)
        time.sleep(max(0.02, float(hold_time)))
        ctypes.windll.user32.PostMessageW(int(hwnd), WM_KEYUP, vk, lparam_up)
        return True
    except Exception:
        return False

def pyautogui_click(x, y):
    try:
        pyautogui.click(int(x), int(y))
        return True
    except Exception:
        return False

def pyautogui_key(key_char, hold_time=0.0):
    try:
        if hold_time > 0:
            pyautogui.keyDown(key_char)
            time.sleep(hold_time)
            pyautogui.keyUp(key_char)
        else:
            pyautogui.press(key_char)
        return True
    except Exception:
        return False

METIN_PRESETS = {
    "golge": {"name": "Gölge Metini", "color": "#253e4b"},
}

class Metin2Bot:
    def __init__(self):
        self.running = False
        self.threshold = 0.8
        self.scan_delay = 30000
        self.click_delay = 30000
        self.templates = []
        self.screen_region = None
        self.attack_count = 0
        self.rotation_counter = 0
        self.monitor_index = 1
        self.window_title = None
        self.detection_mode = "template"
        self.color_hex = "#ffffff"
        self.color_tolerance = 20
        self.input_method = "sendinput"
        self.camera_wait = 0
        self.metin_preset = "golge"

        self.auto_loot_mode = "passive"
        self.auto_loot_interval = 6000
        self._loot_stop_event = threading.Event()
        self._loot_thread = None
        
        self.captcha_enabled = False
        self.captcha_check_interval = 300.0
        self.last_captcha_check = 0
        self._captcha_button_pos = None
        user_dir = os.environ.get("USERPROFILE") or os.path.dirname(os.path.abspath(__file__))
        self.captcha_debug_folder = os.path.join(user_dir, "captchaKontrol")

    def _sleep_interruptible(self, seconds, step=0.05):
        try:
            remaining = float(seconds)
        except Exception:
            return

        if remaining <= 0:
            return

        step = max(0.01, float(step))
        while self.running and remaining > 0:
            dt = min(step, remaining)
            time.sleep(dt)
            remaining -= dt

    def _loot_loop(self, status_callback):
        next_press = time.time() + (max(0, int(self.auto_loot_interval)) / 1000.0)
        while self.running and not self._loot_stop_event.is_set():
            try:
                if (self.auto_loot_mode or "passive") != "active":
                    time.sleep(0.2)
                    continue

                now = time.time()
                if now >= next_press:
                    if self.window_title:
                        self.update_window_region(activate=True)
                    send_key_press(VK_OEM_3, 0.05)
                    if callable(status_callback):
                        status_callback("Oto toplama: \" tuşu basıldı")
                    next_press = now + (max(0, int(self.auto_loot_interval)) / 1000.0)
                else:
                    time.sleep(min(0.2, max(0.01, next_press - now)))
            except Exception:
                time.sleep(0.2)

    def set_screen_monitor(self, monitor_index):
        try:
            idx = int(monitor_index)
        except Exception:
            idx = 1

        if idx < 1:
            idx = 1

        self.monitor_index = idx
        self.window_title = None
        self.screen_region = None
        return True

    def set_detection_mode(self, mode):
        value = (mode or "template").strip().lower()
        if value not in {"template", "color", "metin_preset"}:
            value = "template"
        self.detection_mode = value
        return True
    
    def set_metin_preset(self, preset_key):
        if preset_key in METIN_PRESETS:
            self.metin_preset = preset_key
            self.color_hex = METIN_PRESETS[preset_key]["color"]
            return True
        return False

    def set_color_target(self, hex_color, tolerance):
        self.color_hex = (hex_color or "").strip()
        try:
            self.color_tolerance = int(tolerance)
        except Exception:
            self.color_tolerance = 20

        if self.color_tolerance < 0:
            self.color_tolerance = 0
        if self.color_tolerance > 80:
            self.color_tolerance = 80
        return self._parse_hex_color(self.color_hex) is not None

    def _parse_hex_color(self, hex_color):
        s = (hex_color or "").strip().lstrip("#")
        if len(s) == 3:
            s = "".join([c * 2 for c in s])
        if len(s) != 6:
            return None
        try:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            return (b, g, r)
        except Exception:
            return None

    def set_target_window(self, window_title):
        title = (window_title or "").strip()
        if not title:
            self.window_title = None
            self.screen_region = None
            return False

        self.window_title = title
        return self.update_window_region(activate=True)

    def _get_window(self):
        if not self.window_title:
            return None
        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            return None
        return windows[0]

    def update_window_region(self, activate=False):
        win = self._get_window()
        if win is None:
            self.screen_region = None
            return False

        try:
            if getattr(win, "isMinimized", False):
                try:
                    win.restore()
                    time.sleep(0.1)
                except Exception:
                    pass

            if activate:
                try:
                    win.activate()
                    time.sleep(0.05)
                except Exception:
                    pass

                try:
                    hwnd = int(getattr(win, "_hWnd", 0))
                    if hwnd:
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        time.sleep(0.02)
                except Exception:
                    pass

            hwnd = 0
            try:
                hwnd = int(getattr(win, "_hWnd", 0))
            except Exception:
                hwnd = 0

            if hwnd:
                rect = RECT()
                if ctypes.windll.user32.GetClientRect(int(hwnd), ctypes.byref(rect)):
                    pt = POINT(0, 0)
                    ctypes.windll.user32.ClientToScreen(int(hwnd), ctypes.byref(pt))
                    left = int(pt.x)
                    top = int(pt.y)
                    width = int(rect.right - rect.left)
                    height = int(rect.bottom - rect.top)
                else:
                    left = int(getattr(win, "left", 0))
                    top = int(getattr(win, "top", 0))
                    width = int(getattr(win, "width", 0))
                    height = int(getattr(win, "height", 0))
            else:
                left = int(getattr(win, "left", 0))
                top = int(getattr(win, "top", 0))
                width = int(getattr(win, "width", 0))
                height = int(getattr(win, "height", 0))
            if width <= 0 or height <= 0:
                self.screen_region = None
                return False

            right = left + width
            bottom = top + height

            with mss() as sct:
                virtual = sct.monitors[0]
                v_left = int(virtual["left"])
                v_top = int(virtual["top"])
                v_right = v_left + int(virtual["width"])
                v_bottom = v_top + int(virtual["height"])

            c_left = max(v_left, left)
            c_top = max(v_top, top)
            c_right = min(v_right, right)
            c_bottom = min(v_bottom, bottom)

            c_width = c_right - c_left
            c_height = c_bottom - c_top
            if c_width <= 0 or c_height <= 0:
                self.screen_region = None
                return False

            self.screen_region = {
                "left": c_left,
                "top": c_top,
                "width": c_width,
                "height": c_height,
            }
            return True
        except Exception:
            self.screen_region = None
            return False
        
    def grab_screen(self):
        with mss() as sct:
            if self.screen_region:
                monitor = self.screen_region
            else:
                monitor = sct.monitors[self.monitor_index]
            
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    def detect_target(self, screen):
        det_mode = (self.detection_mode or "template")
        if det_mode == "color" or det_mode == "metin_preset":
            return self.detect_target_color(screen)
        return self.detect_target_template(screen)

    def _allowed_rois(self, frame_width, frame_height):
        w = int(frame_width)
        h = int(frame_height)
        if w <= 0 or h <= 0:
            return [(0, 0, 0, 0)]

        top = 40
        bottom = h - 40
        if bottom <= top:
            return [(0, 0, 0, 0)]

        cx = w / 2
        cy = h / 2
        half = 50

        x1 = int(max(0, cx - half))
        x2 = int(min(w, cx + half))
        y1 = int(max(top, cy - half))
        y2 = int(min(bottom, cy + half))

        rois = []

        if y1 > top:
            rois.append((0, top, w, y1))

        if y2 < bottom:
            rois.append((0, y2, w, bottom))

        mid_y1 = y1
        mid_y2 = y2
        if mid_y2 > mid_y1:
            if x1 > 0:
                rois.append((0, mid_y1, x1, mid_y2))
            if x2 < w:
                rois.append((x2, mid_y1, w, mid_y2))

        rois = [(rx1, ry1, rx2, ry2) for (rx1, ry1, rx2, ry2) in rois if rx2 - rx1 > 0 and ry2 - ry1 > 0]
        if not rois:
            return [(0, 0, 0, 0)]
        return rois

    def _zero_forbidden_in_mask(self, mask):
        if mask is None:
            return mask
        h, w = mask.shape[:2]
        if h <= 0 or w <= 0:
            return mask

        top = 40
        bottom = h - 40
        if top > 0 and top < h:
            mask[0:top, :] = 0
        if bottom >= 0 and bottom < h:
            mask[bottom:h, :] = 0

        cx = int(w / 2)
        cy = int(h / 2)
        half = 50
        x1 = max(0, cx - half)
        x2 = min(w, cx + half)
        y1 = max(0, cy - half)
        y2 = min(h, cy + half)
        mask[y1:y2, x1:x2] = 0

        return mask
    
    def _is_in_forbidden_zone(self, local_x, local_y, frame_width, frame_height):
        if frame_width <= 0 or frame_height <= 0:
            return False

        if local_y < 40 or local_y >= (frame_height - 40):
            return True

        center_x = frame_width / 2
        center_y = frame_height / 2
        if abs(local_x - center_x) <= 50 and abs(local_y - center_y) <= 50:
            return True

        return False

    def detect_target_template(self, screen):
        best_match = None
        best_val = 0
        best_template = None

        frame_h, frame_w = screen.shape[:2]
        rois = self._allowed_rois(frame_w, frame_h)

        for template_path in self.templates:
            if not os.path.exists(template_path):
                continue

            template = cv2.imread(template_path)
            if template is None:
                continue

            th, tw = template.shape[:2]
            if th <= 0 or tw <= 0:
                continue

            for (x1, y1, x2, y2) in rois:
                roi_w = x2 - x1
                roi_h = y2 - y1
                if roi_w < tw or roi_h < th:
                    continue

                roi = screen[y1:y2, x1:x2]
                result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                if max_val > self.threshold and max_val > best_val:
                    best_val = max_val
                    best_match = (int(max_loc[0] + x1), int(max_loc[1] + y1))
                    best_template = template

        if best_match and best_template is not None:
            th, tw = best_template.shape[:2]
            center_x = int(best_match[0] + tw // 2)
            center_y = int(best_match[1] + th // 2)

            if self.screen_region:
                center_x += self.screen_region['left']
                center_y += self.screen_region['top']

            return (center_x, center_y), best_val

        return None, 0

    def detect_target_color(self, screen):
        bgr = self._parse_hex_color(self.color_hex)
        if bgr is None:
            return None, 0

        hsv_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
        target_hsv = cv2.cvtColor(np.uint8([[list(bgr)]]), cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = int(target_hsv[0]), int(target_hsv[1]), int(target_hsv[2])

        tol = int(self.color_tolerance)
        h_tol = max(0, min(80, tol))
        sv_tol = max(0, min(255, tol * 3))

        lower_sv = np.array([0, max(0, s - sv_tol), max(0, v - sv_tol)], dtype=np.uint8)
        upper_sv = np.array([179, min(255, s + sv_tol), min(255, v + sv_tol)], dtype=np.uint8)

        h_low = h - h_tol
        h_high = h + h_tol

        if h_low < 0:
            lower1 = np.array([0, lower_sv[1], lower_sv[2]], dtype=np.uint8)
            upper1 = np.array([h_high, upper_sv[1], upper_sv[2]], dtype=np.uint8)
            lower2 = np.array([179 + h_low, lower_sv[1], lower_sv[2]], dtype=np.uint8)
            upper2 = np.array([179, upper_sv[1], upper_sv[2]], dtype=np.uint8)
            mask = cv2.inRange(hsv_screen, lower1, upper1) | cv2.inRange(hsv_screen, lower2, upper2)
        elif h_high > 179:
            lower1 = np.array([h_low, lower_sv[1], lower_sv[2]], dtype=np.uint8)
            upper1 = np.array([179, upper_sv[1], upper_sv[2]], dtype=np.uint8)
            lower2 = np.array([0, lower_sv[1], lower_sv[2]], dtype=np.uint8)
            upper2 = np.array([h_high - 179, upper_sv[1], upper_sv[2]], dtype=np.uint8)
            mask = cv2.inRange(hsv_screen, lower1, upper1) | cv2.inRange(hsv_screen, lower2, upper2)
        else:
            lower = np.array([h_low, lower_sv[1], lower_sv[2]], dtype=np.uint8)
            upper = np.array([h_high, upper_sv[1], upper_sv[2]], dtype=np.uint8)
            mask = cv2.inRange(hsv_screen, lower, upper)

        mask = self._zero_forbidden_in_mask(mask)

        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, 0

        best = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(best))
        if area < 60:
            return None, 0

        m = cv2.moments(best)
        if m.get("m00", 0) == 0:
            return None, 0
        cx = int(m["m10"] / m["m00"])
        cy = int(m["m01"] / m["m00"])

        frame_h, frame_w = screen.shape[:2]
        if self._is_in_forbidden_zone(cx, cy, frame_w, frame_h):
            return None, 0

        if self.screen_region:
            cx += self.screen_region["left"]
            cy += self.screen_region["top"]

        screen_area = float(screen.shape[0] * screen.shape[1]) if screen.size else 1.0
        score = min(1.0, area / max(1.0, screen_area))
        return (cx, cy), score
    
    def move_and_attack(self, position):
        if self.window_title:
            self.update_window_region(activate=True)
        x, y = position

        if self.screen_region and isinstance(self.screen_region, dict):
            left = int(self.screen_region.get("left", 0))
            top = int(self.screen_region.get("top", 0))
            width = int(self.screen_region.get("width", 0))
            height = int(self.screen_region.get("height", 0))
            local_x = int(x) - left
            local_y = int(y) - top
            if self._is_in_forbidden_zone(local_x, local_y, width, height):
                return
        
        method = (self.input_method or "sendinput").lower()
        
        if method == "postmessage":
            win = self._get_window()
            hwnd = int(getattr(win, "_hWnd", 0)) if win else 0
            if hwnd:
                postmessage_click(hwnd, x, y)
                time.sleep(0.005)
                postmessage_click(hwnd, x, y)
                self.attack_count += 1
            else:
                send_mouse_click(x, y)
                time.sleep(0.005)
                send_mouse_click(x, y)
                self.attack_count += 1
        elif method == "pyautogui":
            pyautogui_click(x, y)
            time.sleep(0.005)
            pyautogui_click(x, y)
            self.attack_count += 1
        else:
            send_mouse_click(x, y)
            time.sleep(0.005)
            send_mouse_click(x, y)
            self.attack_count += 1
    
    def rotate_camera(self):
        if self.window_title:
            self.update_window_region(activate=True)

        hold_duration = 0.3
        vk_code = VK_E
        send_key_press(vk_code, hold_duration)
        
        self.rotation_counter += 1
    
    def run_bot(self, status_callback):
        self.running = True
        
        status_callback("🚀 Bot başladı")

        if self.window_title:
            if not self.update_window_region(activate=True):
                status_callback("❌ Seçili pencere bulunamadı. Bot durduruldu")
                self.running = False
                return

        self._loot_stop_event.clear()
        if (self.auto_loot_mode or "passive") == "active":
            status_callback(
                f"Oto toplama aktif: {max(0.01, min(0.5, self.auto_loot_interval / 60000.0)):.2f} dk"
            )
            self._loot_thread = threading.Thread(target=self._loot_loop, args=(status_callback,), daemon=True)
            self._loot_thread.start()
        
        if self.captcha_enabled:
            self.last_captcha_check = 0
            status_callback(f"🛡️ Bot Kontrol aktif: İlk kontrol hemen yapılacak, sonra {int(self.captcha_check_interval / 60)} dk aralık")
        
        while self.running:
            try:
                if self.window_title:
                    if not self.update_window_region(activate=False):
                        status_callback("⚠️ Pencere yok/minimized. Tekrar deneniyor...")
                        self._sleep_interruptible(0.5)
                        continue
                
                screen = self.grab_screen()
                
                if self.captcha_enabled:
                    current_time = time.time()
                    if current_time - self.last_captcha_check >= self.captcha_check_interval:
                        captcha_pos = self.detect_captcha(screen)
                        if captcha_pos:
                            status_callback("🧩 Bot Kontrol tespit edildi! Çözülüyor...")
                            if self.handle_captcha(captcha_pos, status_callback):
                                status_callback("✅ Bot Kontrol çözüldü, devam ediliyor")
                            else:
                                status_callback("⚠️ Bot Kontrol çözülemedi, devam ediliyor")
                        self.last_captcha_check = time.time()
                        continue
                
                target_pos, confidence = self.detect_target(screen)
                
                if target_pos:
                    status_callback(f"🎯 Hedef bulundu! ({confidence:.2f}) - Saldırı: {self.attack_count}")
                    self.move_and_attack(target_pos)
                    self._sleep_interruptible(max(0, int(self.click_delay)) / 1000.0)
                else:
                    status_callback("❌ Hedef bulunamadı. Kamera dönüyor... (E tuşu 0.3s)")
                    self.rotate_camera()
                    camera_wait_sec = max(0, int(self.camera_wait)) / 1000.0
                    if camera_wait_sec > 0:
                        self._sleep_interruptible(camera_wait_sec)
                    status_callback("🔍 Tekrar taranıyor...")
                    self._sleep_interruptible(0.05)
                    
            except Exception as e:
                status_callback(f"❌ Hata: {str(e)}")
                self._sleep_interruptible(1)
        
        status_callback("⏸️ Bot durduruldu")
    
    def detect_captcha(self, screen):
        try:
            h, w = screen.shape[:2]

            panel_x = panel_y = panel_w = panel_h = None
            grid_x = grid_y = grid_w = grid_h = None

            captcha_panel = self._detect_captcha_panel(screen)
            if captcha_panel is not None:
                panel_x, panel_y, panel_w, panel_h = captcha_panel
                panel_img = screen[panel_y:panel_y + panel_h, panel_x:panel_x + panel_w]
                grid_detection = self._detect_3x3_grid_in_panel(panel_img)
                if grid_detection is not None:
                    grid_x, grid_y, grid_w, grid_h = grid_detection
                else:
                    panel_x = panel_y = panel_w = panel_h = None

            if panel_x is None:
                grid_abs = self._detect_3x3_grid_on_screen(screen)
                if grid_abs is None:
                    return None

                abs_gx, abs_gy, abs_gw, abs_gh = grid_abs
                panel_x, panel_y, panel_w, panel_h = self._derive_panel_from_grid(w, h, grid_abs)
                panel_img = screen[panel_y:panel_y + panel_h, panel_x:panel_x + panel_w]

                grid_detection = self._detect_3x3_grid_in_panel(panel_img)
                if grid_detection is not None:
                    grid_x, grid_y, grid_w, grid_h = grid_detection
                else:
                    grid_x = max(0, abs_gx - panel_x)
                    grid_y = max(0, abs_gy - panel_y)
                    grid_w = abs_gw
                    grid_h = abs_gh
            
            grid_img = panel_img[grid_y:grid_y+grid_h, grid_x:grid_x+grid_w]
            
            cell_w = grid_w // 3
            cell_h = grid_h // 3
            
            cells = []
            for row in range(3):
                for col in range(3):
                    x1 = col * cell_w
                    y1 = row * cell_h
                    x2 = x1 + cell_w
                    y2 = y1 + cell_h
                    cell = grid_img[y1:y2, x1:x2]
                    cells.append((cell, row, col))
            
            odd_index = self._find_odd_cell(cells)
            if odd_index is None:
                return None
            
            odd_row = odd_index // 3
            odd_col = odd_index % 3
            
            cell_center_x = panel_x + grid_x + (odd_col * cell_w) + (cell_w // 2)
            cell_center_y = panel_y + grid_y + (odd_row * cell_h) + (cell_h // 2)
            
            abs_grid_x = panel_x + grid_x
            abs_grid_y = panel_y + grid_y
            abs_grid_bottom = abs_grid_y + grid_h
            
            confirm_btn = self._find_confirm_button_on_screen(screen, abs_grid_bottom)
            if confirm_btn:
                self._captcha_button_pos = confirm_btn
            else:
                abs_grid_center_x = abs_grid_x + (grid_w // 2)
                btn_offset = int(grid_h * 0.55)
                self._captcha_button_pos = (abs_grid_center_x, abs_grid_bottom + btn_offset)
            
            self._save_captcha_debug(screen, panel_x, panel_y, panel_w, panel_h, 
                                    grid_x, grid_y, grid_w, grid_h,
                                    cell_center_x, cell_center_y, 
                                    self._captcha_button_pos)
            
            return (cell_center_x, cell_center_y)
            
        except Exception:
            return None

    def _detect_3x3_grid_on_screen(self, screen):
        try:
            gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            h, w = screen.shape[:2]
            min_size = int(min(w, h) * 0.10)
            max_size = int(min(w, h) * 0.55)

            best = None
            best_score = 0.0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area <= 0:
                    continue

                x, y, cw, ch = cv2.boundingRect(cnt)
                if cw < min_size or ch < min_size or cw > max_size or ch > max_size:
                    continue

                aspect = float(cw) / float(ch) if ch > 0 else 0
                if not (0.85 < aspect < 1.15):
                    continue

                cx = x + cw / 2.0
                cy = y + ch / 2.0
                center_bonus = 1.0 - min(1.0, abs((cx / w) - 0.5))
                score = float(area) * (1.0 - abs(aspect - 1.0)) * (0.6 + 0.4 * center_bonus)
                if score > best_score:
                    best_score = score
                    best = (x, y, cw, ch)

            return best
        except Exception:
            return None

    def _derive_panel_from_grid(self, screen_w, screen_h, grid_abs):
        gx, gy, gw, gh = grid_abs

        side_pad = int(gw * 0.10)
        top_pad = int(gh * 0.45)
        bottom_pad = int(gh * 1.15)

        px = max(0, gx - side_pad)
        py = max(0, gy - top_pad)
        pr = min(int(screen_w), gx + gw + side_pad)
        pb = min(int(screen_h), gy + gh + bottom_pad)

        pw = max(1, pr - px)
        ph = max(1, pb - py)
        return (px, py, pw, ph)
    
    def _detect_captcha_panel(self, screen):
        try:
            h, w = screen.shape[:2]
            hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
            
            lower_pink = np.array([140, 50, 100])
            upper_pink = np.array([170, 255, 255])
            mask = cv2.inRange(hsv, lower_pink, upper_pink)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            min_area = (w * h) * 0.03
            max_area = (w * h) * 0.4
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area or area > max_area:
                    continue
                
                x, y, cw, ch = cv2.boundingRect(cnt)
                
                if cw > 150 and ch > 200:
                    margin = max(15, int(min(cw, ch) * 0.05))
                    x = max(0, x - margin)
                    y = max(0, y - margin)
                    cw = min(w - x, cw + margin * 2)
                    ch = min(h - y, ch + margin * 2)

                    extra_side = int(cw * 0.1)
                    extra_top = int(ch * 0.25)
                    extra_bottom = int(ch * 0.8)

                    x = max(0, x - extra_side)
                    y = max(0, y - extra_top)
                    cw = min(w - x, cw + extra_side * 2)
                    ch = min(h - y, ch + extra_top + extra_bottom)

                    return (x, y, cw, ch)
            
            return None
        except Exception:
            return None
    
    def _detect_3x3_grid_in_panel(self, panel_img):
        try:
            gray = cv2.cvtColor(panel_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            h, w = panel_img.shape[:2]
            min_size = min(w, h) * 0.4
            max_size = min(w, h) * 0.95
            
            best_candidate = None
            best_score = 0
            
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_size * min_size or area > max_size * max_size:
                    continue
                
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = float(cw) / float(ch) if ch > 0 else 0
                
                if 0.85 < aspect < 1.15:
                    cy_ratio = (y + ch / 2) / h
                    if 0.3 < cy_ratio < 0.7:
                        score = area * (1.0 - abs(aspect - 1.0))
                        if score > best_score:
                            best_score = score
                            best_candidate = (x, y, cw, ch)
            
            return best_candidate
        except Exception:
            return None
    
    def _find_confirm_button_on_screen(self, screen, grid_bottom_y):
        try:
            h, w = screen.shape[:2]
            
            search_y_start = grid_bottom_y
            search_y_end = min(h, grid_bottom_y + 200)
            search_x_start = int(w * 0.25)
            search_x_end = int(w * 0.75)
            
            if search_y_start >= search_y_end:
                return None
            
            button_region = screen[search_y_start:search_y_end, search_x_start:search_x_end]
            
            gray = cv2.cvtColor(button_region, cv2.COLOR_BGR2GRAY)
            
            _, thresh = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            button_candidates = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 1500 or area > 30000:
                    continue
                
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = float(cw) / float(ch) if ch > 0 else 0
                
                if 2.0 < aspect < 8.0 and cw > 70 and ch > 18 and ch < 50:
                    cx = search_x_start + x + cw // 2
                    cy = search_y_start + y + ch // 2
                    
                    center_dist = abs((cx / w) - 0.5)
                    score = area * (1.0 - center_dist)
                    button_candidates.append((cx, cy, score, cw, ch))
            
            if button_candidates:
                button_candidates.sort(key=lambda x: x[2], reverse=True)
                return (button_candidates[0][0], button_candidates[0][1])
            
            return None
            
        except Exception:
            return None
    
    def _find_confirm_button(self, panel_img):
        try:
            h, w = panel_img.shape[:2]
            
            search_y_start = int(h * 0.75)
            search_y_end = h - 10
            
            button_region = panel_img[search_y_start:search_y_end, :]
            
            gray = cv2.cvtColor(button_region, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 30, 100)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            button_candidates = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 500:
                    continue
                
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = float(cw) / float(ch) if ch > 0 else 0
                
                if 1.5 < aspect < 6.0 and cw > 60 and ch > 15:
                    cx = x + cw // 2
                    cy = y + ch // 2
                    center_score = 1.0 - abs((cx / w) - 0.5)
                    button_candidates.append((cx, search_y_start + cy, center_score))
            
            if button_candidates:
                button_candidates.sort(key=lambda x: x[2], reverse=True)
                return (button_candidates[0][0], button_candidates[0][1])
            
            button_x = w // 2
            button_y = search_y_start + 30
            return (button_x, button_y)
            
        except Exception:
            return None
    
    def _find_odd_cell(self, cells):
        try:
            if len(cells) != 9:
                return None
            
            histograms = []
            for cell, _, _ in cells:
                if cell.size == 0:
                    histograms.append(None)
                    continue
                
                hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                histograms.append(hist)
            
            similarity_scores = []
            for i in range(9):
                if histograms[i] is None:
                    similarity_scores.append(0)
                    continue
                
                total_similarity = 0
                count = 0
                for j in range(9):
                    if i != j and histograms[j] is not None:
                        similarity = cv2.compareHist(histograms[i], histograms[j], cv2.HISTCMP_CORREL)
                        total_similarity += similarity
                        count += 1
                
                avg_similarity = total_similarity / count if count > 0 else 0
                similarity_scores.append(avg_similarity)
            
            if not similarity_scores:
                return None
            
            min_score_idx = similarity_scores.index(min(similarity_scores))
            return min_score_idx
            
        except Exception:
            return None
    
    def _human_like_move(self, target_x, target_y):
        import random
        try:
            ctypes.windll.user32.SetCursorPos(int(target_x), int(target_y))
            time.sleep(random.uniform(0.05, 0.1))
            
            for _ in range(random.randint(3, 6)):
                offset_x = random.randint(-8, 8)
                offset_y = random.randint(-5, 5)
                new_x = int(target_x + offset_x)
                new_y = int(target_y + offset_y)
                ctypes.windll.user32.SetCursorPos(new_x, new_y)
                time.sleep(random.uniform(0.02, 0.06))
            
            final_x = int(target_x + random.randint(5, 15))
            final_y = int(target_y + random.randint(-3, 3))
            ctypes.windll.user32.SetCursorPos(final_x, final_y)
            time.sleep(random.uniform(0.08, 0.15))
            
            return (final_x, final_y)
            
        except Exception:
            return (int(target_x), int(target_y))
    
    def _click_at_cursor(self):
        try:
            down = INPUT()
            down.type = 0
            down.union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, ctypes.pointer(wintypes.ULONG(0)))
            ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
            time.sleep(0.01)
            
            up = INPUT()
            up.type = 0
            up.union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, ctypes.pointer(wintypes.ULONG(0)))
            ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
        except Exception:
            pass
    
    def handle_captcha(self, captcha_pos, status_callback):
        try:
            if self.screen_region:
                screen_x = self.screen_region["left"] + captcha_pos[0]
                screen_y = self.screen_region["top"] + captcha_pos[1]
            else:
                with mss() as sct:
                    mon = sct.monitors[self.monitor_index]
                    screen_x = mon["left"] + captcha_pos[0]
                    screen_y = mon["top"] + captcha_pos[1]
            
            if self.input_method == "postmessage" and self.window_title:
                win = self._get_window()
                if win:
                    hwnd = getattr(win, "_hWnd", 0)
                    if hwnd:
                        postmessage_click(hwnd, screen_x, screen_y)
                    else:
                        send_mouse_click(screen_x, screen_y)
                else:
                    send_mouse_click(screen_x, screen_y)
            elif self.input_method == "pyautogui":
                pyautogui_click(screen_x, screen_y)
            else:
                send_mouse_click(screen_x, screen_y)
            
            status_callback(f"🧩 CAPTCHA: Bozuk kare tıklandı (x:{captcha_pos[0]}, y:{captcha_pos[1]})")
            time.sleep(0.8)
            
            if self._captcha_button_pos:
                btn_x_rel, btn_y_rel = self._captcha_button_pos
                status_callback(f"🔘 CAPTCHA: Onayla butonu bulundu (x:{btn_x_rel}, y:{btn_y_rel})")
                
                if self.screen_region:
                    btn_x = self.screen_region["left"] + btn_x_rel
                    btn_y = self.screen_region["top"] + btn_y_rel
                else:
                    with mss() as sct:
                        mon = sct.monitors[self.monitor_index]
                        btn_x = mon["left"] + btn_x_rel
                        btn_y = mon["top"] + btn_y_rel
            else:
                status_callback("⚠️ CAPTCHA: Onayla butonu bulunamadı")
                return False
            
            final_click_x, final_click_y = self._human_like_move(btn_x, btn_y)
            
            if self.input_method == "postmessage" and self.window_title:
                win = self._get_window()
                if win:
                    hwnd = getattr(win, "_hWnd", 0)
                    if hwnd:
                        postmessage_click(hwnd, final_click_x, final_click_y)
                    else:
                        self._click_at_cursor()
                else:
                    self._click_at_cursor()
            elif self.input_method == "pyautogui":
                pyautogui.click()
            else:
                self._click_at_cursor()
            
            status_callback(f"✅ CAPTCHA: Onayla tıklandı (x:{final_click_x}, y:{final_click_y})")
            time.sleep(1.0)
            
            return True
        except Exception as e:
            status_callback(f"❌ CAPTCHA hata: {str(e)}")
            return False
    
    def _save_captcha_debug(self, screen, panel_x, panel_y, panel_w, panel_h,
                           grid_x, grid_y, grid_w, grid_h,
                           cell_x, cell_y, button_pos):
        try:
            debug_folder = getattr(self, "captcha_debug_folder", os.path.join(os.getcwd(), "captchaKontrol"))
            os.makedirs(debug_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            debug_img = screen.copy()
            
            cv2.rectangle(debug_img, (panel_x, panel_y), 
                         (panel_x + panel_w, panel_y + panel_h), (255, 0, 255), 3)
            cv2.putText(debug_img, "PANEL", (panel_x + 5, panel_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            
            abs_grid_x = panel_x + grid_x
            abs_grid_y = panel_y + grid_y
            cv2.rectangle(debug_img, (abs_grid_x, abs_grid_y),
                         (abs_grid_x + grid_w, abs_grid_y + grid_h), (0, 255, 0), 2)
            cv2.putText(debug_img, "GRID", (abs_grid_x + 5, abs_grid_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.circle(debug_img, (cell_x, cell_y), 15, (0, 0, 255), 3)
            cv2.putText(debug_img, f"BOZUK ({cell_x},{cell_y})", 
                       (cell_x - 60, cell_y - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            if button_pos:
                btn_x, btn_y = button_pos
                cv2.circle(debug_img, (btn_x, btn_y), 15, (255, 255, 0), 3)
                cv2.putText(debug_img, f"ONAYLA ({btn_x},{btn_y})", 
                           (btn_x - 60, btn_y + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            debug_rgb = cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB)
            filename = os.path.join(debug_folder, f"captcha_{timestamp}.png")
            Image.fromarray(debug_rgb).save(filename)
            
            panel_only = screen[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w].copy()
            panel_rgb = cv2.cvtColor(panel_only, cv2.COLOR_BGR2RGB)
            panel_filename = os.path.join(debug_folder, f"panel_{timestamp}.png")
            Image.fromarray(panel_rgb).save(panel_filename)
            self.last_captcha_debug = filename
            self.last_captcha_panel = panel_filename
            print(f"[CAPTCHA] Debug kayıt: {filename}")
            print(f"[CAPTCHA] Panel kayıt: {panel_filename}")
            
        except Exception:
            pass
    
    def stop_bot(self):
        self.running = False
        try:
            self._loot_stop_event.set()
        except Exception:
            pass

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TritonX Metin2 Bot 🐉")
        self.root.geometry("500x800")
        self.root.resizable(False, False)
        
        self.bot = Metin2Bot()
        self.bot_thread = None
        self.hotkey_thread = None
        self._hotkey_stop = False
        self._start_latched = False
        self._stop_latched = False
        self._start_lock = threading.Lock()
        self._starting = False
        
        self.setup_ui()
        self.start_hotkeys()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        title_label = ttk.Label(main_frame, text="🎮 TritonX Bot Kontrol Paneli", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        with mss() as sct:
            monitor_count = len(sct.monitors) - 1
        ttk.Label(main_frame, text=f"Toplam: {monitor_count} ekran", font=("Arial", 9)).grid(
            row=1, column=0, columnspan=3, pady=2
        )

        self.guide_label = ttk.Label(main_frame, text="1) Mod  2) Algılama  3) Seçim  4) Başlat", font=("Arial", 9))
        self.guide_label.grid(row=2, column=0, columnspan=3, pady=2)

        ttk.Label(main_frame, text="Hotkey: Z+C başlat | Z+V durdur", font=("Arial", 9)).grid(
            row=3, column=0, columnspan=3, pady=2
        )
        
        ttk.Label(main_frame, text="🛡️ Bot Kontrol: Aktif yapınca süre seç", font=("Arial", 9), foreground="green").grid(
            row=4, column=0, columnspan=3, pady=2
        )

        ttk.Label(main_frame, text="Mod:", font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.mode_var = tk.StringVar(value="window")
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=5, column=1, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Uygulama (Pencere)", variable=self.mode_var, value="window", command=self.on_mode_change).grid(
            row=0, column=0, padx=5
        )
        ttk.Radiobutton(mode_frame, text="Ekran", variable=self.mode_var, value="screen", command=self.on_mode_change).grid(
            row=0, column=1, padx=5
        )

        ttk.Label(main_frame, text="Algılama:", font=("Arial", 10)).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.detect_var = tk.StringVar(value="template")
        detect_frame = ttk.Frame(main_frame)
        detect_frame.grid(row=5, column=1, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(detect_frame, text="Template", variable=self.detect_var, value="template", command=self.on_detect_change).grid(
            row=0, column=0, padx=5
        )
        ttk.Radiobutton(detect_frame, text="Renk", variable=self.detect_var, value="color", command=self.on_detect_change).grid(
            row=0, column=1, padx=5
        )

        ttk.Label(main_frame, text="Input Metodu:", font=("Arial", 10)).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.input_method_var = tk.StringVar(value="sendinput")
        input_combo = ttk.Combobox(main_frame, textvariable=self.input_method_var, width=30, state="readonly")
        input_combo["values"] = ["SendInput (Windows API)", "PostMessage (Pencere)", "PyAutoGUI"]
        input_combo.current(0)
        input_combo.grid(row=6, column=1, columnspan=2, padx=5)
        input_combo.bind("<<ComboboxSelected>>", self.on_input_method_change)

        self.template_frame = ttk.Frame(main_frame)
        self.template_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E))
        ttk.Label(self.template_frame, text="Template Klasörü:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.template_folder_var = tk.StringVar(value="templates/")
        ttk.Entry(self.template_frame, textvariable=self.template_folder_var, width=30).grid(row=0, column=1, padx=5)
        ttk.Button(self.template_frame, text="Seç", command=self.browse_templates).grid(row=0, column=2)

        self.color_frame = ttk.Frame(main_frame)
        self.color_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E))
        ttk.Label(self.color_frame, text="Renk (HEX):", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.color_hex_var = tk.StringVar(value="#ffffff")
        ttk.Entry(self.color_frame, textvariable=self.color_hex_var, width=30).grid(row=0, column=1, padx=5)
        ttk.Label(self.color_frame, text="Tolerans:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W)
        self.color_tol_var = tk.IntVar(value=20)
        self.color_tol_slider = ttk.Scale(self.color_frame, from_=0, to=80, orient=tk.HORIZONTAL, command=self.update_color_tol)
        self.color_tol_slider.set(20)
        self.color_tol_slider.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.color_tol_label = ttk.Label(self.color_frame, text="20")
        self.color_tol_label.grid(row=1, column=2, sticky=tk.W)

        self.window_frame = ttk.Frame(main_frame)
        self.window_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E))
        ttk.Label(self.window_frame, text="Oyun Penceresi:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.window_var = tk.StringVar(value="")
        self.window_combo = ttk.Combobox(self.window_frame, textvariable=self.window_var, width=30, state="readonly")
        self.window_combo.grid(row=0, column=1, padx=5)
        self.window_combo.bind("<<ComboboxSelected>>", self.on_window_selected)
        ttk.Button(self.window_frame, text="Yenile", command=self.refresh_windows).grid(row=0, column=2)

        self.screen_frame = ttk.Frame(main_frame)
        self.screen_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E))
        ttk.Label(self.screen_frame, text="Ekran Seçimi:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.monitor_var = tk.StringVar(value="1")
        self.monitor_combo = ttk.Combobox(self.screen_frame, textvariable=self.monitor_var, width=30, state="readonly")
        self.monitor_combo["values"] = [str(i) for i in range(1, monitor_count + 1)] if monitor_count > 0 else ["1"]
        self.monitor_combo.grid(row=0, column=1, padx=5)
        self.monitor_combo.bind("<<ComboboxSelected>>", self.on_monitor_selected)
        ttk.Label(self.screen_frame, text="(1..N)", font=("Arial", 9)).grid(row=0, column=2, sticky=tk.W)

        self.refresh_windows()
        self.on_mode_change()
        self.on_detect_change()

        ttk.Label(main_frame, text=f"Algılama Eşiği: {self.bot.threshold}", font=("Arial", 10)).grid(row=10, column=0, sticky=tk.W, pady=5)
        self.threshold_label = ttk.Label(main_frame, text=f"{self.bot.threshold:.2f}")
        self.threshold_slider = ttk.Scale(main_frame, from_=0.5, to=0.95, orient=tk.HORIZONTAL, 
                                          command=self.update_threshold)
        self.threshold_slider.set(self.bot.threshold)
        self.threshold_slider.grid(row=10, column=1, sticky=(tk.W, tk.E), padx=5)
        self.threshold_label.grid(row=10, column=2)

        scan_min_default = max(0.1, min(3.0, self.bot.scan_delay / 60000.0))
        ttk.Label(main_frame, text=f"Tarama (dk): {scan_min_default:.1f}", font=("Arial", 10)).grid(row=10, column=0, sticky=tk.W, pady=5)
        self.scan_label = ttk.Label(main_frame, text=f"{scan_min_default:.1f} dk")
        self.scan_slider = ttk.Scale(main_frame, from_=0.1, to=3.0, orient=tk.HORIZONTAL, command=self.update_scan_delay)
        self.scan_slider.set(scan_min_default)
        self.scan_slider.grid(row=11, column=1, sticky=(tk.W, tk.E), padx=5)
        self.scan_label.grid(row=11, column=2)

        click_min_default = max(0.1, min(3.0, self.bot.click_delay / 60000.0))
        ttk.Label(main_frame, text=f"Tıklama (dk): {click_min_default:.1f}", font=("Arial", 10)).grid(row=11, column=0, sticky=tk.W, pady=5)
        self.click_label = ttk.Label(main_frame, text=f"{click_min_default:.1f} dk")
        self.click_slider = ttk.Scale(main_frame, from_=0.1, to=3.0, orient=tk.HORIZONTAL, command=self.update_click_delay)
        self.click_slider.set(click_min_default)
        self.click_slider.grid(row=12, column=1, sticky=(tk.W, tk.E), padx=5)
        self.click_label.grid(row=12, column=2)

        camera_sec_default = max(0.0, min(2.0, self.bot.camera_wait / 1000.0))
        ttk.Label(main_frame, text=f"Kamera Bekleme (sn): {camera_sec_default:.1f}", font=("Arial", 10)).grid(row=12, column=0, sticky=tk.W, pady=5)
        self.camera_label = ttk.Label(main_frame, text=f"{camera_sec_default:.1f} sn")
        self.camera_slider = ttk.Scale(main_frame, from_=0.0, to=2.0, orient=tk.HORIZONTAL, command=self.update_camera_wait)
        self.camera_slider.set(camera_sec_default)
        self.camera_slider.grid(row=13, column=1, sticky=(tk.W, tk.E), padx=5)
        self.camera_label.grid(row=13, column=2)

        ttk.Label(main_frame, text="Oto Toplama:", font=("Arial", 10)).grid(row=13, column=0, sticky=tk.W, pady=5)
        self.loot_mode_var = tk.StringVar(value="passive")
        loot_mode_frame = ttk.Frame(main_frame)
        loot_mode_frame.grid(row=13, column=1, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(loot_mode_frame, text="Pasif", variable=self.loot_mode_var, value="passive", command=self.on_loot_mode_change).grid(
            row=0, column=0, padx=5
        )
        ttk.Radiobutton(loot_mode_frame, text="Aktif", variable=self.loot_mode_var, value="active", command=self.on_loot_mode_change).grid(
            row=0, column=1, padx=5
        )

        loot_min_default = max(0.01, min(0.5, self.bot.auto_loot_interval / 60000.0))
        ttk.Label(main_frame, text=f"Toplama Aralığı (dk): {loot_min_default:.2f}", font=("Arial", 10)).grid(row=15, column=0, sticky=tk.W, pady=5)
        self.loot_label = ttk.Label(main_frame, text=f"{loot_min_default:.2f} dk")
        self.loot_slider = ttk.Scale(main_frame, from_=0.01, to=0.5, orient=tk.HORIZONTAL, command=self.update_loot_interval)
        self.loot_slider.set(loot_min_default)
        self.loot_slider.grid(row=15, column=1, sticky=(tk.W, tk.E), padx=5)
        self.loot_label.grid(row=15, column=2)
        self.on_loot_mode_change()
        
        ttk.Label(main_frame, text="Bot Kontrol:", font=("Arial", 10)).grid(row=16, column=0, sticky=tk.W, pady=5)
        self.captcha_mode_var = tk.StringVar(value="passive")
        captcha_mode_frame = ttk.Frame(main_frame)
        captcha_mode_frame.grid(row=16, column=1, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(captcha_mode_frame, text="Pasif", variable=self.captcha_mode_var, value="passive", command=self.on_captcha_mode_change).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(captcha_mode_frame, text="Aktif", variable=self.captcha_mode_var, value="active", command=self.on_captcha_mode_change).grid(row=0, column=1, padx=5)
        
        ttk.Label(main_frame, text="Kontrol Süresi:", font=("Arial", 10)).grid(row=17, column=0, sticky=tk.W, pady=5)
        self.captcha_interval_var = tk.StringVar(value="5 dk")
        self.captcha_interval_combo = ttk.Combobox(main_frame, textvariable=self.captcha_interval_var, width=10, state="disabled")
        self.captcha_interval_combo["values"] = ["5 dk", "10 dk", "20 dk", "30 dk"]
        self.captcha_interval_combo.current(0)
        self.captcha_interval_combo.grid(row=17, column=1, sticky=tk.W, padx=5)
        self.captcha_interval_combo.bind("<<ComboboxSelected>>", self.on_captcha_interval_change)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=18, column=0, columnspan=3, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="▶️ BOT BAŞLAT", command=self.start_bot)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ DURDUR", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=19, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(main_frame, text="Durum:", font=("Arial", 10, "bold")).grid(row=20, column=0, sticky=tk.W)
        
        self.status_text = tk.Text(main_frame, height=8, width=55, state=tk.DISABLED, 
                                   bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.status_text.grid(row=21, column=0, columnspan=3, pady=5)
        
        scrollbar = ttk.Scrollbar(main_frame, command=self.status_text.yview)
        scrollbar.grid(row=21, column=3, sticky=(tk.N, tk.S))
        self.status_text['yscrollcommand'] = scrollbar.set
        
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=22, column=0, columnspan=3, pady=10)
        
        self.attack_label = ttk.Label(info_frame, text="Saldırı Sayısı: 0", font=("Arial", 9))
        self.attack_label.grid(row=0, column=0, padx=10)
        
        self.rotation_label = ttk.Label(info_frame, text="Kamera Dönüşü: 0", font=("Arial", 9))
        self.rotation_label.grid(row=0, column=1, padx=10)
        
        self.log_status("💤 Bot hazır. Template'leri yükle ve başlat!")
        
        if not is_admin():
            self.log_status("⚠️ UYARI: Yönetici olarak çalışmıyor! Oyuna tıklama çalışmayabilir.")

    def on_detect_change(self):
        mode = (self.detect_var.get() or "template").strip()
        self.bot.set_detection_mode(mode)
        if mode == "color":
            self.template_frame.grid_remove()
            self.color_frame.grid()
        else:
            self.color_frame.grid_remove()
            self.template_frame.grid()
        self._update_guide()

    def update_color_tol(self, value):
        v = int(float(value))
        self.color_tol_var.set(v)
        self.color_tol_label.config(text=str(v))

    def on_input_method_change(self, event=None):
        selected = (self.input_method_var.get() or "").strip()
        if "SendInput" in selected:
            self.bot.input_method = "sendinput"
            self.log_status("Input: SendInput (Windows API)")
        elif "PostMessage" in selected:
            self.bot.input_method = "postmessage"
            self.log_status("Input: PostMessage (Pencereye direkt mesaj)")
        elif "PyAutoGUI" in selected:
            self.bot.input_method = "pyautogui"
            self.log_status("Input: PyAutoGUI")
        else:
            self.bot.input_method = "sendinput"

    def _update_guide(self):
        mode = (self.mode_var.get() or "window").strip()
        det = (self.detect_var.get() or "template").strip()
        mode_txt = "Ekran" if mode == "screen" else "Uygulama"
        det_txt = "Renk" if det == "color" else "Template"
        if det == "color":
            step2 = "HEX renk gir"
        else:
            step2 = "Template seç"

        if mode == "screen":
            step3 = "Ekran seç"
        else:
            step3 = "Pencere seç"

        self.guide_label.config(text=f"1) Mod: {mode_txt}  2) Algılama: {det_txt} ({step2})  3) {step3}  4) Başlat")

    def on_mode_change(self):
        mode = (self.mode_var.get() or "window").strip()
        if mode == "screen":
            self.window_frame.grid_remove()
            self.screen_frame.grid()
        else:
            self.screen_frame.grid_remove()
            self.window_frame.grid()
        self._update_guide()

    def on_monitor_selected(self, event=None):
        value = (self.monitor_var.get() or "1").strip()
        self.bot.set_screen_monitor(value)
        self.log_status(f"Ekran modu: Ekran {self.bot.monitor_index}")

    def refresh_windows(self):
        try:
            titles = [t.strip() for t in gw.getAllTitles() if t and t.strip()]
            titles = sorted(set(titles), key=lambda s: s.lower())
        except Exception:
            titles = []

        self.window_combo["values"] = titles
        if titles and self.window_var.get() not in titles:
            self.window_var.set("")

    def on_window_selected(self, event=None):
        title = (self.window_var.get() or "").strip()
        if not title:
            return
        ok = self.bot.set_target_window(title)
        if ok:
            self.log_status(f"✅ Pencere seçildi: {title}")
        else:
            self.log_status("❌ Pencere seçilemedi (kapalı/minimized olabilir)")
        
    def browse_templates(self):
        folder = filedialog.askdirectory(initialdir=os.getcwd())
        if folder:
            self.template_folder_var.set(folder)
            self.load_templates()
    
    def load_templates(self):
        template_folder = self.template_folder_var.get()
        if not os.path.exists(template_folder):
            os.makedirs(template_folder)
            self.log_status(f"📁 Klasör oluşturuldu: {template_folder}")
            messagebox.showinfo("Bilgi", f"Template klasörü oluşturuldu!\nBuraya hedef görselleri (.png, .jpg) ekle:\n{template_folder}")
            return
        
        self.bot.templates = []
        for file in os.listdir(template_folder):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.bot.templates.append(os.path.join(template_folder, file))
        
        if self.bot.templates:
            self.log_status(f"✅ {len(self.bot.templates)} template yüklendi")
        else:
            self.log_status(f"⚠️ Template bulunamadı! {template_folder} klasörüne görsel ekle")
    
    def update_threshold(self, value):
        self.bot.threshold = float(value)
        self.threshold_label.config(text=f"{self.bot.threshold:.2f}")
    
    def update_delay(self, value):
        pass

    def update_scan_delay(self, value):
        minutes = float(value)
        minutes = round(minutes * 10) / 10.0
        if minutes < 0.1:
            minutes = 0.1
        if minutes > 3.0:
            minutes = 3.0
        self.bot.scan_delay = int(minutes * 60_000)
        self.scan_label.config(text=f"{minutes:.1f} dk")

    def update_click_delay(self, value):
        minutes = float(value)
        minutes = round(minutes * 10) / 10.0
        if minutes < 0.1:
            minutes = 0.1
        if minutes > 3.0:
            minutes = 3.0
        self.bot.click_delay = int(minutes * 60_000)
        self.click_label.config(text=f"{minutes:.1f} dk")

    def on_loot_mode_change(self):
        mode = (getattr(self, "loot_mode_var", tk.StringVar(value="passive")).get() or "passive").strip()
        self.bot.auto_loot_mode = mode
        try:
            if mode == "active":
                self.loot_slider.state(["!disabled"])
            else:
                self.loot_slider.state(["disabled"])
        except Exception:
            pass

    def update_loot_interval(self, value):
        minutes = float(value)
        minutes = round(minutes * 100) / 100.0
        if minutes < 0.01:
            minutes = 0.01
        if minutes > 0.5:
            minutes = 0.5
        self.bot.auto_loot_interval = int(minutes * 60_000)
        self.loot_label.config(text=f"{minutes:.2f} dk")
    
    def on_captcha_mode_change(self):
        mode = getattr(self, "captcha_mode_var", tk.StringVar(value="passive")).get()
        if mode == "active":
            self.bot.captcha_enabled = True
            self.captcha_interval_combo.config(state="readonly")
            self.on_captcha_interval_change(None)
        else:
            self.bot.captcha_enabled = False
            self.captcha_interval_combo.config(state="disabled")
    
    def on_captcha_interval_change(self, event):
        interval_str = getattr(self, "captcha_interval_var", tk.StringVar(value="5 dk")).get()
        interval_map = {
            "5 dk": 300,
            "10 dk": 600,
            "20 dk": 1200,
            "30 dk": 1800
        }
        self.bot.captcha_check_interval = interval_map.get(interval_str, 300)

    def update_camera_wait(self, value):
        seconds = float(value)
        seconds = round(seconds * 10) / 10.0
        if seconds < 0.0:
            seconds = 0.0
        if seconds > 2.0:
            seconds = 2.0
        self.bot.camera_wait = int(seconds * 1000)
        self.camera_label.config(text=f"{seconds:.1f} sn")

    def start_hotkeys(self):
        if self.hotkey_thread and self.hotkey_thread.is_alive():
            return
        self._hotkey_stop = False
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def _hotkey_loop(self):
        while not self._hotkey_stop:
            try:
                z = is_vk_down(VK_Z)
                c = is_vk_down(VK_C)
                v = is_vk_down(VK_V)

                start_pressed = z and c
                stop_pressed = z and v

                if start_pressed and not self._start_latched:
                    self._start_latched = True
                    self.root.after(0, self.start_bot)
                if not start_pressed:
                    self._start_latched = False

                if stop_pressed and not self._stop_latched:
                    self._stop_latched = True
                    self.root.after(0, self.stop_bot)
                if not stop_pressed:
                    self._stop_latched = False

                time.sleep(0.03)
            except Exception:
                time.sleep(0.1)
    
    def start_bot(self):
        with self._start_lock:
            if self._starting:
                return
            if self.bot.running:
                return
            if self.bot_thread and self.bot_thread.is_alive():
                return
            self._starting = True

        try:
            self.bot.auto_loot_mode = (getattr(self, "loot_mode_var", tk.StringVar(value="passive")).get() or "passive").strip()
        except Exception:
            self.bot.auto_loot_mode = "passive"

        detect_mode = (self.detect_var.get() or "template").strip()
        self.bot.set_detection_mode(detect_mode)

        if detect_mode == "color":
            hex_color = (self.color_hex_var.get() or "").strip()
            tol = int(self.color_tol_var.get())
            if not self.bot.set_color_target(hex_color, tol):
                messagebox.showerror("Hata", "Renk HEX hatalı. Örn: #ff0000")
                with self._start_lock:
                    self._starting = False
                return
            self.log_status(f"Renk modu: {hex_color} | tol={tol}")
        else:
            self.load_templates()
            if not self.bot.templates:
                messagebox.showerror("Hata", "Template yok! Önce hedef görselleri yükle.")
                with self._start_lock:
                    self._starting = False
                return
            self.log_status("Template modu aktif")

        mode = (self.mode_var.get() or "window").strip()
        if mode == "screen":
            selected_monitor = (getattr(self, "monitor_var", tk.StringVar(value="1")).get() or "1").strip()
            self.bot.set_screen_monitor(selected_monitor)
            self.log_status(f"Ekran modu aktif: Ekran {self.bot.monitor_index}")
        else:
            selected_title = (getattr(self, "window_var", tk.StringVar()).get() or "").strip()
            if not selected_title:
                messagebox.showerror("Hata", "Önce oyun penceresini seç.")
                with self._start_lock:
                    self._starting = False
                return

            if not self.bot.set_target_window(selected_title):
                messagebox.showerror("Hata", "Seçili pencere bulunamadı. Pencere açık ve minimize değilken tekrar dene.")
                with self._start_lock:
                    self._starting = False
                return
            self.log_status(f"Pencere modu aktif: {selected_title}")
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.bot.running = True
        
        self.bot_thread = threading.Thread(target=self.bot.run_bot, args=(self.log_status,), daemon=True)
        self.bot_thread.start()

        with self._start_lock:
            self._starting = False
        
        self.update_stats()
    
    def stop_bot(self):
        self.bot.stop_bot()
        with self._start_lock:
            self._starting = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def log_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def update_stats(self):
        if self.bot.running:
            self.attack_label.config(text=f"Saldırı Sayısı: {self.bot.attack_count}")
            self.rotation_label.config(text=f"Kamera Dönüşü: {self.bot.rotation_counter}")
            self.root.after(500, self.update_stats)


MB_OK = 0x00000000
MB_YESNO = 0x00000004
MB_ICONWARNING = 0x00000030
MB_ICONINFORMATION = 0x00000040
IDYES = 6


def _win_message_box(title: str, message: str, flags: int) -> int:
    try:
        return int(ctypes.windll.user32.MessageBoxW(None, str(message), str(title), int(flags)))
    except Exception:
        return 0


def _prompt_yes_no(title: str, message: str) -> bool:
    return _win_message_box(title, message, MB_YESNO | MB_ICONWARNING) == IDYES


def _info(title: str, message: str) -> None:
    _win_message_box(title, message, MB_OK | MB_ICONINFORMATION)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _ensure_web_assets() -> None:
    base = _base_dir()
    src_dir = os.path.join(base, "Assets")
    dst_dir = os.path.join(base, "web", "assets")
    os.makedirs(dst_dir, exist_ok=True)
    for name in ("TritonXlogo.png", "TritonXTextLogo.png"):
        src = os.path.join(src_dir, name)
        dst = os.path.join(dst_dir, name)
        try:
            if os.path.exists(src) and not os.path.exists(dst):
                with open(src, "rb") as rf, open(dst, "wb") as wf:
                    wf.write(rf.read())
        except Exception:
            pass


def _ensure_icon_ico() -> str | None:
    base = _base_dir()
    png_path = os.path.join(base, "Assets", "TritonXlogo.png")
    ico_path = os.path.join(base, "Assets", "TritonXlogo.ico")
    try:
        if os.path.exists(ico_path):
            return ico_path
        if not os.path.exists(png_path):
            return None
        img = Image.open(png_path).convert("RGBA")
        img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        return ico_path
    except Exception:
        return None


_TRITONX_HICON = None


def _try_set_win32_window_icon(window, icon_ico_path: str) -> bool:
    try:
        if not icon_ico_path or not os.path.exists(icon_ico_path):
            return False

        hwnd = None
        for attr in ("_hWnd", "_hwnd", "hwnd"):
            h = getattr(window, attr, None)
            if h:
                try:
                    hwnd = int(h)
                    break
                except Exception:
                    hwnd = None

        if not hwnd:
            return False

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        ICON_SMALL2 = 2

        hicon = ctypes.windll.user32.LoadImageW(None, str(icon_ico_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
        if not hicon:
            return False

        global _TRITONX_HICON
        _TRITONX_HICON = hicon

        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL2, hicon)
        return True
    except Exception:
        return False


class BotController:
    def __init__(self):
        self.bot = Metin2Bot()
        self.bot_thread = None

        self.mode = "window"  # window|screen
        self.template_folder = os.path.join(_base_dir(), "templates")
        self.window_title = ""

        self._start_lock = threading.Lock()
        self._starting = False

        self._log_lock = threading.Lock()
        self._log_cursor = 0
        self._logs = deque(maxlen=800)

        self.hotkey_thread = None
        self._hotkey_stop = False
        self._start_latched = False
        self._stop_latched = False
        
        self._presets_file = os.path.join(_base_dir(), "presets.json")
        self._presets = self._load_presets_file()
        
        self._settings_file = os.path.join(_base_dir(), "settings.json")
        self._settings = self._load_settings_file()
        
        self.start_hotkeys()

        self.log_status("💤 Bot hazır")
    
    def _load_settings_file(self):
        try:
            if os.path.exists(self._settings_file):
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {"theme": "default"}
    
    def _save_settings_file(self):
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def get_theme(self):
        return self._settings.get("theme", "default")
    
    def set_theme(self, theme_id):
        if theme_id in ("default", "voidnox", "sylva", "pulsarspark", "amethyst"):
            self._settings["theme"] = theme_id
            self._save_settings_file()
            return {"ok": True, "theme": theme_id}
        return {"ok": False, "message": "invalid_theme"}
    
    def _load_presets_file(self):
        try:
            if os.path.exists(self._presets_file):
                with open(self._presets_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}
    
    def _save_presets_file(self):
        try:
            with open(self._presets_file, "w", encoding="utf-8") as f:
                json.dump(self._presets, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def list_presets(self):
        return list(self._presets.keys())
    
    def save_preset(self, name):
        if not name or not isinstance(name, str):
            return {"ok": False, "message": "invalid_name"}
        name = name.strip()[:50]
        if not name:
            return {"ok": False, "message": "empty_name"}
        
        scan_minutes = max(0.1, min(3.0, self.bot.scan_delay / 60000.0))
        click_minutes = max(0.1, min(3.0, self.bot.click_delay / 60000.0))
        camera_seconds = max(0.0, min(2.0, self.bot.camera_wait / 1000.0))
        auto_loot_minutes = max(0.01, min(0.5, self.bot.auto_loot_interval / 60000.0))
        
        preset = {
            "mode": str(self.mode),
            "detection_mode": str(self.bot.detection_mode),
            "input_method": str(self.bot.input_method),
            "template_folder": str(self.template_folder),
            "monitor_index": int(getattr(self.bot, "monitor_index", 1) or 1),
            "threshold": float(self.bot.threshold),
            "scan_minutes": float(round(scan_minutes * 20) / 20.0),
            "click_minutes": float(round(click_minutes * 20) / 20.0),
            "camera_seconds": float(round(camera_seconds * 10) / 10.0),
            "auto_loot_mode": str(self.bot.auto_loot_mode or "passive"),
            "auto_loot_minutes": float(round(auto_loot_minutes * 100) / 100.0),
            "color_hex": str(self.bot.color_hex or "#ffffff"),
            "color_tolerance": int(self.bot.color_tolerance),
            "captcha_enabled": bool(getattr(self.bot, "captcha_enabled", False)),
            "captcha_check_interval": int(getattr(self.bot, "captcha_check_interval", 5)),
        }
        
        self._presets[name] = preset
        if self._save_presets_file():
            self.log_status(f"💾 Kayıt '{name}' kaydedildi")
            return {"ok": True, "name": name}
        return {"ok": False, "message": "save_failed"}
    
    def load_preset(self, name):
        if not name or name not in self._presets:
            return {"ok": False, "message": "not_found"}
        
        preset = self._presets[name]
        self.set_config(preset)
        self.log_status(f"📂 Kayıt '{name}' yüklendi")
        return {"ok": True, "name": name}
    
    def delete_preset(self, name):
        if not name or name not in self._presets:
            return {"ok": False, "message": "not_found"}
        
        del self._presets[name]
        if self._save_presets_file():
            self.log_status(f"🗑️ Kayıt '{name}' silindi")
            return {"ok": True}
        return {"ok": False, "message": "delete_failed"}

    def log_status(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        with self._log_lock:
            self._log_cursor += 1
            self._logs.append((self._log_cursor, line))

    def get_logs_since(self, cursor: int):
        cursor = _safe_int(cursor, 0)
        with self._log_lock:
            items = [line for (cid, line) in self._logs if cid > cursor]
            next_cursor = cursor
            if self._logs:
                next_cursor = self._logs[-1][0]
        return {"items": items, "next_cursor": int(next_cursor)}

    def start_hotkeys(self):
        if self.hotkey_thread and self.hotkey_thread.is_alive():
            return
        self._hotkey_stop = False
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def _hotkey_loop(self):
        while not self._hotkey_stop:
            try:
                z = is_vk_down(VK_Z)
                c = is_vk_down(VK_C)
                v = is_vk_down(VK_V)

                start_pressed = z and c
                stop_pressed = z and v

                if start_pressed and not self._start_latched:
                    self._start_latched = True
                    self.start_bot()
                if not start_pressed:
                    self._start_latched = False

                if stop_pressed and not self._stop_latched:
                    self._stop_latched = True
                    self.stop_bot()
                if not stop_pressed:
                    self._stop_latched = False

                time.sleep(0.03)
            except Exception:
                time.sleep(0.1)

    def list_windows(self):
        try:
            titles = [t.strip() for t in gw.getAllTitles() if t and t.strip()]
            titles = sorted(set(titles), key=lambda s: s.lower())
            return titles
        except Exception:
            return []

    def list_monitors(self):
        try:
            with mss() as sct:
                monitor_count = max(1, len(sct.monitors) - 1)
            return [str(i) for i in range(1, monitor_count + 1)]
        except Exception:
            return ["1"]

    def reload_templates(self) -> int:
        folder = (self.template_folder or "").strip()
        if not folder:
            folder = os.path.join(_base_dir(), "templates")
        os.makedirs(folder, exist_ok=True)

        templates = []
        try:
            for file in os.listdir(folder):
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    templates.append(os.path.join(folder, file))
        except Exception:
            templates = []

        self.bot.templates = templates
        self.log_status(f"✅ {len(templates)} template yüklendi")
        return len(templates)

    def set_config(self, patch: dict) -> None:
        if not isinstance(patch, dict):
            return

        if "mode" in patch:
            mode = str(patch.get("mode") or "window").strip()
            if mode in ("window", "screen"):
                self.mode = mode

        if "detection_mode" in patch:
            det = str(patch.get("detection_mode") or "template").strip()
            self.bot.set_detection_mode(det)

        if "input_method" in patch:
            im = str(patch.get("input_method") or "sendinput").strip()
            if im in ("sendinput", "postmessage", "pyautogui"):
                self.bot.input_method = im

        if "template_folder" in patch:
            self.template_folder = str(patch.get("template_folder") or "").strip()

        if "window_title" in patch:
            title = str(patch.get("window_title") or "").strip()
            self.window_title = title
            if title:
                ok = self.bot.set_target_window(title)
                if ok:
                    self.log_status(f"✅ Pencere seçildi: {title}")
                else:
                    self.log_status("❌ Pencere seçilemedi (kapalı/minimized olabilir)")

        if "monitor_index" in patch:
            idx = _safe_int(patch.get("monitor_index"), 1)
            if idx < 1:
                idx = 1
            self.bot.set_screen_monitor(str(idx))

        if "threshold" in patch:
            th = _safe_float(patch.get("threshold"), self.bot.threshold)
            th = max(0.50, min(0.95, th))
            self.bot.threshold = th

        if "scan_minutes" in patch:
            minutes = _safe_float(patch.get("scan_minutes"), self.bot.scan_delay / 60000.0)
            minutes = max(0.1, min(3.0, round(minutes * 20) / 20.0))
            self.bot.scan_delay = int(minutes * 60_000)

        if "click_minutes" in patch:
            minutes = _safe_float(patch.get("click_minutes"), self.bot.click_delay / 60000.0)
            minutes = max(0.1, min(3.0, round(minutes * 20) / 20.0))
            self.bot.click_delay = int(minutes * 60_000)

        if "camera_seconds" in patch:
            seconds = _safe_float(patch.get("camera_seconds"), self.bot.camera_wait / 1000.0)
            seconds = max(0.0, min(2.0, round(seconds * 10) / 10.0))
            self.bot.camera_wait = int(seconds * 1000)

        if "auto_loot_mode" in patch:
            mode = str(patch.get("auto_loot_mode") or "passive").strip()
            if mode in ("passive", "active"):
                self.bot.auto_loot_mode = mode

        if "auto_loot_minutes" in patch:
            minutes = _safe_float(patch.get("auto_loot_minutes"), self.bot.auto_loot_interval / 60000.0)
            minutes = max(0.01, min(0.5, round(minutes * 100) / 100.0))
            self.bot.auto_loot_interval = int(minutes * 60_000)

        if "color_hex" in patch:
            self.bot.color_hex = str(patch.get("color_hex") or "#ffffff").strip()

        if "color_tolerance" in patch:
            tol = _safe_int(patch.get("color_tolerance"), self.bot.color_tolerance)
            tol = max(0, min(80, tol))
            self.bot.color_tolerance = tol

        if "metin_preset" in patch:
            preset = str(patch.get("metin_preset") or "golge").strip()
            self.bot.set_metin_preset(preset)

        if "captcha_enabled" in patch:
            self.bot.captcha_enabled = bool(patch.get("captcha_enabled"))

        if "captcha_check_interval" in patch:
            interval = _safe_int(patch.get("captcha_check_interval"), 5)
            if interval in (5, 10, 20, 30):
                self.bot.captcha_check_interval = interval

    def start_bot(self):
        with self._start_lock:
            if self._starting or self.bot.running:
                return {"ok": False, "message": "already_running"}
            if self.bot_thread and self.bot_thread.is_alive():
                return {"ok": False, "message": "thread_alive"}
            self._starting = True

        try:
            det = (self.bot.detection_mode or "template").strip()
            if det == "color":
                ok = self.bot.set_color_target(self.bot.color_hex, int(self.bot.color_tolerance))
                if not ok:
                    self.log_status("❌ Renk HEX hatalı. Örn: #ff0000")
                    return {"ok": False, "message": "bad_color"}
                self.log_status(f"Renk modu: {self.bot.color_hex} | tol={int(self.bot.color_tolerance)}")
            elif det == "metin_preset":
                preset_key = getattr(self.bot, "metin_preset", "golge")
                if preset_key in METIN_PRESETS:
                    preset_info = METIN_PRESETS[preset_key]
                    self.bot.color_hex = preset_info["color"]
                    ok = self.bot.set_color_target(self.bot.color_hex, int(self.bot.color_tolerance))
                    if not ok:
                        self.log_status("❌ Metin preset renk hatası")
                        return {"ok": False, "message": "bad_preset_color"}
                    self.log_status(f"Metine Göre: {preset_info['name']} ({preset_info['color']}) | tol={int(self.bot.color_tolerance)}")
                else:
                    self.log_status("❌ Geçersiz metin preset")
                    return {"ok": False, "message": "invalid_preset"}
            else:
                if not self.bot.templates:
                    self.reload_templates()
                if not self.bot.templates:
                    self.log_status("❌ Template yok! Önce hedef görselleri yükle.")
                    return {"ok": False, "message": "no_templates"}
                self.log_status("Template modu aktif")

            if (self.mode or "window") == "screen":
                self.log_status(f"Ekran modu aktif: Ekran {self.bot.monitor_index}")
            else:
                title = (self.window_title or "").strip()
                if not title:
                    self.log_status("❌ Önce oyun penceresini seç.")
                    return {"ok": False, "message": "no_window"}
                if not self.bot.set_target_window(title):
                    self.log_status("❌ Seçili pencere bulunamadı. Pencere açık ve minimize değilken tekrar dene.")
                    return {"ok": False, "message": "window_not_found"}
                self.log_status(f"Pencere modu aktif: {title}")

            self.bot.running = True
            self.bot_thread = threading.Thread(target=self.bot.run_bot, args=(self.log_status,), daemon=True)
            self.bot_thread.start()
            return {"ok": True}
        finally:
            with self._start_lock:
                self._starting = False

    def stop_bot(self):
        try:
            self.bot.stop_bot()
        except Exception:
            pass
        return {"ok": True}

    def get_state(self):
        scan_minutes = max(0.1, min(3.0, self.bot.scan_delay / 60000.0))
        click_minutes = max(0.1, min(3.0, self.bot.click_delay / 60000.0))
        camera_seconds = max(0.0, min(2.0, self.bot.camera_wait / 1000.0))
        auto_loot_minutes = max(0.01, min(0.5, self.bot.auto_loot_interval / 60000.0))
        return {
            "running": bool(self.bot.running),
            "mode": str(self.mode),
            "detection_mode": str(self.bot.detection_mode),
            "input_method": str(self.bot.input_method),
            "template_folder": str(self.template_folder),
            "template_count": int(len(self.bot.templates or [])),
            "window_title": str(self.window_title or ""),
            "monitor_index": int(getattr(self.bot, "monitor_index", 1) or 1),
            "threshold": float(self.bot.threshold),
            "scan_minutes": float(round(scan_minutes * 20) / 20.0),
            "click_minutes": float(round(click_minutes * 20) / 20.0),
            "camera_seconds": float(round(camera_seconds * 10) / 10.0),
            "auto_loot_mode": str(self.bot.auto_loot_mode or "passive"),
            "auto_loot_minutes": float(round(auto_loot_minutes * 100) / 100.0),
            "color_hex": str(self.bot.color_hex or "#ffffff"),
            "color_tolerance": int(self.bot.color_tolerance),
            "metin_preset": str(getattr(self.bot, "metin_preset", "golge")),
            "attack_count": int(self.bot.attack_count),
            "rotation_counter": int(self.bot.rotation_counter),
            "captcha_enabled": bool(getattr(self.bot, "captcha_enabled", False)),
            "captcha_check_interval": int(getattr(self.bot, "captcha_check_interval", 5)),
        }


class WebApi:
    def __init__(self, controller: BotController):
        self.controller = controller

    def get_state(self):
        return self.controller.get_state()

    def list_windows(self):
        return self.controller.list_windows()

    def list_monitors(self):
        return self.controller.list_monitors()

    def set_config(self, patch):
        self.controller.set_config(patch)
        return self.controller.get_state()

    def reload_templates(self):
        return {"count": int(self.controller.reload_templates())}

    def start_bot(self):
        return self.controller.start_bot()

    def stop_bot(self):
        return self.controller.stop_bot()

    def get_logs_since(self, cursor):
        return self.controller.get_logs_since(cursor)

    def pick_template_folder(self):
        try:
            if not webview.windows:
                return None
            result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
            if not result:
                return None
            if isinstance(result, (list, tuple)):
                return str(result[0]) if result else None
            return str(result)
        except Exception:
            return None
    
    def list_presets(self):
        return self.controller.list_presets()
    
    def save_preset(self, name):
        return self.controller.save_preset(name)
    
    def load_preset(self, name):
        return self.controller.load_preset(name)
    
    def delete_preset(self, name):
        return self.controller.delete_preset(name)
    
    def get_theme(self):
        return self.controller.get_theme()
    
    def set_theme(self, theme_id):
        return self.controller.set_theme(theme_id)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join([f'"{arg}"' for arg in sys.argv]), 
                None, 
                1
            )
            sys.exit(0)
        except Exception:
            return False
    return True

if __name__ == "__main__":
    try:
        if not is_admin():
            response = _prompt_yes_no(
                "Yönetici İzni Gerekli",
                "Oyun yönetici olarak çalışıyorsa bot da yönetici olarak çalışmalı.\n\n"
                "Yönetici olarak yeniden başlatmak ister misin?",
            )
            if response:
                request_admin()
            else:
                _info(
                    "Uyarı",
                    "Yönetici izni olmadan oyuna tıklama/tuşa basma çalışmayabilir!",
                )

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

        _ensure_web_assets()

        controller = BotController()
        api = WebApi(controller)

        web_path = os.path.join(_base_dir(), "web", "index.html")
        icon_path = _ensure_icon_ico()

        window_kwargs = {
            "title": "TritonX - Auto Bot",
            "url": web_path,
            "js_api": api,
            "width": 1100,
            "height": 720,
            "min_size": (920, 600),
            "background_color": "#0b0b0f",
            "confirm_close": True,
        }

        window = webview.create_window(**window_kwargs)

        def _on_webview_ready():
            if icon_path:
                _try_set_win32_window_icon(window, icon_path)

        webview.start(_on_webview_ready, gui="edgechromium", debug=False, http_server=True)
    except Exception as e:
        try:
            import traceback

            tb = traceback.format_exc()
            log_path = os.path.join(_base_dir(), "tritonx_gui_error.log")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(tb)
            except Exception:
                pass

            msg = (
                "GUI açılırken patladı.\n\n"
                f"Hata: {type(e).__name__}: {e}\n\n"
                f"Log: {log_path}\n\n"
                "Not: Windows'ta PyWebView için Microsoft Edge WebView2 Runtime lazım olabilir."
            )
            _win_message_box("TritonX - Auto Bot", msg, MB_OK | MB_ICONWARNING)
        except Exception:
            pass
