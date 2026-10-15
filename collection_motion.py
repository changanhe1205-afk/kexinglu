"""Short, cancellable collection interactions shared by food and movie cards."""
import asyncio
import ctypes
import os

import flet as ft


def motion_enabled():
    if os.name == "nt":
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            return bool(enabled.value)
    return True


class FlipCard(ft.Container):
    def __init__(self, front, back, width, height, *, face=False, on_face=None):
        self.front_face, self.back_face = front, back
        self.back_visible, self.busy = face, False
        self.on_face = on_face
        self.surface = ft.Container(content=back if face else front,
            width=width, height=height, rotate=0, scale=ft.Scale(scale_x=1,scale_y=1),
            animate_scale=ft.Animation(180,ft.AnimationCurve.EASE_IN_OUT),
            animate_rotation=ft.Animation(260,ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(300,ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(160,ft.AnimationCurve.EASE_OUT))
        super().__init__(width=width,height=height,data={"collection_card": True},
            content=ft.GestureDetector(content=self.surface, on_tap=self.turn,
                                      mouse_cursor=ft.MouseCursor.CLICK))

    def sync(self):
        try:
            self.update()
            return True
        except RuntimeError:
            return False

    async def turn(self, e=None):
        if self.busy:
            return
        self.busy = True
        try:
            animate = motion_enabled()
            if animate:
                self.surface.scale = ft.Scale(scale_x=.035,scale_y=1)
                self.surface.rotate = -.025
                if not self.sync(): return
                await asyncio.sleep(.18)
            self.back_visible = not self.back_visible
            self.surface.content = self.back_face if self.back_visible else self.front_face
            self.surface.scale = ft.Scale(scale_x=1,scale_y=1)
            self.surface.rotate = 0
            if self.on_face: self.on_face(self.back_visible)
            self.sync()
            if animate: await asyncio.sleep(.20)
        finally:
            self.busy = False


    async def celebrate(self, paper=False):
        if self.busy or not motion_enabled(): return
        self.busy = True
        seal = (self.surface.content.data or {}).get("stamp") if paper else None
        try:
            if seal is not None:
                seal.opacity = 0
                seal.scale = 1.3
            self.surface.rotate = -.065 if paper else -.04
            self.surface.scale = ft.Scale(scale_x=.92 if paper else .04,scale_y=.96)
            self.surface.offset = ft.Offset(0,-.035)
            if not self.sync(): return
            await asyncio.sleep(.18)
            self.surface.scale = ft.Scale(scale_x=1,scale_y=1)
            self.surface.rotate = 0
            self.surface.offset = ft.Offset(0,0)
            if seal is not None:
                seal.opacity = 1
                seal.scale = 1
            self.sync()
            await asyncio.sleep(.30)
        finally:
            self.busy = False


class CinemaCard(FlipCard):
    """A sleeve with a brief highlight sweep and pointer lift; never loops."""
    def __init__(self, front, back, width, height):
        super().__init__(front, back, width, height)
        self.on_hover = self.hover
        self.sheen = ft.Container(left=-width*.7,top=0,width=width*.65,height=height,
            opacity=0,offset=ft.Offset(0,0),
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT,end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#00FFFFFF","#28FFFFFF","#00FFFFFF"]),
            animate_offset=ft.Animation(720,ft.AnimationCurve.EASE_IN_OUT),
            animate_opacity=ft.Animation(180,ft.AnimationCurve.EASE_OUT))
        self.content.content = ft.Stack(width=width,height=height,clip_behavior=ft.ClipBehavior.NONE,
            controls=[self.surface,ft.Container(width=width,height=height,ignore_interactions=True,
                content=ft.Stack(width=width,height=height,clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                 controls=[self.sheen]))])

    def hover(self, e):
        if self.busy or not motion_enabled(): return
        entered = str(e.data).lower() == "true"
        self.surface.scale = 1.025 if entered else 1
        self.surface.rotate = -.018 if entered else 0
        self.surface.offset = ft.Offset(0,-.012 if entered else 0)
        self.sync()

    async def celebrate(self, paper=False):
        if self.busy or not motion_enabled(): return
        self.busy=True
        try:
            self.surface.scale=.94
            self.surface.rotate=-.045
            self.surface.offset=ft.Offset(0,.025)
            self.sheen.opacity=0
            self.sheen.offset=ft.Offset(0,0)
            if not self.sync():return
            await asyncio.sleep(.06)
            self.surface.scale=1
            self.surface.rotate=0
            self.surface.offset=ft.Offset(0,0)
            self.sheen.opacity=1
            self.sheen.offset=ft.Offset(2.7,0)
            self.sync()
            await asyncio.sleep(.74)
            self.sheen.opacity=0
            self.sync()
        finally:
            self.busy=False

