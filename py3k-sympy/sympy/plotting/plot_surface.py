from pyglet.gl import *
from .plot_mode_base import PlotModeBase
from sympy.core import S

class PlotSurface(PlotModeBase):

    default_rot_preset = 'perspective'

    def _on_calculate_verts(self):
        self.u_interval = self.intervals[0]
        self.u_set = list(self.u_interval.frange())
        self.v_interval = self.intervals[1]
        self.v_set = list(self.v_interval.frange())
        self.bounds = [ [S.Infinity,-S.Infinity,0],[S.Infinity,-S.Infinity,0],[S.Infinity,-S.Infinity,0] ]
        evaluate = self._get_evaluator()

        self._calculating_verts_pos = 0.0
        self._calculating_verts_len = float(self.u_interval.v_len*self.v_interval.v_len)

        verts = list()
        b = self.bounds
        for u in self.u_set:
            column = list()
            for v in self.v_set:
                try: _e = evaluate(u, v) # calculate vertex
                except: _e = None
                if _e is not None:  # update bounding box
                    for axis in range(3):
                        b[axis][0] = min([b[axis][0], _e[axis]])
                        b[axis][1] = max([b[axis][1], _e[axis]])
                column.append(_e)
                self._calculating_verts_pos += 1.0

            verts.append(column)
        for axis in range(3):
            b[axis][2] = b[axis][1] - b[axis][0]
            if b[axis][2] == 0.0: b[axis][2] = 1.0

        self.verts = verts
        self.push_wireframe(self.draw_verts(False, False))
        self.push_solid(self.draw_verts(False, True))

    def _on_calculate_cverts(self):
        if not self.verts or not self.color: return
        def set_work_len(n): self._calculating_cverts_len = float(n)
        def inc_work_pos(): self._calculating_cverts_pos += 1.0
        set_work_len(1); self._calculating_cverts_pos = 0
        self.cverts = self.color.apply_to_surface(self.verts, self.u_set, self.v_set,
                                                  set_len=set_work_len, inc_pos=inc_work_pos)
        self.push_solid(self.draw_verts(True, True))

    def calculate_one_cvert(self, u, v):
        vert = self.verts[u][v]
        return self.color(vert[0], vert[1], vert[2],
                          self.u_set[u], self.v_set[v])

    def draw_verts(self, use_cverts, use_solid_color):
        def f():
            for u in range( 1, len(self.u_set) ):
                glBegin(GL_QUAD_STRIP)
                for v in range( len(self.v_set) ):
                    pa = self.verts[u-1][v]
                    pb = self.verts[u][v]
                    if pa is None or pb is None:
                        glEnd()
                        glBegin(GL_QUAD_STRIP)
                        continue
                    if use_cverts:
                        ca = self.cverts[u-1][v]
                        cb = self.cverts[u][v]
                        if ca is None:
                            ca = (0,0,0)
                        if cb is None:
                            cb = (0,0,0)
                    else:
                        if use_solid_color: ca = cb = self.default_solid_color
                        else: ca = cb = self.default_wireframe_color
                    glColor3f(*ca)
                    glVertex3f(*pa)
                    glColor3f(*cb)
                    glVertex3f(*pb)
                glEnd()
        return f
