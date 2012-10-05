# Copyright (C) Peter Hollobon 2005
# 

import pyHook
import win32api
import ctypes
from ctypes import wintypes
import win32gui
import win32con

byref = ctypes.byref
user32 = ctypes.windll.user32

_leftMouseButtonDown = False
_rightMouseButtonDown = False
_altKeyDown = False
_moving = False
_windowHandle = 0
_no_resize_window_titles = ['Extension Manager']

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]

class RECT(ctypes.Structure):
    _fields_ = ("a", POINT), ("b", POINT)
      
class TITLEBARINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint), 
        ("rcTitleBar", RECT), 
        ("rgstate", ctypes.c_uint * 6)
    ]

class WINDOWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint), 
        ("rcWindow", RECT),
        ("rcClient", RECT),
        ("dwStyle", ctypes.c_uint),
        ("dwExStyle", ctypes.c_uint),
        ("dwWindowStatus", ctypes.c_uint),
        ("cxWindowBorders", ctypes.c_uint),
        ("cyWindowBorders", ctypes.c_uint),
        ("atomWindowType", ctypes.c_uint),
        ("wCreatorVersion", ctypes.c_ushort),
    ]

def get_titlebar_size(windowHandle):
    tbi = TITLEBARINFO()
    tbi.cbSize = ctypes.sizeof(TITLEBARINFO)
    user32.GetTitleBarInfo(windowHandle, byref(tbi))
    win32api.FormatMessage(win32api.GetLastError())

    return (tbi.rcTitleBar.b.x - tbi.rcTitleBar.a.x, tbi.rcTitleBar.b.y - tbi.rcTitleBar.a.y)

def get_border_size(windowHandle):
    wi = WINDOWINFO()
    wi.cbSize = ctypes.sizeof(WINDOWINFO)
    user32.GetWindowInfo(windowHandle, byref(wi))

    return wi.cxWindowBorders, wi.cyWindowBorders
    #return wi.rcClient.a.x - wi.r

def is_movable_window(windowHandle):
    return  win32gui.IsWindowVisible(windowHandle) and \
            win32gui.GetWindowText(windowHandle) != ""

class mover(object):    
  def __init__(self):
    self.hm = pyHook.HookManager()

    # register two callbacks
    self.hm.MouseAllButtons = self.OnMouseClick
    self.hm.KeyDown = self.OnKeyboardEvent
    self.hm.KeyUp = self.OnKeyboardEvent
#    self.hm.KeyAll = self.OnKeyboardAll

    # hook into the mouse and keyboard events
    self.hm.HookMouse()
    self.hm.HookKeyboard()

  def OnMouseClick(self, event):
    global _leftMouseButtonDown, _rightMouseButtonDown, _windowHandle, _clientPos, _xrp, _yrp, _originalPos, _windowSize, _windowPos

    if event.MessageName.startswith("mouse") and event.MessageName.endswith("down"):
        if event.MessageName == 'mouse left down':
            _leftMouseButtonDown = True
        if event.MessageName == 'mouse right down':
            _rightMouseButtonDown = True
            
        if _altKeyDown:
            windowHandle = win32gui.WindowFromPoint(event.Position)

            #wp = win32gui.GetWindowPlacement(windowHandle)

            #while not is_movable_window(windowHandle) and win32gui.GetParent(windowHandle):
            while win32gui.GetParent(windowHandle):
                try:
                    windowHandle = win32gui.GetParent(windowHandle)
                except:
                    break
                    
            _windowHandle = windowHandle
            _originalPos = event.Position
            _clientPos = win32gui.ScreenToClient(_windowHandle, _originalPos)
            windowRect = win32gui.GetWindowRect(_windowHandle)
            _windowSize = (windowRect[2] - windowRect[0], windowRect[3] - windowRect[1])
            _windowPos = windowRect[0:2]

            _xrp =  _clientPos[0] / (_windowSize[0] / 2)
            _yrp =  _clientPos[1] / (_windowSize[1] / 2)
            
            self.hm.MouseMove = self.OnMouseMove

            return False

    if event.MessageName == 'mouse left up':
        _leftMouseButtonDown = False
        _windowHandle = 0
        self.hm.MouseMove = None
        if _altKeyDown:
            return False

    if event.MessageName == 'mouse right up':
        _rightMouseButtonDown = False
        _windowHandle = 0
        self.hm.MouseMove = None
        if _altKeyDown:
            return False

    return True

  def OnMouseMove(self, event):
    if _altKeyDown and _leftMouseButtonDown:
        tbWidth, tbHeight = get_titlebar_size(_windowHandle)
        xBorder, yBorder = get_border_size(_windowHandle)
        
        win32gui.SetWindowPos(
            _windowHandle,
            0,
            event.Position[0] - _clientPos[0] - xBorder,
            event.Position[1] - _clientPos[1] - (tbHeight + yBorder),
            0,
            0,
            win32con.SWP_NOSIZE)
    
    elif _altKeyDown and _rightMouseButtonDown \
    and win32gui.GetWindowText(_windowHandle) not in _no_resize_window_titles:
        cx = event.Position[0] - _originalPos[0] 
        cy = event.Position[1] - _originalPos[1] 

        if _xrp == 0:
            px = _windowPos[0] + cx
            sx = _windowSize[0] - cx
        else:
            px = _windowPos[0]
            sx = _windowSize[0] + cx

        if _yrp == 0:
            py = _windowPos[1] + cy
            sy = _windowSize[1] - cy
        else:
            py = _windowPos[1]
            sy = _windowSize[1] + cy

        win32gui.SetWindowPos(_windowHandle, 0, px, py, sx, sy, 0)

    win32api.SetCursorPos(event.Position)

    return False

  def OnKeyboardAll(self, event):
    print "%x - %s" % (event.KeyID, chr(event.Ascii))
    return True

  def OnKeyboardEvent(self, event):
    if event.KeyID == 164:
        global _altKeyDown

        if _altKeyDown and (_leftMouseButtonDown or _rightMouseButtonDown):
            _altKeyDown = event.Transition == 0
            return False

        _altKeyDown = event.Transition == 0
    
    # return True to pass the event to other handlers
    # return False to stop the event from propagating    
    return True

try:
    x = mover()
    msg = wintypes.MSG()
    while user32.GetMessageA(byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(byref(msg))
        user32.DispatchMessageA(byref(msg))

finally:
    pass
